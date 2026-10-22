"""El frontend pide `page_size` (p. ej. 100 préstamos activos al generar
contratos); antes DRF lo ignoraba y devolvía siempre 20."""

import pytest


@pytest.fixture
def customers(tenant_schema):
    from datetime import date

    from apps.loans.models import Customer

    for n in range(25):
        Customer.objects.create(
            first_name="Ana", last_name=f"Gómez {n}", date_of_birth=date(1990, 1, 1), gender="F",
            email=f"pag{n}@crediflux.test", phone="+18095550000", address_line1="Calle 1",
            city="Santo Domingo", state="DN", postal_code="10101", id_type="cedula",
            id_number=f"002-{n:07d}-1", employment_status="employed",
        )


def test_por_defecto_sigue_en_20(auth_client, customers):
    data = auth_client.get("/api/loans/customers/").json()
    assert data["count"] == 25
    assert len(data["results"]) == 20


def test_respeta_page_size(auth_client, customers):
    data = auth_client.get("/api/loans/customers/?page_size=100").json()
    assert len(data["results"]) == 25


def test_page_size_tiene_tope(auth_client, customers):
    from apps.core.pagination import StandardPagination

    assert StandardPagination.max_page_size == 500
    data = auth_client.get("/api/loans/customers/?page_size=100000").json()
    assert len(data["results"]) == 25
