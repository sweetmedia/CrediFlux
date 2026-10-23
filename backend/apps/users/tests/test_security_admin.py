"""Admin de Django acotado por tenant (Task 4 de la remediación)."""
import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db
PASSWORD = "clave-de-prueba-123"
HOST = "tenant.test.localhost"
PRIVILEGE_FIELDS = ("is_superuser", "is_staff", "groups", "user_permissions", "tenant", "is_tenant_owner")


@pytest.fixture
def tenant_admin(user_factory):
    return user_factory(role="admin", is_tenant_owner=True, is_staff=True)


@pytest.fixture
def admin_client(tenant_admin):
    client = Client(HTTP_HOST=HOST)
    client.force_login(tenant_admin)
    return client


def reset_url(user):
    return reverse("admin:users_user_reset_password", args=[user.pk])


def new_password_body(password="Nueva-Clave-456!"):
    return {"new_password": password, "confirm_password": password}


def test_tenant_admin_cannot_reset_a_superuser(admin_client, user_factory):
    superuser = user_factory(is_superuser=True, is_staff=True)
    r = admin_client.post(reset_url(superuser), new_password_body())
    assert r.status_code == 403
    superuser.refresh_from_db()
    assert superuser.check_password(PASSWORD)


def test_tenant_admin_cannot_reset_user_of_other_tenant(admin_client, other_tenant, user_factory):
    outsider = user_factory(tenant=other_tenant)
    r = admin_client.post(reset_url(outsider), {"generate_random": "true"})
    assert r.status_code == 403
    outsider.refresh_from_db()
    assert outsider.check_password(PASSWORD)


def test_viewer_cannot_open_reset_view(user_factory):
    viewer = user_factory(role="viewer", is_staff=True)
    target = user_factory()
    client = Client(HTTP_HOST=HOST)
    client.force_login(viewer)
    assert client.get(reset_url(target)).status_code == 403


def test_bulk_reset_action_skips_users_it_cannot_reset(admin_client, user_factory):
    member = user_factory()
    superuser = user_factory(is_superuser=True, is_staff=True)
    r = admin_client.post(
        reverse("admin:users_user_changelist"),
        {"action": "reset_password_action", "_selected_action": [member.pk, superuser.pk]},
    )
    assert r.status_code == 302
    member.refresh_from_db()
    superuser.refresh_from_db()
    assert not member.check_password(PASSWORD)
    assert superuser.check_password(PASSWORD)


def test_change_form_ignores_privilege_fields(admin_client, user_factory):
    member = user_factory(role="loan_officer")
    url = reverse("admin:users_user_change", args=[member.pk])

    form_fields = admin_client.get(url).context["adminform"].form.fields
    for name in PRIVILEGE_FIELDS:
        assert name not in form_fields

    body = {
        "username": member.username,
        "email": member.email,
        "first_name": "Cambiado",
        "last_name": member.last_name,
        "role": member.role,
        "is_active": "on",
        "is_superuser": "on",
        "is_staff": "on",
        "is_tenant_owner": "on",
        "receive_notifications": "on",
    }
    r = admin_client.post(url, body)
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r.content
    member.refresh_from_db()
    assert member.first_name == "Cambiado"
    assert member.is_superuser is False
    assert member.is_tenant_owner is False


def test_demo_data_view_is_superuser_only(admin_client):
    assert admin_client.get(reverse("admin:generate_demo_data")).status_code == 403


def test_tenant_admin_can_reset_own_team_member(admin_client, user_factory):
    member = user_factory(role="loan_officer")
    r = admin_client.post(reset_url(member), new_password_body())
    assert r.status_code == 302
    member.refresh_from_db()
    assert member.check_password("Nueva-Clave-456!")


def test_user_added_by_tenant_admin_stays_in_their_tenant(admin_client, tenant_admin):
    from apps.users.models import User

    body = {
        "email": "nuevo-miembro@crediflux.test",
        "username": "nuevo-miembro",
        "first_name": "Nuevo",
        "last_name": "Miembro",
        "role": "loan_officer",
        "password1": "Nueva-Clave-456!",
        "password2": "Nueva-Clave-456!",
        "tenant": "",
        "is_tenant_owner": "on",
    }
    r = admin_client.post(reverse("admin:users_user_add"), body)
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r.content
    created = User.objects.get(email="nuevo-miembro@crediflux.test")
    assert created.tenant_id == tenant_admin.tenant_id
    assert created.is_tenant_owner is False


def test_tenant_schema_name_is_read_only(user_factory, tenant_schema):
    platform_admin = user_factory(tenant=None, is_superuser=True, is_staff=True)
    client = Client(HTTP_HOST=HOST)
    client.force_login(platform_admin)
    r = client.get(reverse("admin:tenants_tenant_change", args=[tenant_schema.pk]))
    assert r.status_code == 200
    assert "schema_name" not in r.context["adminform"].form.fields
