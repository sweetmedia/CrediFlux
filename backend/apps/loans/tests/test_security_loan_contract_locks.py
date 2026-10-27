"""Borrar un préstamo vs firmar su contrato, y un solo contrato abierto por préstamo (ronda 31).

Parte A. Borrar un préstamo bloqueaba sólo el préstamo y dejaba al colector de Django borrar los
hijos antes que el padre: préstamo → token (DELETE) → contrato (DELETE). La firma pública bloquea
contrato → token, así que un borrado y una firma simultáneos se interbloqueaban (500 por
`deadlock detected`). Ahora los tres caminos de borrado (API, admin individual y acción masiva)
bloquean, después del préstamo y antes del primer DELETE, sus contratos en orden de pk
(préstamo → contrato → token). La firma que esperaba encuentra el contrato borrado: 404, no 500.

Parte B. «Como mucho un contrato abierto (active, signed, pending_signature) por préstamo» sólo se
comprobaba al crear y sin bloqueo. Ahora todo camino que crea un contrato o lo pasa de no abierto
a abierto bloquea primero el préstamo y decide sobre ese estado (excluyendo el propio contrato):
el alta de la API y del admin, `send_for_signature` y `sign_customer`/`sign_officer` de un borrador.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
OPEN_MSG = "Este préstamo ya tiene un contrato activo"
INVALID_LINK = {"error": "Enlace de firma inválido"}
_PNG_1X1 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


# `policy` (política permisiva del tenant) viene de apps/loans/tests/conftest.py.

def _api(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def officer_client(user_factory):
    return _api(user_factory(role="loan_officer"))


@pytest.fixture
def admin_client(user_factory):
    client = Client(HTTP_HOST=HOST)
    client.force_login(user_factory(role="admin", is_staff=True, is_superuser=True))
    return client


@pytest.fixture
def template():
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(name="Base r31", content="Préstamo {{loan_number}}", is_active=True)


@pytest.fixture
def loan(policy, loan_factory):
    return loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"),
                        interest_type="flat", term_months=4)


def _contract(loan, **fields):
    from apps.loans.models_contracts import Contract

    data = {"content": "texto", "status": "draft"}
    data.update(fields)
    return Contract.objects.create(loan=loan, **data)


def _token(contract, suffix=""):
    from apps.loans.models_contracts import ContractSignatureToken

    return ContractSignatureToken.objects.create(
        contract=contract, token=f"r31-{contract.pk.hex[:16]}{suffix}", email="cliente@crediflux.test",
        expires_at=timezone.now() + timedelta(days=7),
    )


def _tables():
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    return Loan._meta.db_table, Contract._meta.db_table


def _locks(sqls, table):
    return [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]


def _statements(sqls):
    """Resumen legible (para el mensaje de fallo) de bloqueos y borrados, en orden."""
    return [sql[:90] for sql in sqls if "FOR UPDATE" in sql or sql.startswith("DELETE")]


# ---------------------------------------------------------------------------------------------
# Parte A — los borrados de préstamos bloquean sus contratos (por pk) antes del primer DELETE
# ---------------------------------------------------------------------------------------------

def _delete_via(op, officer_client, admin_client, loan):
    if op == "api":
        return officer_client.delete(f"/api/loans/{loan.pk}/")
    if op == "admin":
        return admin_client.post(reverse("admin:loans_loan_delete", args=[loan.pk]), {"post": "yes"})
    return admin_client.post(reverse("admin:loans_loan_changelist"), {
        "action": "delete_selected", "_selected_action": [str(loan.pk)], "post": "yes",
    })


@pytest.mark.parametrize("op", ["api", "admin", "admin_bulk"])
def test_loan_delete_locks_loan_then_contracts_by_pk_before_deleting(op, officer_client, admin_client, loan):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract, ContractSignatureToken

    first = _contract(loan, status="pending_signature")
    second = _contract(loan, status="cancelled")
    _token(first)
    _token(second)

    with CaptureQueriesContext(connection) as ctx:
        response = _delete_via(op, officer_client, admin_client, loan)

    assert response.status_code in (204, 302), response.content
    assert not Loan.objects.filter(pk=loan.pk).exists()
    assert not Contract.objects.filter(pk__in=[first.pk, second.pk]).exists()
    assert not ContractSignatureToken.objects.filter(contract_id__in=[first.pk, second.pk]).exists()

    loan_table, contract_table = _tables()
    sqls = [q["sql"] for q in ctx.captured_queries]
    trace = _statements(sqls)
    loan_locks = _locks(sqls, loan_table)
    contract_locks = _locks(sqls, contract_table)
    deletes = [i for i, sql in enumerate(sqls) if sql.startswith("DELETE")]
    assert loan_locks and deletes, trace
    assert contract_locks, f"el borrado no bloquea los contratos: {trace}"
    # Orden del módulo: préstamo → contrato → (token, DELETE del colector).
    assert loan_locks[0] < contract_locks[0] < deletes[0], trace
    lock_sql = sqls[contract_locks[0]]
    assert f'FOR UPDATE OF "{contract_table}"' in lock_sql
    assert f'ORDER BY "{contract_table}"."id" ASC' in lock_sql


def _delete_loan_now(loan):
    from apps.loans.models import Loan

    Loan.objects.filter(pk=loan.pk).delete()


def test_public_sign_of_a_contract_deleted_with_its_loan_is_a_uniform_404(api_client, loan, monkeypatch):
    from apps.loans.models_contracts import Contract

    contract = _contract(loan, status="pending_signature")
    token = _token(contract)
    original = Contract.objects.select_for_update
    fired = []

    def _select_for_update(*args, **kwargs):
        # El borrado del préstamo se confirma mientras la firma espera el bloqueo del contrato.
        if not fired:
            fired.append(True)
            _delete_loan_now(loan)
        return original(*args, **kwargs)

    monkeypatch.setattr(Contract.objects, "select_for_update", _select_for_update)

    response = APIClient(HTTP_HOST=HOST).post(
        f"/api/loans/public/contracts/{token.token}/sign/", {"signature_data": _PNG_1X1}, format="json"
    )

    assert fired
    assert response.status_code == 404
    assert response.json() == INVALID_LINK


def _delete_after_get_object(monkeypatch, action, loan):
    from apps.loans.views import ContractViewSet

    original = ContractViewSet.get_object
    fired = []

    def _get_object(self):
        obj = original(self)
        if not fired and self.action == action:
            fired.append(True)
            _delete_loan_now(loan)
        return obj

    monkeypatch.setattr(ContractViewSet, "get_object", _get_object)
    return fired


@pytest.mark.parametrize("action,status", [
    ("sign_customer", "draft"),
    ("sign_officer", "pending_signature"),
    ("send_for_signature", "draft"),
    ("send_for_signature", "pending_signature"),
])
def test_actions_on_a_contract_deleted_with_its_loan_are_a_clean_404(
    officer_client, loan, monkeypatch, mailoutbox, action, status
):
    contract = _contract(loan, status=status)
    fired = _delete_after_get_object(monkeypatch, action, loan)

    response = officer_client.post(
        f"/api/loans/contracts/{contract.pk}/{action}/",
        {"signature_data": _PNG_1X1, "email": "cliente@crediflux.test", "send_via": "email"},
        format="json",
    )

    assert fired
    assert response.status_code == 404, response.content
    assert len(mailoutbox) == 0


# ---------------------------------------------------------------------------------------------
# Parte B — un solo contrato abierto por préstamo, decidido con el préstamo bloqueado
# ---------------------------------------------------------------------------------------------

def test_api_create_rechecks_open_contract_under_the_loan_lock(officer_client, loan, template, monkeypatch):
    from apps.loans.models_contracts import Contract
    from apps.loans.serializers import ContractCreateSerializer

    other = _contract(loan, status="draft")
    original = ContractCreateSerializer.validate_loan

    def _validate_loan(self, value):
        value = original(self, value)
        # Otra petición pasa el otro contrato a pending_signature tras la validación sin bloqueo.
        Contract.objects.filter(pk=other.pk).update(status="pending_signature")
        return value

    monkeypatch.setattr(ContractCreateSerializer, "validate_loan", _validate_loan)

    response = officer_client.post(
        "/api/loans/contracts/", {"loan": str(loan.pk), "template": str(template.pk)}, format="json"
    )

    assert response.status_code == 400, response.content
    assert response.json() == {"loan": [OPEN_MSG]}
    assert list(Contract.objects.filter(loan=loan).values_list("pk", flat=True)) == [other.pk]


def test_api_create_locks_the_loan_before_inserting(officer_client, loan, template):
    from apps.loans.models_contracts import Contract

    with CaptureQueriesContext(connection) as ctx:
        response = officer_client.post(
            "/api/loans/contracts/", {"loan": str(loan.pk), "template": str(template.pk)}, format="json"
        )

    assert response.status_code == 201, response.content
    assert Contract.objects.filter(loan=loan).count() == 1
    loan_table, contract_table = _tables()
    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks = _locks(sqls, loan_table)
    inserts = [i for i, sql in enumerate(sqls) if sql.startswith(f'INSERT INTO "{contract_table}"')]
    assert loan_locks and inserts
    assert loan_locks[0] < inserts[0]
    assert f'FOR UPDATE OF "{loan_table}"' in sqls[loan_locks[0]]


def _admin_add(client, loan, template):
    return client.post(reverse("admin:loans_contract_add"), {
        "loan": str(loan.pk), "template": str(template.pk), "special_terms": "", "notes": "",
        "witness_name": "", "witness_id": "", "_save": "Guardar",
    })


def test_admin_add_rechecks_open_contract_under_the_loan_lock(admin_client, loan, template, monkeypatch):
    from apps.loans.admin import ContractAdminForm
    from apps.loans.models_contracts import Contract

    other = _contract(loan, status="draft")
    original = ContractAdminForm.clean_loan

    def _clean_loan(self):
        value = original(self)
        Contract.objects.filter(pk=other.pk).update(status="pending_signature")
        return value

    monkeypatch.setattr(ContractAdminForm, "clean_loan", _clean_loan)

    response = _admin_add(admin_client, loan, template)

    assert response.status_code == 403
    assert list(Contract.objects.filter(loan=loan).values_list("pk", flat=True)) == [other.pk]


def test_admin_add_locks_the_loan_before_inserting(admin_client, loan, template):
    from apps.loans.models_contracts import Contract

    with CaptureQueriesContext(connection) as ctx:
        response = _admin_add(admin_client, loan, template)

    assert response.status_code == 302, response.content
    assert Contract.objects.filter(loan=loan).count() == 1
    loan_table, contract_table = _tables()
    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks = _locks(sqls, loan_table)
    inserts = [i for i, sql in enumerate(sqls) if sql.startswith(f'INSERT INTO "{contract_table}"')]
    assert loan_locks and inserts
    assert loan_locks[0] < inserts[0]


def _act(client, contract, action):
    return client.post(
        f"/api/loans/contracts/{contract.pk}/{action}/",
        {"signature_data": _PNG_1X1, "email": "cliente@crediflux.test", "send_via": "email"},
        format="json",
    )


@pytest.mark.parametrize("action", ["send_for_signature", "sign_customer", "sign_officer"])
@pytest.mark.parametrize("open_status", ["pending_signature", "signed", "active"])
def test_draft_does_not_open_while_another_contract_is_open(
    officer_client, loan, mailoutbox, action, open_status
):
    from apps.loans.models_contracts import ContractSignatureToken

    _contract(loan, status=open_status)
    draft = _contract(loan, status="draft")

    response = _act(officer_client, draft, action)

    assert response.status_code == 400, response.content
    assert response.json() == {"error": OPEN_MSG}
    draft.refresh_from_db()
    assert draft.status == "draft"
    assert draft.customer_signed_at is None and draft.officer_signed_at is None
    assert not ContractSignatureToken.objects.filter(contract=draft).exists()
    assert len(mailoutbox) == 0


@pytest.mark.parametrize("action", ["send_for_signature", "sign_customer", "sign_officer"])
def test_draft_opens_when_the_other_contracts_are_closed(officer_client, loan, mailoutbox, action):
    _contract(loan, status="cancelled")
    draft = _contract(loan, status="draft")

    response = _act(officer_client, draft, action)

    assert response.status_code == 200, response.content
    draft.refresh_from_db()
    assert draft.status == "pending_signature"


def test_draft_rechecks_a_contract_opened_after_get_object(officer_client, loan, monkeypatch):
    from apps.loans.models_contracts import Contract
    from apps.loans.views import ContractViewSet

    other = _contract(loan, status="draft")
    draft = _contract(loan, status="draft")
    original = ContractViewSet.get_object

    def _get_object(self):
        obj = original(self)
        Contract.objects.filter(pk=other.pk).update(status="pending_signature")
        return obj

    monkeypatch.setattr(ContractViewSet, "get_object", _get_object)

    response = _act(officer_client, draft, "sign_customer")

    assert response.status_code == 400, response.content
    draft.refresh_from_db()
    assert draft.status == "draft" and draft.customer_signed_at is None


@pytest.mark.parametrize("action,status", [
    ("send_for_signature", "draft"),
    ("send_for_signature", "pending_signature"),
    ("sign_customer", "draft"),
    ("sign_officer", "pending_signature"),
])
def test_opening_actions_lock_the_loan_before_the_contract(officer_client, loan, mailoutbox, action, status):
    contract = _contract(loan, status=status)

    with CaptureQueriesContext(connection) as ctx:
        response = _act(officer_client, contract, action)

    assert response.status_code == 200, response.content
    loan_table, contract_table = _tables()
    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks = _locks(sqls, loan_table)
    contract_locks = _locks(sqls, contract_table)
    assert loan_locks and contract_locks, _statements(sqls)
    assert loan_locks[0] < contract_locks[0]
    assert f'FOR UPDATE OF "{loan_table}"' in sqls[loan_locks[0]]


def test_resending_a_pending_contract_still_works(officer_client, loan, mailoutbox):
    """Reenviar uno ya abierto (pending → pending) no pasa por la regla: no cambia la cuenta.

    La regla sólo se consulta en el paso de no abierto a abierto, así que el propio contrato nunca
    se cuenta (por eso loan_has_open_contract no tiene parámetro `exclude`, ronda 31.1).
    """
    from apps.loans.models_contracts import ContractSignatureToken

    pending = _contract(loan, status="pending_signature")
    _contract(loan, status="cancelled")

    response = _act(officer_client, pending, "send_for_signature")

    assert response.status_code == 200, response.content
    pending.refresh_from_db()
    assert pending.status == "pending_signature"
    assert ContractSignatureToken.objects.filter(contract=pending).count() == 1
    assert len(mailoutbox) == 1


def test_normal_flow_create_sign_activate_still_works(officer_client, loan, template):
    from apps.loans.models_contracts import Contract

    response = officer_client.post(
        "/api/loans/contracts/", {"loan": str(loan.pk), "template": str(template.pk)}, format="json"
    )
    assert response.status_code == 201, response.content
    contract = Contract.objects.get(loan=loan)
    assert contract.status == "draft"

    assert _act(officer_client, contract, "sign_customer").status_code == 200
    contract.refresh_from_db()
    assert contract.status == "pending_signature"
    assert _act(officer_client, contract, "sign_officer").status_code == 200
    contract.refresh_from_db()
    assert contract.status == "signed"
    assert _act(officer_client, contract, "activate").status_code == 200
    contract.refresh_from_db()
    assert contract.status == "active"

    # Con uno abierto, otra alta se rechaza (la regla sin bloqueo sigue dando el 400 de UX).
    again = officer_client.post(
        "/api/loans/contracts/", {"loan": str(loan.pk), "template": str(template.pk)}, format="json"
    )
    assert again.status_code == 400
    assert again.json() == {"loan": [OPEN_MSG]}


# ---------------------------------------------------------------------------------------------
# Ronda 31.1
# ---------------------------------------------------------------------------------------------

def test_admin_bulk_delete_locks_the_loans_in_pk_order(admin_client, loan_factory, policy):
    from apps.loans.models import Loan

    loans = [loan_factory(status="pending", disbursement_date=None) for _ in range(2)]

    with CaptureQueriesContext(connection) as ctx:
        response = admin_client.post(reverse("admin:loans_loan_changelist"), {
            "action": "delete_selected", "_selected_action": [str(x.pk) for x in loans], "post": "yes",
        })

    assert response.status_code == 302
    assert not Loan.objects.filter(pk__in=[x.pk for x in loans]).exists()
    loan_table, _ = _tables()
    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks = _locks(sqls, loan_table)
    assert loan_locks, _statements(sqls)
    assert f'ORDER BY "{loan_table}"."id" ASC' in sqls[loan_locks[0]]


ACTIVATE_STATUS_MSG = "Solo se activan contratos pendientes de firma o firmados."


@pytest.mark.parametrize("current", ["draft", "active"])
def test_activate_only_moves_pending_or_signed_contracts(officer_client, loan, current):
    # Estado forzado en la BD: hoy ninguna vía deja un borrador con ambas firmas.
    now = timezone.now()
    contract = _contract(loan, status=current, customer_signed_at=now, officer_signed_at=now)

    response = _act(officer_client, contract, "activate")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": ACTIVATE_STATUS_MSG}
    contract.refresh_from_db()
    assert contract.status == current


@pytest.mark.parametrize("module", ["views", "admin"])
def test_create_for_a_loan_deleted_before_the_lock_is_a_clean_404(
    officer_client, admin_client, loan, template, monkeypatch, module
):
    import importlib

    from apps.loans import locks
    from apps.loans.models_contracts import Contract

    target = importlib.import_module(f"apps.loans.{module}")
    fired = []

    def _lock_loan(pk):
        # Otra petición borra el préstamo entre la validación y el bloqueo.
        if not fired:
            fired.append(True)
            _delete_loan_now(loan)
        return locks.lock_loan(pk)

    monkeypatch.setattr(target, "lock_loan", _lock_loan)

    if module == "views":
        response = officer_client.post(
            "/api/loans/contracts/", {"loan": str(loan.pk), "template": str(template.pk)}, format="json"
        )
    else:
        response = _admin_add(admin_client, loan, template)

    assert fired
    assert response.status_code == 404
    assert not Contract.objects.filter(loan_id=loan.pk).exists()
