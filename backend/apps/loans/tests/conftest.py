"""Fixtures del módulo de préstamos: clientes y préstamos en el tenant de pruebas."""

from datetime import date
from decimal import Decimal
from itertools import count

import pytest
from moneyed import Money

_seq = count(1)


@pytest.fixture
def customer_factory(tenant_schema):
    from apps.loans.models import Customer

    def _create(**overrides):
        n = next(_seq)
        data = {
            "first_name": "Juana",
            "last_name": f"Pérez {n}",
            "date_of_birth": date(1990, 1, 1),
            "gender": "F",
            "email": f"cliente{n}@crediflux.test",
            "phone": "+18095550000",
            "address_line1": "Calle 1",
            "city": "Santo Domingo",
            "state": "DN",
            "postal_code": "10101",
            "id_type": "cedula",
            "id_number": f"001-{n:07d}-1",
            "employment_status": "employed",
        }
        data.update(overrides)
        return Customer.objects.create(**data)

    return _create


@pytest.fixture
def loan_factory(customer_factory):
    from apps.loans.models import Loan

    def _create(**overrides):
        data = {
            "customer": overrides.pop("customer", None) or customer_factory(),
            "loan_type": "personal",
            "principal_amount": Money(Decimal("10000.00"), "DOP"),
            "interest_rate": Decimal("5.00"),
            "interest_type": "french",
            "term_months": 6,
            "payment_frequency": "monthly",
            "payment_amount": Money(Decimal("1.00"), "DOP"),
            "status": "approved",
            "disbursement_date": date(2026, 1, 1),
            "first_payment_date": date(2026, 2, 1),
        }
        data.update(overrides)
        loan = Loan.objects.create(**data)
        loan.outstanding_balance = loan.principal_amount
        loan.save()
        return loan

    return _create


@pytest.fixture
def active_loan(loan_factory):
    """Préstamo activo con cronograma generado (6 cuotas mensuales)."""
    from apps.loans.views import LoanViewSet

    loan = loan_factory()
    loan.status = "active"
    loan.save()
    LoanViewSet()._generate_payment_schedule(loan)
    loan.refresh_from_db()
    return loan


# Política del tenant que no estorba: los tests que la usan prueban otra cosa (bloqueos,
# precondiciones del contrato). Los módulos con su propia política definen su `policy`.
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
