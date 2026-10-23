"""Límite de intentos de login, fortaleza de contraseñas y rate limit del login del admin."""

import os
import subprocess
import sys

import pytest
from django.core.cache import cache
from django.test import Client, override_settings

from apps.users import lockout
from config.settings.base import AUTH_PASSWORD_VALIDATORS as BASE_VALIDATORS

LOGIN_URL = "/api/tenants/login/"
PASSWORD = "clave-de-prueba-123"  # contraseña de UserFactory
LOCKOUT_MSG = "Demasiados intentos. Intenta de nuevo en unos minutos."

strong_validators = override_settings(AUTH_PASSWORD_VALIDATORS=BASE_VALIDATORS)


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def _login(client, email, password, ip="10.0.0.1"):
    return client.post(
        LOGIN_URL, {"email": email, "password": password}, format="json", REMOTE_ADDR=ip
    )


def _errors(response):
    return str(response.json())


def test_sixth_attempt_is_locked_even_with_correct_password(api_client, user_factory):
    user = user_factory(email="bloqueo@crediflux.test")
    for _ in range(lockout.LOGIN_FAIL_LIMIT):
        response = _login(api_client, user.email, "incorrecta-xyz")
        assert response.status_code == 400
        assert LOCKOUT_MSG not in _errors(response)

    response = _login(api_client, user.email, PASSWORD)
    assert response.status_code == 400
    assert LOCKOUT_MSG in _errors(response)


def test_lockout_message_does_not_reveal_unknown_accounts(api_client):
    for _ in range(lockout.LOGIN_FAIL_LIMIT):
        _login(api_client, "no-existe@crediflux.test", "incorrecta-xyz")
    response = _login(api_client, "no-existe@crediflux.test", "incorrecta-xyz")
    assert response.status_code == 400
    assert LOCKOUT_MSG in _errors(response)


def test_per_email_counter_applies_across_ips(api_client, user_factory):
    user = user_factory(email="multi-ip@crediflux.test")
    for i in range(lockout.LOGIN_FAIL_LIMIT):
        _login(api_client, user.email.upper(), "incorrecta-xyz", ip=f"10.0.1.{i}")
    response = _login(api_client, user.email, PASSWORD, ip="10.0.2.1")
    assert LOCKOUT_MSG in _errors(response)


def test_per_ip_counter_applies_across_emails(api_client, user_factory):
    user = user_factory(email="spray@crediflux.test")
    for i in range(lockout.LOGIN_FAIL_LIMIT):
        _login(api_client, f"otro{i}@crediflux.test", "incorrecta-xyz", ip="10.0.3.1")
    response = _login(api_client, user.email, PASSWORD, ip="10.0.3.1")
    assert LOCKOUT_MSG in _errors(response)


def test_login_succeeds_after_reset(api_client, user_factory):
    user = user_factory(email="reset@crediflux.test")
    for _ in range(lockout.LOGIN_FAIL_LIMIT):
        _login(api_client, user.email, "incorrecta-xyz")
    assert LOCKOUT_MSG in _errors(_login(api_client, user.email, PASSWORD))

    lockout.reset(user.email)
    # El contador por IP es independiente y caduca con la ventana; otra IP aísla el de la cuenta.
    response = _login(api_client, user.email, PASSWORD, ip="10.0.9.9")
    assert response.status_code == 200, response.content


def test_successful_login_resets_the_account_counter(api_client, user_factory):
    user = user_factory(email="exito@crediflux.test")
    for _ in range(lockout.LOGIN_FAIL_LIMIT - 1):
        _login(api_client, user.email, "incorrecta-xyz", ip="10.0.4.1")
    assert _login(api_client, user.email, PASSWORD, ip="10.0.4.2").status_code == 200
    # Sin el reset, este fallo sería el quinto y el siguiente intento quedaría bloqueado.
    _login(api_client, user.email, "incorrecta-xyz", ip="10.0.4.3")
    assert _login(api_client, user.email, PASSWORD, ip="10.0.4.4").status_code == 200


def test_tenant_aware_login_serializer_shares_the_counter(tenant_schema, user_factory):
    from django.test import RequestFactory
    from rest_framework import serializers

    from apps.users.serializers import TenantAwareLoginSerializer

    user = user_factory(email="dj-rest-auth@crediflux.test")
    request = RequestFactory().post("/", REMOTE_ADDR="10.0.5.1")
    request.tenant = tenant_schema

    def attempt(password):
        serializer = TenantAwareLoginSerializer(context={"request": request})
        return serializer.validate({"email": user.email, "password": password})

    for _ in range(lockout.LOGIN_FAIL_LIMIT):
        with pytest.raises(serializers.ValidationError) as exc:
            attempt("incorrecta-xyz")
        assert LOCKOUT_MSG not in str(exc.value.detail)
    with pytest.raises(serializers.ValidationError) as exc:
        attempt(PASSWORD)
    assert LOCKOUT_MSG in str(exc.value.detail)


@strong_validators
def test_team_create_rejects_weak_password(auth_client):
    payload = {
        "email": "debil@crediflux.test",
        "username": "debil",
        "first_name": "Ana",
        "last_name": "Pérez",
        "password": "password1",
        "role": "loan_officer",
    }
    response = auth_client.post("/api/users/team/create/", payload, format="json")
    assert response.status_code == 400
    assert "password" in response.json()


@strong_validators
def test_change_password_rejects_weak_password(auth_client):
    response = auth_client.post(
        "/api/users/profile/change-password/",
        {"current_password": PASSWORD, "new_password": "12345678", "confirm_password": "12345678"},
        format="json",
    )
    assert response.status_code == 400
    assert "new_password" in response.json()


@strong_validators
def test_validate_strength_raises_drf_error():
    from rest_framework import serializers

    with pytest.raises(serializers.ValidationError):
        lockout.validate_strength("12345678")
    lockout.validate_strength("Un4-frase-larga-y-rara")


def test_development_settings_keep_password_validators():
    env = {**os.environ, "DJANGO_ENVIRONMENT": "development"}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    # Subproceso: importar development.py aquí mutaría listas/dicts compartidos con base.py.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import config.settings.development as d; assert d.AUTH_PASSWORD_VALIDATORS, 'vacío'",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    )
    assert result.returncode == 0, result.stderr


def test_admin_login_is_rate_limited(tenant_schema):
    client = Client(HTTP_HOST="tenant.test.localhost")
    data = {"username": "admin-rl@crediflux.test", "password": "incorrecta-xyz"}
    for _ in range(5):
        assert client.post("/admin/login/", data).status_code == 200
    assert client.post("/admin/login/", data).status_code == 403
