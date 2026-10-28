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
    # Mismo redirect que un pk inexistente (sin oráculo de existencia entre tenants).
    assert r.status_code == 302
    assert r["Location"] == reverse("admin:users_user_changelist")
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


@pytest.fixture
def platform_client(user_factory):
    platform_admin = user_factory(tenant=None, is_superuser=True, is_staff=True)
    client = Client(HTTP_HOST=HOST)
    client.force_login(platform_admin)
    return client


def form_post_data(form):
    """Datos POST equivalentes a enviar el formulario tal como se renderiza."""
    from django.forms import MultiWidget

    data = {}
    for name in form.fields:
        bound = form[name]
        value = bound.value()
        widget = bound.field.widget
        if isinstance(widget, MultiWidget):
            parts = value if isinstance(value, (list, tuple)) else widget.decompress(value)
            for suffix, part in zip(widget.widgets_names, parts):
                data[f"{bound.html_name}{suffix}"] = "" if part is None else part
        elif isinstance(value, bool):
            if value:
                data[bound.html_name] = "on"
        elif value is not None:
            data[bound.html_name] = value
    return data


def test_tenant_schema_name_is_read_only_when_editing(platform_client, tenant_schema):
    r = platform_client.get(reverse("admin:tenants_tenant_change", args=[tenant_schema.pk]))
    assert r.status_code == 200
    assert "schema_name" not in r.context["adminform"].form.fields
    assert "schema_name" in r.context["adminform"].readonly_fields


def test_platform_superuser_can_create_tenant_with_schema_name(user_factory, monkeypatch):
    from apps.tenants.models import Tenant

    monkeypatch.setattr(Tenant, "auto_create_schema", False)  # no crear el schema real
    # Los tenants sólo se crean desde el schema público.
    platform_client = Client(HTTP_HOST="localhost")
    platform_client.force_login(user_factory(tenant=None, is_superuser=True, is_staff=True))
    url = reverse("admin:tenants_tenant_add")
    r = platform_client.get(url)
    assert r.status_code == 200
    form = r.context["adminform"].form
    assert "schema_name" in form.fields

    body = form_post_data(form)
    body.update({
        "name": "Financiera Nueva",
        "schema_name": "financiera_nueva",
        "business_name": "Financiera Nueva SRL",
        "email": "admin@nueva.test",
    })
    r = platform_client.post(url, body)
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r.content
    assert Tenant.objects.filter(schema_name="financiera_nueva", name="Financiera Nueva").exists()


# --- Un admin que no es dueño no puede tomar la cuenta del dueño ------------------------

@pytest.fixture
def owner(tenant_admin):
    return tenant_admin  # role=admin, is_tenant_owner=True


@pytest.fixture
def non_owner_admin(user_factory):
    return user_factory(role="admin", is_tenant_owner=False, is_staff=True)


@pytest.fixture
def non_owner_client(non_owner_admin):
    client = Client(HTTP_HOST=HOST)
    client.force_login(non_owner_admin)
    return client


def _change_body(user, **overrides):
    body = {
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name or "Nombre",
        "last_name": user.last_name or "Apellido",
        "role": user.role,
        "is_active": "on",
        "receive_notifications": "on",
    }
    body.update(overrides)
    return body


def test_non_owner_admin_cannot_reset_owner_password(non_owner_client, owner):
    assert non_owner_client.post(reset_url(owner), new_password_body()).status_code == 403
    assert non_owner_client.post(reset_url(owner), {"generate_random": "true"}).status_code == 403
    owner.refresh_from_db()
    assert owner.check_password(PASSWORD)


def test_bulk_reset_skips_owner_for_non_owner_admin(non_owner_client, owner, user_factory):
    member = user_factory()
    r = non_owner_client.post(
        reverse("admin:users_user_changelist"),
        {"action": "reset_password_action", "_selected_action": [member.pk, owner.pk]},
    )
    assert r.status_code == 302
    owner.refresh_from_db()
    member.refresh_from_db()
    assert owner.check_password(PASSWORD)
    assert not member.check_password(PASSWORD)


def test_non_owner_admin_cannot_edit_owner(non_owner_client, owner):
    url = reverse("admin:users_user_change", args=[owner.pk])
    original_email = owner.email
    r = non_owner_client.post(url, _change_body(owner, email="tomado@atacante.test"))
    assert r.status_code == 403
    owner.refresh_from_db()
    assert owner.email == original_email


def test_owner_can_promote_member_to_admin(admin_client, user_factory):
    member = user_factory(role="loan_officer")
    url = reverse("admin:users_user_change", args=[member.pk])
    r = admin_client.post(url, _change_body(member, role="admin"))
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r.content
    member.refresh_from_db()
    assert member.role == "admin"


def test_non_owner_admin_cannot_promote_to_admin(non_owner_client, user_factory):
    member = user_factory(role="loan_officer")
    url = reverse("admin:users_user_change", args=[member.pk])
    r = non_owner_client.post(url, _change_body(member, role="admin"))
    assert r.status_code == 200  # el formulario vuelve con el error
    assert "role" in r.context["adminform"].form.errors
    member.refresh_from_db()
    assert member.role == "loan_officer"


def test_non_owner_admin_cannot_create_admin(non_owner_client):
    from apps.users.models import User

    body = {
        "email": "nuevo-admin@crediflux.test",
        "username": "nuevo-admin",
        "first_name": "Nuevo",
        "last_name": "Admin",
        "role": "admin",
        "password1": "Nueva-Clave-456!",
        "password2": "Nueva-Clave-456!",
    }
    r = non_owner_client.post(reverse("admin:users_user_add"), body)
    assert r.status_code == 200
    assert "role" in r.context["adminform"].form.errors
    assert not User.objects.filter(email="nuevo-admin@crediflux.test").exists()


def test_non_owner_admin_can_edit_own_account_without_changing_role(non_owner_client, non_owner_admin):
    # Mandar el rol admin que ya tiene no es asignarlo (D6).
    url = reverse("admin:users_user_change", args=[non_owner_admin.pk])
    r = non_owner_client.post(url, _change_body(non_owner_admin, first_name="Cambiado"))
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r.content


def test_non_owner_admin_cannot_edit_another_admin(non_owner_client, user_factory):
    # D6: a un admin sólo lo gestiona el dueño (puede_gestionar).
    other_admin = user_factory(role="admin", is_tenant_owner=False)
    url = reverse("admin:users_user_change", args=[other_admin.pk])
    r = non_owner_client.post(url, _change_body(other_admin, email="tomado@atacante.test"))
    assert r.status_code == 403
    other_admin.refresh_from_db()
    assert other_admin.email != "tomado@atacante.test"


def test_non_owner_admin_cannot_toggle_is_tenant_owner(non_owner_client, user_factory):
    member = user_factory(role="loan_officer")
    url = reverse("admin:users_user_change", args=[member.pk])
    assert "is_tenant_owner" not in non_owner_client.get(url).context["adminform"].form.fields
    r = non_owner_client.post(url, _change_body(member, is_tenant_owner="on"))
    assert r.status_code == 302
    member.refresh_from_db()
    assert member.is_tenant_owner is False


def test_reset_view_foreign_pk_looks_like_missing_pk(admin_client, other_tenant, user_factory):
    from apps.users.models import User

    outsider = user_factory(tenant=other_tenant)
    missing_pk = (User.objects.order_by("-pk").values_list("pk", flat=True).first() or 0) + 1000
    r_foreign = admin_client.post(reset_url(outsider), {"generate_random": "true"})
    r_missing = admin_client.post(
        reverse("admin:users_user_reset_password", args=[missing_pk]), {"generate_random": "true"}
    )
    assert r_foreign.status_code == r_missing.status_code == 302
    assert r_foreign["Location"] == r_missing["Location"]
    outsider.refresh_from_db()
    assert outsider.check_password(PASSWORD)
