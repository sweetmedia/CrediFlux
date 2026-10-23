"""Política de originación del tenant aplicada en préstamos.

Cubre: rango de monto/tasa/plazo, préstamos activos por cliente, garante en la
aprobación, segregación aprobación/desembolso y validación cruzada de la
configuración del tenant.
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from moneyed import Money
from rest_framework.test import APIClient

TENANT_HOST = "tenant.test.localhost"

POLICY = {
    "max_loan_amount": Money(Decimal("50000.00"), "DOP"),
    "max_interest_rate": Decimal("20.00"),
    "max_loan_term_months": 12,
    "require_guarantor": True,
    "guarantor_required_above": None,
    "require_collateral_default": False,
    "require_id_document": False,
    "require_credit_score": False,
    "require_disbursement_approval": True,
    "max_active_loans_per_customer": 1,
}


def _client_for(user):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def policy(tenant_schema):
    """El dueño ajusta la política del tenant (se guarda en el schema public)."""
    snapshot = {field: getattr(tenant_schema, field) for field in POLICY}
    for field, value in POLICY.items():
        setattr(tenant_schema, field, value)
    tenant_schema.save()
    yield tenant_schema
    # La BD se revierte sola; el objeto de sesión en memoria no.
    for field, value in snapshot.items():
        setattr(tenant_schema, field, value)


@pytest.fixture
def manager(user_factory):
    return user_factory(role="manager")


@pytest.fixture
def manager_client(manager):
    return _client_for(manager)


@pytest.fixture
def contract_template(tenant_schema):
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(
        name="Base", content="Préstamo {{loan_number}}", is_active=True, is_default=True
    )


def _loan_payload(customer, **overrides):
    data = {
        "customer": str(customer.id),
        "loan_type": "personal",
        "principal_amount": "5000.00",
        "principal_amount_currency": "DOP",
        "interest_rate": "5.00",
        "interest_type": "flat",
        "term_months": 2,
        "payment_frequency": "monthly",
        "payment_amount": "0.01",
        "payment_amount_currency": "DOP",
    }
    data.update(overrides)
    return data


def _add_guarantor(loan):
    from apps.loans.models_guarantors import Guarantor

    return Guarantor.objects.create(
        loan=loan,
        first_name="Pedro",
        last_name="Garante",
        id_type="cedula",
        id_number="001-0000001-1",
        phone="+18095550001",
        address="Calle 3",
        relationship="friend",
    )


def _sign_contract(loan):
    from apps.loans.models_contracts import Contract

    Contract.objects.create(
        loan=loan, content="Contrato", status="signed", customer_signed_at=timezone.now()
    )


def test_loan_outside_policy_is_rejected(policy, manager_client, customer_factory, contract_template):
    from apps.loans.models import Loan

    payload = _loan_payload(
        customer_factory(), principal_amount="60000.00", interest_rate="25.00", term_months=24
    )
    response = manager_client.post("/api/loans/", payload, format="json")

    assert response.status_code == 400, response.content
    errors = response.json()
    assert {"principal_amount", "interest_rate", "term_months"} <= set(errors)
    assert Loan.objects.count() == 0


def test_loan_within_policy_is_created(policy, manager_client, customer_factory, contract_template):
    response = manager_client.post("/api/loans/", _loan_payload(customer_factory()), format="json")

    assert response.status_code == 201, response.content


def test_second_active_loan_for_same_customer_is_rejected(
    policy, manager_client, customer_factory, loan_factory, contract_template
):
    from apps.loans.models import Loan

    customer = customer_factory()
    loan_factory(customer=customer, status="pending", disbursement_date=None)

    response = manager_client.post("/api/loans/", _loan_payload(customer), format="json")

    assert response.status_code == 400, response.content
    assert "customer" in response.json()
    assert Loan.objects.filter(customer=customer).count() == 1


def test_finished_loans_do_not_count_against_the_limit(
    policy, manager_client, customer_factory, loan_factory, contract_template
):
    customer = customer_factory()
    loan_factory(customer=customer, status="paid")
    loan_factory(customer=customer, status="rejected", disbursement_date=None)

    response = manager_client.post("/api/loans/", _loan_payload(customer), format="json")

    assert response.status_code == 201, response.content


def test_approve_without_guarantor_is_rejected(policy, manager_client, loan_factory):
    from apps.loans.models import Loan

    loan = loan_factory(status="pending", disbursement_date=None)

    response = manager_client.post(f"/api/loans/{loan.id}/approve/")
    assert response.status_code == 400, response.content
    assert "guarantor" in response.json()
    stored = Loan.objects.get(pk=loan.pk)
    assert stored.status == "pending"
    assert stored.approved_by_id is None

    _add_guarantor(loan)
    response = manager_client.post(f"/api/loans/{loan.id}/approve/")
    assert response.status_code == 200, response.content
    assert Loan.objects.get(pk=loan.pk).status == "approved"


def test_same_manager_cannot_approve_and_disburse(
    policy, manager, manager_client, user_factory, loan_factory
):
    from apps.loans.models import Loan

    loan = loan_factory(status="pending", disbursement_date=None)
    _add_guarantor(loan)
    _sign_contract(loan)

    assert manager_client.post(f"/api/loans/{loan.id}/approve/").status_code == 200

    response = manager_client.post(f"/api/loans/{loan.id}/disburse/")
    assert response.status_code == 400, response.content
    assert "approved_by" in response.json()
    assert Loan.objects.get(pk=loan.pk).status == "approved"

    other_manager_client = _client_for(user_factory(role="manager"))
    response = other_manager_client.post(f"/api/loans/{loan.id}/disburse/")
    assert response.status_code == 200, response.content
    assert Loan.objects.get(pk=loan.pk).status == "active"


def test_owner_may_disburse_own_approval(policy, auth_client, loan_factory):
    from apps.loans.models import Loan

    loan = loan_factory(status="pending", disbursement_date=None)
    _add_guarantor(loan)
    _sign_contract(loan)

    assert auth_client.post(f"/api/loans/{loan.id}/approve/").status_code == 200
    response = auth_client.post(f"/api/loans/{loan.id}/disburse/")
    assert response.status_code == 200, response.content
    assert Loan.objects.get(pk=loan.pk).status == "active"


def test_validate_origination_reports_field_keys(policy, customer_factory):
    from rest_framework import serializers

    from apps.loans.policy import validate_origination

    attrs = {
        "principal_amount": Money(Decimal("50.00"), "DOP"),
        "interest_rate": Decimal("1.00"),
        "term_months": 13,
    }
    with pytest.raises(serializers.ValidationError) as exc:
        validate_origination(attrs, customer_factory())

    assert {"principal_amount", "interest_rate", "term_months"} <= set(exc.value.detail)


def test_patch_cannot_push_loan_outside_policy(policy, manager_client, loan_factory):
    from apps.loans.models import Loan

    loan = loan_factory(status="pending", disbursement_date=None)

    response = manager_client.patch(
        f"/api/loans/{loan.id}/", {"interest_rate": "30.00", "term_months": 36}, format="json"
    )

    assert response.status_code == 400, response.content
    assert {"interest_rate", "term_months"} <= set(response.json())
    stored = Loan.objects.get(pk=loan.pk)
    assert stored.interest_rate == Decimal("5.00")
    assert stored.term_months == 6


@pytest.mark.parametrize(
    "data, key",
    [
        ({"min_interest_rate": "30.00", "max_interest_rate": "10.00"}, "min_interest_rate"),
        ({"min_loan_amount": "9000.00", "max_loan_amount": "1000.00"}, "min_loan_amount"),
        ({"min_loan_term_months": 24, "max_loan_term_months": 12}, "min_loan_term_months"),
        ({"min_loan_amount": "-1.00"}, "min_loan_amount"),
        ({"guarantor_required_above": "-5.00"}, "guarantor_required_above"),
        ({"max_active_loans_per_customer": 0}, "max_active_loans_per_customer"),
    ],
)
def test_tenant_settings_cross_validation(tenant_schema, data, key):
    from apps.tenants.serializers import TenantUpdateSerializer

    serializer = TenantUpdateSerializer(instance=tenant_schema, data=data, partial=True)

    assert not serializer.is_valid()
    assert key in serializer.errors


def test_tenant_settings_valid_policy_passes(tenant_schema):
    from apps.tenants.serializers import TenantUpdateSerializer

    serializer = TenantUpdateSerializer(
        instance=tenant_schema,
        data={"min_loan_amount": "500.00", "max_loan_amount": "40000.00", "max_active_loans_per_customer": 2},
        partial=True,
    )

    assert serializer.is_valid(), serializer.errors
