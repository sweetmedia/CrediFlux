"""Rutas genéricas de la API (run-4): PATCH/PUT del préstamo y PATCH/DELETE del contrato.

- PATCH/PUT del préstamo: dentro de la transacción se bloquea el préstamo y luego sus contratos
  (orden préstamo → contrato), la regla de campos bloqueados se vuelve a evaluar sobre la fila
  bloqueada y sólo se guardan los campos enviados (estado, desembolso y saldos conservan el valor
  de la fila bloqueada).
- PATCH/PUT del contrato: se bloquea el contrato, uno cancelado o completado da 400 y sólo se
  guardan los campos editables enviados.
- DELETE del contrato: sólo contratos sin firmas, en borrador o por firmar, de préstamos no
  desembolsados; si no, 400 (use cancelar).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"

CONTRACT_REFUSED = {'status': 'Este contrato está cancelado o completado; genere uno nuevo.'}
DELETE_REFUSED = {
    'error': 'Solo se eliminan contratos sin firmas de préstamos no desembolsados; use cancelar.'
}


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


# `policy` (política permisiva del tenant) viene de apps/loans/tests/conftest.py.


@pytest.fixture
def officer_client(user_factory):
    return _client(user_factory(role="loan_officer"))


def _pending_loan(loan_factory):
    return loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"),
                        interest_type="flat", term_months=4)


def _contract(loan, status="pending_signature", **fields):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(loan=loan, content="Tasa 1.50% mensual", status=status, **fields)


def _loan_url(loan):
    return f"/api/loans/{loan.pk}/"


def _contract_url(contract):
    return f"/api/loans/contracts/{contract.pk}/"


def _sqls(ctx):
    return [q["sql"] for q in ctx.captured_queries]


def _lock_indexes(sqls, table):
    return [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]


def _update_indexes(sqls, table):
    return [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]


def _set_clause(sql):
    # Sólo la parte SET del UPDATE (el WHERE nombra la clave primaria).
    return sql.split(" SET ", 1)[1].split(" WHERE ", 1)[0]


def _change_before_lock(monkeypatch, model, change):
    original = model.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición confirma un cambio justo antes del bloqueo.
        change()
        return original(*args, **kwargs)

    monkeypatch.setattr(model.objects, "select_for_update", _select_for_update)


# (a) PATCH del préstamo: orden del bloqueo y sólo los campos enviados

def test_loan_patch_locks_loan_then_contracts_and_updates_only_the_patched_fields(
    policy, officer_client, loan_factory
):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    _contract(loan)
    with CaptureQueriesContext(connection) as ctx:
        response = officer_client.patch(_loan_url(loan), {"notes": "nota nueva"}, format="json")

    assert response.status_code == 200, response.content
    assert response.json()["notes"] == "nota nueva"
    sqls = _sqls(ctx)
    loan_locks = _lock_indexes(sqls, Loan._meta.db_table)
    contract_locks = _lock_indexes(sqls, Contract._meta.db_table)
    updates = _update_indexes(sqls, Loan._meta.db_table)
    assert loan_locks, "el PATCH no bloquea el préstamo"
    assert contract_locks, "el PATCH no bloquea los contratos"
    assert updates
    # Orden préstamo → contrato, ambos antes de escribir el préstamo.
    assert loan_locks[0] < contract_locks[0] < updates[0]
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < loan_locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"
    set_clause = _set_clause(sqls[updates[0]])
    assert '"notes"' in set_clause
    assert '"status"' not in set_clause
    assert '"disbursement_date"' not in set_clause
    assert '"outstanding_balance"' not in set_clause
    loan.refresh_from_db()
    assert loan.notes == "nota nueva"
    assert loan.status == "pending"


# (b) PATCH del préstamo: carrera con approve + disburse y con una firma

def test_loan_patch_keeps_a_disbursement_committed_meanwhile(
    policy, officer_client, user_factory, loan_factory, monkeypatch
):
    from apps.loans.models import Loan

    approver = user_factory(role="manager")
    loan = _pending_loan(loan_factory)
    _contract(loan, status="active", customer_signed_at=timezone.now(),
              officer_signed_at=timezone.now())
    _change_before_lock(monkeypatch, Loan, lambda: Loan.objects.filter(pk=loan.pk).update(
        status="active", approved_by=approver, approval_date=date(2026, 3, 1),
        disbursement_date=date(2026, 3, 2),
    ))

    response = officer_client.patch(_loan_url(loan), {"notes": "nota nueva"}, format="json")

    assert response.status_code == 200, response.content
    loan.refresh_from_db()
    assert loan.status == "active"
    assert loan.disbursement_date == date(2026, 3, 2)
    assert loan.approved_by == approver
    assert loan.notes == "nota nueva"
    assert response.json()["status"] == "active"

    # El préstamo desembolsado ya no se puede borrar.
    response = officer_client.delete(_loan_url(loan))
    assert response.status_code == 400, response.content
    assert Loan.objects.filter(pk=loan.pk).exists()


def test_loan_terms_patch_is_refused_when_the_contract_is_signed_meanwhile(
    policy, officer_client, loan_factory, monkeypatch
):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    contract = _contract(loan)
    _change_before_lock(monkeypatch, Loan, lambda: Contract.objects.filter(pk=contract.pk).update(
        customer_signed_at=timezone.now()
    ))

    response = officer_client.patch(_loan_url(loan), {"interest_rate": "2.75"}, format="json")

    assert response.status_code == 400, response.content
    assert "interest_rate" in response.json()
    loan.refresh_from_db()
    assert loan.interest_rate == Decimal("1.50")
    contract.refresh_from_db()
    assert contract.content == "Tasa 1.50% mensual"


def test_loan_terms_patch_on_an_unsigned_pending_loan_still_works(
    policy, officer_client, loan_factory
):
    loan = _pending_loan(loan_factory)
    _contract(loan)

    response = officer_client.patch(_loan_url(loan), {"interest_rate": "2.75"}, format="json")

    assert response.status_code == 200, response.content
    loan.refresh_from_db()
    assert loan.interest_rate == Decimal("2.75")
    assert loan.status == "pending"


# (c) PATCH del contrato: orden del bloqueo, carrera con cancel y regresión

def test_contract_patch_locks_the_contract_and_updates_only_the_patched_fields(
    officer_client, loan_factory
):
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    signed_at = timezone.now()
    contract = _contract(loan, customer_signed_at=signed_at)
    with CaptureQueriesContext(connection) as ctx:
        response = officer_client.patch(_contract_url(contract), {"notes": "nota"}, format="json")

    assert response.status_code == 200, response.content
    assert response.json()["notes"] == "nota"
    sqls = _sqls(ctx)
    table = Contract._meta.db_table
    locks = _lock_indexes(sqls, table)
    updates = _update_indexes(sqls, table)
    assert locks, "el PATCH no bloquea el contrato"
    assert updates
    assert locks[0] < updates[0]
    set_clause = _set_clause(sqls[updates[0]])
    assert set_clause.count("=") == 2, set_clause
    assert '"notes"' in set_clause
    assert '"updated_at"' in set_clause
    contract.refresh_from_db()
    assert contract.notes == "nota"
    assert contract.status == "pending_signature"
    assert contract.customer_signed_at == signed_at


def test_contract_patch_does_not_revive_a_contract_cancelled_meanwhile(
    officer_client, loan_factory, monkeypatch
):
    from apps.loans.models_contracts import Contract

    loan = _pending_loan(loan_factory)
    signed_at = timezone.now()
    contract = _contract(loan, customer_signed_at=signed_at, notes="original")
    _change_before_lock(monkeypatch, Contract, lambda: Contract.objects.filter(pk=contract.pk).update(
        status="cancelled", notes="original\n\nCancelado"
    ))

    with CaptureQueriesContext(connection) as ctx:
        response = officer_client.patch(_contract_url(contract), {"notes": "nota"}, format="json")

    assert response.status_code == 400, response.content
    assert response.json() == CONTRACT_REFUSED
    # El cancel simulado corre dentro de la transacción de la vista y el 400 lo deshace junto
    # con todo lo demás; lo que importa es que el PATCH no escribió nada: el único UPDATE del
    # contrato es el del cancel simulado (no se reescriben estado, firma ni notas).
    updates = _update_indexes(_sqls(ctx), Contract._meta.db_table)
    assert len(updates) == 1, [ctx.captured_queries[i]["sql"] for i in updates]
    assert '"status"' in _set_clause(ctx.captured_queries[updates[0]]["sql"])
    contract.refresh_from_db()
    assert contract.notes == "original"
    assert contract.customer_signed_at == signed_at


@pytest.mark.parametrize("contract_status", ["cancelled", "completed"])
def test_contract_patch_refuses_terminal_contracts(officer_client, loan_factory, contract_status):
    contract = _contract(_pending_loan(loan_factory), status=contract_status, notes="original")

    response = officer_client.patch(_contract_url(contract), {"notes": "nota"}, format="json")

    assert response.status_code == 400, response.content
    assert response.json() == CONTRACT_REFUSED
    contract.refresh_from_db()
    assert contract.notes == "original"
    assert contract.status == contract_status


# (d) DELETE del contrato

def test_contract_delete_refuses_a_signed_active_contract_of_an_active_loan(
    officer_client, loan_factory
):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="active")
    contract = _contract(loan, status="active", customer_signed_at=timezone.now(),
                         officer_signed_at=timezone.now())

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 400, response.content
    assert response.json() == DELETE_REFUSED
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_contract_delete_refuses_a_contract_with_a_customer_signature(officer_client, loan_factory):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory), customer_signed_at=timezone.now())

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 400, response.content
    assert response.json() == DELETE_REFUSED
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_contract_delete_refuses_an_unsigned_contract_of_a_disbursed_loan(
    officer_client, loan_factory
):
    from apps.loans.models_contracts import Contract

    contract = _contract(loan_factory(status="active"))

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 400, response.content
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_contract_delete_refuses_a_contract_signed_meanwhile(
    officer_client, loan_factory, monkeypatch
):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory))
    _change_before_lock(monkeypatch, Contract, lambda: Contract.objects.filter(pk=contract.pk).update(
        customer_signed_at=timezone.now()
    ))

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 400, response.content
    assert Contract.objects.filter(pk=contract.pk).exists()


def test_contract_delete_allows_an_unsigned_pending_contract_of_a_pending_loan(
    officer_client, loan_factory
):
    from apps.loans.models_contracts import Contract

    contract = _contract(_pending_loan(loan_factory))

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 204, response.content
    assert not Contract.objects.filter(pk=contract.pk).exists()


def test_contract_delete_allows_an_unsigned_draft_of_an_approved_loan(
    officer_client, user_factory, loan_factory
):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="approved", disbursement_date=None,
                        approved_by=user_factory(role="manager"), approval_date=date(2026, 3, 1))
    contract = _contract(loan, status="draft")

    response = officer_client.delete(_contract_url(contract))

    assert response.status_code == 204, response.content
    assert not Contract.objects.filter(pk=contract.pk).exists()
