"""El login del admin de Django exige el segundo factor y su sesión no autentica la API (run-2)."""
import pyotp
import pytest
from django.core.cache import cache
from django.test import Client

from apps.users.backup_codes import hash_codes
from apps.users.lockout import LOCKOUT_MESSAGE, TWO_FA_FAIL_LIMIT, check_and_count_2fa

pytestmark = pytest.mark.django_db
PASSWORD = "clave-de-prueba-123"
HOST = "tenant.test.localhost"
LOGIN_URL = "/admin/login/"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff_2fa(user_factory):
    return user_factory(
        role="manager", is_staff=True, is_2fa_enabled=True, totp_secret=pyotp.random_base32(),
        backup_codes=hash_codes(["ABCD1234"]),
    )


def _login(user, **extra):
    client = Client(HTTP_HOST=HOST)
    response = client.post(LOGIN_URL, {"username": user.email, "password": PASSWORD, "next": "/admin/", **extra})
    return client, response


def _is_logged_in(client):
    return "_auth_user_id" in client.session


def test_password_only_admin_login_of_2fa_user_gets_no_session(staff_2fa):
    client, response = _login(staff_2fa)
    assert response.status_code == 200  # se vuelve a pintar el formulario
    assert not _is_logged_in(client)
    assert client.get("/admin/").status_code == 302


def test_wrong_otp_is_refused(staff_2fa):
    client, response = _login(staff_2fa, otp="000000")
    assert response.status_code == 200
    assert not _is_logged_in(client)


def test_valid_totp_logs_in(staff_2fa):
    client, response = _login(staff_2fa, otp=pyotp.TOTP(staff_2fa.totp_secret).now())
    assert response.status_code == 302
    assert _is_logged_in(client)
    assert client.get("/admin/").status_code == 200


def test_backup_code_logs_in_once(staff_2fa):
    client, response = _login(staff_2fa, otp="abcd1234")
    assert response.status_code == 302 and _is_logged_in(client)
    client, response = _login(staff_2fa, otp="ABCD1234")
    assert not _is_logged_in(client)


def test_admin_2fa_attempts_share_the_lockout(staff_2fa):
    # Fallos previos en cualquier puerta (JWT o admin) gastan el mismo contador por usuario.
    for _ in range(TWO_FA_FAIL_LIMIT):
        check_and_count_2fa(staff_2fa)
    client, response = _login(staff_2fa, otp=pyotp.TOTP(staff_2fa.totp_secret).now())
    assert response.status_code == 200  # formulario con error, no un 500
    assert LOCKOUT_MESSAGE in response.content.decode()
    assert not _is_logged_in(client)


def test_user_without_2fa_logs_in_with_password(user_factory):
    user = user_factory(role="manager", is_staff=True)
    client, response = _login(user)
    assert response.status_code == 302
    assert _is_logged_in(client)


def test_admin_session_does_not_authenticate_the_api(user_factory):
    user = user_factory(role="manager", is_staff=True)
    client, _ = _login(user)
    assert client.get("/admin/").status_code == 200
    assert client.get("/api/users/profile/").status_code == 401


def test_login_page_renders_the_otp_field(tenant_schema):
    assert 'name="otp"' in Client(HTTP_HOST=HOST).get(LOGIN_URL).content.decode()
