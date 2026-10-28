"""Bug 3 (Fase 0): los pagos no se editan ni se borran por la API.

Un pago registrado sólo cambia de estado por sus acciones (`confirm`,
`cancel`, `reverse`); el reverso exige `payments.void`, motivo y el TOTP de un dueño o
administrador (Task 14, test_payment_reverse_totp.py), y deja traza.
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


def test_el_reverso_sigue_siendo_la_via_para_anular_un_pago(auth_client, payment, autorizacion_reverso):
    response = auth_client.post(
        _url(payment, "reverse/"), {"reason": "Pago duplicado", **autorizacion_reverso()}, format="json"
    )

    assert response.status_code == 200, response.content
    payment.refresh_from_db()
    assert payment.status == "reversed"


@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "   "}])
def test_el_reverso_exige_motivo(auth_client, payment, body):
    response = auth_client.post(_url(payment, "reverse/"), body, format="json")

    assert response.status_code == 400
    payment.refresh_from_db()
    assert payment.status == "completed"


def test_el_reverso_deja_traza_en_el_pago_y_en_auditoria(
    auth_client, payment, tenant, autorizacion_reverso
):
    from apps.audit.models import AuditLog

    response = auth_client.post(
        _url(payment, "reverse/"),
        {"reason": "Cliente pagó dos veces", **autorizacion_reverso()},
        format="json",
    )
    assert response.status_code == 200, response.content

    payment.refresh_from_db()
    assert payment.reversal_reason == "Cliente pagó dos veces"
    assert payment.reversed_by == auth_client.user
    assert payment.reversed_at is not None
    detail = auth_client.get(_url(payment)).json()
    assert detail["reversal_reason"] == "Cliente pagó dos veces"

    log = AuditLog.objects.get(action="payment_void", object_id=str(payment.id))
    assert log.tenant == tenant
    assert log.user == auth_client.user
    assert log.model_name == "LoanPayment"
    assert log.changes == {"status": {"old": "completed", "new": "reversed"}}
    assert log.extra_data["reason"] == "Cliente pagó dos veces"
    assert log.extra_data["amount"] == "500.00"
    assert log.extra_data["loan_number"] == payment.loan.loan_number


def test_cancelar_deja_traza_en_auditoria(auth_client, active_loan, admin_user):
    from apps.audit.models import AuditLog
    from apps.loans.models import LoanPayment

    pending = LoanPayment.objects.create(
        loan=active_loan, amount=Money(Decimal("300.00"), "DOP"),
        payment_method="check", status="pending", created_by=admin_user,
    )
    auth_client.post(_url(pending, "cancel/"), {"reason": "Cheque devuelto"}, format="json")

    log = AuditLog.objects.get(action="payment_void", object_id=str(pending.id))
    assert log.changes == {"status": {"old": "pending", "new": "cancelled"}}
    assert log.extra_data["reason"] == "Cheque devuelto"


def test_el_reverso_exige_payments_void(api_client, user_factory, payment):
    cashier = user_factory(role="cashier")  # registra pagos, no anula
    api_client.force_authenticate(user=cashier)

    response = api_client.post(_url(payment, "reverse/"), {"reason": "x"}, format="json")

    assert response.status_code == 403
    assert response.json()["required_permission"] == "payments.void"
    payment.refresh_from_db()
    assert payment.status == "completed"
