"""Autorización por rol en los viewsets de préstamos y campos de estado de solo lectura.

Cubre: rol por viewset (no sólo en las acciones), `status`/aprobación del préstamo,
firmas y contenido del contrato, `verification_status` del documento, FKs de usuario
limitadas al tenant y revocación de los enlaces públicos de firma al cancelar.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from moneyed import Money
from rest_framework.test import APIClient

TENANT_HOST = "tenant.test.localhost"


def _client_for(user):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def viewer_client(user_factory):
    return _client_for(user_factory(role="viewer"))


@pytest.fixture
def officer(user_factory):
    return user_factory(role="loan_officer")


@pytest.fixture
def officer_client(officer):
    return _client_for(officer)


@pytest.fixture
def contract_template(tenant_schema):
    from apps.loans.models_contracts import ContractTemplate

    return ContractTemplate.objects.create(
        name="Base", content="Préstamo {{loan_number}}", is_active=True, is_default=True
    )


@pytest.fixture
def contract(loan_factory, contract_template):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(
        loan=loan_factory(),
        template=contract_template,
        content="Contenido original",
        status="pending_signature",
    )


@pytest.fixture
def document(customer_factory):
    from apps.loans.models import CustomerDocument

    return CustomerDocument.objects.create(
        customer=customer_factory(),
        document_type="id_card",
        title="Cédula",
        document_file="customer_documents/cedula.pdf",
        file_size=10,
        file_type="application/pdf",
    )


def _customer_payload(n):
    return {
        "first_name": "Ana",
        "last_name": f"Gómez {n}",
        "date_of_birth": "1990-01-01",
        "gender": "F",
        "email": f"ana{n}@crediflux.test",
        "phone": "+18095551234",
        "address_line1": "Calle 2",
        "city": "Santiago",
        "state": "STI",
        "postal_code": "51000",
        "id_type": "cedula",
        "id_number": f"402-{n:07d}-9",
        "employment_status": "employed",
    }


def _loan_payload(customer):
    return {
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


def test_viewer_cannot_create_customer_or_loan(viewer_client, customer_factory, contract_template):
    from apps.loans.models import Customer, Loan

    customers_before = Customer.objects.count()
    response = viewer_client.post("/api/loans/customers/", _customer_payload(1), format="json")
    assert response.status_code == 403, response.content
    assert Customer.objects.count() == customers_before

    response = viewer_client.post("/api/loans/", _loan_payload(customer_factory()), format="json")
    assert response.status_code == 403, response.content
    assert Loan.objects.count() == 0


def test_officer_can_create_customer_and_loan(officer_client, officer, customer_factory, contract_template):
    response = officer_client.post("/api/loans/customers/", _customer_payload(2), format="json")
    assert response.status_code == 201, response.content

    payload = _loan_payload(customer_factory())
    payload["loan_officer"] = officer.pk
    response = officer_client.post("/api/loans/", payload, format="json")
    assert response.status_code == 201, response.content


def test_viewer_cannot_patch_loan(viewer_client, loan_factory):
    loan = loan_factory(status="pending")

    response = viewer_client.patch(f"/api/loans/{loan.id}/", {"notes": "x"}, format="json")

    assert response.status_code == 403, response.content


def test_officer_patch_keeps_status_and_approved_by(officer_client, officer, loan_factory):
    from apps.loans.models import Loan

    loan = loan_factory(status="pending", disbursement_date=None)

    response = officer_client.patch(
        f"/api/loans/{loan.id}/",
        {
            "status": "active",
            "approved_by": officer.pk,
            "approval_date": "2026-01-01",
            "approval_notes": "aprobado por PATCH",
            "notes": "nota legítima",
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    stored = Loan.objects.get(pk=loan.pk)
    assert stored.status == "pending"
    assert stored.approved_by_id is None
    assert stored.approval_date is None
    assert not stored.approval_notes
    assert stored.notes == "nota legítima"


def test_officer_cannot_assign_user_of_other_tenant_as_officer(
    officer_client, loan_factory, user_factory, other_tenant, tenant_schema
):
    from django.db import connection

    from apps.loans.models import Loan

    foreign = user_factory(role="loan_officer", tenant=other_tenant)
    connection.set_tenant(tenant_schema)  # `other_tenant` deja activo el schema public
    loan = loan_factory(status="pending")

    response = officer_client.patch(
        f"/api/loans/{loan.id}/", {"loan_officer": foreign.pk}, format="json"
    )

    assert response.status_code == 400, response.content
    assert response.json()["loan_officer"] == ["Usuario no válido para esta organización."]
    assert Loan.objects.get(pk=loan.pk).loan_officer_id is None

    # Un id inexistente da el mismo mensaje: no se distingue de un usuario foráneo.
    response = officer_client.patch(
        f"/api/loans/{loan.id}/", {"loan_officer": foreign.pk + 99999}, format="json"
    )
    assert response.status_code == 400, response.content
    assert response.json()["loan_officer"] == ["Usuario no válido para esta organización."]


def test_viewer_cannot_sign_customer_nor_patch_contract(viewer_client, contract):
    from apps.loans.models_contracts import Contract

    response = viewer_client.post(f"/api/loans/contracts/{contract.id}/sign_customer/")
    assert response.status_code == 403, response.content

    response = viewer_client.patch(
        f"/api/loans/contracts/{contract.id}/", {"notes": "x"}, format="json"
    )
    assert response.status_code == 403, response.content
    assert Contract.objects.get(pk=contract.pk).customer_signed_at is None


def test_officer_patch_cannot_change_signatures_or_content(officer_client, contract):
    from apps.loans.models_contracts import Contract

    response = officer_client.patch(
        f"/api/loans/contracts/{contract.id}/",
        {
            "content": "Contenido alterado",
            "status": "signed",
            "customer_signed_at": "2026-01-01T00:00:00Z",
            "officer_signed_at": "2026-01-01T00:00:00Z",
            "witness_signed_at": "2026-01-01T00:00:00Z",
            "notes": "nota legítima",
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    stored = Contract.objects.get(pk=contract.pk)
    assert stored.content == "Contenido original"
    assert stored.status == "pending_signature"
    assert stored.customer_signed_at is None
    assert stored.officer_signed_at is None
    assert stored.witness_signed_at is None
    assert stored.notes == "nota legítima"


def test_verification_status_is_read_only_on_generic_routes(viewer_client, officer_client, document):
    from apps.loans.models import CustomerDocument

    url = f"/api/loans/customer-documents/{document.id}/"
    body = {"verification_status": "verified", "rejection_reason": "x"}

    response = viewer_client.patch(url, body, format="json")
    assert response.status_code == 403, response.content

    response = officer_client.patch(url, body, format="json")
    assert response.status_code == 200, response.content
    stored = CustomerDocument.objects.get(pk=document.pk)
    assert stored.verification_status == "pending"
    assert not stored.rejection_reason


def _token(contract, **overrides):
    from apps.loans.models_contracts import ContractSignatureToken

    data = {
        "contract": contract,
        "token": f"tok-{contract.pk.hex[:16]}",
        "email": "cliente@crediflux.test",
        "expires_at": timezone.now() + timedelta(days=7),
    }
    data.update(overrides)
    return ContractSignatureToken.objects.create(**data)


def test_cancel_revokes_tokens_and_public_view_is_gone(officer_client, api_client, contract):
    token = _token(contract)

    response = officer_client.post(f"/api/loans/contracts/{contract.id}/cancel/")
    assert response.status_code == 200, response.content

    token.refresh_from_db()
    assert token.used_at is not None
    assert api_client.get(f"/api/loans/public/contracts/{token.token}/").status_code == 410
    response = api_client.post(
        f"/api/loans/public/contracts/{token.token}/sign/",
        {"signature_data": "aGVsbG8="},
        format="json",
    )
    assert response.status_code == 410


@pytest.mark.parametrize("change", [{"status": "cancelled"}, {"status": "signed"}, {"is_archived": True}])
def test_public_views_reject_contract_not_pending_signature(api_client, contract, change):
    from apps.loans.models_contracts import Contract

    token = _token(contract)
    Contract.objects.filter(pk=contract.pk).update(**change)

    assert api_client.get(f"/api/loans/public/contracts/{token.token}/").status_code == 410
    response = api_client.post(
        f"/api/loans/public/contracts/{token.token}/sign/",
        {"signature_data": "aGVsbG8="},
        format="json",
    )
    assert response.status_code == 410
    assert Contract.objects.get(pk=contract.pk).customer_signed_at is None


def test_regenerate_skips_signed_contract(contract):
    from apps.loans.models_contracts import Contract
    from apps.loans.utils_contracts import regenerate_latest_loan_contract

    Contract.objects.filter(pk=contract.pk).update(customer_signed_at=timezone.now())
    contract.refresh_from_db()

    assert regenerate_latest_loan_contract(contract.loan) is None
    assert Contract.objects.get(pk=contract.pk).content == "Contenido original"


def test_payment_generic_writes_stay_closed(officer_client, active_loan, officer):
    from apps.loans.models import LoanPayment

    payment = LoanPayment.objects.create(
        loan=active_loan,
        amount=Money(Decimal("500.00"), "DOP"),
        payment_method="cash",
        status="completed",
        created_by=officer,
    )
    url = f"/api/loans/payments/{payment.id}/"

    assert officer_client.patch(url, {"amount": "1.00"}, format="json").status_code == 405
    assert officer_client.delete(url).status_code == 405
    assert LoanPayment.objects.filter(pk=payment.pk).exists()


def test_regenerate_refuses_signed_contract(officer_client, contract):
    from apps.loans.models_contracts import Contract

    Contract.objects.filter(pk=contract.pk).update(customer_signed_at=timezone.now())

    response = officer_client.post(f"/api/loans/contracts/{contract.id}/regenerate/")

    assert response.status_code == 400, response.content
    assert Contract.objects.get(pk=contract.pk).content == "Contenido original"


def test_officer_patch_cannot_move_contract_loan_or_template(officer_client, contract, loan_factory):
    from apps.loans.models_contracts import Contract, ContractTemplate

    other_template = ContractTemplate.objects.create(name="Otra", content="Otro texto", is_active=True)
    other_loan = loan_factory()

    response = officer_client.patch(
        f"/api/loans/contracts/{contract.id}/",
        {"template": str(other_template.id), "loan": str(other_loan.id)},
        format="json",
    )

    assert response.status_code == 200, response.content
    stored = Contract.objects.get(pk=contract.pk)
    assert stored.template_id == contract.template_id
    assert stored.loan_id == contract.loan_id


def test_collections_gate_on_customer_phones(viewer_client, user_factory, customer_factory):
    from apps.loans.models_contacts import CustomerPhone

    customer = customer_factory()
    body = {"customer": str(customer.id), "phone": "+18095557777", "phone_type": "mobile"}

    response = viewer_client.post("/api/loans/customer-phones/", body, format="json")
    assert response.status_code == 403, response.content
    assert not CustomerPhone.objects.filter(customer=customer).exists()

    collector_client = _client_for(user_factory(role="collector"))
    response = collector_client.post("/api/loans/customer-phones/", body, format="json")
    assert response.status_code == 201, response.content
