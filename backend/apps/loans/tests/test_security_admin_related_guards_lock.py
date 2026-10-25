"""Los guardas de escritura de los admins de garantías y garantes bloquean el préstamo (ronda 13).

CollateralAdmin decidía «sólo mientras el préstamo está pendiente» leyendo el estado sin
bloquearlo, y GuarantorAdmin no tenía regla de ciclo de vida. Ahora el alta, la edición (incluido
mover la fila a otro préstamo), el borrado uno a uno y la acción masiva «Eliminar» bloquean los
préstamos afectados con SELECT ... FOR UPDATE (ordenados por pk) dentro de la transacción y
comprueban el estado sobre la fila bloqueada. Un préstamo aprobado por la API entre la
comprobación y la escritura ya no recibe la garantía/el garante ni se le rehace el contrato.
"""
import pytest
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .test_security_admin_related_regeneration import (  # noqa: F401  (admin_client y template son fixtures)
    HOST, _assert_saved, _collateral, _collateral_body, _contract, _guarantor, _guarantor_body,
    _pending, admin_client, template,
)

pytestmark = pytest.mark.django_db

KINDS = pytest.mark.parametrize("kind", ["collateral", "guarantor"])
OPS = pytest.mark.parametrize("op", ["add", "change", "delete", "bulk_delete"])


def _model(kind):
    from apps.loans.models import Collateral
    from apps.loans.models_guarantors import Guarantor

    return Collateral if kind == "collateral" else Guarantor


def _row(kind, loan, name="Fila vieja"):
    return _collateral(loan, name) if kind == "collateral" else _guarantor(loan, name)


def _body(kind, loan_id, name):
    return _collateral_body(loan_id, name) if kind == "collateral" else _guarantor_body(loan_id, name)


def _name(kind, row):
    return row.description if kind == "collateral" else row.first_name


def _post(client, kind, op, loan, row=None, name="Nombre nuevo"):
    if op == "add":
        return client.post(reverse(f"admin:loans_{kind}_add"), _body(kind, loan.pk, name))
    if op == "change":
        return client.post(reverse(f"admin:loans_{kind}_change", args=[row.pk]), _body(kind, loan.pk, name))
    if op == "delete":
        return client.post(reverse(f"admin:loans_{kind}_delete", args=[row.pk]), {"post": "yes"})
    return client.post(reverse(f"admin:loans_{kind}_changelist"), {
        "action": "delete_selected", "_selected_action": [row.pk], "post": "yes",
    })


def _loan_locks(sqls):
    from apps.loans.models import Loan

    table = Loan._meta.db_table
    return [i for i, sql in enumerate(sqls) if f'FROM "{table}"' in sql and "FOR UPDATE" in sql]


# (a) orden del bloqueo: FOR UPDATE del préstamo antes de la primera escritura de la fila

@KINDS
@OPS
def test_admin_write_locks_the_loan_before_writing(admin_client, template, loan_factory, kind, op):
    loan = _pending(loan_factory)
    row = None if op == "add" else _row(kind, loan)
    _contract(loan, template)
    table = _model(kind)._meta.db_table

    with CaptureQueriesContext(connection) as ctx:
        response = _post(admin_client, kind, op, loan, row)
    _assert_saved(response)

    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = _loan_locks(sqls)
    writes = [
        i for i, sql in enumerate(sqls)
        if sql.startswith((f'INSERT INTO "{table}"', f'UPDATE "{table}"', f'DELETE FROM "{table}"'))
    ]
    assert locks, "el admin no bloquea el préstamo"
    assert writes
    assert locks[0] < writes[0]
    savepoints = [i for i, sql in enumerate(sqls) if sql.startswith("SAVEPOINT")]
    assert any(i < locks[0] for i in savepoints), "el bloqueo no va dentro de una transacción"


# (b) carrera: el préstamo se aprueba justo antes del bloqueo

def _approve_before_lock(monkeypatch, loan):
    from apps.loans.models import Loan

    original = Loan.objects.select_for_update

    def _select_for_update(*args, **kwargs):
        # Otra petición (la API) aprueba el préstamo justo antes de que el admin lo bloquee.
        Loan.objects.filter(pk=loan.pk).update(status="approved")
        return original(*args, **kwargs)

    monkeypatch.setattr(Loan.objects, "select_for_update", _select_for_update)


@KINDS
@OPS
def test_admin_write_refuses_a_loan_approved_meanwhile(
    admin_client, template, loan_factory, monkeypatch, kind, op
):
    model = _model(kind)
    loan = _pending(loan_factory)
    row = None if op == "add" else _row(kind, loan)
    contract = _contract(loan, template)
    before = model.objects.count()
    _approve_before_lock(monkeypatch, loan)

    response = _post(admin_client, kind, op, loan, row, name="Intrusa")

    assert response.status_code == 403
    assert model.objects.count() == before
    if row is not None:
        row.refresh_from_db()
        assert _name(kind, row) == "Fila vieja"
        assert row.loan_id == loan.pk
    contract.refresh_from_db()
    assert contract.content == "texto viejo"


# (c) mover la fila entre dos préstamos pendientes bloquea ambos, ordenados por pk

@KINDS
def test_moving_a_row_locks_both_loans_in_pk_order(admin_client, template, loan_factory, kind):
    from apps.loans.models import Loan

    old_loan, new_loan = _pending(loan_factory), _pending(loan_factory)
    row = _row(kind, old_loan, "Movida")
    old_contract, new_contract = _contract(old_loan, template), _contract(new_loan, template)

    with CaptureQueriesContext(connection) as ctx:
        _assert_saved(_post(admin_client, kind, "change", new_loan, row, name="Movida"))

    sqls = [q["sql"] for q in ctx.captured_queries]
    locks = [sqls[i] for i in _loan_locks(sqls)]
    assert locks, "el admin no bloquea los préstamos"
    lock = locks[0]
    assert str(old_loan.pk) in lock and str(new_loan.pk) in lock
    assert f'ORDER BY "{Loan._meta.db_table}"."id" ASC' in lock

    old_contract.refresh_from_db()
    new_contract.refresh_from_db()
    if kind == "collateral":
        assert "Sin garantías" in old_contract.content
        assert "Movida" in new_contract.content
    else:
        assert "Garante: N/A" in old_contract.content
        assert "Movida Gómez" in new_contract.content


# (d) ciclo de vida de los garantes (nuevo)

def test_guarantor_admin_follows_the_loan_lifecycle(admin_client, active_loan, loan_factory):
    from apps.loans.models_guarantors import Guarantor

    locked = _guarantor(active_loan, "Bloqueado")
    url = reverse("admin:loans_guarantor_change", args=[locked.pk])
    assert admin_client.post(url, _guarantor_body(active_loan.pk, "Cambiado")).status_code == 403
    locked.refresh_from_db()
    assert locked.first_name == "Bloqueado"
    assert admin_client.post(
        reverse("admin:loans_guarantor_delete", args=[locked.pk]), {"post": "yes"}
    ).status_code == 403
    assert Guarantor.objects.filter(pk=locked.pk).exists()

    # Alta contra un préstamo activo: se rechaza y no se crea.
    response = admin_client.post(
        reverse("admin:loans_guarantor_add"), _guarantor_body(active_loan.pk, "Nuevo")
    )
    assert response.status_code == 403
    assert not Guarantor.objects.filter(first_name="Nuevo").exists()

    editable = _guarantor(_pending(loan_factory), "Editable")
    url = reverse("admin:loans_guarantor_change", args=[editable.pk])
    _assert_saved(admin_client.post(url, _guarantor_body(editable.loan_id, "Cambiado")))
    editable.refresh_from_db()
    assert editable.first_name == "Cambiado"


def test_guarantor_bulk_delete_of_mixed_statuses_deletes_nothing(
    admin_client, superuser, active_loan, loan_factory
):
    from django.test import RequestFactory
    from apps.loans.admin import GuarantorAdmin
    from apps.loans.models_guarantors import Guarantor

    pending = _guarantor(_pending(loan_factory), "Pendiente")
    locked = _guarantor(active_loan, "Activo")
    ids = [pending.pk, locked.pk]

    admin_client.post(reverse("admin:loans_guarantor_changelist"), {
        "action": "delete_selected", "_selected_action": ids, "post": "yes",
    })
    assert Guarantor.objects.filter(pk__in=ids).count() == 2

    # Respaldo: delete_queryset mismo rechaza la selección aunque se salte la confirmación.
    request = RequestFactory().post("/", HTTP_HOST=HOST)
    request.user = superuser
    with pytest.raises(PermissionDenied):
        GuarantorAdmin(Guarantor, admin.site).delete_queryset(request, Guarantor.objects.filter(pk__in=ids))
    assert Guarantor.objects.filter(pk__in=ids).count() == 2
