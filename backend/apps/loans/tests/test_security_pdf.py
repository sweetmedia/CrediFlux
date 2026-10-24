"""PDF de contratos sin markup inyectable y validación de `id_number` del cliente.

Cubre: el contenido del contrato y los datos del cliente/préstamo llegan escapados a
`Paragraph` (ninguna etiqueta `<img>`/`<font>`/`<a>` del usuario se interpreta),
reportlab no confía en ningún esquema/host para recursos remotos, y el alta de un
cliente rechaza un `id_number` con caracteres de fórmula o con longitud inválida.
"""

from itertools import count
from unittest import mock

import pytest
from rest_framework.test import APIClient

TENANT_HOST = "tenant.test.localhost"

INJECTED = '<img src="file:///etc/passwd" width="10" height="10"/> <font color="red">x</font>'

_seq = count(1)


@pytest.fixture
def contract(loan_factory, customer_factory):
    from apps.loans.models_contracts import Contract

    customer = customer_factory(first_name='<a href="http://evil.test">Ana</a>')
    return Contract.objects.create(
        loan=loan_factory(customer=customer),
        content=f"Cláusula primera\n{INJECTED}\n\nCláusula segunda & final",
        status="pending_signature",
    )


def test_contract_pdf_escapes_user_markup(contract):
    from apps.loans import utils_pdf

    with mock.patch.object(utils_pdf, "Paragraph", wraps=utils_pdf.Paragraph) as paragraph:
        buffer = utils_pdf.generate_contract_pdf(contract, tenant=None)

    data = buffer.getvalue()
    assert data.startswith(b"%PDF") and len(data) > 1000

    texts = [call.args[0] for call in paragraph.call_args_list]
    body = [t for t in texts if "Cláusula primera" in t]
    assert body == [
        'Cláusula primera<br/>&lt;img src="file:///etc/passwd" width="10" height="10"/&gt; '
        '&lt;font color="red"&gt;x&lt;/font&gt;'
    ]
    assert "Cláusula segunda &amp; final" in texts
    # Ningún texto de usuario llega con etiquetas crudas.
    assert not any("<img" in t or "<font" in t or "<a " in t for t in texts)
    assert any("&lt;a href=" in t for t in texts)  # nombre del cliente escapado


def test_reportlab_trusts_no_remote_schemes():
    """Fijado en `LoansConfig.ready()`: vale tras `django.setup()`, sin importar utils_pdf."""
    from reportlab import rl_config

    assert rl_config.trustedSchemes == []
    assert rl_config.trustedHosts == []


def _customer_payload(id_type, id_number):
    n = next(_seq)
    return {
        "first_name": "Ana",
        "last_name": f"Gómez {n}",
        "date_of_birth": "1990-01-01",
        "gender": "F",
        "email": f"ana.idnum{n}@crediflux.test",
        "phone": "+18095551234",
        "address_line1": "Calle 2",
        "city": "Santiago",
        "state": "STI",
        "postal_code": "51000",
        "id_type": id_type,
        "id_number": id_number,
        "employment_status": "employed",
    }


@pytest.fixture
def officer_client(user_factory):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user_factory(role="loan_officer"))
    return client


@pytest.mark.parametrize(
    "id_type,id_number",
    [
        ("cedula", "=HYPERLINK(1)"),
        ("passport", "=HYPERLINK(1)"),
        ("passport", "@SUM(A1)"),
        ("cedula", "001-000000-1"),  # 10 dígitos
        ("rnc", "1-01-01010-11"),  # 10 dígitos
    ],
)
def test_customer_create_rejects_invalid_id_number(officer_client, tenant_schema, id_type, id_number):
    from apps.loans.models import Customer

    response = officer_client.post(
        "/api/loans/customers/", _customer_payload(id_type, id_number), format="json"
    )

    assert response.status_code == 400, response.content
    assert "id_number" in response.json()
    assert not Customer.objects.filter(id_number=id_number).exists()


@pytest.mark.parametrize(
    "id_type,id_number",
    [
        ("cedula", "402-1234567-8"),
        ("rnc", "1-01-01010-1"),
        ("passport", "RD 12345-AB"),
    ],
)
def test_customer_create_accepts_valid_id_number(officer_client, tenant_schema, id_type, id_number):
    response = officer_client.post(
        "/api/loans/customers/", _customer_payload(id_type, id_number), format="json"
    )

    assert response.status_code == 201, response.content


def test_customer_partial_update_checks_id_number_against_stored_type(officer_client, customer_factory):
    customer = customer_factory()  # cédula

    response = officer_client.patch(
        f"/api/loans/customers/{customer.id}/", {"id_number": "123456789"}, format="json"
    )

    assert response.status_code == 400
    assert "id_number" in response.json()


@pytest.fixture
def legacy_customer(customer_factory):
    # Cliente previo a la validación: cédula de 8 dígitos guardada por ORM.
    return customer_factory(id_type="cedula", id_number="001-23456")


def _full_payload(client, customer, **changes):
    data = client.get(f"/api/loans/customers/{customer.id}/").json()
    payload = {k: v for k, v in data.items() if v is not None and k not in (
        "id", "customer_id", "full_name", "total_loans", "active_loans", "documents",
        "created_at", "updated_at", "id_document", "photo", "monthly_income",
    )}
    payload.update(changes)
    return payload


def test_legacy_customer_full_put_without_id_change_is_allowed(officer_client, legacy_customer):
    payload = _full_payload(officer_client, legacy_customer, phone="+18095559999")

    response = officer_client.put(
        f"/api/loans/customers/{legacy_customer.id}/", payload, format="json"
    )

    assert response.status_code == 200, response.content
    legacy_customer.refresh_from_db()
    assert str(legacy_customer.phone) == "+18095559999"
    assert legacy_customer.id_number == "001-23456"


def test_legacy_customer_full_put_changing_id_is_validated(officer_client, legacy_customer):
    payload = _full_payload(officer_client, legacy_customer, id_number="001-99999")

    response = officer_client.put(
        f"/api/loans/customers/{legacy_customer.id}/", payload, format="json"
    )

    assert response.status_code == 400
    assert "id_number" in response.json()
    legacy_customer.refresh_from_db()
    assert legacy_customer.id_number == "001-23456"
