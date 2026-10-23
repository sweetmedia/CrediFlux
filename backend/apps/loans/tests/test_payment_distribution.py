"""#15 (Fase 0): distribución interés/capital de un pago sin cuotas vencidas.

Antes se cobraba `outstanding_balance × tasa`, pero `outstanding_balance` ya
incluye los intereses futuros del cronograma: interés sobre interés. Ahora el
pago se reparte contra la próxima cuota pendiente (la misma a la que lo aplica
la conciliación) y, sin cronograma, sobre el capital pendiente.
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from moneyed import Money


def _pay(client, loan, amount):
    response = client.post(
        "/api/loans/payments/",
        {
            "loan": str(loan.id),
            "amount": amount,
            "amount_currency": "DOP",
            "payment_method": "bank_transfer",
            "payment_date": str(timezone.now().date()),
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    from apps.loans.models import LoanPayment

    return LoanPayment.objects.filter(loan=loan).latest("created_at")


@pytest.fixture
def future_loan(loan_factory):
    """Préstamo activo cuya primera cuota vence en el futuro (nada vencido)."""
    from datetime import timedelta

    from apps.loans.views import LoanViewSet

    today = timezone.now().date()
    loan = loan_factory(
        interest_type="french",
        disbursement_date=today,
        first_payment_date=today + timedelta(days=30),
    )
    loan.status = "active"
    loan.save()
    LoanViewSet()._generate_payment_schedule(loan)
    loan.refresh_from_db()
    return loan


def test_pago_adelantado_cobra_el_interes_de_la_proxima_cuota(auth_client, future_loan):
    first = future_loan.payment_schedules.get(installment_number=1)
    assert future_loan.outstanding_balance.amount > future_loan.principal_amount.amount

    payment = _pay(auth_client, future_loan, "1000.00")

    # 10,000 × 5 % = 500 de interés; nunca outstanding_balance (con intereses futuros) × 5 %
    assert payment.interest_paid == Money(first.interest_amount.amount, "DOP") == Money(Decimal("500.00"), "DOP")
    assert payment.principal_paid == Money(Decimal("500.00"), "DOP")
    assert payment.schedule == first


def test_segundo_pago_adelantado_sigue_con_el_interes_restante(auth_client, future_loan):
    _pay(auth_client, future_loan, "300.00")  # sólo cubre interés de la cuota 1
    payment = _pay(auth_client, future_loan, "1000.00")

    assert payment.interest_paid == Money(Decimal("200.00"), "DOP")
    assert payment.principal_paid == Money(Decimal("800.00"), "DOP")


def test_sin_cronograma_el_interes_va_sobre_el_capital_pendiente(auth_client, loan_factory):
    loan = loan_factory(status="active")  # sin cuotas generadas
    loan.outstanding_balance = Money(Decimal("12000.00"), "DOP")  # incluye intereses
    loan.save()

    payment = _pay(auth_client, loan, "1000.00")

    assert payment.interest_paid == Money(Decimal("500.00"), "DOP")  # 10,000 × 5 %
    assert payment.principal_paid == Money(Decimal("500.00"), "DOP")
