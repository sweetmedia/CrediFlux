"""Borrar un tenant confirma: la auditoría del borrado queda a nivel plataforma (tenant=None).

Antes, `audit_post_delete` insertaba filas `AuditLog(tenant=<tenant en borrado>)` (del propio
tenant y de su dueño, en cascada) que el Collector no conocía: la FK diferida fallaba en el
COMMIT y deshacía todo el borrado. Ahora esas filas se escriben con `tenant=None` mientras dura
el borrado, la marca no sobrevive a un borrado fallido y las filas de plataforma no se ven
desde la API de tenant ni desde el admin de un staff de tenant.
"""
import contextvars
import uuid
from datetime import date
from unittest import mock

import pytest
from django.contrib import admin
from django.db import connection, transaction
from django.db.models.signals import post_delete, pre_delete
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.tenants.models import Domain, Tenant, is_tenant_being_deleted
from apps.users.models import User

pytestmark = pytest.mark.django_db

TENANT_HOST = "tenant.test.localhost"


def _tenant_with_owner(n):
    """Tenant sin schema, con dominio y dueño (como un registro pendiente)."""
    tenant = Tenant(
        schema_name=f"borrable{n}", name=f"Borrable {n}", business_name=f"Borrable {n} SRL",
        email=f"borrable{n}@crediflux.test",
    )
    tenant.auto_create_schema = False
    tenant.save(verbosity=0)
    Domain.objects.create(domain=f"borrable{n}.test.localhost", tenant=tenant, is_primary=True)
    User.objects.create_user(
        username=f"dueno-borrable{n}", email=f"dueno-borrable{n}@crediflux.test", password="x",
        tenant=tenant, is_tenant_owner=True, role="admin",
    )
    return tenant


def _assert_platform_trace(pk):
    """Ninguna fila apunta al tenant borrado y su borrado queda como fila de plataforma."""
    assert not Tenant.objects.filter(pk=pk).exists()
    assert not AuditLog.objects.filter(tenant_id=pk).exists()
    assert AuditLog.objects.filter(
        tenant__isnull=True, action="delete", model_name="Tenant", object_id=str(pk),
    ).exists()


def _platform_row():
    return AuditLog.objects.create(
        tenant=None, user_email="system@crediflux.app", action="delete",
        model_name="Tenant", object_id="999999", object_repr="Tenant borrado",
    )


# --- el borrado confirma -------------------------------------------------------------------

def test_tenant_delete_passes_deferred_fk_checks(public_schema):
    tenant = _tenant_with_owner(1)
    pk = tenant.pk
    assert AuditLog.objects.filter(tenant_id=pk).exists()  # historia previa del tenant

    with transaction.atomic():
        tenant.delete()
        connection.check_constraints()  # SET CONSTRAINTS ALL IMMEDIATE: lo que haría el COMMIT

    _assert_platform_trace(pk)
    assert not User.objects.filter(email="dueno-borrable1@crediflux.test").exists()
    # El dueño borrado en cascada también queda como fila de plataforma
    assert AuditLog.objects.filter(tenant__isnull=True, action="delete", model_name="User").exists()


def test_bulk_tenant_delete_passes_deferred_fk_checks(public_schema):
    pks = [_tenant_with_owner(2).pk, _tenant_with_owner(3).pk]

    with transaction.atomic():
        Tenant.objects.filter(pk__in=pks).delete()
        connection.check_constraints()

    for pk in pks:
        _assert_platform_trace(pk)


def _platform_superuser():
    return User.objects.create_user(
        username="plataforma-borrado", email="plataforma-borrado@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )


# --- la marca de "tenant en borrado" no se fuga ------------------------------------------

def test_failed_tenant_delete_does_not_leave_the_mark(public_schema):
    tenant = _tenant_with_owner(5)

    def boom(sender, instance, **kwargs):
        raise RuntimeError("borrado interrumpido")

    post_delete.connect(boom, sender=User, dispatch_uid="test-boom-tenant-delete")
    try:
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                tenant.delete()
    finally:
        post_delete.disconnect(sender=User, dispatch_uid="test-boom-tenant-delete")

    tenant = Tenant.objects.get(pk=tenant.pk)  # sigue vivo
    tenant.business_name = "Sigue Viva SRL"
    tenant.save()
    log = AuditLog.objects.filter(
        model_name="Tenant", object_id=str(tenant.pk), action="update",
    ).latest("timestamp")
    assert log.tenant_id == tenant.pk


def test_context_copied_inside_the_scope_does_not_keep_the_mark(public_schema):
    """Un contexto copiado durante el borrado (tarea asyncio, copy_context().run) no conserva el pk."""
    tenant = _tenant_with_owner(6)
    copied = []

    def copy_and_fail(sender, instance, **kwargs):
        copied.append(contextvars.copy_context())
        raise RuntimeError("borrado interrumpido")

    post_delete.connect(copy_and_fail, sender=User, dispatch_uid="test-copy-ctx-tenant-delete")
    try:
        with pytest.raises(RuntimeError):
            with transaction.atomic():
                tenant.delete()
    finally:
        post_delete.disconnect(sender=User, dispatch_uid="test-copy-ctx-tenant-delete")

    assert copied
    assert copied[0].run(is_tenant_being_deleted, tenant.pk) is False


def test_dependent_pre_delete_audit_is_written_as_platform_row(public_schema):
    """La marca existe antes de los pre_delete de la cascada (User va antes que Tenant)."""
    tenant = _tenant_with_owner(7)
    pk = tenant.pk

    def touch_owner(sender, instance, **kwargs):
        if instance.tenant_id == pk:
            instance.first_name = "Tocado"
            instance.save(update_fields=["first_name"])  # update auditado del usuario

    pre_delete.connect(touch_owner, sender=User, dispatch_uid="test-touch-owner-pre-delete")
    try:
        with transaction.atomic():
            tenant.delete()
            connection.check_constraints()
    finally:
        pre_delete.disconnect(sender=User, dispatch_uid="test-touch-owner-pre-delete")

    _assert_platform_trace(pk)
    assert AuditLog.objects.filter(
        tenant__isnull=True, action="update", model_name="User", changes__has_key="first_name",
    ).exists()


def test_request_user_of_the_deleted_tenant_is_not_linked(public_schema):
    """Si quien borra es usuario del tenant, la fila conserva su correo pero no el enlace."""
    tenant = _tenant_with_owner(8)
    pk = tenant.pk
    owner = User.objects.get(tenant=tenant, is_tenant_owner=True)
    request = RequestFactory().delete("/")
    request.user = owner

    with mock.patch("apps.audit.signals.get_current_request", return_value=request):
        with transaction.atomic():
            tenant.delete()
            connection.check_constraints()  # sin el arreglo: IntegrityError en user_id

    _assert_platform_trace(pk)
    log = AuditLog.objects.get(tenant__isnull=True, action="delete", model_name="Tenant", object_id=str(pk))
    assert log.user_id is None
    assert log.user_email == "dueno-borrable8@crediflux.test"


def test_delete_inside_a_live_tenant_keeps_its_tenant(tenant_schema):
    from apps.loans.models import Customer

    customer = Customer.objects.create(
        first_name="Cliente", last_name="Borrado", date_of_birth=date(1990, 1, 1),
        gender="F", email="borrado@crediflux.test", phone="+18095550000",
        address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
        id_type="cedula", id_number="001-0000099-1", employment_status="employed",
    )
    pk = customer.pk
    customer.delete()

    log = AuditLog.objects.get(model_name="Customer", object_id=str(pk), action="delete")
    assert log.tenant_id == tenant_schema.pk


# --- las filas de plataforma no se ven desde los tenants ---------------------------------

def test_api_user_without_tenant_sees_no_logs(tenant_schema):
    row = _platform_row()
    platform_admin = User.objects.create_user(
        username="sin-tenant", email="sin-tenant@crediflux.test", password="x",
        role="admin", is_superuser=True,
    )
    client = APIClient(HTTP_HOST=TENANT_HOST)
    client.force_authenticate(user=platform_admin)

    listing = client.get("/api/audit/")
    assert listing.status_code == 200
    results = listing.data["results"] if isinstance(listing.data, dict) else listing.data
    assert list(results) == []
    assert client.get(f"/api/audit/{row.id}/").status_code == 404
    stats = client.get("/api/audit/stats/")
    assert stats.status_code == 200 and stats.data["total_logs"] == 0


def test_tenant_admin_does_not_see_platform_rows(auth_client, tenant_schema):
    row = _platform_row()
    own = AuditLog.objects.create(
        tenant=tenant_schema, user_email="x@crediflux.test", action="create",
        model_name="Customer", object_id="1", object_repr="Cliente",
    )

    listing = auth_client.get("/api/audit/")
    assert listing.status_code == 200
    results = listing.data["results"] if isinstance(listing.data, dict) else listing.data
    ids = {str(item["id"]) for item in results}
    assert str(own.id) in ids
    assert str(row.id) not in ids
    assert auth_client.get(f"/api/audit/{row.id}/").status_code == 404


def test_django_admin_scopes_audit_logs_by_tenant(tenant_schema, admin_user):
    row = _platform_row()
    own = AuditLog.objects.create(
        tenant=tenant_schema, user_email="x@crediflux.test", action="create",
        model_name="Customer", object_id="1", object_repr="Cliente",
    )
    model_admin = admin.site._registry[AuditLog]

    staff_request = RequestFactory().get("/admin/audit/auditlog/")
    staff_request.user = admin_user
    staff_ids = set(model_admin.get_queryset(staff_request).values_list("id", flat=True))
    assert own.id in staff_ids and row.id not in staff_ids
    assert not model_admin.get_queryset(staff_request).exclude(tenant=tenant_schema).exists()

    platform_request = RequestFactory().get("/admin/audit/auditlog/")
    platform_request.user = _platform_superuser()
    platform_ids = set(model_admin.get_queryset(platform_request).values_list("id", flat=True))
    assert {own.id, row.id} <= platform_ids

    orphan = User.objects.create_user(
        username=f"staff-{uuid.uuid4().hex[:6]}", email="staff-sin-tenant@crediflux.test",
        password="x", is_staff=True,
    )
    orphan_request = RequestFactory().get("/admin/audit/auditlog/")
    orphan_request.user = orphan
    assert not model_admin.get_queryset(orphan_request).exists()
