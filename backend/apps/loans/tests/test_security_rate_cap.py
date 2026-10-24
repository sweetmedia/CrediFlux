"""Tope de tasa del tenant con interest_type=variable_rd (tasa directa por período) (run-2).

variable_rd aplica la tasa a cada cuota, así que su tasa anual nominal es tasa × cuotas
al año (diaria ×360, semanal ×48, quincenal ×24). Cubre alta y PATCH.
"""
from decimal import Decimal

import pytest
from moneyed import Money
from rest_framework.test import APIClient

from apps.loans.policy import annual_nominal_rate

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"


@pytest.fixture
def capped_tenant(tenant_schema):
    snapshot = (tenant_schema.max_interest_rate, tenant_schema.min_interest_rate)
    tenant_schema.max_interest_rate = Decimal("36.00")
    tenant_schema.min_interest_rate = Decimal("0.00")
    tenant_schema.save()
    yield tenant_schema
    tenant_schema.max_interest_rate, tenant_schema.min_interest_rate = snapshot


@pytest.fixture
def officer_client(user_factory):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user_factory(role="loan_officer"))
    return client


@pytest.fixture
def contract_template(tenant_schema):
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(name="Base", content="Préstamo {{loan_number}}", is_active=True, is_default=True)


def _payload(customer, **overrides):
    data = {
        "customer": str(customer.id), "loan_type": "personal",
        "principal_amount": "10000.00", "principal_amount_currency": "DOP",
        "interest_rate": "2.50", "interest_type": "flat", "term_months": 1,
        "payment_frequency": "monthly", "payment_amount": "0.01", "payment_amount_currency": "DOP",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("rate, interest_type, frequency, expected", [
    ("2.50", "flat", "daily", "30.00"),
    ("2.50", "variable_rd", "monthly", "30.00"),
    ("2.50", "variable_rd", "daily", "900.00"),
    ("0.50", "variable_rd", "weekly", "24.00"),
    ("1.00", "variable_rd", "biweekly", "24.00"),
    ("3.00", "variable_rd", "quarterly", "12.00"),
])
def test_annual_nominal_rate(rate, interest_type, frequency, expected):
    assert annual_nominal_rate(Decimal(rate), interest_type, frequency) == Decimal(expected)


def test_variable_rd_daily_above_cap_is_rejected(capped_tenant, officer_client, customer_factory, contract_template):
    response = officer_client.post(
        "/api/loans/", _payload(customer_factory(), interest_type="variable_rd", payment_frequency="daily"),
        format="json",
    )
    assert response.status_code == 400
    assert "interest_rate" in response.data


def test_variable_rd_within_cap_is_accepted(capped_tenant, officer_client, customer_factory, contract_template):
    response = officer_client.post(
        "/api/loans/",
        _payload(customer_factory(), interest_rate="0.10", interest_type="variable_rd", payment_frequency="daily"),
        format="json",
    )
    assert response.status_code == 201, response.data


def test_patch_to_variable_rd_daily_is_rechecked(capped_tenant, officer_client, loan_factory):
    loan = loan_factory(
        status="pending", interest_rate=Decimal("2.50"), interest_type="flat", payment_frequency="monthly",
        term_months=1, principal_amount=Money(Decimal("10000.00"), "DOP"),
    )
    response = officer_client.patch(
        f"/api/loans/{loan.pk}/", {"interest_type": "variable_rd", "payment_frequency": "daily"}, format="json"
    )
    assert response.status_code == 400
    loan.refresh_from_db()
    assert (loan.interest_type, loan.payment_frequency) == ("flat", "monthly")
