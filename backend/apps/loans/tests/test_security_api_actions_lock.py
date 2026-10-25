"""Las acciones de la API aprobar, rechazar y desembolsar bloquean el préstamo antes de decidir.

`get_object()` sigue dando el 404/403; luego, dentro de una transacción, el préstamo se vuelve a
leer con SELECT ... FOR UPDATE y el estado, la política y las escrituras se hacen sobre la fila
bloqueada. En el desembolso, `check_disbursable` corre después del bloqueo y bloquea también el
contrato que valida, para que una cancelación concurrente no se cuele entre la validación y el
desembolso.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _pending(loan_factory):
    return loan_factory(status="pending", disbursement_date=None)


def _approved(loan_factory, approver):
    return loan_factory(status="approved", disbursement_date=None, interest_rate=Decimal("1.50"),
                        term_months=4, payment_frequency="monthly",
                        approved_by=approver, approval_date=date(2026, 3, 1))


def _contract(loan, status="signed"):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(
        loan=loan, content="Contrato", status=status, customer_signed_at=timezone.now()
    )


def _post(client, loan, action, data=None):
    return client.post(f"/api/loans/{loan.id}/{action}/", data or {}, format="json")


def _assert_locked_before_update(ctx, extra_locked_tables=()):
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]
    updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert locks, "la acción no bloquea el préstamo"
    assert updates
    assert locks[0] < updates[0]
    # El bloqueo va dentro de la transacción de la acción (en pytest, un SAVEPOINT).
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"
    for other in extra_locked_tables:
        other_locks = [i for i, sql in enumerate(sqls)
                       if f'FROM "{other}"' in sql and "FOR UPDATE" in sql]
        assert other_locks, f"no se bloquea {other}"
        assert other_locks[0] < updates[0]


# (a) orden del bloqueo

@pytest.mark.parametrize("action,expected", [("approve", "approved"), ("reject", "rejected")])
def test_approve_and_reject_lock_the_loan_before_updating(
    policy, auth_client, loan_factory, action, expected
):
    loan = _pending(loan_factory)
    with CaptureQueriesContext(connection) as ctx:
        response = _post(auth_client, loan, action, {"notes": "motivo"})

    assert response.status_code == 200, response.content
    _assert_locked_before_update(ctx)
    loan.refresh_from_db()
    assert loan.status == expected


def test_disburse_locks_the_loan_and_the_contract_before_updating(
    policy, auth_client, user_factory, loan_factory
):
    from apps.loans.models_contracts import Contract

    loan = _approved(loan_factory, user_factory(role="manager"))
    contract = _contract(loan)
    with CaptureQueriesContext(connection) as ctx:
        response = _post(auth_client, loan, "disburse")

    assert response.status_code == 200, response.content
    assert response.json() == {"status": "loan disbursed", "contract_id": str(contract.id)}
    _assert_locked_before_update(ctx, extra_locked_tables=[Contract._meta.db_table])
    loan.refresh_from_db()
    assert loan.status == "active"


# (b) carrera: el préstamo cambia entre get_object() y el bloqueo

def _change_before_lock(monkeypatch, change):
    from apps.loans.models import Loan

    original = Loan.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición (u otra acción del admin) cambia el estado justo antes del bloqueo.
        change()
        return original(*args, **kwargs)

    monkeypatch.setattr(Loan.objects, "select_for_update", _select_for_update)


def _flip_loan(monkeypatch, loan, **changes):
    from apps.loans.models import Loan

    _change_before_lock(monkeypatch, lambda: Loan.objects.filter(pk=loan.pk).update(**changes))


def test_approve_does_not_overwrite_a_loan_rejected_meanwhile(
    policy, auth_client, user_factory, loan_factory, monkeypatch
):
    other = user_factory(role="admin")
    loan = _pending(loan_factory)
    _flip_loan(monkeypatch, loan, status="rejected", rejected_by=other,
               rejection_date=date(2026, 3, 1))

    response = _post(auth_client, loan, "approve")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": "Solo se pueden aprobar préstamos pendientes"}
    loan.refresh_from_db()
    assert loan.status == "rejected"
    assert loan.approved_by is None
    assert loan.approval_date is None
    assert loan.rejected_by == other


def test_reject_does_not_overwrite_a_loan_approved_meanwhile(
    policy, auth_client, user_factory, loan_factory, monkeypatch
):
    other = user_factory(role="admin")
    loan = _pending(loan_factory)
    _flip_loan(monkeypatch, loan, status="approved", approved_by=other,
               approval_date=date(2026, 3, 1))

    response = _post(auth_client, loan, "reject", {"notes": "motivo"})

    assert response.status_code == 400, response.content
    assert response.json() == {"error": "Solo se pueden rechazar préstamos pendientes"}
    loan.refresh_from_db()
    assert loan.status == "approved"
    assert loan.rejected_by is None
    assert loan.rejection_date is None
    assert loan.approved_by == other


def _assert_not_disbursed(loan):
    from apps.loans.models import LoanSchedule

    loan.refresh_from_db()
    assert loan.disbursement_date is None
    assert not LoanSchedule.objects.filter(loan=loan).exists()


def test_disburse_does_not_activate_a_loan_reverted_to_pending_meanwhile(
    policy, auth_client, user_factory, loan_factory, monkeypatch
):
    loan = _approved(loan_factory, user_factory(role="manager"))
    _contract(loan)
    _flip_loan(monkeypatch, loan, status="pending", approved_by=None, approval_date=None)

    response = _post(auth_client, loan, "disburse")

    assert response.status_code == 400, response.content
    assert response.json() == {"error": "Only approved loans can be disbursed"}
    _assert_not_disbursed(loan)
    assert loan.status == "pending"


# (c) el contrato se cancela entre get_object() y el bloqueo

def test_disburse_rejects_a_contract_cancelled_meanwhile(
    policy, auth_client, user_factory, loan_factory, monkeypatch
):
    from apps.loans.models_contracts import Contract

    loan = _approved(loan_factory, user_factory(role="manager"))
    contract = _contract(loan)
    _change_before_lock(
        monkeypatch, lambda: Contract.objects.filter(pk=contract.pk).update(status="cancelled")
    )

    response = _post(auth_client, loan, "disburse")

    assert response.status_code == 400, response.content
    body = response.json()
    assert body["contract_id"] == str(contract.id)
    assert body["contract_status"] == "cancelled"
    _assert_not_disbursed(loan)
    assert loan.status == "approved"
    contract.refresh_from_db()
    assert contract.status == "cancelled"
