"""La API de garantías y garantes sigue el ciclo de vida del préstamo, bloqueado (ronda 14).

CollateralViewSet y GuarantorViewSet eran ModelViewSet sin regla de estado: se podía crear,
editar, mover o borrar una garantía/un garante de un préstamo aprobado o activo, cambiando lo que
describe el contrato y lo que revisó el aprobador. Ahora el alta, la edición (incluido mover la
fila a otro préstamo) y el borrado bloquean los préstamos afectados con SELECT ... FOR UPDATE
dentro de una transacción (helpers compartidos con el admin en apps/loans/locks.py), exigen que
sigan pendientes y responden 400 si no. El borrado además rehace el contrato por firmar.
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .test_security_admin_related_regeneration import (  # noqa: F401  (template es fixture)
    HOST, _collateral, _contract, _guarantor, _pending, template,
)

pytestmark = pytest.mark.django_db

KINDS = pytest.mark.parametrize("kind", ["collateral", "guarantor"])
OPS = pytest.mark.parametrize("op", ["create", "update", "delete"])

MESSAGES = {
    ("collateral", "write"): "Las garantías sólo se modifican mientras el préstamo está pendiente.",
    ("collateral", "delete"): "Las garantías sólo se eliminan mientras el préstamo está pendiente.",
    ("guarantor", "write"): "Los garantes sólo se modifican mientras el préstamo está pendiente.",
    ("guarantor", "delete"): "Los garantes sólo se eliminan mientras el préstamo está pendiente.",
}


@pytest.fixture
def api(user_factory, policy):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user_factory(role="manager"))
    return client


def _model(kind):
    from apps.loans.models import Collateral
    from apps.loans.models_guarantors import Guarantor

    return Collateral if kind == "collateral" else Guarantor


def _url(kind, row=None):
    base = "/api/loans/collaterals/" if kind == "collateral" else "/api/loans/guarantors/"
    return base if row is None else f"{base}{row.pk}/"


def _row(kind, loan, name="Fila vieja"):
    return _collateral(loan, name) if kind == "collateral" else _guarantor(loan, name)


def _name(kind, row):
    return row.description if kind == "collateral" else row.first_name


def _payload(kind, loan, name):
    if kind == "collateral":
        return {
            "loan": str(loan.pk), "collateral_type": "vehicle", "description": name,
            "estimated_value": "5000.00",
        }
    return {
        "loan": str(loan.pk), "first_name": name, "last_name": "Gómez", "id_type": "cedula",
        "id_number": "00112345678", "phone": "+18095551234", "address": "Calle 1",
        "relationship": "friend",
    }


def _patch_body(kind, loan, name):
    # GuarantorSerializer.validate exige teléfono y dirección también en PATCH (comportamiento previo).
    if kind == "collateral":
        return {"loan": str(loan.pk), "description": name}
    return {"loan": str(loan.pk), "first_name": name, "phone": "+18095551234", "address": "Calle 1"}


def _request(api, kind, op, loan, row=None, name="Nombre nuevo"):
    if op == "create":
        return api.post(_url(kind), _payload(kind, loan, name), format="json")
    if op == "update":
        return api.patch(_url(kind, row), _patch_body(kind, loan, name), format="json")
    return api.delete(_url(kind, row))


def _expected(kind, op):
    return MESSAGES[(kind, "delete" if op == "delete" else "write")]


def _assert_refused(response, kind, op):
    assert response.status_code == 400, response.content
    loan_errors = response.json()["loan"]
    text = loan_errors if isinstance(loan_errors, str) else " ".join(map(str, loan_errors))
    assert _expected(kind, op) in text


# (a) ciclo de vida

@KINDS
def test_create_on_an_active_loan_is_refused(api, active_loan, kind):
    model = _model(kind)
    before = model.objects.count()

    response = _request(api, kind, "create", active_loan, name="Intrusa")

    _assert_refused(response, kind, "create")
    assert model.objects.count() == before


@KINDS
def test_patch_and_put_of_a_row_on_an_active_loan_are_refused(api, active_loan, kind):
    row = _row(kind, active_loan)

    _assert_refused(_request(api, kind, "update", active_loan, row, name="Cambiada"), kind, "update")
    put = api.put(_url(kind, row), _payload(kind, active_loan, "Cambiada"), format="json")
    _assert_refused(put, kind, "update")

    row.refresh_from_db()
    assert _name(kind, row) == "Fila vieja"


@KINDS
def test_moving_a_row_onto_an_active_loan_is_refused(api, active_loan, loan_factory, kind):
    loan = _pending(loan_factory)
    row = _row(kind, loan)

    _assert_refused(_request(api, kind, "update", active_loan, row, name="Fila vieja"), kind, "update")

    row.refresh_from_db()
    assert row.loan_id == loan.pk


@KINDS
def test_delete_of_a_row_on_an_active_loan_is_refused(api, active_loan, kind):
    row = _row(kind, active_loan)

    _assert_refused(_request(api, kind, "delete", active_loan, row), kind, "delete")

    assert _model(kind).objects.filter(pk=row.pk).exists()


@KINDS
def test_pending_loan_writes_still_work(api, loan_factory, kind):
    model = _model(kind)
    loan = _pending(loan_factory)

    response = _request(api, kind, "create", loan, name="Nueva")
    assert response.status_code == 201, response.content
    row = model.objects.get(pk=response.json()["id"])
    assert row.created_by_id is not None

    response = _request(api, kind, "update", loan, row, name="Editada")
    assert response.status_code == 200, response.content
    row.refresh_from_db()
    assert _name(kind, row) == "Editada"

    assert _request(api, kind, "delete", loan, row).status_code == 204
    assert not model.objects.filter(pk=row.pk).exists()


# (b) orden del bloqueo: FOR UPDATE del préstamo antes de la primera escritura de la fila

def _loan_locks(sqls):
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    return [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]


@KINDS
@OPS
def test_api_write_locks_the_loan_before_writing(api, template, loan_factory, kind, op):
    loan = _pending(loan_factory)
    row = None if op == "create" else _row(kind, loan)
    _contract(loan, template)
    table = _model(kind)._meta.db_table

    with CaptureQueriesContext(connection) as ctx:
        response = _request(api, kind, op, loan, row)
    assert response.status_code in (200, 201, 204), response.content

    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = _loan_locks(sqls)
    writes = [
        i for i, sql in enumerate(sqls)
        if sql.startswith((f'INSERT INTO "{table}"', f'UPDATE "{table}"', f'DELETE FROM "{table}"'))
    ]
    assert locks, "la API no bloquea el préstamo"
    assert writes
    assert locks[0] < writes[0]
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"


# (c) carrera: el préstamo se aprueba justo antes del bloqueo

def _approve_before_lock(monkeypatch, loan):
    from apps.loans.models import Loan

    original = Loan.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición aprueba el préstamo justo antes de que la API lo bloquee.
        Loan.objects.filter(pk=loan.pk).update(status="approved")
        return original(*args, **kwargs)

    monkeypatch.setattr(Loan.objects, "select_for_update", _select_for_update)


@KINDS
@OPS
def test_api_write_refuses_a_loan_approved_meanwhile(
    api, template, loan_factory, monkeypatch, kind, op
):
    model = _model(kind)
    loan = _pending(loan_factory)
    row = None if op == "create" else _row(kind, loan)
    contract = _contract(loan, template)
    before = model.objects.count()
    _approve_before_lock(monkeypatch, loan)

    response = _request(api, kind, op, loan, row, name="Intrusa")

    _assert_refused(response, kind, op)
    assert model.objects.count() == before
    if row is not None:
        row.refresh_from_db()
        assert _name(kind, row) == "Fila vieja"
        assert row.loan_id == loan.pk
    contract.refresh_from_db()
    assert contract.content == "texto viejo"


# (d) el borrado rehace el contrato; mover entre préstamos pendientes rehace ambos

@KINDS
def test_delete_regenerates_the_pending_contract(api, template, loan_factory, kind):
    loan = _pending(loan_factory)
    row = _row(kind, loan, "Borrable")
    contract = _contract(loan, template)

    assert _request(api, kind, "delete", loan, row).status_code == 204

    contract.refresh_from_db()
    assert "Borrable" not in contract.content
    if kind == "collateral":
        assert "Sin garantías" in contract.content
    else:
        assert "Garante: N/A" in contract.content


@KINDS
def test_moving_a_row_regenerates_both_contracts(api, template, loan_factory, kind):
    old_loan, new_loan = _pending(loan_factory), _pending(loan_factory)
    row = _row(kind, old_loan, "Movida")
    old_contract, new_contract = _contract(old_loan, template), _contract(new_loan, template)

    response = _request(api, kind, "update", new_loan, row, name="Movida")
    assert response.status_code == 200, response.content

    row.refresh_from_db()
    assert row.loan_id == new_loan.pk
    old_contract.refresh_from_db()
    new_contract.refresh_from_db()
    if kind == "collateral":
        assert "Sin garantías" in old_contract.content
        assert "Movida" in new_contract.content
    else:
        assert "Garante: N/A" in old_contract.content
        assert "Movida Gómez" in new_contract.content
