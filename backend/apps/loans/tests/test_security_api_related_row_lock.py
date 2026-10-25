"""La API de garantías y garantes escribe sobre la fila leída bajo bloqueo (ronda 15).

_PendingLoanRowMixin bloqueaba los préstamos y revalidaba el loan_id de la fila, pero guardaba o
borraba la instancia que DRF leyó antes del bloqueo. ModelSerializer.update guarda todas las
columnas, así que un cambio confirmado en la misma fila entretanto (un release/liquidate de la
garantía, otra edición) se pisaba con valores viejos. Ahora, tras el bloqueo de los préstamos, la
fila se bloquea (SELECT ... FOR UPDATE, orden préstamo → fila → contrato → token) y el serializer
aplica los campos validados sobre esa fila fresca; el borrado borra la fila fresca. Una fila que
desapareció entretanto responde 404. release/liquidate bloquean la fila y sólo escriben status.
"""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .test_security_admin_related_regeneration import (  # noqa: F401  (template es fixture)
    _contract, _pending, template,
)
from .test_security_api_related_lifecycle import (  # noqa: F401  (api es fixture)
    KINDS, _loan_locks, _model, _name, _request, _row, _url, api,
)

pytestmark = pytest.mark.django_db

WRITE_OPS = pytest.mark.parametrize("op", ["update", "delete"])

# Campo que otra petición cambia en la misma fila mientras la API edita el nombre.
CONCURRENT = {"collateral": ("status", "active", "released"), "guarantor": ("notes", "", "Nota ajena")}


def _row_locks(sqls, table):
    return [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]


def _row_writes(sqls, table):
    return [
        i for i, sql in enumerate(sqls)
        if sql.startswith((f'UPDATE "{table}"', f'DELETE FROM "{table}"'))
    ]


# (a) orden del bloqueo: préstamo → fila → escritura de la fila

@KINDS
@WRITE_OPS
def test_api_write_locks_the_loan_then_the_row_then_writes(api, template, loan_factory, kind, op):
    loan = _pending(loan_factory)
    row = _row(kind, loan)
    _contract(loan, template)
    table = _model(kind)._meta.db_table

    with CaptureQueriesContext(connection) as ctx:
        response = _request(api, kind, op, loan, row)
    assert response.status_code in (200, 204), response.content

    sqls = [q["sql"] for q in ctx.captured_queries]
    loan_locks, row_locks, writes = _loan_locks(sqls), _row_locks(sqls, table), _row_writes(sqls, table)
    assert loan_locks, "la API no bloquea el préstamo"
    assert row_locks, "la API no bloquea la fila"
    assert writes
    assert loan_locks[0] < row_locks[0] < writes[0]
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert [i for i in savepoints if i < loan_locks[0]], "el bloqueo no va dentro de una transacción"


@pytest.mark.parametrize("action,status", [("release", "released"), ("liquidate", "liquidated")])
def test_release_and_liquidate_lock_the_row_and_only_write_status(
    api, loan_factory, action, status
):
    from apps.loans.models import Collateral

    loan = _pending(loan_factory)
    row = _row("collateral", loan)
    table = Collateral._meta.db_table

    with CaptureQueriesContext(connection) as ctx:
        response = api.post(f"{_url('collateral', row)}{action}/", format="json")
    assert response.status_code == 200, response.content

    sqls = [q["sql"] for q in ctx.captured_queries]
    row_locks = _row_locks(sqls, table)
    updates = [i for i, sql in enumerate(sqls) if sql.startswith(f'UPDATE "{table}"')]
    assert row_locks, "release/liquidate no bloquean la fila"
    assert updates
    assert row_locks[0] < updates[0]
    for i in updates:
        assert '"status"' in sqls[i]
        assert '"description"' not in sqls[i]
    row.refresh_from_db()
    assert row.status == status
    assert row.description == "Fila vieja"


# (b) carrera: otra petición cambia la misma fila entre la lectura de DRF y el bloqueo

def _change_row_before(monkeypatch, manager_owner, kind, row):
    field, _, new = CONCURRENT[kind]
    model = _model(kind)
    original = manager_owner.objects.select_for_update
    done = []

    def _select_for_update(*args, **kwargs):
        if not done:
            done.append(True)
            model.objects.filter(pk=row.pk).update(**{field: new})
        return original(*args, **kwargs)

    monkeypatch.setattr(manager_owner.objects, "select_for_update", _select_for_update)


@KINDS
@pytest.mark.parametrize("moment", ["loan_lock", "row_lock"])
def test_patch_keeps_a_concurrent_change_to_the_same_row(
    api, template, loan_factory, monkeypatch, kind, moment
):
    from apps.loans.models import Loan

    loan = _pending(loan_factory)
    row = _row(kind, loan)
    _contract(loan, template)
    field, old, new = CONCURRENT[kind]
    assert getattr(row, field) == old
    _change_row_before(monkeypatch, Loan if moment == "loan_lock" else _model(kind), kind, row)

    response = _request(api, kind, "update", loan, row, name="Nueva")

    assert response.status_code == 200, response.content
    row.refresh_from_db()
    assert getattr(row, field) == new, "la edición pisó el cambio concurrente con valores viejos"
    assert _name(kind, row) == "Nueva"


# (d) la fila desaparece justo antes del bloqueo de la fila: 404, nada se rehace

def _delete_row_before_row_lock(monkeypatch, kind, row):
    model = _model(kind)
    original = model.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        model.objects.filter(pk=row.pk).delete()
        return original(*args, **kwargs)

    monkeypatch.setattr(model.objects, "select_for_update", _select_for_update)


@KINDS
@WRITE_OPS
def test_write_on_a_row_that_vanished_meanwhile_is_404(
    api, template, loan_factory, monkeypatch, kind, op
):
    loan = _pending(loan_factory)
    row = _row(kind, loan)
    contract = _contract(loan, template)
    _delete_row_before_row_lock(monkeypatch, kind, row)

    response = _request(api, kind, op, loan, row, name="Resucitada")

    assert response.status_code == 404, response.content
    # El borrado simulado corre en la misma transacción de la petición y el 404 la deshace con
    # todo lo demás; lo que importa es que la API no resucitó ni editó la fila.
    for stored in _model(kind).objects.filter(pk=row.pk):
        assert _name(kind, stored) == "Fila vieja"
    contract.refresh_from_db()
    assert contract.content == "texto viejo"
