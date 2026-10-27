"""`send_for_signature` decide y escribe sobre el contrato bloqueado (ronda 28).

Era la única acción del ciclo de vida del contrato que leía con `get_object()` sin bloqueo y hacía
un `save()` completo: un `cancel` o una firma confirmados entre la lectura y el guardado se
borraban (el contrato cancelado volvía a `pending_signature` con un enlace nuevo que el titular
anónimo podía firmar). Ahora se valida la entrada (incluido `days_valid`, 1..30), se bloquea el
contrato, sólo se envían contratos en borrador o pendientes de firma, se escribe sólo el estado y
se crea el token en la misma transacción; el email/WhatsApp sale después de confirmarla.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"

TERMINAL_MSG = ("Este contrato está cancelado o completado y ya no se puede firmar ni activar; "
                "genere uno nuevo.")
ARCHIVED_MSG = "Un contrato archivado no se puede enviar a firma."
NOT_SENDABLE_MSG = "Solo se pueden enviar a firma contratos en borrador o pendientes de firma."
DAYS_MSG = "days_valid debe ser un número entero de días entre 1 y 30."
_PNG_1X1 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


# `policy` (política permisiva del tenant) viene de apps/loans/tests/conftest.py.


@pytest.fixture
def officer_client(user_factory):
    return _client(user_factory(role="loan_officer"))


@pytest.fixture
def manager_client(user_factory):
    return _client(user_factory(role="manager", first_name="Gerente", last_name="Rival"))


def _make_contract(loan_factory, **fields):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"),
                        interest_type="flat", term_months=4)
    return Contract.objects.create(loan=loan, content="Tasa 1.50% mensual", **fields)


@pytest.fixture
def draft(policy, loan_factory):
    return _make_contract(loan_factory, status="draft")


@pytest.fixture
def pending(policy, loan_factory):
    return _make_contract(loan_factory, status="pending_signature")


def _send(client, contract, **data):
    payload = {"email": "cliente@crediflux.test", "send_via": "email"}
    payload.update(data)
    return client.post(f"/api/loans/contracts/{contract.pk}/send_for_signature/", payload, format="json")


def _tokens(contract):
    from apps.loans.models_contracts import ContractSignatureToken

    return list(ContractSignatureToken.objects.filter(contract_id=contract.pk).order_by("created_at"))


def _existing_token(contract):
    from apps.loans.models_contracts import ContractSignatureToken

    return ContractSignatureToken.objects.create(
        contract=contract, token=f"tok-{contract.pk.hex[:16]}", email="cliente@crediflux.test",
        expires_at=timezone.now() + timedelta(days=7),
    )


def _public_sign(token):
    return APIClient(HTTP_HOST=HOST).post(
        f"/api/loans/public/contracts/{token.token}/sign/", {"signature_data": _PNG_1X1}, format="json"
    )


def _between_read_and_lock(monkeypatch, change):
    """Otra petición se confirma justo después de que send_for_signature lea con get_object()."""
    from apps.loans.views import ContractViewSet

    original = ContractViewSet.get_object
    fired = []

    def _get_object(self):
        obj = original(self)
        if not fired and self.action == "send_for_signature":
            fired.append(True)
            change()
        return obj

    monkeypatch.setattr(ContractViewSet, "get_object", _get_object)


# (a) carrera: cancelación o firma confirmadas entre la lectura y la escritura

def test_cancel_confirmed_meanwhile_is_not_revived(
    officer_client, manager_client, pending, monkeypatch, mailoutbox
):
    old = _existing_token(pending)

    def _cancel():
        response = manager_client.post(f"/api/loans/contracts/{pending.pk}/cancel/", {}, format="json")
        assert response.status_code == 200, response.content

    _between_read_and_lock(monkeypatch, _cancel)

    response = _send(officer_client, pending)

    assert response.status_code == 400, response.content
    assert response.json() == {"error": TERMINAL_MSG}
    pending.refresh_from_db()
    assert pending.status == "cancelled"
    assert "Cancelado el" in pending.notes and "Gerente Rival" in pending.notes
    assert [t.pk for t in _tokens(pending)] == [old.pk]
    assert mailoutbox == []
    for token in _tokens(pending):
        assert _public_sign(token).status_code == 410
    pending.refresh_from_db()
    assert pending.customer_signed_at is None
    assert pending.status == "cancelled"


def test_officer_signature_confirmed_meanwhile_is_kept(
    officer_client, manager_client, draft, monkeypatch
):
    def _sign_officer():
        response = manager_client.post(
            f"/api/loans/contracts/{draft.pk}/sign_officer/", {"signature_data": _PNG_1X1}, format="json"
        )
        assert response.status_code == 200, response.content

    _between_read_and_lock(monkeypatch, _sign_officer)

    response = _send(officer_client, draft)

    assert response.status_code == 200, response.content
    draft.refresh_from_db()
    assert draft.officer_signed_at is not None
    assert draft.officer_signature
    assert draft.status == "pending_signature"
    assert len(_tokens(draft)) == 1


def test_contract_deleted_meanwhile_is_404(officer_client, draft, monkeypatch, mailoutbox):
    from apps.loans.models_contracts import Contract

    _between_read_and_lock(monkeypatch, lambda: Contract.objects.filter(pk=draft.pk).delete())

    response = _send(officer_client, draft)

    assert response.status_code == 404, response.content
    assert not Contract.objects.filter(pk=draft.pk).exists()
    assert _tokens(draft) == []
    assert mailoutbox == []


# (b) sin carrera: qué contratos se pueden enviar

@pytest.mark.parametrize("fields,message", [
    ({"status": "cancelled"}, TERMINAL_MSG),
    ({"status": "completed"}, TERMINAL_MSG),
    ({"status": "pending_signature", "is_archived": True}, ARCHIVED_MSG),
    ({"status": "signed"}, NOT_SENDABLE_MSG),
    ({"status": "active"}, NOT_SENDABLE_MSG),
])
def test_contracts_that_cannot_be_sent_are_refused(
    officer_client, policy, loan_factory, fields, message, mailoutbox
):
    contract = _make_contract(loan_factory, **fields)

    response = _send(officer_client, contract)

    assert response.status_code == 400, response.content
    assert response.json() == {"error": message}
    contract.refresh_from_db()
    assert contract.status == fields["status"]
    assert _tokens(contract) == []
    assert mailoutbox == []


def test_draft_is_sent_and_becomes_pending_signature(officer_client, draft, mailoutbox):
    with CaptureQueriesContext(connection) as ctx:
        response = _send(officer_client, draft)

    assert response.status_code == 200, response.content
    draft.refresh_from_db()
    assert draft.status == "pending_signature"
    tokens = _tokens(draft)
    assert len(tokens) == 1
    assert response.json()["token_id"] == str(tokens[0].pk)
    assert len(mailoutbox) == 1

    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    sqls = [q["sql"] for q in ctx.captured_queries]
    table = Contract._meta.db_table
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert locks and updates and locks[0] < updates[0]
    # Sólo se escribe el estado: el resto de columnas no se reescribe con la copia leída.
    assert all('"notes"' not in sqls[i] and '"officer_signed_at"' not in sqls[i] for i in updates)
    # El préstamo no se bloquea (orden préstamo → contrato).
    loan_table = Loan._meta.db_table
    assert not [sql for sql in sqls if f'FROM "{loan_table}"' in sql and "FOR UPDATE" in sql]


def test_pending_signature_can_be_resent(officer_client, pending, mailoutbox):
    first = _existing_token(pending)

    response = _send(officer_client, pending)

    assert response.status_code == 200, response.content
    pending.refresh_from_db()
    assert pending.status == "pending_signature"
    tokens = _tokens(pending)
    assert len(tokens) == 2 and first.pk in [t.pk for t in tokens]
    assert len(mailoutbox) == 1


# (c) days_valid

@pytest.mark.parametrize("days_valid", ["abc", 0, -1, 31, "", None, 7.5, True])
def test_invalid_days_valid_is_400(officer_client, draft, days_valid, mailoutbox):
    response = _send(officer_client, draft, days_valid=days_valid)

    assert response.status_code == 400, response.content
    assert response.json() == {"error": DAYS_MSG}
    draft.refresh_from_db()
    assert draft.status == "draft"
    assert _tokens(draft) == []
    assert mailoutbox == []


@pytest.mark.parametrize("days_valid,expected_days", [(30, 30), ("30", 30), (1, 1), ("absent", 7)])
def test_valid_days_valid_sets_the_expiration(officer_client, draft, days_valid, expected_days):
    before = timezone.now()
    if days_valid == "absent":
        response = _send(officer_client, draft)
    else:
        response = _send(officer_client, draft, days_valid=days_valid)
    after = timezone.now()

    assert response.status_code == 200, response.content
    expires_at = parse_datetime(response.json()["expires_at"])
    assert before + timedelta(days=expected_days) <= expires_at <= after + timedelta(days=expected_days)
    assert _tokens(draft)[0].expires_at == expires_at


# (d) regresiones: rol y validación de medios

def test_user_without_manage_loans_gets_403(user_factory, draft, mailoutbox):
    response = _send(_client(user_factory(role="viewer")), draft)

    assert response.status_code == 403, response.content
    draft.refresh_from_db()
    assert draft.status == "draft"
    assert _tokens(draft) == []
    assert mailoutbox == []


def test_missing_email_keeps_its_message(officer_client, draft):
    response = officer_client.post(
        f"/api/loans/contracts/{draft.pk}/send_for_signature/", {"send_via": "email"}, format="json"
    )

    assert response.status_code == 400, response.content
    assert response.json() == {"error": "Se requiere un email"}
    assert _tokens(draft) == []
