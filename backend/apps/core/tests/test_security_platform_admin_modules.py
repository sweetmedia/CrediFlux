"""Módulos del admin de estado global: sólo el superusuario de plataforma los ve y edita.

Constance, Celery beat, los emails de allauth, los tokens de simplejwt/authtoken, grupos, sites,
socialaccount y el padrón de la JCE viven sólo en el schema público y valen para todos los
tenants. Sus admins seguían los permisos de modelo de Django, que un superusuario atado a un
tenant tiene implícitos, y el admin se sirve también en hosts de tenant: desde su propio host,
ese superusuario cambiaba `COMPANY_NAME` global y creaba schedules de beat en public.

Ahora módulo, vista, alta, edición y borrado son sólo del superusuario de plataforma
(`is_superuser` y `tenant=None`), con el mismo mixin que tenants y dominios (ronda 22). Los
admins de datos de tenant (préstamos, cobros, facturación, caja, IA) no cambian.
"""
import pytest
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from constance import config as constance_config
from constance.admin import Config
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import reverse
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from rest_framework.authtoken.models import TokenProxy
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.audit.models import AuditLog
from apps.core.models import PadronJCE
from apps.tenants.models import Domain, Tenant
from apps.users.models import User

pytestmark = pytest.mark.django_db

PUBLIC_HOST = "localhost"
TENANT_HOST = "tenant.test.localhost"
CONSTANCE = "/admin/constance/config/"

# Admins de estado global (apps sólo en SHARED_APPS) que pasan a ser sólo de plataforma.
PLATFORM_MODELS = [
    Config,
    PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule,
    EmailAddress, EmailConfirmation,
    OutstandingToken, BlacklistedToken, TokenProxy,
    Group, Site,
    SocialApp, SocialAccount, SocialToken,
    PadronJCE,
]
PLATFORM_APP_LABELS = {model._meta.app_label for model in PLATFORM_MODELS}
# Sólo-SHARED pero ya acotados por su propia regla (rondas 19-22): no usan el mixin.
SCOPED_EXCEPTIONS = {User, AuditLog, Tenant, Domain}
BEAT_SCHEDULES = ["periodictask", "intervalschedule", "crontabschedule", "solarschedule", "clockedschedule"]


def _client(user, host):
    client = Client(HTTP_HOST=host)
    client.force_login(user)
    return client


def _request(user, host=TENANT_HOST, path="/admin/"):
    request = RequestFactory(HTTP_HOST=host).get(path)
    request.user = user
    return request


def _changelist(model):
    if model is Config:
        return CONSTANCE
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")


def _admin_urls(model):
    """Changelist y, si el admin lo tiene, el alta."""
    urls = [_changelist(model)]
    if model is not Config:
        urls.append(reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_add"))
    return urls


# --- usuarios -----------------------------------------------------------------------------

def _platform_superuser(tenant):
    return User.objects.create_user(
        username="plataforma-r23", email="plataforma-r23@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )


def _tenant_superuser(tenant):
    return User.objects.create_user(
        username="super-tenant-r23", email="super-tenant-r23@crediflux.test", password="x",
        tenant=tenant, is_superuser=True, is_staff=True, role="admin",
    )


def _tenant_staff_with_model_perms(tenant):
    """Staff de tenant con todos los permisos de modelo de los módulos globales."""
    staff = User.objects.create_user(
        username="staff-perm-r23", email="staff-perm-r23@crediflux.test", password="x",
        tenant=tenant, is_staff=True, role="admin",
    )
    perms = Permission.objects.filter(content_type__app_label__in=PLATFORM_APP_LABELS)
    assert perms.filter(content_type__app_label="constance", codename="change_config").exists()
    staff.user_permissions.add(*perms)
    return User.objects.get(pk=staff.pk)  # sin la caché de permisos


NON_PLATFORM = [_tenant_superuser, _tenant_staff_with_model_perms]


@pytest.fixture
def setup(tenant, public_schema):
    return tenant


def _assert_no_permission(model_admin, request, label):
    assert model_admin.has_module_permission(request) is False, label
    assert model_admin.has_view_permission(request) is False, label
    assert model_admin.has_change_permission(request) is False, label
    assert model_admin.has_add_permission(request) is False, label
    assert model_admin.has_delete_permission(request) is False, label


# --- no plataforma: ni ve ni toca los módulos globales ---------------------------------------

@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_has_no_permission_on_platform_modules(make_user, setup):
    request = _request(make_user(setup))

    for model in PLATFORM_MODELS:
        _assert_no_permission(admin.site._registry[model], request, model.__name__)

    app_labels = {app["app_label"] for app in admin.site.get_app_list(request)}
    assert not app_labels & PLATFORM_APP_LABELS, app_labels & PLATFORM_APP_LABELS


@pytest.mark.parametrize("host", [TENANT_HOST, PUBLIC_HOST])
@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_gets_403_on_platform_module_pages(make_user, host, setup):
    client = _client(make_user(setup), host)

    for model in PLATFORM_MODELS:
        for url in _admin_urls(model):
            assert client.get(url).status_code == 403, url


def _constance_post_data(platform_client, company_name):
    """El formulario de Constance tal como lo ve el superusuario de plataforma, con otro nombre."""
    form = platform_client.get(CONSTANCE).context["form"]
    connection.set_schema_to_public()
    data = {}
    for name, field in form.fields.items():
        value = form.initial.get(name, field.initial)
        if name == "COMPANY_NAME":
            value = company_name
        if isinstance(value, bool):
            if value:
                data[name] = "on"
            continue
        data[name] = "" if value is None else str(value)
    return data


@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_cannot_write_platform_state(make_user, setup):
    """El caso reproducido en run-5: desde su host, cambiaba Constance y creaba schedules."""
    data = _constance_post_data(_client(_platform_superuser(setup), PUBLIC_HOST), "CAMBIADO-DESDE-TENANT")
    before = constance_config.COMPANY_NAME
    client = _client(make_user(setup), TENANT_HOST)

    response = client.post(CONSTANCE, data)
    connection.set_schema_to_public()
    assert response.status_code == 403
    assert constance_config.COMPANY_NAME == before

    response = client.post(
        "/admin/django_celery_beat/intervalschedule/add/", {"every": "777", "period": "days"})
    connection.set_schema_to_public()
    assert response.status_code == 403
    assert IntervalSchedule.objects.filter(every=777).count() == 0

    response = client.post("/admin/django_celery_beat/crontabschedule/add/", {
        "minute": "0", "hour": "3", "day_of_week": "*", "day_of_month": "*",
        "month_of_year": "*", "timezone": "UTC",
    })
    connection.set_schema_to_public()
    assert response.status_code == 403
    assert CrontabSchedule.objects.filter(minute="0", hour="3").count() == 0


@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_sees_no_platform_links_in_sidebar(make_user, setup):
    user = make_user(setup)
    connection.set_schema_to_public()  # el sidebar con beat y grupos es el del schema público
    links = _sidebar_links(admin.site.get_sidebar_list(_request(user, PUBLIC_HOST)))
    for link in SIDEBAR_LINKS:
        assert links[link] is False, link


def _sidebar_links(groups):
    """{link: has_permission} de los ítems del sidebar de Unfold."""
    return {
        str(item.get("link_callback") or item["link"]): item["has_permission"]
        for group in groups for item in group.get("items", [])
    }


SIDEBAR_LINKS = (
    CONSTANCE,
    "/admin/django_celery_beat/periodictask/",
    "/admin/auth/group/",
)


# --- superusuario de plataforma: lo ve y lo edita todo ----------------------------------------

def test_platform_superuser_lists_and_opens_platform_modules(setup):
    user = _platform_superuser(setup)
    request = _request(user, PUBLIC_HOST)
    client = _client(user, PUBLIC_HOST)

    for model in PLATFORM_MODELS:
        model_admin = admin.site._registry[model]
        assert model_admin.has_module_permission(request) is True, model.__name__
        assert model_admin.has_view_permission(request) is True, model.__name__
        if model is PadronJCE:
            continue  # tabla no gestionada: no existe en la base de pruebas
        for url in _admin_urls(model):
            if url.endswith("/add/") and not model_admin.has_add_permission(request):
                continue  # padrón y confirmaciones: sin alta manual para nadie
            assert client.get(url).status_code == 200, url

    connection.set_schema_to_public()
    links = _sidebar_links(admin.site.get_sidebar_list(request))
    for link in SIDEBAR_LINKS:
        assert links[link] is True, link


def test_platform_superuser_saves_constance_and_beat_schedules(setup):
    client = _client(_platform_superuser(setup), PUBLIC_HOST)
    before = constance_config.COMPANY_NAME
    try:
        response = client.post(CONSTANCE, _constance_post_data(client, "CAMBIADO-DESDE-PLATAFORMA"))
        connection.set_schema_to_public()
        assert response.status_code == 302
        assert constance_config.COMPANY_NAME == "CAMBIADO-DESDE-PLATAFORMA"
    finally:
        constance_config.COMPANY_NAME = before  # la caché de Constance no vuelve con el rollback

    response = client.post(
        "/admin/django_celery_beat/intervalschedule/add/", {"every": "777", "period": "days"})
    connection.set_schema_to_public()
    assert response.status_code == 302
    assert IntervalSchedule.objects.filter(every=777).count() == 1


# --- datos de tenant: sin cambios -------------------------------------------------------------

def test_tenant_data_admins_keep_django_model_permissions(setup):
    staff = User.objects.create_user(
        username="staff-loans-r23", email="staff-loans-r23@crediflux.test", password="x",
        tenant=setup, is_staff=True, role="admin",
    )
    staff.user_permissions.add(Permission.objects.get(content_type__app_label="loans", codename="view_loan"))
    staff = User.objects.get(pk=staff.pk)

    assert _client(staff, TENANT_HOST).get("/admin/loans/loan/").status_code == 200


def test_is_platform_admin_rule(setup):
    """Una sola regla compartida: superusuario sin tenant. Segura con anónimo y con None."""
    from django.contrib.auth.models import AnonymousUser

    from apps.core.admin_mixins import is_platform_admin

    assert is_platform_admin(_platform_superuser(setup)) is True
    assert is_platform_admin(_tenant_superuser(setup)) is False
    assert is_platform_admin(_tenant_staff_with_model_perms(setup)) is False
    assert is_platform_admin(AnonymousUser()) is False
    assert is_platform_admin(None) is False


# --- barrido: ningún admin global futuro queda abierto ----------------------------------------

def test_every_shared_only_admin_denies_a_tenant_superuser(setup):
    """Todo admin de una app sólo-SHARED (salvo los ya acotados por su regla) deniega a un
    superusuario con tenant. Un admin global nuevo que no use el mixin rompe este test."""
    shared_only = set(settings.SHARED_APPS) - set(settings.TENANT_APPS)
    request = _request(_tenant_superuser(setup))
    platform_request = _request(_platform_superuser(setup), PUBLIC_HOST)

    checked = set()
    for model, model_admin in admin.site._registry.items():
        if model._meta.app_config.name not in shared_only or model in SCOPED_EXCEPTIONS:
            continue
        checked.add(model)
        _assert_no_permission(model_admin, request, model.__name__)
        assert model_admin.has_view_permission(platform_request) is True, model.__name__

    assert set(PLATFORM_MODELS) <= checked, set(PLATFORM_MODELS) - checked
