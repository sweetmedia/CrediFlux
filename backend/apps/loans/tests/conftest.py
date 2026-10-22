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
