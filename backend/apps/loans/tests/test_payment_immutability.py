"""Bug 3 (Fase 0): los pagos no se editan ni se borran por la API.

Un pago registrado sólo cambia de estado por sus acciones (`confirm`,
`cancel`, `reverse`); el reverso exige al dueño del tenant y deja traza.
"""

from decimal import Decimal

import pytest
from moneyed import Money


@pytest.fixture
def payment(active_loan, admin_user):
    from apps.loans.models import LoanPayment

    return LoanPayment.objects.create(
        loan=active_loan,
        amount=Money(Decimal("500.00"), "DOP"),
        payment_method="bank_transfer",
        status="completed",
        created_by=admin_user,
    )


def _url(payment, suffix=""):
    return f"/api/loans/payments/{payment.id}/{suffix}"


@pytest.mark.parametrize(
    "method, body",
    [
        ("put", {"amount": "1.00", "payment_method": "cash", "loan": None}),
        ("patch", {"amount": "1.00"}),
        ("patch", {"status": "reversed"}),
        ("delete", None),
    ],
)
def test_no_se_puede_editar_ni_borrar_un_pago(auth_client, payment, method, body):
    from apps.loans.models import LoanPayment

    if body and "loan" in body:
        body["loan"] = str(payment.loan_id)
    response = getattr(auth_client, method)(_url(payment), body, format="json")

    assert response.status_code == 405, response.content
    stored = LoanPayment.objects.get(pk=payment.pk)
    assert stored.amount == Money(Decimal("500.00"), "DOP")
    assert stored.status == "completed"


def test_ver_y_listar_pagos_sigue_funcionando(auth_client, payment):
    assert auth_client.get(_url(payment)).status_code == 200
    assert auth_client.get("/api/loans/payments/").status_code == 200


def test_cancelar_pago_pendiente_usa_un_estado_valido(auth_client, active_loan, admin_user):
    from apps.loans.models import LoanPayment

    pending = LoanPayment.objects.create(
        loan=active_loan,
        amount=Money(Decimal("300.00"), "DOP"),
        payment_method="check",
        status="pending",
        created_by=admin_user,
    )
    response = auth_client.post(_url(pending, "cancel/"))

    assert response.status_code == 200, response.content
    pending.refresh_from_db()
    valid = {value for value, _ in LoanPayment._meta.get_field("status").choices}
    assert pending.status in valid
    assert pending.status == "cancelled"
    pending.full_clean()


def test_el_reverso_sigue_siendo_la_via_para_anular_un_pago(auth_client, payment):
    response = auth_client.post(_url(payment, "reverse/"))

    assert response.status_code == 200, response.content
    payment.refresh_from_db()
    assert payment.status == "reversed"


def test_el_reverso_exige_dueno_del_tenant(api_client, user_factory, payment):
    manager = user_factory(role="manager")
    api_client.force_authenticate(user=manager)

    response = api_client.post(_url(payment, "reverse/"))

    assert response.status_code == 403
    payment.refresh_from_db()
    assert payment.status == "completed"
