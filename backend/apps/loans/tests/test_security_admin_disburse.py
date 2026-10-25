"""La acción masiva «Desembolsar» del admin aplica las mismas precondiciones que la API.

Sin contrato, con el contrato vigente cancelado (aunque firmado) o sin la firma del
cliente, el préstamo no se desembolsa y el admin informa el error. Con un contrato firmado
se desembolsa igual que por la API: activo, fecha de desembolso, contrato activo y
cronograma generado.
"""
from decimal import Decimal

import pytest
from django.contrib import admin, messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.utils import timezone
from moneyed import Money

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


@pytest.fixture
def policy(tenant_schema):
    snapshot = {field: getattr(tenant_schema, field) for field in PERMISSIVE_POLICY}
    for field, value in PERMISSIVE_POLICY.items():
        setattr(tenant_schema, field, value)
    tenant_schema.save()
    yield tenant_schema
    for field, value in snapshot.items():
        setattr(tenant_schema, field, value)
    tenant_schema.save()


@pytest.fixture
def superuser(user_factory):
    return user_factory(role="admin", is_staff=True, is_superuser=True)


def _admin_request(user):
    request = RequestFactory().post("/admin/loans/loan/", HTTP_HOST=HOST)
    request.user = user
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)
    return request


def _run_action(user, loan):
    from apps.loans.admin import LoanAdmin
    from apps.loans.models import Loan

    request = _admin_request(user)
    LoanAdmin(Loan, admin.site).disburse_loans(request, Loan.objects.filter(pk=loan.pk))
    return [(m.level, str(m)) for m in messages.get_messages(request)]


def _approved_loan(loan_factory):
    return loan_factory(status="approved", disbursement_date=None, interest_rate=Decimal("1.50"),
                        term_months=4, payment_frequency="monthly")


def _contract(loan, status="pending_signature", signed=True):
    from apps.loans.models_contracts import Contract

    return Contract.objects.create(
        loan=loan, content="Deudor tasa plazo", status=status,
        customer_signed_at=timezone.now() if signed else None,
    )


def _schedules(loan):
    from apps.loans.models import LoanSchedule

    return LoanSchedule.objects.filter(loan=loan)


def _assert_not_disbursed(loan, sent):
    loan.refresh_from_db()
    assert loan.status == "approved"
    assert loan.disbursement_date is None
    assert not _schedules(loan).exists()
    errors = [text for level, text in sent if level == messages.ERROR]
    assert errors and loan.loan_number in errors[0]
    assert not [text for level, text in sent if level == messages.SUCCESS]
    return errors[0]


def test_cancelled_signed_contract_blocks_admin_disbursement(policy, superuser, loan_factory):
    loan = _approved_loan(loan_factory)
    contract = _contract(loan, status="cancelled", signed=True)

    error = _assert_not_disbursed(loan, _run_action(superuser, loan))
    assert "estado válido para desembolsar" in error
    contract.refresh_from_db()
    assert contract.status == "cancelled"


def test_loan_without_contract_is_not_disbursed_from_admin(policy, superuser, loan_factory):
    loan = _approved_loan(loan_factory)

    error = _assert_not_disbursed(loan, _run_action(superuser, loan))
    assert "no tiene contrato generado" in error


def test_contract_without_customer_signature_blocks_admin_disbursement(policy, superuser, loan_factory):
    loan = _approved_loan(loan_factory)
    contract = _contract(loan, status="pending_signature", signed=False)

    error = _assert_not_disbursed(loan, _run_action(superuser, loan))
    assert "firmado por el cliente" in error
    contract.refresh_from_db()
    assert contract.status == "pending_signature"


def test_signed_contract_is_disbursed_like_the_api(policy, superuser, loan_factory):
    loan = _approved_loan(loan_factory)
    contract = _contract(loan, status="pending_signature", signed=True)

    sent = _run_action(superuser, loan)

    assert not [text for level, text in sent if level == messages.ERROR]
    assert [text for level, text in sent if level == messages.SUCCESS]
    loan.refresh_from_db()
    contract.refresh_from_db()
    assert loan.status == "active"
    assert loan.disbursement_date == timezone.localdate()
    schedules = _schedules(loan).order_by("installment_number")
    assert schedules.count() == 4
    assert loan.maturity_date == schedules.last().due_date
    assert contract.status == "active"
