import pytest
pytestmark = pytest.mark.django_db
PASSWORD = "clave-de-prueba-123"

def login(client, user):
    r = client.post("/api/tenants/login/", {"email": user.email, "password": PASSWORD}, format="json")
    assert r.status_code == 200, r.content
    return r.json()

def test_password_change_invalidates_existing_tokens(api_client, user_factory):
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    hdr = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}
    assert api_client.get("/api/users/profile/", **hdr).status_code == 200
    body = {"current_password": PASSWORD, "new_password": "Nueva-Clave-456!", "confirm_password": "Nueva-Clave-456!"}
    assert api_client.post("/api/users/profile/change-password/", body, format="json", **hdr).status_code == 200
    assert api_client.get("/api/users/profile/", **hdr).status_code == 401
    assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401

def test_token_without_pwd_ts_claim_is_rejected(api_client, user_factory):
    from rest_framework_simplejwt.tokens import RefreshToken
    legacy = RefreshToken.for_user(user_factory()).access_token
    assert api_client.get("/api/users/profile/", HTTP_AUTHORIZATION=f"Bearer {legacy}").status_code == 401

def test_refresh_is_rejected_after_tenant_deactivation(api_client, user_factory, tenant_schema):
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    tenant_schema.is_active = False
    tenant_schema.save()
    try:
        assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401
    finally:
        tenant_schema.is_active = True
        tenant_schema.save()

def test_reset_request_never_returns_token_material(public_client, user_factory, settings):
    settings.DEBUG = True
    user = user_factory(role="viewer", tenant=None)
    r = public_client.post("/api/users/auth/password-reset/request/", {"email": user.email}, format="json")
    assert r.status_code == 200
    assert not ({"token", "uid", "reset_token"} & set(r.json()))


# --- Complementarios ---------------------------------------------------------

def test_refresh_keeps_simplejwt_shape_and_new_access_works(api_client, user_factory):
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    r = api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json")
    assert r.status_code == 200, r.content
    data = r.json()
    assert {"access", "refresh"} <= set(data)
    hdr = {"HTTP_AUTHORIZATION": f"Bearer {data['access']}"}
    assert api_client.get("/api/users/profile/", **hdr).status_code == 200
    # El refresh rotado queda en lista negra.
    again = api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json")
    assert again.status_code == 401

def test_refresh_without_pwd_ts_claim_is_rejected(api_client, user_factory):
    from rest_framework_simplejwt.tokens import RefreshToken
    legacy = RefreshToken.for_user(user_factory(role="admin"))
    r = api_client.post("/api/auth/token/refresh/", {"refresh": str(legacy)}, format="json")
    assert r.status_code == 401

def test_password_reset_confirm_revokes_tokens(api_client, user_factory):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    user.refresh_from_db()
    body = {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
        "new_password": "Nueva-Clave-456!", "confirm_password": "Nueva-Clave-456!",
    }
    r = api_client.post("/api/users/auth/password-reset/confirm/", body, format="json")
    assert r.status_code == 200, r.content
    hdr = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}
    assert api_client.get("/api/users/profile/", **hdr).status_code == 401
    assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401

def test_tenant_deactivation_blacklists_outstanding_tokens(api_client, user_factory, tenant_schema):
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
    user = user_factory(role="admin")
    login(api_client, user)
    tenant_schema.is_active = False
    tenant_schema.save()
    try:
        assert BlacklistedToken.objects.filter(token__user=user).exists()
    finally:
        tenant_schema.is_active = True
        tenant_schema.save()

def test_two_factor_login_rejected_when_tenant_inactive(user_factory, tenant_schema):
    from django.core.cache import cache
    from apps.users.serializers import TwoFactorLoginSerializer
    user = user_factory(role="admin", is_2fa_enabled=True, backup_codes=["ABCD1234"])
    cache.set("2fa_pending_tmp-token", str(user.pk), timeout=300)
    tenant_schema.is_active = False
    tenant_schema.save()
    try:
        s = TwoFactorLoginSerializer(data={"backup_code": "ABCD1234", "temp_token": "tmp-token"})
        assert not s.is_valid()
        assert s.errors == {"temp_token": ["This account or its organization has been deactivated."]}
        user.refresh_from_db()
        assert user.backup_codes == ["ABCD1234"]  # rechazado antes de consumir el código
    finally:
        tenant_schema.is_active = True
        tenant_schema.save()
        cache.delete("2fa_pending_tmp-token")

def test_admin_password_change_form_revokes_tokens(api_client, user_factory):
    """La página estándar del admin `<id>/password/` usa AdminPasswordChangeForm."""
    from django.contrib.auth.forms import AdminPasswordChangeForm
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    hdr = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}
    assert api_client.get("/api/users/profile/", **hdr).status_code == 200
    user.refresh_from_db()
    form = AdminPasswordChangeForm(user, {"password1": "Nueva-Clave-456!", "password2": "Nueva-Clave-456!"})
    assert form.is_valid(), form.errors
    form.save()
    assert api_client.get("/api/users/profile/", **hdr).status_code == 401
    assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401

def test_password_rehash_on_login_does_not_revoke_tokens(user_factory, settings):
    from django.contrib.auth.hashers import make_password
    from apps.users.models import User
    user = user_factory(role="admin")
    # Hash con un hasher secundario: check_password lo re-hashea con el preferido.
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    ]
    User.objects.filter(pk=user.pk).update(password=make_password(PASSWORD, hasher="pbkdf2_sha256"))
    user.refresh_from_db()
    before = user.password_changed_at
    assert user.check_password(PASSWORD)
    user.refresh_from_db()
    assert user.password.startswith("md5$")
    assert user.password_changed_at == before
