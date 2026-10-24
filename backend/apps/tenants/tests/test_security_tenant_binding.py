import pytest
from rest_framework.test import APIClient
from apps.users.tokens import issue_tokens

pytestmark = pytest.mark.django_db
TENANT = "tenant.test.localhost"
OTHER = "other.test.localhost"

def bearer(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {issue_tokens(user).access_token}"}

def test_token_of_tenant_user_is_rejected_on_other_host(tenant_schema, user_factory, other_tenant):
    user = user_factory(role="admin")
    assert APIClient(HTTP_HOST=OTHER).get("/api/users/profile/", **bearer(user)).status_code == 403

def test_token_of_tenant_user_is_accepted_on_own_host(tenant_schema, user_factory):
    user = user_factory(role="viewer")
    assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(user)).status_code == 200

def test_tenantless_non_superuser_is_rejected_on_tenant_host(tenant_schema, user_factory):
    user = user_factory(role="viewer", tenant=None)
    client = APIClient(HTTP_HOST=TENANT)
    assert client.get("/api/tenants/settings/", **bearer(user)).status_code == 403
    assert client.get("/api/loans/customers/", **bearer(user)).status_code == 403

def test_platform_superuser_is_allowed_on_tenant_and_public_hosts(tenant_schema, user_factory, public_client):
    su = user_factory(role="admin", tenant=None, is_superuser=True, is_staff=True)
    assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(su)).status_code == 200
    assert public_client.get("/api/users/profile/", **bearer(su)).status_code == 200

def test_users_of_inactive_tenant_are_rejected(tenant_schema, user_factory):
    user = user_factory(role="admin")
    tenant_schema.is_active = False
    tenant_schema.save(update_fields=["is_active"])
    user.refresh_from_db()  # la desactivación movió password_changed_at; token vigente
    try:
        assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(user)).status_code == 403
    finally:
        tenant_schema.is_active = True
        tenant_schema.save(update_fields=["is_active"])

def test_team_detail_requires_a_tenant(tenant_schema, user_factory, public_client):
    su = user_factory(role="admin", tenant=None, is_superuser=True, is_staff=True)
    viewer = user_factory(role="viewer", tenant=None)
    assert public_client.get(f"/api/users/team/{su.pk}/", **bearer(viewer)).status_code == 403

def test_own_host_session_does_not_cover_a_foreign_bearer(tenant_schema, user_factory, other_tenant):
    own = user_factory(role="viewer")
    foreign_admin = user_factory(role="admin", tenant=other_tenant)
    client = APIClient(HTTP_HOST=TENANT)
    client.force_login(own)
    assert client.get("/api/users/profile/", **bearer(foreign_admin)).status_code == 403
    # La sesión ya no autentica la API (run-2): el control es el propio bearer del usuario.
    assert client.get("/api/users/profile/", **bearer(own)).status_code == 200

def test_session_user_is_rejected_on_other_host(tenant_schema, user_factory, other_tenant):
    user = user_factory(role="admin")
    client = APIClient(HTTP_HOST=OTHER)
    client.force_login(user)
    assert client.get("/api/users/profile/").status_code == 403
