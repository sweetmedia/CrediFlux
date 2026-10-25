"""Ciclo de vida del contrato frente al bloqueo de términos (run-3).

Un contrato firmado y cancelado no puede volver a ser el contrato vigente: cancelar →
archivar → cambiar términos → desarchivar → aprobar → desembolsar acaba en 400 y el
préstamo sigue aprobado. Desarchivar un contrato cancelado da 400. Archivar no desbloquea
los términos: un contrato firmado bloquea mientras no esté cancelado, archivado o no.
"""
from decimal import Decimal

import pytest
from django.utils import timezone
from moneyed import Money
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"

PERMISSIVE_POLICY = {
    "max_loan_amount": Money(Decimal("100000000.00"), "DOP"),
    "max_interest_rate": Decimal("600.00"),
    "max_loan_term_months": 600,
    "require_guarantor": False,
    "guarantor_required_above": None,
    "require_collateral_default": False,
    "require_id_document": False,
    "require_credit_score": False,
    "require_disbursement_approval": True,
    "max_active_loans_per_customer": 99,
}


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def policy(tenant_schema):
    snapshot = {field: getattr(tenant_schema, field) for field in PERMISSIVE_POLICY}
    for field, value in PERMISSIVE_POLICY.items():
        setattr(tenant_schema, field, value)
    tenant_schema.save()
    yield tenant_schema
    for field, value in snapshot.items():
        setattr(tenant_schema, field, value)


@pytest.fixture
def officer_client(user_factory):
    return _client(user_factory(role="loan_officer"))


@pytest.fixture
def pending_signed(policy, loan_factory):
    from apps.loans.models_contracts import Contract

    loan = loan_factory(status="pending", disbursement_date=None, interest_rate=Decimal("1.50"),
                        interest_type="flat", term_months=4)
    contract = Contract.objects.create(
        loan=loan, content="Tasa 1.50% mensual", status="pending_signature",
        customer_signed_at=timezone.now(),
    )
    return loan, contract


def _contract_url(contract, action):
    return f"/api/loans/contracts/{contract.pk}/{action}/"


def test_cancel_archive_edit_unarchive_cannot_disburse_on_unsigned_terms(
    officer_client, pending_signed, user_factory
):
    loan, contract = pending_signed
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 400

    assert officer_client.post(_contract_url(contract, "cancel"), {}, format="json").status_code == 200
    assert officer_client.post(_contract_url(contract, "archive"), {}, format="json").status_code == 200
    # Cancelado, el contrato ya no bloquea: los términos pueden cambiar (hará falta otro contrato).
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 200

    response = officer_client.post(_contract_url(contract, "unarchive"), {}, format="json")
    assert response.status_code == 400
    contract.refresh_from_db()
    assert contract.is_archived is True

    assert _client(user_factory(role="manager")).post(f"/api/loans/{loan.pk}/approve/").status_code == 200
    response = _client(user_factory(role="loan_officer")).post(f"/api/loans/{loan.pk}/disburse/", {}, format="json")
    assert response.status_code == 400
    loan.refresh_from_db()
    contract.refresh_from_db()
    assert loan.status == "approved"
    assert contract.status == "cancelled"


def test_unarchive_of_a_cancelled_contract_is_refused(officer_client, pending_signed):
    _, contract = pending_signed
    contract.status = "cancelled"
    contract.is_archived = True
    contract.archived_at = timezone.now()
    contract.save()
    response = officer_client.post(_contract_url(contract, "unarchive"), {}, format="json")
    assert response.status_code == 400
    contract.refresh_from_db()
    assert contract.is_archived is True


@pytest.mark.parametrize("contract_status", ["cancelled", "completed"])
def test_disburse_refuses_a_cancelled_or_completed_contract(pending_signed, user_factory, contract_status):
    # Aunque esté sin archivar (p. ej. revivido antes del arreglo), no vale para desembolsar.
    loan, contract = pending_signed
    contract.status = contract_status
    contract.save()
    loan.status = "approved"
    loan.approved_by = user_factory(role="manager")
    loan.save()
    response = _client(user_factory(role="loan_officer")).post(f"/api/loans/{loan.pk}/disburse/", {}, format="json")
    assert response.status_code == 400
    loan.refresh_from_db()
    contract.refresh_from_db()
    assert loan.status == "approved"
    assert contract.status == contract_status


def test_archiving_a_signed_contract_does_not_unlock_the_terms(officer_client, pending_signed):
    loan, contract = pending_signed
    # Archivar exige cancelar por la API; aquí se fuerza el estado para cubrir el bloqueo en sí.
    contract.is_archived = True
    contract.archived_at = timezone.now()
    contract.save()
    response = officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json")
    assert response.status_code == 400
    loan.refresh_from_db()
    assert loan.interest_rate == Decimal("1.50")


def test_officer_signature_alone_also_locks(officer_client, pending_signed):
    loan, contract = pending_signed
    contract.customer_signed_at = None
    contract.officer_signed_at = timezone.now()
    contract.is_archived = True
    contract.save()
    response = officer_client.patch(f"/api/loans/{loan.pk}/", {"term_months": 6}, format="json")
    assert response.status_code == 400


def test_new_signed_contract_after_cancel_allows_disbursement(officer_client, pending_signed, user_factory):
    """La vía legítima: cancelar, cambiar términos, generar y firmar un contrato nuevo."""
    from apps.loans.models_contracts import Contract

    loan, contract = pending_signed
    assert officer_client.post(_contract_url(contract, "cancel"), {}, format="json").status_code == 200
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 200
    Contract.objects.create(
        loan=loan, content="Tasa 2.75% mensual", status="signed", customer_signed_at=timezone.now(),
    )
    assert _client(user_factory(role="manager")).post(f"/api/loans/{loan.pk}/approve/").status_code == 200
    response = _client(user_factory(role="loan_officer")).post(f"/api/loans/{loan.pk}/disburse/", {}, format="json")
    assert response.status_code == 200, response.content
    loan.refresh_from_db()
    assert loan.status == "active"


# --- Cancelado y completado son estados finales (run-3, ronda 2.1) -----------------------
# sign_officer / sign_customer / activate reescribían el estado de un contrato cancelado a
# 'signed' o 'active', y así el contrato revivido volvía a valer para desembolsar.

def _approve_and_disburse(loan, user_factory):
    assert _client(user_factory(role="manager")).post(f"/api/loans/{loan.pk}/approve/").status_code == 200
    return _client(user_factory(role="loan_officer")).post(f"/api/loans/{loan.pk}/disburse/", {}, format="json")


def _assert_not_disbursed(loan, contract, response):
    assert response.status_code == 400
    loan.refresh_from_db()
    contract.refresh_from_db()
    assert loan.status == "approved"
    assert contract.status == "cancelled"


def test_sign_officer_cannot_revive_a_cancelled_archived_contract(officer_client, pending_signed, user_factory):
    loan, contract = pending_signed  # firmado sólo por el cliente
    assert officer_client.post(_contract_url(contract, "cancel"), {}, format="json").status_code == 200
    assert officer_client.post(_contract_url(contract, "archive"), {}, format="json").status_code == 200
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 200

    assert officer_client.post(_contract_url(contract, "sign_officer"), {}, format="json").status_code == 400
    contract.refresh_from_db()
    assert contract.status == "cancelled" and contract.officer_signed_at is None
    assert officer_client.post(_contract_url(contract, "unarchive"), {}, format="json").status_code == 400

    _assert_not_disbursed(loan, contract, _approve_and_disburse(loan, user_factory))


def test_activate_cannot_revive_a_cancelled_archived_contract(officer_client, pending_signed, user_factory):
    loan, contract = pending_signed
    contract.officer_signed_at = timezone.now()  # firmado por ambas partes
    contract.save()
    assert officer_client.post(_contract_url(contract, "cancel"), {}, format="json").status_code == 200
    assert officer_client.post(_contract_url(contract, "archive"), {}, format="json").status_code == 200
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 200

    assert officer_client.post(_contract_url(contract, "activate"), {}, format="json").status_code == 400
    contract.refresh_from_db()
    assert contract.status == "cancelled"
    assert officer_client.post(_contract_url(contract, "unarchive"), {}, format="json").status_code == 400

    _assert_not_disbursed(loan, contract, _approve_and_disburse(loan, user_factory))


def test_cancel_edit_sign_officer_without_archiving_cannot_disburse(officer_client, pending_signed, user_factory):
    loan, contract = pending_signed
    assert officer_client.post(_contract_url(contract, "cancel"), {}, format="json").status_code == 200
    assert officer_client.patch(f"/api/loans/{loan.pk}/", {"interest_rate": "2.75"}, format="json").status_code == 200
    assert officer_client.post(_contract_url(contract, "sign_officer"), {}, format="json").status_code == 400

    _assert_not_disbursed(loan, contract, _approve_and_disburse(loan, user_factory))


@pytest.mark.parametrize("contract_status", ["cancelled", "completed"])
@pytest.mark.parametrize("action", ["sign_customer", "sign_officer", "activate"])
def test_terminal_contract_cannot_be_signed_or_activated(officer_client, pending_signed, action, contract_status):
    _, contract = pending_signed
    contract.status = contract_status
    if action == "sign_customer":
        contract.customer_signed_at = None
    contract.officer_signed_at = timezone.now() if action == "activate" else None
    contract.save()
    before = (contract.customer_signed_at, contract.officer_signed_at)
    response = officer_client.post(_contract_url(contract, action), {}, format="json")
    assert response.status_code == 400
    contract.refresh_from_db()
    assert contract.status == contract_status
    assert (contract.customer_signed_at, contract.officer_signed_at) == before


def test_disburse_requires_an_allowed_contract_status(pending_signed, user_factory):
    # Lista positiva: un borrador firmado tampoco vale.
    loan, contract = pending_signed
    contract.status = "draft"
    contract.save()
    loan.status = "approved"
    loan.approved_by = user_factory(role="manager")
    loan.save()
    response = _client(user_factory(role="loan_officer")).post(f"/api/loans/{loan.pk}/disburse/", {}, format="json")
    assert response.status_code == 400
    loan.refresh_from_db()
    assert loan.status == "approved"
