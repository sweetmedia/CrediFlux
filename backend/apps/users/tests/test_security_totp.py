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


def _assert_stored_hashes_of(user, codes):
    """Se guardan hashes (uno por código), nunca el código en claro."""
    from django.contrib.auth.hashers import check_password

    stored = user.backup_codes
    assert len(stored) == len(codes)
    serialized = repr(stored)
    for code in codes:
        assert code not in serialized
    for code, encoded in zip(codes, stored):
        assert "$" in encoded
        assert check_password(code, encoded)


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
    _assert_stored_hashes_of(user_2fa, codes)


def test_regenerate_backup_codes_wrong_password_keeps_error(api_client, user_2fa, frozen_now):
    api_client.force_authenticate(user=user_2fa)
    code = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    response = api_client.post(
        BACKUP_CODES_URL, {"password": "incorrecta-xyz", "code": code}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()


# --- Límite de intentos del segundo factor (fix round 1) ---

LOCKOUT_MSG = "Demasiados intentos. Intenta de nuevo en unos minutos."


def _wrong_code(user, at):
    valid = pyotp.TOTP(user.totp_secret).at(at)
    return f"{(int(valid) + 1) % 1_000_000:06d}"


def _exhaust_2fa_login(api_client, user, token, now):
    wrong = _wrong_code(user, now)
    for _ in range(5):
        response = api_client.post(
            LOGIN_2FA_URL, {"temp_token": token, "code": wrong}, format="json"
        )
        assert response.status_code == 400
        assert LOCKOUT_MSG not in str(response.json())


def test_2fa_login_locks_after_five_wrong_codes(api_client, user_2fa, frozen_now):
    token = _pending_token(user_2fa, "token-fuerza")
    _exhaust_2fa_login(api_client, user_2fa, token, frozen_now)

    valid = pyotp.TOTP(user_2fa.totp_secret).at(frozen_now)
    response = api_client.post(LOGIN_2FA_URL, {"temp_token": token, "code": valid}, format="json")
    assert response.status_code == 400
    body = response.json()
    assert LOCKOUT_MSG in str(body)
    assert "access" not in body and "refresh" not in body
    # El temp_token quedó invalidado: hay que volver a hacer login.
    assert cache.get(f"2fa_pending_{token}") is None
    again = api_client.post(LOGIN_2FA_URL, {"temp_token": token, "code": valid}, format="json")
    assert again.status_code == 400
    assert "temp_token" in again.json()


def test_2fa_login_works_again_after_window(api_client, user_2fa, frozen_now):
    token = _pending_token(user_2fa, "token-ventana")
    _exhaust_2fa_login(api_client, user_2fa, token, frozen_now)

    later = frozen_now + 301  # pasa la ventana de 300 s del contador
    with mock.patch("apps.users.totp.time.time", return_value=later):
        new_token = _pending_token(user_2fa, "token-nuevo")
        valid = pyotp.TOTP(user_2fa.totp_secret).at(later)
        response = api_client.post(
            LOGIN_2FA_URL, {"temp_token": new_token, "code": valid}, format="json"
        )
    assert response.status_code == 200
    assert "access" in response.json()


def test_disable_locks_after_wrong_codes(api_client, user_2fa, frozen_now):
    api_client.force_authenticate(user=user_2fa)
    wrong = _wrong_code(user_2fa, frozen_now)
    for _ in range(5):
        response = api_client.post(
            DISABLE_URL, {"password": PASSWORD, "code": wrong}, format="json"
        )
        assert response.status_code == 400
        assert LOCKOUT_MSG not in str(response.json())

    response = api_client.post(DISABLE_URL, {"password": PASSWORD, "code": wrong}, format="json")
    assert response.status_code == 400
    assert LOCKOUT_MSG in str(response.json())
    user_2fa.refresh_from_db()
    assert user_2fa.is_2fa_enabled


# --- Códigos de respaldo guardados como hash ---------------------------------------------

VERIFY_URL = "/api/users/auth/2fa/verify/"


def _backup_login(api_client, user, code, token):
    return api_client.post(
        LOGIN_2FA_URL, {"temp_token": _pending_token(user, token), "backup_code": code}, format="json"
    )


def test_enable_2fa_stores_hashed_backup_codes(api_client, user_factory, frozen_now):
    user = user_factory(role="admin", totp_secret=pyotp.random_base32())
    api_client.force_authenticate(user=user)
    code = pyotp.TOTP(user.totp_secret).at(frozen_now)
    response = api_client.post(VERIFY_URL, {"code": code}, format="json")
    assert response.status_code == 200, response.content
    codes = response.json()["backup_codes"]
    assert len(codes) == 10
    user.refresh_from_db()
    _assert_stored_hashes_of(user, codes)


def test_hashed_backup_code_works_once(api_client, user_factory):
    from apps.users.backup_codes import hash_codes

    user = user_factory(role="admin", is_2fa_enabled=True, totp_secret=pyotp.random_base32(),
                        backup_codes=hash_codes(["CAFE0001", "CAFE0002"]))
    response = _backup_login(api_client, user, "cafe0001", "token-hash-1")  # sin distinguir mayúsculas
    assert response.status_code == 200, response.content
    assert "access" in response.json()
    user.refresh_from_db()
    assert len(user.backup_codes) == 1

    reuse = _backup_login(api_client, user, "CAFE0001", "token-hash-2")
    assert reuse.status_code == 400
    assert "backup_code" in reuse.json()
    user.refresh_from_db()
    assert len(user.backup_codes) == 1


def test_wrong_backup_code_consumes_nothing(api_client, user_factory):
    from apps.users.backup_codes import hash_codes

    stored = hash_codes(["CAFE0001"])
    user = user_factory(role="admin", is_2fa_enabled=True, totp_secret=pyotp.random_base32(),
                        backup_codes=stored)
    response = _backup_login(api_client, user, "DEAD0000", "token-mal")
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.backup_codes == stored


def test_legacy_plaintext_code_works_once_and_rest_are_rehashed(api_client, user_2fa):
    response = _backup_login(api_client, user_2fa, OLD_CODES[0], "token-legacy-1")
    assert response.status_code == 200, response.content
    user_2fa.refresh_from_db()
    # Queda sólo el otro código, ya como hash.
    _assert_stored_hashes_of(user_2fa, [OLD_CODES[1]])

    reuse = _backup_login(api_client, user_2fa, OLD_CODES[0], "token-legacy-2")
    assert reuse.status_code == 400
    # El código restante sigue sirviendo después del rehash.
    assert _backup_login(api_client, user_2fa, OLD_CODES[1], "token-legacy-3").status_code == 200
    user_2fa.refresh_from_db()
    assert user_2fa.backup_codes == []


def test_consume_locks_the_user_row(user_factory):
    """El consumo relee la fila con select_for_update dentro de una transacción."""
    from apps.users import backup_codes
    from apps.users.models import User

    user = user_factory(backup_codes=backup_codes.hash_codes(["CAFE0001"]))
    real = User.objects.select_for_update
    with mock.patch.object(User.objects, "select_for_update", side_effect=real) as locked:
        assert backup_codes.consume_backup_code(user, "CAFE0001") is True
    locked.assert_called_once()
    assert backup_codes.consume_backup_code(user, "CAFE0001") is False
