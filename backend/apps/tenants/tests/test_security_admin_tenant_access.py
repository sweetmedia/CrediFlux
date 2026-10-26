"""Tenants y dominios en el admin: sólo el superusuario de plataforma los ve y edita.

`TenantAdmin` y `DomainAdmin` seguían los permisos de modelo de Django (y `DomainAdmin` no tenía
ninguna regla propia): un superusuario CON tenant, o un staff de tenant con `tenants.*`, listaba
todos los tenants (emails, RNC, teléfonos), les cambiaba `is_active`/`max_users`, y podía
reapuntar el hostname de otro tenant al suyo o borrarle el dominio principal. El admin se sirve
también en hosts de tenant.

Ahora módulo, vista, alta, edición y borrado son sólo del superusuario de plataforma
(`is_superuser` y `tenant=None`); las reglas de borrado (ronda 21) y aprovisionamiento (ronda 19)
siguen igual. El sidebar de Unfold, el selector de tenants y el filtro por tenant de la lista de
usuarios tampoco enseñan otros tenants a nadie más.
"""
import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.db import connection
from django.forms import FileField, MultiWidget
from django.test import Client, RequestFactory

from apps.tenants.models import Domain, Tenant
from apps.users.models import User
from config.settings.utils import get_tenant_dropdown

pytestmark = pytest.mark.django_db

PUBLIC_HOST = "localhost"
TENANT_HOST = "tenant.test.localhost"
TENANTS = "/admin/tenants/tenant/"
DOMAINS = "/admin/tenants/domain/"
SIDEBAR_LINKS = (TENANTS, DOMAINS)


def _client(user, host):
    client = Client(HTTP_HOST=host)
    client.force_login(user)
    return client


def _request(user, host=TENANT_HOST, path="/admin/"):
    request = RequestFactory(HTTP_HOST=host).get(path)
    request.user = user
    return request


# --- usuarios -----------------------------------------------------------------------------

def _platform_superuser(tenant):
    return User.objects.create_user(
        username="plataforma-r22", email="plataforma-r22@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )


def _tenant_superuser(tenant):
    return User.objects.create_user(
        username="super-tenant-r22", email="super-tenant-r22@crediflux.test", password="x",
        tenant=tenant, is_superuser=True, is_staff=True, role="admin",
    )


def _tenant_staff_with_model_perms(tenant):
    staff = User.objects.create_user(
        username="staff-perm-r22", email="staff-perm-r22@crediflux.test", password="x",
        tenant=tenant, is_staff=True, role="admin",
    )
    staff.user_permissions.add(*Permission.objects.filter(
        content_type__app_label="tenants",
        codename__in=[f"{verb}_{model}" for verb in ("view", "change", "add", "delete")
                      for model in ("tenant", "domain")],
    ))
    return User.objects.get(pk=staff.pk)  # sin la caché de permisos


def _tenant_owner(tenant):
    return User.objects.create_user(
        username="dueno-r22", email="dueno-r22@crediflux.test", password="x",
        tenant=tenant, is_staff=True, is_tenant_owner=True, role="admin",
    )


NON_PLATFORM = [_tenant_superuser, _tenant_staff_with_model_perms, _tenant_owner]


@pytest.fixture
def setup(tenant, other_tenant, public_schema):
    """Tenant de pruebas (el del usuario) y otro tenant ajeno con su dominio."""
    return tenant, other_tenant, Domain.objects.get(tenant=other_tenant)


# --- no plataforma: ni ve ni toca tenants ni dominios ---------------------------------------

@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_has_no_tenant_or_domain_permission(make_user, setup):
    tenant, other, other_domain = setup
    request = _request(make_user(tenant))

    for model, obj in ((Tenant, other), (Domain, other_domain)):
        model_admin = admin.site._registry[model]
        assert model_admin.has_module_permission(request) is False
        assert model_admin.has_view_permission(request) is False
        assert model_admin.has_view_permission(request, obj) is False
        assert model_admin.has_change_permission(request) is False
        assert model_admin.has_change_permission(request, obj) is False
        assert model_admin.has_add_permission(request) is False
        assert model_admin.has_delete_permission(request) is False
        assert model_admin.has_delete_permission(request, obj) is False

    app_labels = {app["app_label"] for app in admin.site.get_app_list(request)}
    assert "tenants" not in app_labels


@pytest.mark.parametrize("host", [TENANT_HOST, PUBLIC_HOST])
@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_gets_403_on_tenant_and_domain_pages(make_user, host, setup):
    tenant, other, other_domain = setup
    client = _client(make_user(tenant), host)

    urls = [
        TENANTS, f"{TENANTS}add/", f"{TENANTS}{other.pk}/change/", f"{TENANTS}{other.pk}/history/",
        f"{TENANTS}{other.pk}/delete/", f"{TENANTS}generate-demo-data/",
        DOMAINS, f"{DOMAINS}add/", f"{DOMAINS}{other_domain.pk}/change/",
        f"{DOMAINS}{other_domain.pk}/history/", f"{DOMAINS}{other_domain.pk}/delete/",
    ]
    for url in urls:
        assert client.get(url).status_code == 403, url


@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_cannot_edit_another_tenant(make_user, setup):
    tenant, other, _ = setup
    client = _client(make_user(tenant), TENANT_HOST)
    before = (other.is_active, other.max_users)

    response = client.post(f"{TENANTS}{other.pk}/change/", {
        "name": other.name, "schema_name": other.schema_name, "business_name": other.business_name,
        "email": other.email, "is_active": "", "max_users": 9999,
    })
    assert response.status_code == 403
    other.refresh_from_db()
    assert (other.is_active, other.max_users) == before


@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_cannot_take_delete_or_add_domains(make_user, setup):
    tenant, other, other_domain = setup
    client = _client(make_user(tenant), TENANT_HOST)

    # Reapuntar el hostname ajeno a su propio tenant
    taken = client.post(f"{DOMAINS}{other_domain.pk}/change/", {
        "domain": other_domain.domain, "tenant": tenant.pk, "is_primary": "on",
    })
    assert taken.status_code == 403
    other_domain.refresh_from_db()
    assert other_domain.tenant_id == other.pk

    # Borrarlo por la vista y por la acción masiva
    assert client.post(f"{DOMAINS}{other_domain.pk}/delete/", {"post": "yes"}).status_code == 403
    bulk = client.post(DOMAINS, {"action": "delete_selected", "_selected_action": [other_domain.pk], "post": "yes"})
    assert bulk.status_code == 403
    assert Domain.objects.filter(pk=other_domain.pk, tenant=other).exists()

    # Alta forjada
    added = client.post(f"{DOMAINS}add/", {"domain": "robado.test.localhost", "tenant": tenant.pk})
    assert added.status_code == 403
    assert not Domain.objects.filter(domain="robado.test.localhost").exists()


@pytest.mark.parametrize("make_user", NON_PLATFORM)
def test_non_platform_admin_sees_no_tenant_data_in_sidebar_dropdown_or_filters(make_user, setup):
    tenant, _, _ = setup
    user = make_user(tenant)

    connection.set_schema_to_public()  # el sidebar con los dos ítems es el del schema público
    links = _sidebar_links(admin.site.get_sidebar_list(_request(user, PUBLIC_HOST)))
    for link in SIDEBAR_LINKS:
        assert links[link] is False, link

    assert get_tenant_dropdown(_request(user)) == []

    user_admin = admin.site._registry[User]
    assert "tenant" not in user_admin.get_list_filter(_request(user))


def _sidebar_links(groups):
    """{link: has_permission} de los ítems del sidebar de Unfold."""
    return {
        str(item.get("link_callback") or item["link"]): item["has_permission"]
        for group in groups for item in group.get("items", [])
    }


# --- superusuario de plataforma: lo ve y lo edita todo ----------------------------------------

def _form_data(form):
    """Datos POST equivalentes a lo que el formulario ya muestra (para editar un solo campo)."""
    data = {}
    for name, field in form.fields.items():
        if isinstance(field, FileField):
            continue  # sin archivo nuevo, el admin conserva el actual
        value = form[name].value()
        widget = field.widget
        if isinstance(widget, MultiWidget):
            values = value if isinstance(value, (list, tuple)) else widget.decompress(value)
            for suffix, part in zip(widget.widgets_names, values):
                if part is not None:
                    data[f"{name}{suffix}"] = part
        elif value is None or value is False:
            continue
        elif value is True:
            data[name] = "on"
        else:
            data[name] = value
    return data


@pytest.mark.parametrize("host", [PUBLIC_HOST, TENANT_HOST])
def test_platform_superuser_lists_views_and_edits_tenants_and_domains(host, setup):
    tenant, other, other_domain = setup
    user = _platform_superuser(tenant)
    client = _client(user, host)

    for url in (TENANTS, f"{TENANTS}add/", f"{TENANTS}{other.pk}/change/",
                DOMAINS, f"{DOMAINS}add/", f"{DOMAINS}{other_domain.pk}/change/"):
        assert client.get(url).status_code == 200, url

    # Edición de un tenant (el de pruebas: tiene schema, guardarlo no crea ninguno)
    change_url = f"{TENANTS}{tenant.pk}/change/"
    data = _form_data(client.get(change_url).context["adminform"].form)
    data["max_users"] = 77
    response = client.post(change_url, data)
    assert response.status_code == 302, response.context["adminform"].form.errors
    tenant.refresh_from_db()
    assert tenant.max_users == 77

    # Edición de un dominio
    response = client.post(f"{DOMAINS}{other_domain.pk}/change/", {
        "domain": "otra-renombrada.test.localhost", "tenant": other.pk, "is_primary": "on",
    })
    assert response.status_code == 302
    other_domain.refresh_from_db()
    assert other_domain.domain == "otra-renombrada.test.localhost"


def test_platform_superuser_sees_the_sidebar_items_dropdown_and_filter(setup):
    tenant, _, _ = setup
    user = _platform_superuser(tenant)
    request = _request(user, PUBLIC_HOST)

    for model in (Tenant, Domain):
        assert admin.site._registry[model].has_module_permission(request) is True
    assert "tenants" in {app["app_label"] for app in admin.site.get_app_list(request)}

    links = _sidebar_links(admin.site.get_sidebar_list(request))
    for link in SIDEBAR_LINKS:
        assert links[link] is True, link

    assert any(item["title"] == "Financiera de Prueba SRL" for item in get_tenant_dropdown(_request(user)))
    assert "tenant" in admin.site._registry[User].get_list_filter(request)
