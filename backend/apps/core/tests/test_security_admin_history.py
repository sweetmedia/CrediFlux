"""El historial de objetos del admin en el host de un tenant no muestra entradas de otro tenant.

`django.contrib.admin` está sólo en SHARED_APPS: `django_admin_log` es una única tabla en el
schema público. `ModelAdmin.history_view` filtra `LogEntry` sólo por `object_id` y
`content_type`, que son iguales en todos los schemas, y los modelos de tenant con pk entera
repiten pks entre tenants: `/admin/communications/email/<pk>/history/` en el host del tenant A
mostraba las entradas de la fila con el mismo pk del tenant B (quién la cambió, cuándo y el
mensaje de cambio).

Ahora `TenantHistoryMixin` deja en el host de un tenant sólo las entradas escritas por usuarios
de ese tenant; en el host público el historial no cambia. Un test recorre el registro del admin
para que un admin futuro de un modelo de tenant no quede sin el filtro. El panel de acciones
recientes no se toca: Django y Unfold lo filtran por el usuario que pide, y el índice propio
(`templates/admin/index.html`) no lo muestra.
"""
import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client

from apps.communications.models import Email
from apps.core.admin_mixins import TenantHistoryMixin
from apps.users.models import User

pytestmark = pytest.mark.django_db

PUBLIC_HOST = "localhost"
TENANT_HOST = "tenant.test.localhost"
FOREIGN_USERNAME = "ajeno-r27"
FOREIGN_MESSAGE = "Cambiado subject-secreto-del-tenant-B"
OWN_USERNAME = "propio-r27"
OWN_MESSAGE = "Cambiado subject-propio-del-tenant-A"


@pytest.fixture
def email(tenant):
    connection.set_tenant(tenant)
    row = Email.objects.create(
        from_email="a@financiera.test", to_email="b@financiera.test",
        subject="correo-r27", body_text="x",
    )
    connection.set_schema_to_public()
    return row


def _log(user, row, message):
    """Entrada del log con el mismo `content_type` y `object_id` que la fila del tenant A."""
    return LogEntry.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(Email),
        object_id=str(row.pk),
        object_repr=str(row),
        action_flag=CHANGE,
        change_message=message,
    )


def _staff(tenant, name, codenames):
    staff = User.objects.create_user(
        username=name, email=f"{name}@financiera.test", password="x",
        tenant=tenant, is_staff=True, role="viewer",
    )
    staff.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return User.objects.get(pk=staff.pk)  # sin la caché de permisos


def _platform_superuser():
    return User.objects.create_user(
        username="plataforma-r27", email="plataforma-r27@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )


def _history(user, row, host=TENANT_HOST, query=""):
    client = Client(HTTP_HOST=host)
    client.force_login(user)
    return client.get(f"/admin/communications/email/{row.pk}/history/{query}")


@pytest.fixture
def foreign_user(other_tenant):
    """Usuario del tenant B (la fila de B con el mismo pk no hace falta: el log es compartido)."""
    return User.objects.create_user(
        username=FOREIGN_USERNAME, email="ajeno-r27@otra.test", password="x", tenant=other_tenant,
    )


@pytest.fixture
def own_user(tenant):
    return User.objects.create_user(
        username=OWN_USERNAME, email="propio-r27@financiera.test", password="x", tenant=tenant,
    )


def test_history_on_tenant_host_hides_entries_of_another_tenant(tenant, email, foreign_user):
    _log(foreign_user, email, FOREIGN_MESSAGE)

    response = _history(_staff(tenant, "staff-hist-r27", ["view_email"]), email)

    assert response.status_code == 200
    html = response.content.decode()
    assert FOREIGN_USERNAME not in html
    assert "subject-secreto-del-tenant-B" not in html


def test_history_on_tenant_host_keeps_entries_of_own_tenant(tenant, email, foreign_user, own_user):
    _log(foreign_user, email, FOREIGN_MESSAGE)
    _log(own_user, email, OWN_MESSAGE)

    response = _history(_staff(tenant, "staff-hist-own-r27", ["view_email"]), email)

    assert response.status_code == 200
    html = response.content.decode()
    assert OWN_USERNAME in html
    assert "subject-propio-del-tenant-A" in html
    assert FOREIGN_USERNAME not in html
    assert [entry.user_id for entry in response.context["action_list"]] == [own_user.pk]


def test_history_on_tenant_host_hides_platform_actions(tenant, email, own_user):
    """Consecuencia aceptada: el log no guarda el schema de la fila, y una acción del
    superusuario de plataforma (sin tenant) no se puede atribuir a un tenant."""
    platform = _platform_superuser()
    _log(platform, email, "Cambiado por la plataforma")
    _log(own_user, email, OWN_MESSAGE)

    response = _history(platform, email)

    assert response.status_code == 200
    assert [entry.user_id for entry in response.context["action_list"]] == [own_user.pk]


def test_history_pagination_counts_only_own_tenant_entries(tenant, email, foreign_user, own_user):
    """Las entradas ajenas no ocupan páginas: 150 de B y 1 de A caben en una sola página."""
    for _ in range(150):
        _log(foreign_user, email, FOREIGN_MESSAGE)
    _log(own_user, email, OWN_MESSAGE)

    response = _history(_staff(tenant, "staff-hist-pag-r27", ["view_email"]), email, query="?p=2")

    assert response.status_code == 200
    assert response.context["pagination_required"] is False
    assert response.context["action_list"].paginator.count == 1
    assert [entry.user_id for entry in response.context["action_list"]] == [own_user.pk]


def test_platform_superuser_on_public_host_sees_every_entry(public_schema, tenant, foreign_user, own_user):
    """En el host público el historial no cambia: muestra las entradas de todos."""
    row = Email.objects.create(
        from_email="a@crediflux.test", to_email="b@crediflux.test", subject="publico-r27", body_text="x",
    )
    _log(foreign_user, row, FOREIGN_MESSAGE)
    _log(own_user, row, OWN_MESSAGE)

    response = _history(_platform_superuser(), row, host=PUBLIC_HOST)

    assert response.status_code == 200
    html = response.content.decode()
    assert FOREIGN_USERNAME in html
    assert OWN_USERNAME in html
    assert len(response.context["action_list"]) == 2


def test_history_of_missing_object_still_redirects(tenant):
    client = Client(HTTP_HOST=TENANT_HOST)
    client.force_login(_staff(tenant, "staff-hist-404-r27", ["view_email"]))

    response = client.get("/admin/communications/email/999999/history/")

    assert response.status_code == 302


# --- barrido: ningún admin de un modelo de tenant queda sin el filtro --------------------------

def test_every_tenant_model_admin_scopes_history(tenant):
    """Todo admin registrado de un modelo de TENANT_APPS (también los de terceros, como
    `djangosdk`) lleva `TenantHistoryMixin`."""
    tenant_apps = set(settings.TENANT_APPS)
    checked = {
        model: model_admin for model, model_admin in admin.site._registry.items()
        if model._meta.app_config.name in tenant_apps
    }

    # No basta con heredar el mixin: si va detrás de ModelAdmin en el MRO, o si el admin
    # sobrescribe history_view, gana la vista de Django y el historial vuelve a mezclar tenants.
    missing = [type(a).__name__ for a in checked.values()
               if type(a).history_view is not TenantHistoryMixin.history_view]
    assert not missing, missing
    assert {m._meta.app_config.name for m in checked} >= {
        "apps.loans", "apps.communications", "apps.billing", "apps.cashbox", "djangosdk",
    }
