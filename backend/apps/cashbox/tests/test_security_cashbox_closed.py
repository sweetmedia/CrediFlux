"""Caja: una sesión cerrada no se borra en cascada ni se le reescriben los conteos (run-2).

Cubre: un cajero no puede borrar una caja; el dueño tampoco si tiene sesiones (se
desactiva); el modelo protege las sesiones (PROTECT); alta, edición y borrado de
conteos de denominaciones en una sesión cerrada → 400; en sesión abierta siguen.
"""
from decimal import Decimal

import pytest
from django.db.models import ProtectedError
from rest_framework.test import APIClient

from apps.cashbox.models import CashRegister, CashSession, DenominationCount

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
REGISTERS_URL = "/api/cashbox/registers/"
DENOMS_URL = "/api/cashbox/denominations/"


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def cashier(user_factory):
    return user_factory(role="cashier")


@pytest.fixture
def register(tenant_schema):
    return CashRegister.objects.create(name="Caja Turno", code="CAJA-RUN2-01")


def _session(register, user, status):
    return CashSession.objects.create(
        register=register, cashier=user, opening_balance=Decimal("1000.00"), status=status,
    )


def test_cashier_cannot_delete_a_register(cashier, register):
    _session(register, cashier, "closed")
    assert _client(cashier).delete(f"{REGISTERS_URL}{register.pk}/").status_code == 403
    assert CashSession.objects.filter(register=register).count() == 1


def test_owner_cannot_delete_a_register_with_sessions(cashier, register, user_factory):
    _session(register, cashier, "closed")
    owner = user_factory(role="admin", is_tenant_owner=True)
    response = _client(owner).delete(f"{REGISTERS_URL}{register.pk}/")
    assert response.status_code == 400
    assert CashRegister.objects.filter(pk=register.pk).exists()


def test_owner_can_delete_an_unused_register(register, user_factory):
    owner = user_factory(role="admin", is_tenant_owner=True)
    assert _client(owner).delete(f"{REGISTERS_URL}{register.pk}/").status_code == 204


def test_model_protects_sessions_from_register_cascade(cashier, register):
    _session(register, cashier, "closed")
    with pytest.raises(ProtectedError):
        register.delete()


def test_denominations_of_a_closed_session_are_immutable(cashier, register):
    closed = _session(register, cashier, "closed")
    count = DenominationCount.objects.create(session=closed, count_type="closing", bills_1000=1)
    client = _client(cashier)

    assert client.post(
        DENOMS_URL, {"session": str(closed.pk), "count_type": "closing", "bills_1000": 1}, format="json"
    ).status_code == 400
    assert client.patch(f"{DENOMS_URL}{count.pk}/", {"bills_1000": 0, "bills_50": 3}, format="json").status_code == 400
    assert client.delete(f"{DENOMS_URL}{count.pk}/").status_code == 400

    count.refresh_from_db()
    assert (count.bills_1000, count.bills_50) == (1, 0)
    assert DenominationCount.objects.filter(session=closed).count() == 1


def test_denomination_cannot_be_moved_into_a_closed_session(cashier, register):
    open_session = _session(register, cashier, "open")
    other = CashRegister.objects.create(name="Caja B", code="CAJA-RUN2-02")
    closed = _session(other, cashier, "closed")
    count = DenominationCount.objects.create(session=open_session, count_type="closing")
    response = _client(cashier).patch(f"{DENOMS_URL}{count.pk}/", {"session": str(closed.pk)}, format="json")
    assert response.status_code == 400


def test_denominations_of_an_open_session_still_work(cashier, register):
    open_session = _session(register, cashier, "open")
    client = _client(cashier)
    response = client.post(
        DENOMS_URL, {"session": str(open_session.pk), "count_type": "closing", "bills_1000": 1}, format="json"
    )
    assert response.status_code == 201, response.data
    count_id = response.data["id"]
    assert client.patch(f"{DENOMS_URL}{count_id}/", {"bills_50": 2}, format="json").status_code == 200
    assert client.delete(f"{DENOMS_URL}{count_id}/").status_code == 204
