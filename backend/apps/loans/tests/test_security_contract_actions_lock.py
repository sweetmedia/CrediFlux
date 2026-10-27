"""Las acciones del contrato y la firma pública bloquean el contrato antes de decidir (ronda 12).

`get_object()` sigue dando el 404/403; luego, dentro de una transacción, el contrato se vuelve a
leer con SELECT ... FOR UPDATE y todas las comprobaciones y escrituras se hacen sobre la fila
bloqueada. Así un `cancel` que esperó al desembolso ve el préstamo ya activo, y un `sign_*` o un
`activate` no reviven un contrato cancelado mientras tanto. Además, el contrato de un préstamo ya
desembolsado no se puede cancelar. La firma pública bloquea el contrato y el token antes de
comprobar el enlace, para que el mismo enlace no se use dos veces.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"

DISBURSED_MSG = "No se puede cancelar el contrato de un préstamo ya desembolsado."
TERMINAL_MSG = ("Este contrato está cancelado o completado y ya no se puede firmar ni activar; "
                "genere uno nuevo.")
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
def pending_signed(policy, loan_factory):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"),
                        interest_type="flat", term_months=4)
    contract = Contract.objects.create(
        loan=loan, content="Tasa 1.50% mensual", status="pending_signature",
        customer_signed_at=timezone.now(),
    )
    return loan, contract


def _contract_url(contract, action):
    return f"/api/loans/contracts/{contract.pk}/{action}/"


def _post(client, contract, action):
    return client.post(_contract_url(contract, action), {}, format="json")


def _assert_contract_locked_before_update(ctx, extra_locked_tables=()):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    table = Contract._meta.db_table
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert locks, "la acción no bloquea el contrato"
    assert updates
    assert locks[0] < updates[0]
    # El bloqueo va dentro de la transacción de la acción (en pytest, un SAVEPOINT).
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    opened_before = [i for i in savepoints if i < locks[0]]
    assert opened_before, "el bloqueo no va dentro de una transacción"
    # Y ese savepoint sigue abierto hasta pasada la escritura: no hay RELEASE entre medias.
    releases = [i for i, sql in enumerate(sqls) if sql.startswith("RELEASE SAVEPOINT")]
    assert not [i for i in releases if opened_before[-1] < i < updates[0]], (
        "la transacción se cierra antes de la escritura"
    )
    for other in extra_locked_tables:
        other_locks = [i for i, sql in enumerate(sqls)
                       if f'FROM "{other}"' in sql and "FOR UPDATE" in sql]
        assert other_locks, f"no se bloquea {other}"
        assert other_locks[0] < updates[0]
    # Orden préstamo → contrato: estas acciones nunca bloquean el préstamo tras el contrato. Las
    # que pueden abrir un contrato (sign_*, ronda 31) lo bloquean antes.
    loan_table = Loan._meta.db_table
    loan_locks = [i for i, sql in enumerate(sqls) if f'FROM "{loan_table}"' in sql and "FOR UPDATE" in sql]
    assert all(i < locks[0] for i in loan_locks)


def _change_before_lock(monkeypatch, manager, change):
    original = manager.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición cambia la fila justo antes del bloqueo.
        change()
        return original(*args, **kwargs)

    monkeypatch.setattr(manager, "select_for_update", _select_for_update)


def _change_contract_before_lock(monkeypatch, change):
    from apps.loans.models_contracts import Contract

    _change_before_lock(monkeypatch, Contract.objects, change)


# (a) orden del bloqueo

def _prepare(action, contract):
    from apps.loans.models_contracts import ContractTemplate

    if action == "archive":
        contract.status = "cancelled"
    elif action == "unarchive":
        contract.is_archived = True
        contract.archived_at = timezone.now()
    elif action == "activate":
        contract.officer_signed_at = timezone.now()
        contract.status = "signed"
    elif action == "regenerate":
        contract.customer_signed_at = None
        contract.status = "draft"
        contract.template = ContractTemplate.objects.create(
            name="Base", content="Préstamo {{loan_number}}", is_active=True, is_default=True
        )
    contract.save()


@pytest.mark.parametrize("action,expected_status", [
    ("cancel", "cancelled"),
    ("archive", "cancelled"),
    ("unarchive", "pending_signature"),
    ("sign_officer", "signed"),
    ("activate", "active"),
    ("regenerate", "draft"),
])
def test_contract_actions_lock_the_contract_before_updating(
    officer_client, pending_signed, action, expected_status
):
    _, contract = pending_signed
    _prepare(action, contract)
    with CaptureQueriesContext(connection) as ctx:
        response = _post(officer_client, contract, action)

    assert response.status_code == 200, response.content
    _assert_contract_locked_before_update(ctx)
    contract.refresh_from_db()
    assert contract.status == expected_status


# (b) carrera: el contrato o el préstamo cambian entre get_object() y el bloqueo

def test_cancel_waiting_on_a_disbursement_is_refused(officer_client, pending_signed, monkeypatch):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    loan, contract = pending_signed

    def _disburse_meanwhile():
        Loan.objects.filter(pk=loan.pk).update(status="active")
        Contract.objects.filter(pk=contract.pk).update(status="active")

    _change_contract_before_lock(monkeypatch, _disburse_meanwhile)

    response = _post(officer_client, contract, "cancel")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": DISBURSED_MSG}
    contract.refresh_from_db()
    assert contract.status == "active"


@pytest.mark.parametrize("action", ["sign_officer", "activate"])
def test_sign_officer_and_activate_do_not_revive_a_contract_cancelled_meanwhile(
    officer_client, pending_signed, monkeypatch, action
):
    from apps.loans.models_contracts import Contract

    _, contract = pending_signed
    if action == "activate":
        # `activate` exige ambas firmas: el oficial ya firmó antes de la cancelación.
        contract.officer_signed_at = timezone.now()
        contract.status = "signed"
        contract.save()
    before = Contract.objects.get(pk=contract.pk).officer_signed_at
    _change_contract_before_lock(
        monkeypatch, lambda: Contract.objects.filter(pk=contract.pk).update(status="cancelled")
    )

    response = _post(officer_client, contract, action)

    assert response.status_code == 400, response.content
    assert response.json() == {"error": TERMINAL_MSG}
    contract.refresh_from_db()
    assert contract.status == "cancelled"
    assert contract.officer_signed_at == before


def test_concurrent_customer_signature_keeps_the_first_one(officer_client, pending_signed, monkeypatch):
    from apps.loans.models_contracts import Contract

    _, contract = pending_signed
    contract.customer_signed_at = None
    contract.save()
    first = timezone.now() - timedelta(minutes=5)
    _change_contract_before_lock(
        monkeypatch, lambda: Contract.objects.filter(pk=contract.pk).update(customer_signed_at=first)
    )

    response = _post(officer_client, contract, "sign_customer")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": "El cliente ya firmó este contrato"}
    contract.refresh_from_db()
    assert contract.customer_signed_at == first


# (c) regla: el contrato de un préstamo desembolsado no se cancela

def test_cancel_refuses_the_contract_of_a_disbursed_loan(officer_client, pending_signed):
    loan, contract = pending_signed
    loan.status = "active"
    loan.save()
    contract.officer_signed_at = timezone.now()
    contract.status = "active"
    contract.save()

    response = _post(officer_client, contract, "cancel")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": DISBURSED_MSG}
    contract.refresh_from_db()
    assert contract.status == "active"


def test_cancel_of_a_pending_loan_contract_still_works(officer_client, pending_signed):
    _, contract = pending_signed

    response = _post(officer_client, contract, "cancel")

    assert response.status_code == 200, response.content
    assert response.json() == {"message": "Contrato cancelado"}
    contract.refresh_from_db()
    assert contract.status == "cancelled"


# (d) firma pública: el contrato y el token se bloquean antes de comprobar el enlace

def _token(contract):
    from apps.loans.models_contracts import ContractSignatureToken

    return ContractSignatureToken.objects.create(
        contract=contract, token=f"tok-{contract.pk.hex[:16]}", email="cliente@crediflux.test",
        expires_at=timezone.now() + timedelta(days=7),
    )


@pytest.fixture
def unsigned(pending_signed):
    _, contract = pending_signed
    contract.customer_signed_at = None
    contract.save()
    return contract


def _public_sign(api_client, token):
    return api_client.post(
        f"/api/loans/public/contracts/{token.token}/sign/", {"signature_data": _PNG_1X1}, format="json"
    )


def test_public_sign_locks_the_token_and_the_contract_before_updating(api_client, unsigned):
    from apps.loans.models_contracts import ContractSignatureToken

    token = _token(unsigned)
    with CaptureQueriesContext(connection) as ctx:
        response = _public_sign(api_client, token)

    assert response.status_code == 200, response.content
    _assert_contract_locked_before_update(
        ctx, extra_locked_tables=[ContractSignatureToken._meta.db_table]
    )
    # Orden contrato → token, el mismo que `cancel` (bloquea el contrato y luego actualiza
    # sus tokens): al revés, firma y cancelación simultáneas se interbloquearían.
    from apps.loans.models_contracts import Contract

    sqls = [q["sql"] for q in ctx.captured_queries]

    def _first_lock(table):
        return next(i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql)

    assert _first_lock(Contract._meta.db_table) < _first_lock(ContractSignatureToken._meta.db_table)
    token.refresh_from_db()
    assert token.used_at is not None


def test_public_sign_with_a_link_used_meanwhile_is_gone(api_client, unsigned, monkeypatch):
    from apps.loans.models_contracts import ContractSignatureToken

    token = _token(unsigned)
    _change_before_lock(
        monkeypatch, ContractSignatureToken.objects,
        lambda: ContractSignatureToken.objects.filter(pk=token.pk).update(used_at=timezone.now()),
    )

    response = _public_sign(api_client, token)

    assert response.status_code == 410, response.content
    assert response.json() == {"error": "Este enlace ya ha sido utilizado"}
    unsigned.refresh_from_db()
    assert unsigned.customer_signed_at is None
    assert not unsigned.customer_signature
