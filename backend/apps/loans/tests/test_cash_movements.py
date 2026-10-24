"""Bug 4 (Fase 0): pagos y desembolsos en efectivo mueven la caja.

Un pago en efectivo con caja abierta crea su `CashMovement` de entrada; un
desembolso en efectivo crea el de salida. Todo en la misma transacción que el
pago/desembolso.
"""

from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from moneyed import Money


@pytest.fixture
def register(tenant_schema):
    from apps.cashbox.models import CashRegister

    return CashRegister.objects.create(name="Caja Principal", code="CAJA-01")


@pytest.fixture
def open_session(register, admin_user):
    from apps.cashbox.models import CashSession

    return CashSession.objects.create(
        register=register,
        cashier=admin_user,
        opening_balance=Money(Decimal("20000.00"), "DOP"),
        status="open",
    )


def _pay(client, loan, method="cash", amount="1000.00", **extra):
    return client.post(
        "/api/loans/payments/",
        {
            "loan": str(loan.id),
            "amount": amount,
            "amount_currency": "DOP",
            "payment_method": method,
            "payment_date": str(timezone.now().date()),
            **extra,
        },
        format="json",
    )


def test_pago_en_efectivo_con_caja_abierta_crea_entrada(auth_client, active_loan, open_session):
    from apps.cashbox.models import CashMovement
    from apps.loans.models import LoanPayment

    response = _pay(auth_client, active_loan)
    assert response.status_code == 201, response.content

    payment = LoanPayment.objects.get(loan=active_loan)
    movement = CashMovement.objects.get(loan_payment=payment)
    assert movement.session == open_session
    assert movement.movement_type == "inflow"
    assert movement.category == "loan_payment"
    assert movement.amount == Money(Decimal("1000.00"), "DOP")
    assert movement.loan == active_loan
    assert movement.reference == payment.payment_number
    assert movement.recorded_by == auth_client.user
    assert open_session.total_inflows == Decimal("1000.00")


def test_la_mora_cobrada_va_en_su_propia_categoria(auth_client, active_loan, open_session):
    from apps.cashbox.models import CashMovement

    schedule = active_loan.payment_schedules.get(installment_number=1)
    schedule.late_fee_amount = Money(Decimal("150.00"), "DOP")
    schedule.save()

    response = _pay(auth_client, active_loan, schedule=str(schedule.id))
    assert response.status_code == 201, response.content

    movements = {m.category: m.amount for m in CashMovement.objects.filter(session=open_session)}
    assert movements == {
        "late_fee": Money(Decimal("150.00"), "DOP"),
        "loan_payment": Money(Decimal("850.00"), "DOP"),
    }


@pytest.mark.parametrize("method", ["bank_transfer", "check", "card", "mobile_payment"])
def test_pagos_que_no_son_efectivo_no_tocan_la_caja(auth_client, active_loan, open_session, method):
    from apps.cashbox.models import CashMovement

    assert _pay(auth_client, active_loan, method=method).status_code == 201
    assert not CashMovement.objects.exists()


def test_pago_en_efectivo_sin_caja_abierta_se_registra_sin_movimiento(auth_client, active_loan):
    from apps.cashbox.models import CashMovement
    from apps.loans.models import LoanPayment

    assert _pay(auth_client, active_loan).status_code == 201
    assert LoanPayment.objects.filter(loan=active_loan).count() == 1
    assert not CashMovement.objects.exists()


def test_usa_la_unica_caja_abierta_si_el_usuario_no_tiene_la_suya(
    api_client, user_factory, active_loan, open_session
):
    from apps.cashbox.models import CashMovement

    officer = user_factory(role="loan_officer")
    api_client.force_authenticate(user=officer)

    assert _pay(api_client, active_loan).status_code == 201
    assert CashMovement.objects.get().session == open_session


def test_pago_pendiente_mueve_caja_al_confirmarse(auth_client, active_loan, open_session):
    from apps.cashbox.models import CashMovement
    from apps.loans.models import LoanPayment

    assert _pay(auth_client, active_loan, status="pending").status_code == 201
    assert not CashMovement.objects.exists()

    payment = LoanPayment.objects.get(loan=active_loan)
    assert auth_client.post(f"/api/loans/payments/{payment.id}/confirm/").status_code == 200
    assert CashMovement.objects.get().loan_payment == payment


def test_reverso_con_la_caja_aun_abierta_saca_el_efectivo(auth_client, active_loan, open_session):
    from apps.cashbox.models import CashMovement
    from apps.loans.models import LoanPayment

    _pay(auth_client, active_loan)
    payment = LoanPayment.objects.get(loan=active_loan)
    assert auth_client.post(
        f"/api/loans/payments/{payment.id}/reverse/", {"reason": "Error de cobro"}, format="json"
    ).status_code == 200

    refund = CashMovement.objects.get(movement_type="outflow")
    assert refund.category == "refund"
    assert refund.amount == Money(Decimal("1000.00"), "DOP")
    assert refund.loan_payment == payment
    assert open_session.total_inflows - open_session.total_outflows == 0


def test_si_falla_la_caja_no_queda_el_pago(auth_client, active_loan, open_session):
    from apps.loans.models import LoanPayment

    with mock.patch(
        "apps.cashbox.services.CashMovement.objects.create", side_effect=RuntimeError("boom")
    ):
        with pytest.raises(RuntimeError):
            _pay(auth_client, active_loan)

    assert not LoanPayment.objects.filter(loan=active_loan).exists()


# ---------------------------------------------------------------------------
# Desembolsos
# ---------------------------------------------------------------------------


@pytest.fixture
def signed_loan(loan_factory, admin_user):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="approved")
    # El desembolso vuelve a aplicar la política de aprobación (cédula cargada por defecto).
    loan.customer.id_document.name = "customer_documents/ids/cedula.pdf"
    loan.customer.save(update_fields=["id_document"])
    Contract.objects.create(
        loan=loan,
        content="Contrato",
        status="signed",
        customer_signed_at=timezone.now(),
        generated_by=admin_user,
    )
    return loan


def _disburse(client, loan, **body):
    return client.post(f"/api/loans/{loan.id}/disburse/", body, format="json")


def test_desembolso_en_efectivo_crea_salida(auth_client, signed_loan, open_session):
    from apps.cashbox.models import CashMovement

    response = _disburse(auth_client, signed_loan, disbursement_method="cash")
    assert response.status_code == 200, response.content

    movement = CashMovement.objects.get()
    assert movement.session == open_session
    assert movement.movement_type == "outflow"
    assert movement.category == "loan_disbursement"
    assert movement.amount == Money(Decimal("10000.00"), "DOP")
    assert movement.loan == signed_loan
    signed_loan.refresh_from_db()
    assert signed_loan.status == "active"


def test_desembolso_en_efectivo_sin_caja_abierta_se_rechaza(auth_client, signed_loan):
    response = _disburse(auth_client, signed_loan, disbursement_method="cash")

    assert response.status_code == 400
    signed_loan.refresh_from_db()
    assert signed_loan.status == "approved"
    assert not signed_loan.payment_schedules.exists()


def test_desembolso_sin_metodo_o_por_transferencia_no_toca_la_caja(auth_client, signed_loan, open_session):
    from apps.cashbox.models import CashMovement

    assert _disburse(auth_client, signed_loan, disbursement_method="bank_transfer").status_code == 200
    assert not CashMovement.objects.exists()
