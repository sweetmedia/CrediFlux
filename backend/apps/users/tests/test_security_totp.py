"""TOTP de un solo uso por paso y regeneración de códigos de respaldo con segundo factor."""

import time
from unittest import mock

import pyotp
import pytest
from django.core.cache import cache

LOGIN_2FA_URL = "/api/users/auth/2fa/login/"
BACKUP_CODES_URL = "/api/users/auth/2fa/backup-codes/"
DISABLE_URL = "/api/users/auth/2fa/disable/"
PASSWORD = "clave-de-prueba-123"  # contraseña de UserFactory
OLD_CODES = ["AAAA1111", "BBBB2222"]


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def frozen_now():
    """Congela el reloj a mitad de un paso de 30 s para que la prueba no cruce un límite."""
    now = (int(time.time()) // 30) * 30 + 10
    with mock.patch("apps.users.totp.time.time", return_value=now):
        yield now


@pytest.fixture
def user_2fa(user_factory):
    return user_factory(
        role="admin",
        is_2fa_enabled=True,
        totp_secret=pyotp.random_base32(),
        backup_codes=list(OLD_CODES),
    )


def _pending_token(user, token):
    # Igual que TenantLoginSerializer: el temp_token vive en caché 300 s.
    cache.set(f"2fa_pending_{token}", str(user.pk), timeout=300)
    return token


def test_totp_code_cannot_be_replayed_within_same_step(api_client, user_2fa, frozen_now):
    code = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    first = _pending_token(user_2fa, "token-uno")
    second = _pending_token(user_2fa, "token-dos")

    ok = api_client.post(LOGIN_2FA_URL, {"temp_token": first, "code": code}, format="json")
    assert ok.status_code == 200
    assert "access" in ok.json()

    replay = api_client.post(LOGIN_2FA_URL, {"temp_token": second, "code": code}, format="json")
    assert replay.status_code == 400
    body = replay.json()
    assert "access" not in body and "refresh" not in body
    assert "code" in body


def test_totp_replay_rejected_by_disable_after_login(api_client, user_2fa, frozen_now):
    code = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    token = _pending_token(user_2fa, "token-login")
    assert api_client.post(
        LOGIN_2FA_URL, {"temp_token": token, "code": code}, format="json"
    ).status_code == 200

    api_client.force_authenticate(user=user_2fa)
    response = api_client.post(DISABLE_URL, {"password": PASSWORD, "code": code}, format="json")
    assert response.status_code == 400
    user_2fa.refresh_from_db()
    assert user_2fa.is_2fa_enabled


def test_regenerate_backup_codes_requires_totp_code(api_client, user_2fa):
    api_client.force_authenticate(user=user_2fa)
    response = api_client.post(BACKUP_CODES_URL, {"password": PASSWORD}, format="json")
    assert response.status_code == 400
    assert "code" in response.json()
    user_2fa.refresh_from_db()
    assert user_2fa.backup_codes == OLD_CODES


def test_regenerate_backup_codes_rejects_invalid_code(api_client, user_2fa, frozen_now):
    api_client.force_authenticate(user=user_2fa)
    valid = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    wrong = f"{(int(valid) + 1) % 1_000_000:06d}"
    response = api_client.post(
        BACKUP_CODES_URL, {"password": PASSWORD, "code": wrong}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["code"] == ["Código de verificación inválido."]
    user_2fa.refresh_from_db()
    assert user_2fa.backup_codes == OLD_CODES


def test_regenerate_backup_codes_with_password_and_totp(api_client, user_2fa, frozen_now):
    api_client.force_authenticate(user=user_2fa)
    code = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    response = api_client.post(
        BACKUP_CODES_URL, {"password": PASSWORD, "code": code}, format="json"
    )
    assert response.status_code == 200
    codes = response.json()["backup_codes"]
    assert len(codes) == 10
    user_2fa.refresh_from_db()
    assert user_2fa.backup_codes == codes


def test_regenerate_backup_codes_wrong_password_keeps_error(api_client, user_2fa, frozen_now):
    api_client.force_authenticate(user=user_2fa)
    code = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    response = api_client.post(
        BACKUP_CODES_URL, {"password": "incorrecta-xyz", "code": code}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()
