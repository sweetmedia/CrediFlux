"""Re-autenticación con contraseña (cambio de clave, desactivar 2FA, códigos de respaldo) (run-2).

Cada endpoint gasta un contador por usuario (`reauth_fail:<pk>`): tras 5 contraseñas
incorrectas, la correcta también se rechaza hasta que caduca la ventana. El contador es
propio: no bloquea la puerta de login de la víctima.
"""
import pyotp
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.users.lockout import LOCKOUT_MESSAGE, REAUTH_FAIL_LIMIT

pytestmark = pytest.mark.django_db
HOST = "tenant.test.localhost"
PASSWORD = "clave-de-prueba-123"
NEW_PASSWORD = "Otra-Clave-Segura-789!"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


def _client(user):
    client = APIClient(HTTP_HOST=HOST)
    client.force_authenticate(user=user)
    return client


def _change_password(client, current):
    return client.post(
        "/api/users/profile/change-password/",
        {"current_password": current, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        format="json",
    )


def _disable_2fa(client, password):
    return client.post("/api/users/auth/2fa/disable/", {"password": password, "code": "000000"}, format="json")


def _backup_codes(client, password):
    return client.post("/api/users/auth/2fa/backup-codes/", {"password": password, "code": "000000"}, format="json")


def _locked(response):
    return response.status_code == 400 and LOCKOUT_MESSAGE in str(response.data)


def test_change_password_locks_after_budget(user_factory):
    user = user_factory(role="loan_officer")
    client = _client(user)
    for i in range(REAUTH_FAIL_LIMIT):
        response = _change_password(client, f"incorrecta-{i}")
        assert response.status_code == 400 and not _locked(response)
    assert _locked(_change_password(client, PASSWORD))
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_change_password_success_clears_the_counter(user_factory):
    user = user_factory(role="loan_officer")
    client = _client(user)
    for i in range(REAUTH_FAIL_LIMIT - 1):
        _change_password(client, f"incorrecta-{i}")
    assert _change_password(client, PASSWORD).status_code == 200
    assert cache.get(f"reauth_fail:{user.pk}") is None


@pytest.mark.parametrize("call", [_disable_2fa, _backup_codes])
def test_2fa_endpoints_lock_after_budget(call, user_factory):
    user = user_factory(role="loan_officer", is_2fa_enabled=True, totp_secret=pyotp.random_base32())
    client = _client(user)
    for i in range(REAUTH_FAIL_LIMIT):
        call(client, f"incorrecta-{i}")
    assert _locked(call(client, PASSWORD))
    user.refresh_from_db()
    assert user.is_2fa_enabled


def test_reauth_counter_does_not_lock_the_login_door(user_factory):
    user = user_factory(role="loan_officer")
    client = _client(user)
    for i in range(REAUTH_FAIL_LIMIT + 2):
        _change_password(client, f"incorrecta-{i}")
    response = APIClient(HTTP_HOST=HOST).post(
        "/api/tenants/login/", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200, response.data
