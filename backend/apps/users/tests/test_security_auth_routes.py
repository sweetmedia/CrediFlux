import pytest
pytestmark = pytest.mark.django_db

@pytest.mark.parametrize("path", [
    "/api/auth/registration/", "/api/auth/login/", "/api/auth/password/change/",
    "/api/auth/password/reset/", "/api/auth/user/",
])
def test_parallel_dj_rest_auth_routes_are_gone(public_client, path):
    assert public_client.post(path, {}, format="json").status_code == 404

def test_token_refresh_route_is_still_mounted(api_client):
    assert api_client.post("/api/auth/token/refresh/", {"refresh": "x"}, format="json").status_code in (400, 401)

def test_legacy_rest_auth_serializers_key_is_gone(settings):
    assert not hasattr(settings, "REST_AUTH_SERIALIZERS")
    assert settings.REST_AUTH["LOGIN_SERIALIZER"] == "apps.users.serializers.TenantAwareLoginSerializer"
