"""Petición de reset de contraseña sin oráculo, alineada con `verify-email/send` (ronda 33).

`password-reset/request` responde siempre lo mismo (200 y mensaje genérico) a cualquier correo con
formato válido y sólo envía el enlace a un usuario activo que pasa `user_on_request_host` en el host
de la petición (la misma regla que el canje). Un fallo de SMTP no da 500, tiene throttle propio por
red del cliente (`password_reset_request`) y un enfriamiento silencioso por destinatario.
"""
import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

from apps.tenants.models import Domain, Tenant
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

BASE = "crediflux.test"
HOST_A = f"acme.{BASE}"
HOST_B = f"beta.{BASE}"
PUBLIC_HOST = "localhost"  # dominio del tenant público en conftest

RESET_REQUEST = "/api/users/auth/password-reset/request/"
RESET_CONFIRM = "/api/users/auth/password-reset/confirm/"
NEW_PASSWORD = "Zq8!nWv#4rTy6uPo"
RESET_GENERIC = {
    "message": "If an account exists with this email, a password reset link has been sent.",
}

links = override_settings(FRONTEND_URL=f"https://{BASE}", TENANT_BASE_DOMAIN=BASE)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def make_tenant(name, *domains):
    """Tenant sin schema propio (sólo resuelve hosts y es FK de usuarios)."""
    tenant = Tenant(schema_name=name, name=name, business_name=f"{name} SRL", email=f"admin@{name}.test")
    tenant.auto_create_schema = False
    tenant.save(verbosity=0)
    for index, domain in enumerate(domains):
        Domain.objects.create(domain=domain, tenant=tenant, is_primary=index == 0)
    return tenant


@pytest.fixture
def tenants(public_schema):
    return make_tenant("acme", HOST_A), make_tenant("beta", HOST_B)


def client_on(host, **extra):
    return APIClient(HTTP_HOST=host, **extra)


def ask(host, email, **extra):
    return client_on(host, **extra).post(RESET_REQUEST, {"email": email}, format="json")


def reset_link(message):
    match = re.search(r"(https?://\S+/reset-password\S*)", message.body)
    assert match, message.body
    return urlparse(match.group(1))


# ---------------------------------------------------------------------------
# Misma respuesta en todos los casos; sólo el usuario válido en su host recibe correo
# ---------------------------------------------------------------------------


def _unknown(tenants):
    return HOST_B, "nadie-nunca@beta.test"


def _inactive(tenants):
    UserFactory(email="baja@beta.test", tenant=tenants[1], is_active=False)
    return HOST_B, "baja@beta.test"


def _other_tenant_from_b(tenants):
    UserFactory(email="cajero@acme.test", tenant=tenants[0])
    return HOST_B, "cajero@acme.test"


def _platform_superuser_from_tenant_host(tenants):
    UserFactory(email="plataforma@crediflux.test", tenant=None, is_superuser=True, is_staff=True)
    return HOST_B, "plataforma@crediflux.test"


def _tenant_user_from_public_host(tenants):
    UserFactory(email="cajero@beta.test", tenant=tenants[1])
    return PUBLIC_HOST, "cajero@beta.test"


NO_MAIL_CASES = pytest.mark.parametrize("case", [
    _unknown, _inactive, _other_tenant_from_b, _platform_superuser_from_tenant_host,
    _tenant_user_from_public_host,
], ids=lambda case: case.__name__.strip("_"))


@links
@NO_MAIL_CASES
def test_no_recipient_on_this_host_gets_the_same_response_and_no_mail(tenants, case):
    host, email = case(tenants)
    UserFactory(email="valido@beta.test", tenant=tenants[1])
    reference = ask(HOST_B, "valido@beta.test")
    assert len(mail.outbox) == 1
    mail.outbox.clear()

    response = ask(host, email)

    assert response.status_code == reference.status_code == 200
    assert response.content == reference.content
    assert response.json() == RESET_GENERIC
    assert mail.outbox == []


@links
def test_valid_user_on_its_own_host_gets_the_link_to_its_tenant_domain(tenants):
    _, beta = tenants
    user = UserFactory(email="cajero@beta.test", tenant=beta)

    response = ask(HOST_B, user.email)

    assert response.status_code == 200
    assert response.json() == RESET_GENERIC
    assert [message.to for message in mail.outbox] == [[user.email]]
    assert reset_link(mail.outbox[0]).netloc == HOST_B


@links
def test_user_without_tenant_gets_the_link_only_from_the_public_host(tenants):
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None)

    assert ask(HOST_A, user.email).json() == RESET_GENERIC
    assert mail.outbox == []

    assert ask(PUBLIC_HOST, user.email).json() == RESET_GENERIC
    assert [message.to for message in mail.outbox] == [[user.email]]
    assert reset_link(mail.outbox[0]).netloc == BASE


@links
def test_platform_superuser_gets_the_link_from_the_public_host(tenants):
    user = UserFactory(email="plataforma@crediflux.test", tenant=None, is_superuser=True, is_staff=True)

    assert ask(PUBLIC_HOST, user.email).json() == RESET_GENERIC
    assert [message.to for message in mail.outbox] == [[user.email]]


def test_invalid_email_format_is_still_a_field_error(public_schema):
    response = ask(PUBLIC_HOST, "no-es-un-correo")

    assert response.status_code == 400
    assert "email" in response.json()


# ---------------------------------------------------------------------------
# SMTP, request ausente y flujo normal
# ---------------------------------------------------------------------------


@links
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="127.0.0.1", EMAIL_PORT=1,
    EMAIL_TIMEOUT=2,
)
def test_smtp_failure_gives_the_same_response(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)
    reference = ask(HOST_A, "nadie-nunca@acme.test")

    response = ask(HOST_A, user.email)

    assert response.status_code == 200
    assert response.content == reference.content


def test_request_without_request_in_context_sends_nothing(public_schema):
    from apps.users.serializers import PasswordResetRequestSerializer

    # Usuario sin tenant: sin la guarda pasaría `user_on_request_host` con request None.
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None)
    serializer = PasswordResetRequestSerializer(data={"email": user.email})
    assert serializer.is_valid(), serializer.errors

    assert serializer.save() == RESET_GENERIC
    assert mail.outbox == []


@links
def test_normal_reset_flow_still_works(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)

    assert ask(HOST_A, user.email).status_code == 200
    query = parse_qs(reset_link(mail.outbox[0]).query)
    response = client_on(HOST_A).post(
        RESET_CONFIRM,
        {"uid": query["uid"][0], "token": query["token"][0],
         "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        format="json",
    )

    user.refresh_from_db()
    assert response.status_code == 200, response.content
    assert user.check_password(NEW_PASSWORD)


# ---------------------------------------------------------------------------
# Throttle propio y enfriamiento por destinatario
# ---------------------------------------------------------------------------


def throttled_settings(rate="2/hour"):
    rf = dict(api_settings.user_settings)
    rf["DEFAULT_THROTTLE_RATES"] = {"password_reset_request": rate}
    return override_settings(REST_FRAMEWORK=rf)


def test_request_view_uses_its_own_scope():
    from django.conf import settings

    from apps.users.views import PasswordResetRequestThrottle, PasswordResetRequestView

    assert list(PasswordResetRequestView.throttle_classes) == [PasswordResetRequestThrottle]
    assert PasswordResetRequestThrottle.scope == "password_reset_request"
    assert "password_reset_request" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]


@links
def test_request_is_throttled_per_client_ip(tenants):
    # Usuarios reales en su host: BASE también les responde 200, así que en BASE el test falla
    # justo por la falta del 429.
    acme, beta = tenants
    uno = UserFactory(email="uno@acme.test", tenant=acme)
    dos = UserFactory(email="dos@beta.test", tenant=beta)
    tres = UserFactory(email="tres@acme.test", tenant=acme)

    with throttled_settings():
        # Correos distintos: el throttle cuenta por IP, no por correo.
        statuses = [ask(HOST_A, uno.email).status_code, ask(HOST_B, dos.email).status_code]
        third = ask(HOST_A, tres.email)
        # Otra IP conserva su cupo.
        other_ip = ask(HOST_A, tres.email, REMOTE_ADDR="198.51.100.7")

    assert third.status_code == 429
    assert statuses == [200, 200]
    assert other_ip.status_code == 200


@links
def test_second_request_within_the_cooldown_sends_nothing_and_answers_the_same(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)
    other = UserFactory(email="otro@acme.test", tenant=acme)

    first = ask(HOST_A, user.email)
    second = ask(HOST_A, user.email, REMOTE_ADDR="198.51.100.7")  # otra IP: el enfriamiento es por usuario
    third = ask(HOST_A, other.email)

    assert first.status_code == second.status_code == third.status_code == 200
    assert first.content == second.content == third.content
    assert [message.to for message in mail.outbox] == [[user.email], [other.email]]

    # Pasado el enfriamiento (aquí, borrando su clave) vuelve a enviarse.
    cache.delete(f"password_reset_request_cooldown:{user.pk}")
    assert ask(HOST_A, user.email).content == first.content
    assert [message.to for message in mail.outbox][-1] == [user.email]
    assert len(mail.outbox) == 3


@links
def test_cooldown_key_is_written_only_on_a_real_send(tenants):
    acme, beta = tenants
    on_beta = UserFactory(email="cajero@beta.test", tenant=beta)

    ask(HOST_A, on_beta.email)  # host ajeno: no se envía

    assert mail.outbox == []
    assert cache.get(f"password_reset_request_cooldown:{on_beta.pk}") is None
    ask(HOST_B, on_beta.email)
    assert len(mail.outbox) == 1


# ---------------------------------------------------------------------------
# Ronda 33.1 — un envío fallido libera el enfriamiento
# ---------------------------------------------------------------------------

SMTP_DOWN = override_settings(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="127.0.0.1", EMAIL_PORT=1,
    EMAIL_TIMEOUT=2,
)


@links
def test_failed_send_releases_the_cooldown_and_answers_the_same(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)
    reference = ask(HOST_A, "nadie-nunca@acme.test")

    with SMTP_DOWN:
        failed = ask(HOST_A, user.email)

    assert failed.status_code == 200
    assert failed.content == reference.content
    assert cache.get(f"password_reset_request_cooldown:{user.pk}") is None
    # El siguiente intento, ya con SMTP, sí envía: el fallo no lo bloquea 10 minutos.
    assert ask(HOST_A, user.email).content == reference.content
    assert [message.to for message in mail.outbox] == [[user.email]]


@links
def test_send_mail_returning_zero_releases_the_cooldown(tenants):
    from unittest import mock

    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)

    with mock.patch("apps.users.serializers.send_mail", return_value=0) as fake:
        response = ask(HOST_A, user.email)

    assert fake.call_count == 1
    assert response.json() == RESET_GENERIC
    assert cache.get(f"password_reset_request_cooldown:{user.pk}") is None


# ---------------------------------------------------------------------------
# Ronda 33.2 — una excepción al enviar no da 500 y `None` no libera el enfriamiento
# ---------------------------------------------------------------------------


@links
def test_exception_while_sending_gives_the_same_response_and_releases_the_cooldown(tenants, caplog):
    from unittest import mock

    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)
    reference = ask(HOST_A, "nadie-nunca@acme.test")

    with mock.patch("apps.users.serializers.send_mail", side_effect=RuntimeError("backend roto")):
        with caplog.at_level("ERROR", logger="apps.users.serializers"):
            response = ask(HOST_A, user.email)

    assert response.status_code == reference.status_code == 200
    assert response.content == reference.content
    assert cache.get(f"password_reset_request_cooldown:{user.pk}") is None
    assert [r for r in caplog.records if r.name == "apps.users.serializers" and r.exc_info]


@links
def test_backend_returning_none_keeps_the_cooldown(tenants):
    from unittest import mock

    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)

    with mock.patch("apps.users.serializers.send_mail", return_value=None) as fake:
        ask(HOST_A, user.email)
        ask(HOST_A, user.email)

    assert fake.call_count == 1
    assert cache.get(f"password_reset_request_cooldown:{user.pk}") == 1
