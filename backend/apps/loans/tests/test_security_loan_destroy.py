"""Sólo se borran préstamos pendientes o rechazados (run-2).

Un préstamo aprobado, desembolsado (activo) o cerrado no se borra por el DELETE
genérico: se conserva con su calendario y su contrato.
"""
import pytest
from rest_framework.test import APIClient

from apps.loans.models import Loan

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"


@pytest.fixture
def officer_client(user_factory):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user_factory(role="loan_officer"))
    return client


@pytest.mark.parametrize("status", ["approved", "active", "paid", "defaulted", "written_off"])
def test_non_pending_loans_cannot_be_deleted(status, officer_client, loan_factory):
    loan = loan_factory(status=status)
    response = officer_client.delete(f"/api/loans/{loan.pk}/")
    assert response.status_code == 400
    assert Loan.objects.filter(pk=loan.pk).exists()


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_pending_or_rejected_loans_can_be_deleted(status, officer_client, loan_factory):
    loan = loan_factory(status=status, disbursement_date=None)
    assert officer_client.delete(f"/api/loans/{loan.pk}/").status_code == 204
    assert not Loan.objects.filter(pk=loan.pk).exists()
