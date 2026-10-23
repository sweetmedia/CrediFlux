"""Caja: movimientos sólo en sesión abierta, con monto positivo y libro cerrado inmutable.

Cubre: alta de movimiento en sesión cerrada → 400, monto negativo o cero → 400, PATCH
y DELETE de un movimiento de sesión cerrada → 400 (el movimiento queda intacto), PATCH
que mueve un movimiento a una sesión cerrada o pone monto negativo → 400, y alta en
sesión abierta → 201.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.cashbox.models import CashMovement, CashRegister, CashSession

TENANT_HOST = "tenant.test.localhost"
MOVEMENTS_URL = "/api/cashbox/movements/"
SESSIONS_URL = "/api/cashbox/sessions/"


@pytest.fixture
def cashier_client(user_factory):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user_factory(role="cashier"))
    return client


@pytest.fixture
def register(tenant_schema):
    return CashRegister.objects.create(name="Caja Principal", code="CAJA-SEC-01")


def _open_session(client, register):
    response = client.post(
        f"{SESSIONS_URL}open/",
        {"register": str(register.id), "opening_balance": "1000.00"},
        format="json",
    )
    assert response.status_code == 201, response.data
    return CashSession.objects.get(id=response.data["id"])


def _movement_payload(session, amount="500.00"):
    return {
        "session": str(session.id),
        "movement_type": "inflow",
        "category": "loan_payment",
        "amount": amount,
        "description": "Pago de cuota",
    }


def _create_movement(client, session):
    response = client.post(MOVEMENTS_URL, _movement_payload(session), format="json")
    assert response.status_code == 201, response.data
    return CashMovement.objects.get(session=session)


@pytest.fixture
def open_session(cashier_client, register):
    return _open_session(cashier_client, register)


@pytest.fixture
def closed_session_with_movement(cashier_client, register):
    """Sesión abierta + movimiento de 500 + cierre por la API."""
    session = _open_session(cashier_client, register)
    movement = _create_movement(cashier_client, session)

    response = cashier_client.post(
        f"{SESSIONS_URL}{session.id}/close/", {"closing_balance": "1500.00"}, format="json"
    )
    assert response.status_code == 200, response.data
    session.refresh_from_db()
    assert session.status == "closed"
    return session, movement


def test_create_movement_in_open_session_succeeds(cashier_client, open_session):
    response = cashier_client.post(MOVEMENTS_URL, _movement_payload(open_session), format="json")

    assert response.status_code == 201, response.data
    movement = CashMovement.objects.get(session=open_session)
    assert movement.amount.amount == Decimal("500.00")


def test_create_movement_in_closed_session_is_rejected(cashier_client, closed_session_with_movement):
    session, _ = closed_session_with_movement

    response = cashier_client.post(MOVEMENTS_URL, _movement_payload(session), format="json")

    assert response.status_code == 400
    assert response.data["session"] == ["La sesión de caja no está abierta."]
    assert CashMovement.objects.filter(session=session).count() == 1


def test_create_movement_with_negative_amount_is_rejected(cashier_client, open_session):
    response = cashier_client.post(
        MOVEMENTS_URL, _movement_payload(open_session, amount="-100.00"), format="json"
    )

    assert response.status_code == 400
    assert response.data["amount"] == ["El monto debe ser mayor que cero."]
    assert not CashMovement.objects.filter(session=open_session).exists()


def test_create_movement_with_zero_amount_is_rejected(cashier_client, open_session):
    response = cashier_client.post(
        MOVEMENTS_URL, _movement_payload(open_session, amount="0.00"), format="json"
    )

    assert response.status_code == 400
    assert response.data["amount"] == ["El monto debe ser mayor que cero."]
    assert not CashMovement.objects.filter(session=open_session).exists()


def test_patch_movement_of_closed_session_is_rejected(cashier_client, closed_session_with_movement):
    _, movement = closed_session_with_movement

    response = cashier_client.patch(
        f"{MOVEMENTS_URL}{movement.id}/", {"amount": "50.00"}, format="json"
    )

    assert response.status_code == 400
    movement.refresh_from_db()
    assert movement.amount.amount == Decimal("500.00")


def test_delete_movement_of_closed_session_is_rejected(cashier_client, closed_session_with_movement):
    _, movement = closed_session_with_movement

    response = cashier_client.delete(f"{MOVEMENTS_URL}{movement.id}/")

    assert response.status_code == 400
    assert CashMovement.objects.filter(id=movement.id).exists()


def test_patch_cannot_move_movement_into_closed_session(
    cashier_client, closed_session_with_movement, register
):
    closed_session, _ = closed_session_with_movement
    session = _open_session(cashier_client, register)
    movement = _create_movement(cashier_client, session)

    response = cashier_client.patch(
        f"{MOVEMENTS_URL}{movement.id}/", {"session": str(closed_session.id)}, format="json"
    )

    assert response.status_code == 400
    assert response.data["session"] == ["La sesión de caja no está abierta."]
    movement.refresh_from_db()
    assert movement.session_id == session.id


def test_patch_cannot_set_negative_amount(cashier_client, open_session):
    movement = _create_movement(cashier_client, open_session)

    response = cashier_client.patch(
        f"{MOVEMENTS_URL}{movement.id}/", {"amount": "-100.00"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["amount"] == ["El monto debe ser mayor que cero."]
    movement.refresh_from_db()
    assert movement.amount.amount == Decimal("500.00")
