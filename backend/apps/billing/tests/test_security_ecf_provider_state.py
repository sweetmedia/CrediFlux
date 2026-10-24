"""Proveedores e-CF DGMax/EF2: submit y cancel respetan el estado de la factura (run-2).

Cubre: enviar una factura ya aceptada → 400, sin llamada saliente y sin tocar estado,
e-NCF ni trackid; anular un borrador → 400 sin llamada; los mismos guardas en los
proveedores directos; un borrador sí se envía.
"""
from datetime import date
from decimal import Decimal
from itertools import count
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Invoice, InvoiceItem
from apps.billing.services.ecf_provider import DGMaxProvider, DirectDGIIProvider, ECFProviderError, EF2Provider

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
POST = "apps.billing.services.ecf_provider.requests.post"
_seq = count(1)


@pytest.fixture(params=["dgmax", "ef2"])
def psfe_tenant(request, tenant_schema):
    original = (tenant_schema.ecf_provider, tenant_schema.ecf_provider_api_key)
    tenant_schema.ecf_provider = request.param
    tenant_schema.ecf_provider_api_key = "clave-ficticia"
    tenant_schema.save(update_fields=["ecf_provider", "ecf_provider_api_key"])
    yield tenant_schema
    tenant_schema.ecf_provider, tenant_schema.ecf_provider_api_key = original
    tenant_schema.save(update_fields=["ecf_provider", "ecf_provider_api_key"])


@pytest.fixture
def accountant_client(user_factory):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user_factory(role="accountant"))
    return client


def _invoice(**overrides):
    from apps.loans.models import Customer

    n = next(_seq)
    customer = Customer.objects.create(
        first_name="Juana", last_name="Pérez", date_of_birth=date(1990, 1, 1), gender="F",
        email=f"cliente.ecf{n}@crediflux.test", phone="+18095550000",
        address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
        id_type="cedula", id_number=f"002-{n:07d}-1", employment_status="employed",
    )
    inv = Invoice.objects.create(
        customer=customer, ecf_type="32", issue_date=date.today(),
        comprador_rnc="101010101", comprador_razon_social="Cliente SRL", **overrides,
    )
    item = InvoiceItem(invoice=inv, line_number=1, description="Servicio",
                       quantity=Decimal("1"), unit_price=Decimal("5000.00"), itbis_rate="0")
    item.calculate_totals()
    item.save()
    return inv


def _ok_response():
    response = mock.Mock(status_code=200)
    response.json.return_value = {"ncf": "E310000000099", "trackid": "TRK-NEW", "ok": True}
    response.raise_for_status.return_value = None
    return response


def test_submit_of_an_accepted_invoice_is_refused(psfe_tenant, accountant_client):
    inv = _invoice(status="accepted", encf_number="E310000000001", dgii_trackid="TRK-ORIG")
    with mock.patch(POST, return_value=_ok_response()) as post:
        response = accountant_client.post("/api/billing/ecf-provider/submit/", {"invoice_id": str(inv.id)}, format="json")
    assert response.status_code == 400
    post.assert_not_called()
    inv.refresh_from_db()
    assert (inv.status, inv.encf_number, inv.dgii_trackid) == ("accepted", "E310000000001", "TRK-ORIG")


def test_cancel_of_a_draft_is_refused(psfe_tenant, accountant_client):
    inv = _invoice()
    with mock.patch(POST, return_value=_ok_response()) as post:
        response = accountant_client.post(
            "/api/billing/ecf-provider/cancel/", {"invoice_id": str(inv.id), "reason": "prueba"}, format="json"
        )
    assert response.status_code == 400
    post.assert_not_called()
    inv.refresh_from_db()
    assert inv.status == "draft"


def test_submit_of_a_draft_still_goes_out(psfe_tenant, accountant_client):
    inv = _invoice()
    with mock.patch(POST, return_value=_ok_response()) as post:
        accountant_client.post("/api/billing/ecf-provider/submit/", {"invoice_id": str(inv.id)}, format="json")
    post.assert_called_once()


@pytest.mark.parametrize("provider_class", [DGMaxProvider, EF2Provider, DirectDGIIProvider])
def test_providers_guard_submit_themselves(provider_class, tenant_schema):
    # El guarda va antes de cualquier configuración (API key, certificado): mensaje de estado.
    inv = _invoice(status="accepted", encf_number="E310000000001", dgii_trackid="TRK-ORIG")
    with mock.patch(POST) as post, pytest.raises(ECFProviderError, match="estado"):
        provider_class(tenant_schema).submit_invoice(inv)
    post.assert_not_called()


def test_direct_provider_only_sends_signed_invoices(tenant_schema):
    with pytest.raises(ECFProviderError, match="estado"):
        DirectDGIIProvider(tenant_schema).submit_invoice(_invoice())
    # Firmada: pasa el guarda y llega a la configuración (sin certificado en el test).
    with pytest.raises(ECFProviderError, match="certificado"):
        DirectDGIIProvider(tenant_schema).submit_invoice(_invoice(status="signed"))


def test_submit_of_a_draft_with_trackid_is_refused(tenant_schema):
    inv = _invoice(dgii_trackid="TRK-ORIG")
    with mock.patch(POST) as post, pytest.raises(ECFProviderError, match="enviada"):
        DGMaxProvider(tenant_schema).submit_invoice(inv)
    post.assert_not_called()
