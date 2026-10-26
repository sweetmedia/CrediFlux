"""Borrar tenants desde el admin: sólo el superusuario de plataforma y sólo registros pendientes.

- La cascada sobre `AuditLog` (cuyo admin no deja borrar a nadie) ya no bloquea el borrado del
  superusuario de plataforma: la historia del tenant se va con él y queda la fila de plataforma
  de la ronda 20. Cualquier otro modelo relacionado sin permiso sigue bloqueando.
- Ningún otro staff (superusuario con tenant, staff con `tenants.delete_tenant`) borra tenants.
- Un tenant aprovisionado no se borra desde el admin: su schema conserva filas con FK a
  `public.users_user` (p. ej. `created_by`) que la cascada, que corre en public, no ve; el
  COMMIT fallaría (test de investigación abajo). El admin lo rehúsa con un mensaje, sin 500.
- `AuditLogAdmin` sigue sin borrar filas para nadie.
"""
from datetime import date

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory
from django_tenants.utils import schema_context, schema_exists

from apps.audit.models import AuditLog
from apps.tenants.models import Domain, Tenant
from apps.users.models import User

pytestmark = pytest.mark.django_db

PUBLIC_HOST = "localhost"
TENANT_HOST = "tenant.test.localhost"
CHANGELIST = "/admin/tenants/tenant/"


def _delete_url(pk):
    return f"{CHANGELIST}{pk}/delete/"


def _pending_tenant(n):
    """Registro pendiente (sin schema) con dominio y dueño, como lo deja el registro público."""
    tenant = Tenant(
        schema_name=f"pendiente{n}", name=f"Pendiente {n}", business_name=f"Pendiente {n} SRL",
        email=f"pendiente{n}@crediflux.test", provisioning_pending=True, is_active=False,
    )
    tenant.auto_create_schema = False
    tenant.save(verbosity=0)
    Domain.objects.create(domain=f"pendiente{n}.test.localhost", tenant=tenant, is_primary=True)
    User.objects.create_user(
        username=f"dueno-pendiente{n}", email=f"dueno-pendiente{n}@crediflux.test", password="x",
        tenant=tenant, is_tenant_owner=True, role="admin", is_active=False,
    )
    assert AuditLog.objects.filter(tenant=tenant).exists()  # historia propia del tenant
    return tenant


def _platform_superuser():
    return User.objects.create_user(
        username="plataforma-admin", email="plataforma-admin@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )


def _client(user, host=PUBLIC_HOST):
    client = Client(HTTP_HOST=host)
    client.force_login(user)
    return client


def _messages(response):
    return [str(m) for m in response.wsgi_request._messages]


def _assert_deleted_with_platform_trace(pk):
    connection.check_constraints()  # SET CONSTRAINTS ALL IMMEDIATE: lo que haría el COMMIT
    assert not Tenant.objects.filter(pk=pk).exists()
    assert not AuditLog.objects.filter(tenant_id=pk).exists()
    assert AuditLog.objects.filter(
        tenant__isnull=True, action="delete", model_name="Tenant", object_id=str(pk),
    ).exists()


@pytest.fixture
def platform_client(public_schema):
    return _client(_platform_superuser())


# --- superusuario de plataforma: borra registros pendientes --------------------------------

def test_platform_superuser_deletes_a_pending_tenant_from_delete_view(platform_client):
    tenant = _pending_tenant(1)
    audit_rows = AuditLog.objects.filter(tenant=tenant).count()

    confirm = platform_client.get(_delete_url(tenant.pk))
    assert confirm.status_code == 200
    assert not confirm.context["perms_lacking"]  # AuditLog ya no bloquea
    assert not confirm.context["protected"]
    # La historia del tenant se va con él y la confirmación lo dice
    assert dict(confirm.context["model_count"]).get("Registros de Auditoria") == audit_rows

    response = platform_client.post(_delete_url(tenant.pk), {"post": "yes"})
    assert response.status_code == 302
    _assert_deleted_with_platform_trace(tenant.pk)
    assert not User.objects.filter(email="dueno-pendiente1@crediflux.test").exists()


def test_platform_superuser_bulk_deletes_pending_tenants(platform_client):
    pks = [_pending_tenant(2).pk, _pending_tenant(3).pk]
    data = {"action": "delete_selected", "_selected_action": pks}

    confirm = platform_client.post(CHANGELIST, data)
    assert confirm.status_code == 200
    assert not confirm.context["perms_lacking"]

    response = platform_client.post(CHANGELIST, {**data, "post": "yes"})
    assert response.status_code == 302
    for pk in pks:
        _assert_deleted_with_platform_trace(pk)


def test_bulk_delete_goes_through_the_tenant_deletion_scope(platform_client, monkeypatch):
    """`delete_queryset` usa `TenantQuerySet.delete()` (ámbito `tenant_deletion` de la ronda 20)."""
    from apps.tenants.models import TenantQuerySet

    calls = []
    original = TenantQuerySet.delete

    def spy(self):
        calls.append(sorted(self.values_list("pk", flat=True)))
        return original(self)

    monkeypatch.setattr(TenantQuerySet, "delete", spy)
    pk = _pending_tenant(4).pk
    response = platform_client.post(
        CHANGELIST, {"action": "delete_selected", "_selected_action": [pk], "post": "yes"},
    )
    assert response.status_code == 302
    assert calls == [[pk]]
    _assert_deleted_with_platform_trace(pk)


def test_other_related_model_without_delete_permission_still_blocks(platform_client, monkeypatch):
    """Sólo AuditLog deja de contar: otro modelo de la cascada sin permiso sigue bloqueando."""
    tenant = _pending_tenant(5)
    domain_admin = admin.site._registry[Domain]
    monkeypatch.setattr(domain_admin, "has_delete_permission", lambda request, obj=None: False)

    confirm = platform_client.get(_delete_url(tenant.pk))
    assert confirm.status_code == 200
    assert set(confirm.context["perms_lacking"]) == {str(Domain._meta.verbose_name)}

    assert platform_client.post(_delete_url(tenant.pk), {"post": "yes"}).status_code == 403
    assert Tenant.objects.filter(pk=tenant.pk).exists()


# --- tenants aprovisionados ----------------------------------------------------------------

def test_investigation_provisioned_tenant_delete_fails_at_commit(tenant, public_schema):
    """Punto 4 del brief: la cascada corre en public y no ve las filas del schema del tenant.

    `Customer.created_by` (SET_NULL) se actualiza en `public.loans_customer`, no en
    `test.loans_customer`: la FK diferida a `public.users_user` falla en el COMMIT.
    """
    from apps.loans.models import Customer

    owner = User.objects.create_user(
        username="dueno-aprovisionado", email="dueno-aprovisionado@crediflux.test", password="x",
        tenant=tenant, role="admin",
    )
    with schema_context(tenant.schema_name):
        Customer.objects.create(
            first_name="Cliente", last_name="Aprovisionado", date_of_birth=date(1990, 1, 1),
            gender="F", email="aprovisionado@crediflux.test", phone="+18095550001",
            address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
            id_type="cedula", id_number="001-0000098-1", employment_status="employed",
            created_by=owner,
        )

    victim = Tenant.objects.get(pk=tenant.pk)  # instancia propia: delete() anula el pk
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            victim.delete()
            connection.check_constraints()

    assert Tenant.objects.filter(pk=tenant.pk).exists()


def test_admin_refuses_to_delete_a_provisioned_tenant(platform_client, tenant):
    for method, data in (("get", None), ("post", {"post": "yes"})):
        response = getattr(platform_client, method)(_delete_url(tenant.pk), data)
        assert response.status_code == 302
        assert response["Location"] == f"{CHANGELIST}{tenant.pk}/change/"
        assert any("schema aprovisionado" in m for m in _messages(response))

    assert Tenant.objects.filter(pk=tenant.pk).exists()
    assert schema_exists(tenant.schema_name)


def test_admin_refuses_to_delete_the_public_tenant(platform_client):
    public = Tenant.objects.get(schema_name="public")
    response = platform_client.post(_delete_url(public.pk), {"post": "yes"})
    assert response.status_code == 302
    assert Tenant.objects.filter(pk=public.pk).exists()


def test_bulk_delete_with_a_provisioned_tenant_deletes_none(platform_client, tenant):
    pending = _pending_tenant(6)
    data = {"action": "delete_selected", "_selected_action": [pending.pk, tenant.pk]}

    for extra in ({}, {"post": "yes"}):
        response = platform_client.post(CHANGELIST, {**data, **extra})
        assert response.status_code == 302
        assert any("schema aprovisionado" in m for m in _messages(response))

    assert Tenant.objects.filter(pk__in=[pending.pk, tenant.pk]).count() == 2


def test_delete_model_decides_on_the_locked_row(public_schema):
    """Si el pendiente se aprovisiona entre la confirmación y el borrado: 403, no 500."""
    from django.core.exceptions import PermissionDenied

    model_admin = admin.site._registry[Tenant]
    stale = _pending_tenant(7)
    Tenant.objects.filter(pk=stale.pk).update(provisioning_pending=False)  # otro operador
    request = RequestFactory().post(_delete_url(stale.pk))
    request.user = _platform_superuser()

    with pytest.raises(PermissionDenied):
        model_admin.delete_model(request, stale)
    with pytest.raises(PermissionDenied):
        model_admin.delete_queryset(request, Tenant.objects.filter(pk=stale.pk))
    assert Tenant.objects.filter(pk=stale.pk).exists()


# --- nadie más borra tenants ---------------------------------------------------------------

def _tenant_superuser(tenant):
    return User.objects.create_user(
        username="super-de-tenant", email="super-de-tenant@crediflux.test", password="x",
        tenant=tenant, is_superuser=True, is_staff=True, role="admin",
    )


def _tenant_staff_with_model_perm(tenant):
    staff = User.objects.create_user(
        username="staff-con-permiso", email="staff-con-permiso@crediflux.test", password="x",
        tenant=tenant, is_staff=True, role="admin",
    )
    staff.user_permissions.add(*Permission.objects.filter(
        content_type__app_label="tenants", codename__in=["view_tenant", "change_tenant", "delete_tenant"],
    ))
    return User.objects.get(pk=staff.pk)  # sin la caché de permisos


@pytest.mark.parametrize("make_user", [_tenant_superuser, _tenant_staff_with_model_perm])
def test_other_staff_cannot_delete_tenants(make_user, tenant, public_schema):
    user = make_user(tenant)
    pending = _pending_tenant(8)
    model_admin = admin.site._registry[Tenant]
    request = RequestFactory().get(CHANGELIST)
    request.user = user

    assert model_admin.has_delete_permission(request) is False
    assert model_admin.has_delete_permission(request, pending) is False
    assert "delete_selected" not in model_admin.get_actions(request)

    client = _client(user, host=TENANT_HOST)
    assert client.post(_delete_url(pending.pk), {"post": "yes"}).status_code == 403
    client.post(CHANGELIST, {"action": "delete_selected", "_selected_action": [pending.pk], "post": "yes"})
    assert Tenant.objects.filter(pk=pending.pk).exists()


# --- AuditLogAdmin sigue sin borrar --------------------------------------------------------

def test_platform_superuser_cannot_delete_audit_rows(platform_client):
    row = AuditLog.objects.create(
        tenant=None, user_email="system@crediflux.app", action="delete",
        model_name="Tenant", object_id="999999", object_repr="Tenant borrado",
    )
    model_admin = admin.site._registry[AuditLog]
    request = RequestFactory().get("/admin/audit/auditlog/")
    request.user = User.objects.get(email="plataforma-admin@crediflux.test")

    assert model_admin.has_delete_permission(request) is False
    assert model_admin.has_delete_permission(request, row) is False
    assert "delete_selected" not in model_admin.get_actions(request)

    assert platform_client.get(f"/admin/audit/auditlog/{row.pk}/delete/").status_code == 403
    assert platform_client.post(f"/admin/audit/auditlog/{row.pk}/delete/", {"post": "yes"}).status_code == 403
    forged = platform_client.post(
        "/admin/audit/auditlog/", {"action": "delete_selected", "_selected_action": [row.pk], "post": "yes"},
    )
    assert forged.status_code in (200, 302)  # "ninguna acción seleccionada": la acción no existe
    assert AuditLog.objects.filter(pk=row.pk).exists()
