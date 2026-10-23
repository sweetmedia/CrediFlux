"""Bug 1 (Fase 0): la tasa es MENSUAL en calculadora, wizard y cronograma.

Antes, el cronograma de saldo_insoluto/german dividía la tasa entre 12/52/26/365
(la trataba como anual), así que la cotización y el contrato daban cuotas
distintas. Ahora los tres usan `apps.loans.amortization`.
"""

from decimal import Decimal

import pytest
from moneyed import Money

METHODS = ["saldo_insoluto", "french", "german", "flat"]
FREQUENCIES = ["daily", "weekly", "biweekly", "monthly"]
TERM_MONTHS = 3
RATE = Decimal("5.00")  # 5 % mensual
PRINCIPAL = Decimal("10000.00")
PAYMENTS_PER_MONTH = {"daily": 30, "weekly": 4, "biweekly": 2, "monthly": 1}


def number_of_payments(term_months, frequency):
    return term_months * PAYMENTS_PER_MONTH[frequency]


def _calculator(auth_client, method, frequency):
    response = auth_client.post(
        "/api/loans/calculate/",
        {
            "principal_amount": str(PRINCIPAL),
            "interest_rate": str(RATE),
            "term": number_of_payments(TERM_MONTHS, frequency),
            "payment_frequency": frequency,
            "amortization_method": method,
            "start_date": "2026-01-01",
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()


@pytest.mark.parametrize("frequency", FREQUENCIES)
@pytest.mark.parametrize("method", METHODS)
def test_cronograma_y_calculadora_dan_la_misma_cuota(auth_client, loan_factory, method, frequency):
    from apps.loans.views import LoanViewSet

    quote = _calculator(auth_client, method, frequency)

    loan = loan_factory(
        principal_amount=Money(PRINCIPAL, "DOP"),
        interest_rate=RATE,
        interest_type=method,
        term_months=TERM_MONTHS,
        payment_frequency=frequency,
    )
    LoanViewSet()._generate_payment_schedule(loan)
    rows = list(loan.payment_schedules.order_by("installment_number"))

    assert len(rows) == len(quote["schedule"]) == number_of_payments(TERM_MONTHS, frequency)
    for row, q in zip(rows, quote["schedule"]):
        assert row.total_amount.amount == Decimal(str(q["payment"])), row.installment_number
        assert row.principal_amount.amount == Decimal(str(q["principal"])), row.installment_number
        assert row.interest_amount.amount == Decimal(str(q["interest"])), row.installment_number

    assert rows[0].total_amount.amount == Decimal(str(quote["payment_amount"]))
    assert sum(r.interest_amount.amount for r in rows) == Decimal(str(quote["total_interest"]))
    assert sum(r.principal_amount.amount for r in rows) == PRINCIPAL


def test_saldo_insoluto_mensual_usa_tasa_mensual(loan_factory):
    """10,000 al 5 % mensual: la primera cuota paga 500 de interés, no 41.67."""
    from apps.loans.views import LoanViewSet

    loan = loan_factory(interest_type="saldo_insoluto", term_months=4)
    LoanViewSet()._generate_payment_schedule(loan)
    first = loan.payment_schedules.get(installment_number=1)

    assert first.interest_amount.amount == Decimal("500.00")
    assert first.principal_amount.amount == Decimal("2500.00")


def test_flat_semanal_cobra_tasa_mensual_por_mes(loan_factory):
    """Interés plano = capital × tasa mensual × meses, sin importar la frecuencia."""
    from apps.loans.views import LoanViewSet

    loan = loan_factory(interest_type="flat", term_months=3, payment_frequency="weekly")
    LoanViewSet()._generate_payment_schedule(loan)
    total = sum(r.total_amount.amount for r in loan.payment_schedules.all())
    assert total == loan.total_amount.amount == Decimal("11500.00")


def test_help_text_de_interest_rate_dice_mensual():
    from apps.loans.models import Loan

    help_text = str(Loan._meta.get_field("interest_rate").help_text).lower()
    assert "mensual" in help_text
    assert "annual" not in help_text


@pytest.fixture
def tasa_alta_permitida(tenant_schema):
    """5% mensual = 60% anual: el tenant debe permitirlo (el default es 36% anual)."""
    original = tenant_schema.max_interest_rate
    tenant_schema.max_interest_rate = Decimal("60.00")
    tenant_schema.save()
    yield
    tenant_schema.max_interest_rate = original  # la BD se revierte; el objeto de sesión no


def test_crear_prestamo_fija_la_cuota_en_el_servidor(auth_client, customer_factory, tasa_alta_permitida):
    """La cuota del contrato sale del mismo cálculo que el cronograma, no del cliente."""
    from apps.loans.models import Loan
    from apps.loans.models_contracts import ContractTemplate

    ContractTemplate.objects.create(
        name="Contrato base", content="Cuota: {{monthly_payment}}", is_active=True, is_default=True
    )
    response = auth_client.post(
        "/api/loans/",
        {
            "customer": str(customer_factory().id),
            "loan_type": "personal",
            "principal_amount": "10000.00",
            "principal_amount_currency": "DOP",
            "interest_rate": "5.00",
            "interest_type": "saldo_insoluto",
            "term_months": 4,
            "payment_frequency": "monthly",
            "payment_amount": "999.99",  # valor del front desactualizado / manipulado
            "payment_amount_currency": "DOP",
            "application_date": "2026-01-01",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    loan = Loan.objects.get(id=response.json()["id"])
    assert loan.payment_amount.amount == Decimal("3000.00")  # 2,500 capital + 500 interés
    assert "3,000.00" in loan.contracts.get().content
