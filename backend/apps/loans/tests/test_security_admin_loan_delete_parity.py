"""LoanAdmin sigue a LoanViewSet al escribir y al borrar (ronda 25.1).

- Escribir préstamos, garantías y garantes en el admin exige, como la API (CanManageLoans), el
  rol gestor además del permiso de modelo: un cajero con esos permisos recibe 403 (ronda 25.2
  para garantías y garantes).
- Borrar un préstamo pendiente o rechazado arrastra sus contratos y enlaces de firma igual que
  LoanViewSet.perform_destroy. Desde la ronda 25 el admin de enlaces no deja borrar enlaces sueltos y
  el de contratos aplica su propio predicado; eso no debe impedir la cascada de un préstamo que sí se
  puede borrar (la regla del préstamo, sobre la fila bloqueada, sigue siendo la única puerta). Lo
  mismo con garantías y garantes de un préstamo rechazado o sin sus permisos de modelo (ronda 25.2).
- Un borrado masivo rechazado por la relectura bloqueada no deja entradas de «eliminado» en el
  historial (préstamos, garantías y garantes): la acción corre dentro de una transacción.
"""
from datetime import timedelta

import pytest
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth.models import Permission
from django.db.models import QuerySet
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from .test_security_admin_related_guards_lock import _approve_before_lock, _model, _post as _related_post, _row
from .test_security_admin_related_regeneration import _collateral, _guarantor, _pending

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
LOAN_PERMS = ["view_loan", "add_loan", "change_loan", "delete_loan"]


def _client(user):
    client = Client(HTTP_HOST=HOST)
    client.force_login(user)
    return client


def _staff(user_factory, role, codenames):
    from apps.users.models import User

    user = user_factory(role=role, is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(content_type__app_label="loans", codename__in=codenames))
    return User.objects.get(pk=user.pk)


def _contract_with_link(loan, **extra):
    from apps.loans.models_contracts import Contract, ContractSignatureToken

    contract = Contract.objects.create(loan=loan, content="texto", status="pending_signature", **extra)
    token = ContractSignatureToken.objects.create(
        contract=contract, token=f"r251-{loan.pk}", email="cliente@financiera.test",
        expires_at=timezone.now() + timedelta(days=3),
    )
    return contract, token


def _delete_loan(client, op, loan):
    if op == "delete":
        return client.post(reverse("admin:loans_loan_delete", args=[loan.pk]), {"post": "yes"})
    return client.post(reverse("admin:loans_loan_changelist"), {
        "action": "delete_selected", "_selected_action": [str(loan.pk)], "post": "yes",
    })


@pytest.fixture(params=["superuser", "manager"])
def loan_deleter(request, user_factory):
    if request.param == "superuser":
        return _client(user_factory(role="admin", is_staff=True, is_superuser=True))
    # Sólo permisos de préstamo: ni de contrato ni de enlace (como un gerente con la API).
    return _client(_staff(user_factory, "manager", LOAN_PERMS))


OPS = pytest.mark.parametrize("op", ["delete", "bulk_delete"])


# --- I2: la cascada de contratos y enlaces no bloquea el borrado del préstamo -----------------

@OPS
@pytest.mark.parametrize("status", ["pending", "rejected"])
@pytest.mark.parametrize("signed", [False, True])
def test_deleting_a_pending_loan_cascades_its_contract_and_link(loan_deleter, loan_factory, op, status, signed):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import Contract, ContractSignatureToken

    loan = _pending(loan_factory)
    Loan.objects.filter(pk=loan.pk).update(status=status)
    contract, token = _contract_with_link(loan, customer_signed_at=timezone.now() if signed else None)

    response = _delete_loan(loan_deleter, op, loan)

    assert response.status_code == 302
    assert not Loan.objects.filter(pk=loan.pk).exists()
    assert not Contract.objects.filter(pk=contract.pk).exists()
    assert not ContractSignatureToken.objects.filter(pk=token.pk).exists()


@OPS
@pytest.mark.parametrize("status", ["approved", "active"])
def test_a_non_pending_loan_is_still_refused(loan_deleter, loan_factory, op, status):
    from apps.loans.models import Loan

    loan = loan_factory(status=status)
    _contract_with_link(loan)

    response = _delete_loan(loan_deleter, op, loan)

    assert response.status_code == 403
    assert Loan.objects.filter(pk=loan.pk).exists()


# --- paridad de rol: el admin de préstamos exige el criterio de CanManageLoans ----------------

@pytest.mark.parametrize("role", ["cashier", "viewer"])
def test_role_without_manage_loans_cannot_write_loans(user_factory, loan_factory, role):
    from apps.loans.models import Loan

    client = _client(_staff(user_factory, role, LOAN_PERMS))
    loan = _pending(loan_factory)

    assert client.get(reverse("admin:loans_loan_add")).status_code == 403
    assert client.post(reverse("admin:loans_loan_add"), {"_save": "Guardar"}).status_code == 403
    change = client.post(reverse("admin:loans_loan_change", args=[loan.pk]), {"notes": "x", "_save": "Guardar"})
    assert change.status_code == 403
    assert _delete_loan(client, "delete", loan).status_code == 403
    # Sin permiso de escritura no queda ninguna acción: Django ignora el POST y pinta la lista.
    assert _delete_loan(client, "bulk_delete", loan).status_code == 200
    assert Loan.objects.filter(pk=loan.pk, status="pending").exists()
    # Puede seguir consultando.
    assert client.get(reverse("admin:loans_loan_change", args=[loan.pk])).status_code == 200


# --- M5: un borrado masivo rechazado no deja historial de «eliminado» -------------------------

def test_refused_bulk_loan_delete_leaves_no_deletion_log_entry(user_factory, loan_factory, monkeypatch):
    from apps.loans.models import Loan

    client = _client(user_factory(role="admin", is_staff=True, is_superuser=True))
    loan = _pending(loan_factory)
    original = QuerySet.select_for_update

    def _select_for_update(self, *args, **kwargs):
        # La API aprueba el préstamo justo antes de que la acción masiva lo bloquee.
        if self.model is Loan:
            Loan.objects.filter(pk=loan.pk).update(status="approved")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "select_for_update", _select_for_update)

    response = _delete_loan(client, "bulk_delete", loan)

    assert response.status_code == 403
    assert Loan.objects.filter(pk=loan.pk).exists()
    assert not LogEntry.objects.filter(action_flag=DELETION, object_id=str(loan.pk)).exists()


@pytest.mark.parametrize("kind", ["collateral", "guarantor"])
def test_refused_bulk_related_delete_leaves_no_deletion_log_entry(user_factory, loan_factory, monkeypatch, kind):
    client = _client(user_factory(role="admin", is_staff=True, is_superuser=True))
    loan = _pending(loan_factory)
    row = _row(kind, loan)
    _approve_before_lock(monkeypatch, loan)

    response = _related_post(client, kind, "bulk_delete", loan, row)

    assert response.status_code == 403
    assert _model(kind).objects.filter(pk=row.pk).exists()
    assert not LogEntry.objects.filter(action_flag=DELETION, object_id=str(row.pk)).exists()



# --- ronda 25.2 -------------------------------------------------------------------------------

# Garantías y garantes también caen con el préstamo, como en LoanViewSet.perform_destroy: sus
# admins sólo los borran sueltos con el préstamo pendiente (y con permiso de modelo), pero eso no
# debe impedir borrar un préstamo pendiente o rechazado.
@OPS
@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_deleting_a_loan_cascades_its_collateral_and_guarantors(loan_deleter, loan_factory, op, status):
    from apps.loans.models import Collateral, Loan
    from apps.loans.models_guarantors import Guarantor

    loan = _pending(loan_factory)
    collateral, guarantor = _collateral(loan), _guarantor(loan)
    _contract_with_link(loan)
    Loan.objects.filter(pk=loan.pk).update(status=status)

    response = _delete_loan(loan_deleter, op, loan)

    assert response.status_code == 302
    assert not Loan.objects.filter(pk=loan.pk).exists()
    assert not Collateral.objects.filter(pk=collateral.pk).exists()
    assert not Guarantor.objects.filter(pk=guarantor.pk).exists()


@OPS
@pytest.mark.parametrize("status", ["approved", "active"])
def test_a_non_pending_loan_with_collateral_is_still_refused(loan_deleter, loan_factory, op, status):
    from apps.loans.models import Collateral, Loan
    from apps.loans.models_guarantors import Guarantor

    loan = _pending(loan_factory)
    collateral, guarantor = _collateral(loan), _guarantor(loan)
    Loan.objects.filter(pk=loan.pk).update(status=status)

    response = _delete_loan(loan_deleter, op, loan)

    assert response.status_code == 403
    assert Loan.objects.filter(pk=loan.pk).exists()
    assert Collateral.objects.filter(pk=collateral.pk).exists()
    assert Guarantor.objects.filter(pk=guarantor.pk).exists()


# Paridad de rol: CollateralViewSet y GuarantorViewSet exigen CanManageLoans.
KINDS = pytest.mark.parametrize("kind", ["collateral", "guarantor"])


def _related_perms(kind):
    return [f"{action}_{kind}" for action in ("view", "add", "change", "delete")]


@KINDS
@pytest.mark.parametrize("role", ["cashier", "viewer"])
def test_role_without_manage_loans_cannot_write_collateral_or_guarantors(user_factory, loan_factory, kind, role):
    client = _client(_staff(user_factory, role, _related_perms(kind)))
    loan = _pending(loan_factory)
    row = _row(kind, loan)
    before = _model(kind).objects.count()

    assert client.get(reverse(f"admin:loans_{kind}_add")).status_code == 403
    assert _related_post(client, kind, "add", loan).status_code == 403
    assert _related_post(client, kind, "change", loan, row).status_code == 403
    assert _related_post(client, kind, "delete", loan, row).status_code == 403
    # Sin permiso de borrado no queda ninguna acción: Django ignora el POST y pinta la lista.
    assert _related_post(client, kind, "bulk_delete", loan, row).status_code == 200
    assert _model(kind).objects.count() == before
    row.refresh_from_db()
    assert row.loan_id == loan.pk
    # Puede seguir consultando.
    assert client.get(reverse(f"admin:loans_{kind}_change", args=[row.pk])).status_code == 200


@KINDS
@pytest.mark.parametrize("op", ["add", "change", "delete", "bulk_delete"])
def test_loan_officer_still_writes_collateral_and_guarantors(user_factory, loan_factory, kind, op):
    client = _client(_staff(user_factory, "loan_officer", _related_perms(kind)))
    loan = _pending(loan_factory)
    row = None if op == "add" else _row(kind, loan)

    response = _related_post(client, kind, op, loan, row)

    assert response.status_code == 302
