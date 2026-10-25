"""Borrower y términos de un préstamo quedan fijos tras la aprobación o la firma (run-2).

Cubre: PATCH de cliente/tasa/plazo/frecuencia de un préstamo aprobado → 400 y sin
cambios; lo mismo en un pendiente con contrato firmado; un pendiente sin firma sigue
editable; campos no económicos (notas) siguen editables; un PUT que repite los mismos
valores pasa; y el desembolso vuelve a aplicar la política de aprobación.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from moneyed import Money
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def officer_client(user_factory):
    return _client(user_factory(role="loan_officer"))


def _contract(loan, signed=False, archived=False, status="pending_signature"):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(
        loan=loan, content="Deudor tasa plazo", status=status,
        customer_signed_at=timezone.now() if signed else None, is_archived=archived,
    )


@pytest.fixture
def approved_loan(loan_factory):
    loan = loan_factory(status="approved", disbursement_date=None, interest_rate=Decimal("1.50"),
                        term_months=4, payment_frequency="monthly")
    _contract(loan, signed=True)
    return loan


TERM_PATCH = {"interest_rate": "2.75", "term_months": 12, "payment_frequency": "weekly"}


def test_terms_of_an_approved_loan_cannot_change(officer_client, approved_loan, customer_factory):
    other = customer_factory()
    response = officer_client.patch(
        f"/api/loans/{approved_loan.pk}/", {"customer": str(other.pk), **TERM_PATCH}, format="json"
    )
    assert response.status_code == 400
    assert {"customer", "interest_rate", "term_months", "payment_frequency"} <= set(response.data)
    approved_loan.refresh_from_db()
    assert approved_loan.customer_id != other.pk
    assert (approved_loan.interest_rate, approved_loan.term_months, approved_loan.payment_frequency) == (
        Decimal("1.50"), 4, "monthly"
    )


def test_principal_of_an_approved_loan_cannot_change(officer_client, approved_loan):
    # principal_amount es de sólo lectura en LoanSerializer: se ignora, no se guarda.
    officer_client.patch(
        f"/api/loans/{approved_loan.pk}/",
        {"principal_amount": "90000.00", "principal_amount_currency": "DOP"}, format="json",
    )
    approved_loan.refresh_from_db()
    assert approved_loan.principal_amount.amount == Decimal("10000.00")


def test_pending_loan_with_signed_contract_is_locked(officer_client, loan_factory):
    loan = loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"))
    _contract(loan, signed=True)
    response = officer_client.patch(f"/api/loans/{loan.pk}/", {"term_months": 3}, format="json")
    assert response.status_code == 400


def test_pending_unsigned_loan_stays_editable(officer_client, loan_factory):
    loan = loan_factory(status="pending", disbursement_date=None, term_months=6, interest_rate=Decimal("1.50"))
    # Un contrato firmado y cancelado (la API sólo archiva cancelados) no bloquea.
    _contract(loan, signed=True, archived=True, status="cancelled")
    _contract(loan, signed=False)
    response = officer_client.patch(f"/api/loans/{loan.pk}/", {"term_months": 3}, format="json")
    assert response.status_code == 200, response.data
    loan.refresh_from_db()
    assert loan.term_months == 3


def test_non_economic_fields_stay_editable_and_same_values_pass(officer_client, approved_loan):
    response = officer_client.patch(
        f"/api/loans/{approved_loan.pk}/",
        {"notes": "Llamar el lunes", "interest_rate": "1.50", "term_months": 4, "customer": str(approved_loan.customer_id)},
        format="json",
    )
    assert response.status_code == 200, response.data


def test_term_edit_on_pending_loan_regenerates_contract_and_installment(officer_client, customer_factory):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import ContractTemplate

    ContractTemplate.objects.create(
        name="Base", content="Tasa {{interest_rate}} cuota {{monthly_payment}}", is_active=True, is_default=True
    )
    created = officer_client.post("/api/loans/", {
        "customer": str(customer_factory().id), "loan_type": "personal",
        "principal_amount": "10000.00", "principal_amount_currency": "DOP",
        "interest_rate": "1.50", "interest_type": "flat", "term_months": 4,
        "payment_frequency": "monthly", "payment_amount": "0.01", "payment_amount_currency": "DOP",
    }, format="json")
    assert created.status_code == 201, created.data
    loan = Loan.objects.get(pk=created.data["id"])
    old_payment = loan.payment_amount
    old_content = loan.contracts.get().content

    response = officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json")
    assert response.status_code == 200, response.data
    loan.refresh_from_db()
    contract = loan.contracts.get()
    assert loan.payment_amount != old_payment
    assert contract.content != old_content
    assert "2.75" in contract.content


def test_disburse_reapplies_the_approval_policy(tenant_schema, approved_loan, user_factory):
    snapshot = (tenant_schema.require_credit_score, tenant_schema.minimum_credit_score)
    tenant_schema.require_credit_score = True
    tenant_schema.minimum_credit_score = 650
    tenant_schema.save()
    try:
        approved_loan.customer.credit_score = 420
        approved_loan.customer.save()
        response = _client(user_factory(role="admin")).post(f"/api/loans/{approved_loan.pk}/disburse/", {}, format="json")
        assert response.status_code == 400
        assert "credit_score" in response.data
        approved_loan.refresh_from_db()
        assert approved_loan.status == "approved"
    finally:
        tenant_schema.require_credit_score, tenant_schema.minimum_credit_score = snapshot
