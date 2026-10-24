"""Audit log: sin secretos, con el tenant del schema y sin caché global de snapshots.

Cubre: un PATCH de settings con `smtp_password` (y otros secretos) no deja el valor en
`changes` (ni old ni new) ni en los snapshots; un movimiento de caja (API) y una
factura (ORM) generan `AuditLog` con el tenant del schema aunque el modelo no tenga
FK a tenant; tras N PATCH de clientes no queda dict de módulo `_pre_save_instances`
ni el snapshot colgado de la instancia.
"""

import json
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.audit import signals
from apps.audit.models import AuditLog

TENANT_HOST = "tenant.test.localhost"
SMTP_SECRET = "SmtpS3cret-NoDebeAparecer"
AI_SECRET = "sk-ai-NoDebeAparecer"
WA_SECRET = "wa-token-NoDebeAparecer"
CERT_SECRET = "CertPw-NoDebeAparecer"


def _fresh_client(user):
    """Cliente con el usuario recargado: el PATCH no toca el tenant de sesión en memoria."""
    from apps.users.models import User

    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=User.objects.select_related("tenant").get(pk=user.pk))
    return client


def _customer(n):
    from apps.loans.models import Customer

    return Customer.objects.create(
        first_name=f"Cliente{n}", last_name="Auditado", date_of_birth=date(1990, 1, 1),
        gender="F", email=f"audit{n}@crediflux.test", phone="+18095550000",
        address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
        id_type="cedula", id_number=f"001-00000{n:02d}-1", employment_status="employed",
    )


def test_settings_patch_never_logs_secrets(admin_user, tenant_schema):
    client = _fresh_client(admin_user)
    response = client.patch(
        "/api/tenants/settings/",
        {
            "smtp_password": SMTP_SECRET,
            "ai_api_key": AI_SECRET,
            "whatsapp_token": WA_SECRET,
            "smtp_host": "smtp.audit.test",
        },
        format="json",
    )
    assert response.status_code == 200, response.data

    log = AuditLog.objects.filter(
        model_name="Tenant", object_id=str(tenant_schema.pk), action="update"
    ).latest("timestamp")
    assert log.tenant_id == tenant_schema.id
    # El cambio no secreto sí queda registrado
    assert log.changes["smtp_host"]["new"] == "smtp.audit.test"
    for field in ("smtp_password", "ai_api_key", "whatsapp_token"):
        assert field not in log.changes
    dumped = json.dumps(log.changes)
    for secret in (SMTP_SECRET, AI_SECRET, WA_SECRET):
        assert secret not in dumped


@pytest.mark.parametrize(
    "name",
    [
        "smtp_password", "imap_password", "whatsapp_access_token", "whatsapp_app_secret",
        "whatsapp_verify_token", "ai_api_key", "nexconnect_api_key", "certificate_password",
        "stripe_secret_key", "paypal_client_secret", "ecf_provider_api_key", "Some_TOKEN_x",
    ],
)
def test_sensitive_field_names_are_excluded(name):
    assert name in signals.EXCLUDED_FIELDS or signals.is_sensitive_field(name)


def test_certificate_snapshots_have_no_password(tenant_schema):
    from django.core.files.base import ContentFile

    from apps.billing.models import DigitalCertificate

    cert = DigitalCertificate(name="Cert audit", certificate_password=CERT_SECRET)
    cert.certificate_file.save("audit.p12", ContentFile(b"x"), save=False)
    cert.save()
    log = AuditLog.objects.get(
        model_name="DigitalCertificate", object_id=str(cert.pk), action="create"
    )
    assert log.tenant_id == tenant_schema.id
    assert CERT_SECRET not in json.dumps(log.changes)

    cert.certificate_password = CERT_SECRET + "-2"
    cert.name = "Cert audit renombrado"
    cert.save()
    log = AuditLog.objects.get(
        model_name="DigitalCertificate", object_id=str(cert.pk), action="update"
    )
    assert "certificate_password" not in log.changes
    assert CERT_SECRET not in json.dumps(log.changes)

    cert_pk = str(cert.pk)
    cert.delete()
    log = AuditLog.objects.get(model_name="DigitalCertificate", object_id=cert_pk, action="delete")
    assert log.tenant_id == tenant_schema.id
    assert CERT_SECRET not in json.dumps(log.changes)


def test_cash_movement_is_logged_with_schema_tenant(user_factory, tenant_schema):
    from apps.cashbox.models import CashMovement, CashRegister

    register = CashRegister.objects.create(name="Caja Audit", code="CAJA-AUD-01")
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=user_factory(role="cashier"))
    response = client.post(
        "/api/cashbox/sessions/open/",
        {"register": str(register.id), "opening_balance": "1000.00"},
        format="json",
    )
    assert response.status_code == 201, response.data
    session_id = response.data["id"]
    response = client.post(
        "/api/cashbox/movements/",
        {
            "session": str(session_id), "movement_type": "inflow",
            "category": "loan_payment", "amount": "500.00", "description": "Pago",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    movement = CashMovement.objects.get(session_id=session_id)

    log = AuditLog.objects.get(model_name="CashMovement", object_id=str(movement.pk))
    assert log.action == "create"
    assert log.tenant_id == tenant_schema.id
    assert AuditLog.objects.filter(
        model_name="CashSession", object_id=str(session_id), tenant_id=tenant_schema.id
    ).exists()


def test_invoice_is_logged_with_schema_tenant(tenant_schema):
    from apps.billing.models import FiscalSequence, Invoice

    invoice = Invoice.objects.create(
        customer=_customer(1), ecf_type="32", issue_date=date.today(),
        comprador_rnc="101010101", comprador_razon_social="Cliente SRL",
    )
    log = AuditLog.objects.get(model_name="Invoice", object_id=str(invoice.pk), action="create")
    assert log.tenant_id == tenant_schema.id

    invoice.comprador_razon_social = "Cliente Cambiado SRL"
    invoice.save()
    log = AuditLog.objects.get(model_name="Invoice", object_id=str(invoice.pk), action="update")
    assert log.tenant_id == tenant_schema.id
    assert log.changes["comprador_razon_social"]["new"] == "Cliente Cambiado SRL"
    assert signals.should_track_model(FiscalSequence())


def test_contract_key_points_to_real_module():
    from apps.loans.models_contracts import Contract

    assert "apps.loans.models_contracts.Contract" in signals.TRACKED_MODELS
    assert "apps.contracts.models.Contract" not in signals.TRACKED_MODELS
    assert f"{Contract.__module__}.Contract" in signals.TRACKED_MODELS


def test_no_module_level_pre_save_cache(admin_user, tenant_schema):
    client = _fresh_client(admin_user)
    customers = [_customer(n) for n in range(10, 15)]
    for i, customer in enumerate(customers):
        response = client.patch(
            f"/api/loans/customers/{customer.pk}/", {"city": f"Santiago {i}"}, format="json"
        )
        assert response.status_code == 200, response.data
        assert AuditLog.objects.filter(
            model_name="Customer", object_id=str(customer.pk), action="update",
            tenant_id=tenant_schema.id,
        ).exists()

    assert not hasattr(signals, "_pre_save_instances")

    customer = customers[0]
    customer.city = "La Vega"
    customer.save()
    assert "_audit_old_instance" not in customer.__dict__
    # Un save sin cambios (post_save retorna temprano) tampoco deja el snapshot
    customer.save()
    assert "_audit_old_instance" not in customer.__dict__


# ---------------------------------------------------------------------------
# Fix round 1
# ---------------------------------------------------------------------------


def test_schema_context_wins_over_request_tenant(tenant, public_schema):
    """Un request del host público que corre bajo schema_context(B) registra el tenant B."""
    from types import SimpleNamespace

    from django_tenants.utils import schema_context

    from apps.audit import middleware
    from apps.billing.models import Invoice

    middleware._thread_locals.request = SimpleNamespace(
        tenant=public_schema, user=None, META={"REMOTE_ADDR": "127.0.0.1"}
    )
    try:
        with schema_context(tenant.schema_name):
            invoice = Invoice.objects.create(
                customer=_customer(2), ecf_type="32", issue_date=date.today(),
                comprador_rnc="101010101", comprador_razon_social="Webhook SRL",
            )
            log = AuditLog.objects.get(
                model_name="Invoice", object_id=str(invoice.pk), action="create"
            )
    finally:
        del middleware._thread_locals.request
    assert log.tenant_id == tenant.id


def test_invoice_xml_blobs_are_not_logged(tenant_schema):
    from apps.billing.models import Invoice

    invoice = Invoice.objects.create(
        customer=_customer(3), ecf_type="32", issue_date=date.today(),
        comprador_rnc="101010101", comprador_razon_social="Cliente SRL",
    )
    invoice.xml_content = "<ECF>" + "x" * 5000 + "</ECF>"
    invoice.signed_xml = "<ECF signed/>"
    invoice.dgii_response = {"estado": "Aceptado"}
    invoice.notes = "enviada"
    invoice.save()
    log = AuditLog.objects.get(model_name="Invoice", object_id=str(invoice.pk), action="update")
    assert "notes" in log.changes
    for field in ("xml_content", "signed_xml", "dgii_response"):
        assert field not in log.changes


def test_failed_audit_insert_does_not_break_outer_transaction(tenant_schema):
    """Un INSERT de auditoría que falla en la BD no deja rota la transacción del caller."""
    from unittest import mock

    from django.db import connection, transaction

    from apps.loans.models import Customer

    def failing_create(**kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1/0")  # error real de Postgres: aborta la transacción

    customer = _customer(4)
    with transaction.atomic():
        with mock.patch.object(AuditLog.objects, "create", side_effect=failing_create):
            customer.city = "Moca"
            customer.save()
        # La transacción externa sigue usable
        assert Customer.objects.filter(pk=customer.pk, city="Moca").exists()


def test_audit_client_ip_honours_num_proxies():
    """La IP del audit log es la del cliente según NUM_PROXIES, no el primer valor de XFF."""
    from django.conf import settings
    from django.test import RequestFactory, override_settings

    from apps.audit.middleware import get_client_ip

    request = RequestFactory().get(
        "/", REMOTE_ADDR="172.18.0.5", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9"
    )
    with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}):
        assert get_client_ip(request) == "203.0.113.9"
    with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": 0}):
        assert get_client_ip(request) == "172.18.0.5"
