"""Facturación fiscal (e-CF): rol, estado, totales e identidad protegidos.

Cubre: `CanManageBilling` en los viewsets (y en las acciones DGII aunque sean GET),
estado/totales/identidad fiscal de solo lectura en la factura, edición y borrado sólo
en borrador, firma sólo con certificado activo y vigente, ambiente DGII tomado del
tenant (nunca del request), `recalculate_totals` y e-NCF bajo bloqueo.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import DigitalCertificate, FiscalSequence, Invoice, InvoiceItem

TENANT_HOST = "tenant.test.localhost"


def _client_for(user):
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def viewer_client(user_factory):
    return _client_for(user_factory(role="viewer"))


@pytest.fixture
def accountant_client(user_factory):
    return _client_for(user_factory(role="accountant"))


@pytest.fixture
def direct_tenant(tenant_schema):
    """Tenant con flujo directo (certificado propio) y ambiente de certificación."""
    original = (tenant_schema.ecf_provider, tenant_schema.dgii_environment)
    tenant_schema.ecf_provider = "direct"
    tenant_schema.dgii_environment = "certecf"
    tenant_schema.save(update_fields=["ecf_provider", "dgii_environment"])
    yield tenant_schema
    tenant_schema.ecf_provider, tenant_schema.dgii_environment = original
    tenant_schema.save(update_fields=["ecf_provider", "dgii_environment"])


@pytest.fixture
def customer(tenant_schema):
    from apps.loans.models import Customer

    return Customer.objects.create(
        first_name="Juana", last_name="Pérez", date_of_birth=date(1990, 1, 1), gender="F",
        email="cliente.billing@crediflux.test", phone="+18095550000",
        address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
        id_type="cedula", id_number="001-0000001-1", employment_status="employed",
    )


@pytest.fixture
def invoice(customer):
    """Factura en borrador con un ítem exento de 5000.00."""
    inv = Invoice.objects.create(
        customer=customer,
        ecf_type="32",
        issue_date=date.today(),
        comprador_rnc="101010101",
        comprador_razon_social="Cliente Original SRL",
    )
    item = InvoiceItem(
        invoice=inv, line_number=1, description="Servicio",
        quantity=Decimal("1"), unit_price=Decimal("5000.00"), itbis_rate="0",
    )
    item.calculate_totals()
    item.save()
    return inv


def _certificate(**overrides):
    fields = dict(
        name="Cert", is_active=True,
        valid_until=timezone.now() + timedelta(days=365),
    )
    fields.update(overrides)
    return DigitalCertificate.objects.create(**fields)


def _sequence(**overrides):
    fields = dict(
        ecf_type="32", prefix="E32", range_from=1, range_to=10, current_number=1,
        expiration_date=date(2030, 12, 31),
    )
    fields.update(overrides)
    return FiscalSequence.objects.create(**fields)


def test_viewer_cannot_create_sequence_or_edit_invoice(viewer_client, invoice):
    response = viewer_client.post(
        "/api/billing/sequences/",
        {"ecf_type": "32", "prefix": "E32", "range_from": 1, "range_to": 100,
         "current_number": 1, "expiration_date": "2030-12-31"},
        format="json",
    )
    assert response.status_code == 403
    assert not FiscalSequence.objects.exists()

    response = viewer_client.patch(
        f"/api/billing/invoices/{invoice.id}/", {"notes": "hack"}, format="json"
    )
    assert response.status_code == 403
    invoice.refresh_from_db()
    assert invoice.notes == ""

    # Las acciones DGII no están abiertas ni siquiera por GET.
    response = viewer_client.get(f"/api/billing/invoices/{invoice.id}/dgii-status/")
    assert response.status_code == 403
    # La lectura normal sí.
    assert viewer_client.get(f"/api/billing/invoices/{invoice.id}/").status_code == 200


def test_accountant_patch_keeps_status_and_total(accountant_client, invoice):
    invoice.recalculate_totals()
    seq = _sequence()
    response = accountant_client.patch(
        f"/api/billing/invoices/{invoice.id}/",
        {"status": "accepted", "total": "1.00", "subtotal": "1.00", "total_itbis": "0.00",
         "encf_number": "E320000009999", "fiscal_sequence": str(seq.id),
         "emisor_rnc": "999999999", "comprador_rnc": "888888888",
         "comprador_razon_social": "Otro", "security_code": "ABC123",
         "notes": "nota legítima"},
        format="json",
    )
    assert response.status_code == 200, response.data
    invoice.refresh_from_db()
    assert invoice.status == "draft"
    assert invoice.total.amount == Decimal("5000.00")
    assert invoice.subtotal.amount == Decimal("5000.00")
    assert not invoice.encf_number
    assert invoice.fiscal_sequence_id is None
    assert invoice.emisor_rnc == ""
    assert invoice.comprador_rnc == "101010101"
    assert invoice.comprador_razon_social == "Cliente Original SRL"
    assert invoice.security_code == ""
    assert invoice.notes == "nota legítima"


def test_issued_invoice_cannot_be_deleted(accountant_client, invoice):
    Invoice.objects.filter(pk=invoice.pk).update(status="generated")

    response = accountant_client.delete(f"/api/billing/invoices/{invoice.id}/")
    assert response.status_code == 400
    assert "Solo facturas en borrador pueden modificarse" in str(response.data)
    assert Invoice.objects.filter(pk=invoice.pk).exists()

    response = accountant_client.patch(
        f"/api/billing/invoices/{invoice.id}/", {"notes": "tarde"}, format="json"
    )
    assert response.status_code == 400
    invoice.refresh_from_db()
    assert invoice.notes == ""


def test_draft_invoice_can_be_deleted(accountant_client, invoice):
    response = accountant_client.delete(f"/api/billing/invoices/{invoice.id}/")
    assert response.status_code == 204
    assert not Invoice.objects.filter(pk=invoice.pk).exists()


@pytest.mark.parametrize("cert_kwargs", [
    {"is_active": False},
    {"valid_until": timezone.now() - timedelta(days=1)},
], ids=["inactive", "expired"])
def test_sign_rejects_inactive_certificate(accountant_client, direct_tenant, invoice, cert_kwargs):
    Invoice.objects.filter(pk=invoice.pk).update(status="generated", xml_content="<ECF/>")
    cert = _certificate(**cert_kwargs)

    with mock.patch("apps.billing.views.ECFSigner") as signer:
        response = accountant_client.post(
            f"/api/billing/invoices/{invoice.id}/sign/",
            {"certificate_id": str(cert.id)}, format="json",
        )
    assert response.status_code == 400
    assert "certificado" in response.data["error"].lower()
    signer.assert_not_called()
    invoice.refresh_from_db()
    assert invoice.status == "generated"
    assert invoice.certificate_id is None


def test_sign_accepts_active_valid_certificate(accountant_client, direct_tenant, invoice):
    Invoice.objects.filter(pk=invoice.pk).update(status="generated", xml_content="<ECF/>")
    cert = _certificate()

    with mock.patch("apps.billing.views.ECFSigner") as signer:
        signer.return_value.sign_xml.return_value = "<ECF signed/>"
        response = accountant_client.post(
            f"/api/billing/invoices/{invoice.id}/sign/",
            {"certificate_id": str(cert.id)}, format="json",
        )
    assert response.status_code == 200, response.data
    invoice.refresh_from_db()
    assert invoice.status == "signed"
    assert invoice.certificate_id == cert.id


def test_submit_uses_tenant_environment(accountant_client, direct_tenant, invoice):
    cert = _certificate()
    Invoice.objects.filter(pk=invoice.pk).update(
        status="signed", signed_xml="<ECF signed/>", certificate=cert
    )

    with mock.patch("apps.billing.views.DGIIClient") as client_cls:
        response = accountant_client.post(
            f"/api/billing/invoices/{invoice.id}/submit-dgii/",
            {"environment": "ecf"}, format="json",
        )
    assert response.status_code == 200, response.data
    client_cls.assert_called_once()
    assert client_cls.call_args.kwargs["environment"] == direct_tenant.dgii_environment == "certecf"
    client_cls.return_value.submit_ecf.assert_called_once()


def test_dgii_status_uses_tenant_environment(accountant_client, direct_tenant, invoice):
    Invoice.objects.filter(pk=invoice.pk).update(status="submitted", dgii_trackid="TRK-1")

    with mock.patch("apps.billing.views.DGIIClient") as client_cls:
        response = accountant_client.get(
            f"/api/billing/invoices/{invoice.id}/dgii-status/?environment=ecf"
        )
    assert response.status_code == 200, response.data
    assert client_cls.call_args.kwargs["environment"] == "certecf"


def test_generate_ecf_recalculates_totals(accountant_client, direct_tenant, invoice):
    _sequence()
    assert invoice.total.amount == Decimal("0.00")  # aún sin recalcular

    with mock.patch("apps.billing.views.ECFGenerator") as generator:
        generator.return_value.generate.return_value = "<ECF/>"
        response = accountant_client.post(f"/api/billing/invoices/{invoice.id}/generate-ecf/")
    assert response.status_code == 200, response.data
    invoice.refresh_from_db()
    assert invoice.status == "generated"
    assert invoice.encf_number == "E320000000001"
    assert invoice.total.amount == Decimal("5000.00")


def test_accountant_can_create_sequence_and_invoice(accountant_client, customer):
    response = accountant_client.post(
        "/api/billing/sequences/",
        {"ecf_type": "32", "prefix": "E32", "range_from": 1, "range_to": 100,
         "current_number": 50, "expiration_date": "2030-12-31"},
        format="json",
    )
    assert response.status_code == 201, response.data
    seq = FiscalSequence.objects.get(pk=response.data["id"])
    # current_number es de solo lectura: arranca en range_from, no en lo enviado.
    assert seq.current_number == 1

    response = accountant_client.post(
        "/api/billing/invoices/",
        {"ecf_type": "32", "issue_date": str(date.today()), "customer": str(customer.id),
         "items": [{"line_number": 1, "description": "Servicio", "quantity": "1",
                    "unit_price": "5000.00", "itbis_rate": "0"}]},
        format="json",
    )
    assert response.status_code == 201, response.data
    inv = Invoice.objects.get()
    assert inv.status == "draft"
    assert inv.items.count() == 1


def test_recalculate_totals_sums_items(invoice):
    InvoiceItem.objects.create(
        invoice=invoice, line_number=2, description="Gravado",
        quantity=Decimal("2"), unit_price=Decimal("100.00"),
        discount_amount=Decimal("20.00"), itbis_rate="18",
    )
    invoice.recalculate_totals()
    invoice.refresh_from_db()
    # Línea 1: 5000 exento. Línea 2: 2×100 − 20 = 180, ITBIS 32.40.
    assert invoice.subtotal.amount == Decimal("5180.00")
    assert invoice.total_discount.amount == Decimal("20.00")
    assert invoice.total_itbis.amount == Decimal("32.40")
    assert invoice.total.amount == Decimal("5212.40")


def test_get_next_encf_rereads_under_lock(tenant_schema):
    seq = _sequence(range_to=2)
    stale = FiscalSequence.objects.get(pk=seq.pk)
    assert seq.get_next_encf() == "E320000000001"
    # Una instancia desactualizada no reutiliza el número: relee bajo bloqueo.
    assert stale.get_next_encf() == "E320000000002"
    assert stale.get_next_encf() is None
    seq.refresh_from_db()
    assert seq.current_number == 3
