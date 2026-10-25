"""Registro de tenants por encima del tope global: queda pendiente en vez de rechazarse (run-4).

El tope global diario (MAX_TENANTS_PER_DAY) lo llenaba un solo solicitante con pocas
identidades de red y después cada alta legítima recibía el 400 genérico. Ahora el tope
sólo limita el aprovisionamiento automático: por encima, el registro se guarda pendiente
(sin schema, tenant y dueño inactivos) y un superusuario lo aprovisiona después.
"""
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory, override_settings
from django.utils import timezone
from django_tenants.utils import schema_exists

from apps.tenants.models import Domain, Tenant
from apps.users.models import User

from .test_security_registration import GENERIC, URL, payload

pytestmark = pytest.mark.django_db

PENDING_MESSAGE = 'Registro recibido. Su cuenta quedará activa tras la revisión.'


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def no_schema(monkeypatch):
    monkeypatch.setattr(Tenant, "auto_create_schema", False)


@pytest.fixture
def no_recent_tenants(public_schema):
    Tenant.objects.update(created_on=timezone.now() - timedelta(days=2))


def _register(client, n, ip):
    data = payload(tenant_name=f"financiera-{n}", subdomain=f"financiera-{n}", owner_email=f"dueno{n}@nueva.test")
    return client.post(URL, data, format="json", REMOTE_ADDR=ip)


def _day_budget():
    return cache.get(f"tenant_provisioning:{timezone.now():%Y%m%d}") or 0


# --- (a) por encima del tope global: 202 pendiente, sin schema ---------------------------

def test_registration_over_the_global_cap_is_pending_not_rejected(public_client, no_schema, no_recent_tenants,
                                                                   monkeypatch, settings):
    assert settings.MAX_TENANTS_PER_DAY == 20 and settings.MAX_TENANTS_PER_IP_PER_DAY == 2
    for n in range(20):  # 10 identidades, 2 altas cada una: el tope global queda lleno
        assert _register(public_client, n, f"198.51.100.{n // 2}").status_code == 201

    # Si el camino pendiente aprovisionara, ahora crearía el schema de verdad.
    monkeypatch.setattr(Tenant, "auto_create_schema", True)
    response = _register(public_client, 99, "203.0.113.50")

    assert response.status_code == 202, response.content
    body = response.json()
    assert body == {"status": "pending", "message": PENDING_MESSAGE}
    tenant = Tenant.objects.get(name="financiera-99")
    assert tenant.provisioning_pending is True
    assert tenant.pending_since is not None
    assert tenant.is_active is False
    assert not schema_exists(tenant.schema_name)
    owner = User.objects.get(email="dueno99@nueva.test")
    assert owner.tenant_id == tenant.pk and owner.is_tenant_owner
    assert owner.is_active is False
    assert Domain.objects.filter(tenant=tenant, domain="financiera-99").exists()


def test_pending_tenants_do_not_count_as_provisioned(public_client, no_schema, no_recent_tenants):
    with override_settings(MAX_TENANTS_PER_DAY=0):
        assert _register(public_client, 1, "198.51.100.1").status_code == 202
    cache.clear()
    with override_settings(MAX_TENANTS_PER_DAY=1):
        assert _register(public_client, 2, "198.51.100.2").status_code == 201


# --- (b) el presupuesto por cliente sigue aplicando ---------------------------------------

@override_settings(MAX_TENANTS_PER_DAY=1, MAX_TENANTS_PER_IP_PER_DAY=2)
def test_client_budget_still_applies_when_the_global_cap_is_reached(public_client, no_schema, no_recent_tenants):
    ip = "198.51.100.20"
    assert _register(public_client, 1, ip).status_code == 201
    assert _register(public_client, 2, ip).status_code == 202
    before = Tenant.objects.count()
    response = _register(public_client, 3, ip)
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert Tenant.objects.count() == before


# --- (c) tope de registros pendientes -----------------------------------------------------

@override_settings(MAX_TENANTS_PER_DAY=0, MAX_PENDING_REGISTRATIONS_PER_DAY=1)
def test_pending_cap_rejects_with_the_generic_message(public_client, no_schema, no_recent_tenants):
    assert _register(public_client, 1, "198.51.100.1").status_code == 202
    before = (Tenant.objects.count(), User.objects.count(), Domain.objects.count())
    response = _register(public_client, 2, "198.51.100.2")
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert (Tenant.objects.count(), User.objects.count(), Domain.objects.count()) == before


# --- (d) aprovisionamiento: acción del admin y comando ------------------------------------

@pytest.fixture
def pending_tenant(public_client, no_recent_tenants):
    with override_settings(MAX_TENANTS_PER_DAY=0):
        assert _register(public_client, 7, "198.51.100.7").status_code == 202
    cache.clear()
    return Tenant.objects.get(name="financiera-7")


def _admin_request(user):
    request = RequestFactory().post("/admin/tenants/tenant/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def _run_action(user, queryset):
    from django.contrib import admin

    model_admin = admin.site._registry[Tenant]
    model_admin.provision_pending_action(_admin_request(user), queryset)


def _assert_provisioned(tenant):
    tenant.refresh_from_db()
    assert tenant.provisioning_pending is False
    assert tenant.is_active is True
    assert User.objects.get(tenant=tenant, is_tenant_owner=True).is_active is True


def test_admin_action_provisions_a_pending_tenant(pending_tenant, public_schema):
    superuser = User.objects.create_user(
        username="plataforma", email="plataforma@crediflux.test", password="x", is_superuser=True, is_staff=True,
    )
    provisioned = Tenant.objects.filter(provisioning_pending=False).exclude(schema_name="public").first()
    assert not schema_exists(pending_tenant.schema_name)

    _run_action(superuser, Tenant.objects.filter(pk__in=[pending_tenant.pk, provisioned.pk]))

    _assert_provisioned(pending_tenant)
    assert schema_exists(pending_tenant.schema_name)
    assert _day_budget() == 1  # sólo el pendiente cuenta; el ya aprovisionado se salta
    provisioned.refresh_from_db()
    assert provisioned.provisioning_pending is False


def test_non_superuser_cannot_run_the_provisioning_action(pending_tenant, public_schema, monkeypatch):
    staff = User.objects.create_user(
        username="staff", email="staff@crediflux.test", password="x", is_staff=True,
    )
    calls = []
    monkeypatch.setattr(Tenant, "create_schema", lambda self, *a, **kw: calls.append(self.pk))
    _run_action(staff, Tenant.objects.filter(pk=pending_tenant.pk))
    pending_tenant.refresh_from_db()
    assert pending_tenant.provisioning_pending is True
    assert pending_tenant.is_active is False
    assert calls == []
    assert _day_budget() == 0


def test_provisioning_action_is_hidden_from_non_superusers(public_schema):
    from django.contrib import admin

    staff = User.objects.create_user(
        username="staff2", email="staff2@crediflux.test", password="x", is_staff=True,
    )
    model_admin = admin.site._registry[Tenant]
    assert "provision_pending_action" not in model_admin.get_actions(_admin_request(staff))


def test_management_command_provisions_pending_tenants(pending_tenant, public_schema, monkeypatch):
    created = []

    def fake_create_schema(self, check_if_exists=False, sync_schema=True, verbosity=1):
        created.append(self.schema_name)

    monkeypatch.setattr(Tenant, "create_schema", fake_create_schema)
    out = StringIO()
    call_command("provision_pending_tenants", stdout=out)

    assert created == [pending_tenant.schema_name]  # sólo el pendiente
    _assert_provisioned(pending_tenant)
    assert _day_budget() == 1
    assert "1" in out.getvalue()

    created.clear()
    call_command("provision_pending_tenants", stdout=StringIO())
    assert created == []


def test_management_command_respects_limit(public_client, no_schema, no_recent_tenants, monkeypatch):
    with override_settings(MAX_TENANTS_PER_DAY=0):
        for n in (1, 2):
            assert _register(public_client, n, f"198.51.100.{n}").status_code == 202
    cache.clear()
    monkeypatch.setattr(Tenant, "create_schema", lambda self, *a, **kw: None)
    call_command("provision_pending_tenants", "--limit", "1", stdout=StringIO())
    assert Tenant.objects.filter(provisioning_pending=True).count() == 1


# --- un tenant pendiente no sirve peticiones en su dominio --------------------------------

def test_pending_tenant_domain_answers_404(pending_tenant, monkeypatch):
    from rest_framework.test import APIClient

    from apps.tenants.provisioning import provision_pending_tenant

    client = APIClient(HTTP_HOST="financiera-7")
    assert client.get("/api/loans/").status_code == 404

    # Control: el mismo dominio ya aprovisionado llega a la vista (401 sin credenciales).
    monkeypatch.setattr(Tenant, "create_schema", lambda self, *a, **kw: None)
    assert provision_pending_tenant(pending_tenant.pk) is True
    assert client.get("/api/loans/").status_code == 401


# --- Fix round 19.1 ----------------------------------------------------------------------

def test_migrate_schemas_skips_pending_tenants(pending_tenant):
    # C1: con un pendiente (sin schema), migrate_schemas fallaba con
    # "no schema has been selected to create in" y el backend no arrancaba.
    call_command("migrate_schemas", interactive=False, verbosity=0)
    assert not schema_exists(pending_tenant.schema_name)


def test_executor_keeps_public_and_existing_schemas(pending_tenant):
    from apps.tenants.migration_executors import _skip_missing

    assert _skip_missing(["public", "test", pending_tenant.schema_name]) == ["public", "test"]


def test_provisioned_excludes_public_and_pending(pending_tenant):
    schemas = set(Tenant.objects.provisioned().values_list("schema_name", flat=True))
    assert "test" in schemas
    assert "public" not in schemas
    assert pending_tenant.schema_name not in schemas


def test_late_fee_task_skips_pending_tenants(pending_tenant, monkeypatch):
    # I1: schema_context(<pendiente>) dejaba el search_path en el schema público.
    from apps.loans import tasks

    seen = []
    monkeypatch.setattr(tasks, "call_command", lambda name, tenant: seen.append(tenant))
    result = tasks.calculate_late_fees(force=True)
    assert "test" in seen
    assert pending_tenant.schema_name not in seen
    assert pending_tenant.schema_name not in result["processed"] + result["failed"]


def test_late_fee_command_refuses_a_pending_tenant(pending_tenant):
    out = StringIO()
    call_command("calculate_late_fees", tenant=pending_tenant.schema_name, stdout=out)
    assert "not found" in out.getvalue()


def test_admin_save_of_a_pending_tenant_does_not_create_its_schema(pending_tenant, public_schema):
    # M2: TenantMixin.save crea el schema de un tenant existente sin schema.
    from django.contrib import admin

    model_admin = admin.site._registry[Tenant]
    superuser = User.objects.create_user(
        username="plataforma3", email="plataforma3@crediflux.test", password="x", is_superuser=True, is_staff=True,
    )
    tenant = Tenant.objects.get(pk=pending_tenant.pk)
    tenant.business_name = "Otro nombre"
    model_admin.save_model(_admin_request(superuser), tenant, form=None, change=True)
    tenant.refresh_from_db()
    assert tenant.business_name == "Otro nombre"
    assert tenant.provisioning_pending is True
    assert not schema_exists(tenant.schema_name)


def test_provisioning_migrates_a_schema_that_already_exists(pending_tenant, public_schema, monkeypatch):
    # M3: con el schema ya creado, save() no migra: el aprovisionamiento lo hace explícitamente.
    from django.db import connection

    from apps.tenants import provisioning

    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{pending_tenant.schema_name}"')
    migrated = []
    monkeypatch.setattr(provisioning, "call_command",
                        lambda name, **kw: migrated.append((name, kw.get("schema_name"), kw.get("tenant"))))
    assert provisioning.provision_pending_tenant(pending_tenant.pk) is True
    assert migrated == [("migrate_schemas", pending_tenant.schema_name, True)]
    _assert_provisioned(pending_tenant)


def test_management_command_rejects_limit_below_one(pending_tenant):
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("provision_pending_tenants", "--limit", "0", stdout=StringIO())
    pending_tenant.refresh_from_db()
    assert pending_tenant.provisioning_pending is True


def test_pending_domain_404_matches_an_unknown_host(pending_tenant):
    # M5: el 404 de un pendiente no se distingue del de un host sin tenant.
    from rest_framework.test import APIClient

    pending = APIClient(HTTP_HOST="financiera-7").get("/api/loans/")
    unknown = APIClient(HTTP_HOST="no-existe-este-host").get("/api/loans/")
    assert pending.status_code == unknown.status_code == 404
    assert pending.content == unknown.content
    assert pending.get("Content-Type") == unknown.get("Content-Type")


def test_expire_pending_registrations(public_client, no_schema, no_recent_tenants):
    with override_settings(MAX_TENANTS_PER_DAY=0):
        assert _register(public_client, 1, "198.51.100.1").status_code == 202
        assert _register(public_client, 2, "198.51.100.2").status_code == 202
    old = Tenant.objects.get(name="financiera-1")
    Tenant.objects.filter(pk=old.pk).update(pending_since=timezone.now() - timedelta(days=8))
    provisioned_count = Tenant.objects.filter(provisioning_pending=False).count()

    out = StringIO()
    call_command("expire_pending_registrations", "--days", "7", stdout=out)

    assert not Tenant.objects.filter(pk=old.pk).exists()
    assert not User.objects.filter(email="dueno1@nueva.test").exists()
    assert not Domain.objects.filter(domain="financiera-1").exists()
    assert Tenant.objects.filter(name="financiera-2", provisioning_pending=True).exists()
    assert Tenant.objects.filter(provisioning_pending=False).count() == provisioned_count
    assert "1" in out.getvalue()
    # Sin rodeo: el borrado confirma y deja su traza a nivel plataforma (tenant=None)
    from django.db import connection

    from apps.audit.models import AuditLog

    connection.check_constraints()  # lo que haría el COMMIT con las FK diferidas
    assert not AuditLog.objects.filter(tenant_id=old.pk).exists()
    assert AuditLog.objects.filter(
        tenant__isnull=True, action="delete", model_name="Tenant", object_id=str(old.pk),
    ).exists()


def test_expire_pending_registrations_rejects_days_below_one():
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("expire_pending_registrations", "--days", "0", stdout=StringIO())
