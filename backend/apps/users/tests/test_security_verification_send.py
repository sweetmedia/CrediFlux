"""Verificación de correo: token propio y envío sin oráculo (ronda 32).

Parte A: el token de verificación sale de `email_verification_token` (salt propio y `email_verified`
en el hash). No sirve como token de reset, un token de reset no verifica y el de verificación deja de
valer al usarse.

Parte B: `verify-email/send` responde siempre lo mismo (200 y mensaje genérico) a cualquier correo con
formato válido y sólo envía el enlace a un usuario activo, sin verificar y que pasa
`user_on_request_host` en el host de la petición. Tiene throttle propio por IP (`verify_email_send`).
"""
import re
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

from apps.tenants.models import Domain, Tenant
from apps.users.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

BASE = "crediflux.test"
HOST_A = f"acme.{BASE}"
HOST_B = f"beta.{BASE}"
PUBLIC_HOST = "localhost"  # dominio del tenant público en conftest

VERIFY_SEND = "/api/users/auth/verify-email/send/"
VERIFY_CONFIRM = "/api/users/auth/verify-email/confirm/"
RESET_REQUEST = "/api/users/auth/password-reset/request/"
RESET_CONFIRM = "/api/users/auth/password-reset/confirm/"

NEW_PASSWORD = "Zq8!nWv#4rTy6uPo"
RESET_EXTRA = {"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}
RESET_ERROR = {"token": ["Invalid or expired reset token."]}
VERIFY_ERROR = {"token": ["Invalid or expired verification token."]}
SEND_GENERIC = {
    "message": "If an account with this email needs verification, a verification link has been sent.",
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


def link_in(message, path):
    match = re.search(r"(https?://\S+" + re.escape(path) + r"\S*)", message.body)
    assert match, message.body
    return urlparse(match.group(1))


def token_from(message, path):
    query = parse_qs(link_in(message, path).query)
    return {"uid": query["uid"][0], "token": query["token"][0]}


def send(host, email, **extra):
    return client_on(host, **extra).post(VERIFY_SEND, {"email": email}, format="json")


def verification_token(host, user):
    response = send(host, user.email)
    assert response.status_code == 200, response.content
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [user.email]
    return token_from(mail.outbox[0], "/verify-email")


def reset_token(host, user):
    response = client_on(host).post(RESET_REQUEST, {"email": user.email}, format="json")
    assert response.status_code == 200, response.content
    return token_from(mail.outbox[-1], "/reset-password")


# ---------------------------------------------------------------------------
# Parte A — el token de verificación no es un token de reset
# ---------------------------------------------------------------------------


@links
def test_verification_token_is_not_a_password_reset_token(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    body = verification_token(HOST_A, user)

    response = client_on(HOST_A).post(RESET_CONFIRM, {**body, **RESET_EXTRA}, format="json")

    user.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == RESET_ERROR
    assert not user.check_password(NEW_PASSWORD)


@links
def test_password_reset_token_is_not_a_verification_token(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    body = reset_token(HOST_A, user)

    response = client_on(HOST_A).post(VERIFY_CONFIRM, body, format="json")

    user.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == VERIFY_ERROR
    assert user.email_verified is False


@links
def test_verification_token_is_single_use(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    body = verification_token(HOST_A, user)
    on_acme = client_on(HOST_A)

    first = on_acme.post(VERIFY_CONFIRM, body, format="json")
    again = on_acme.post(VERIFY_CONFIRM, body, format="json")

    assert first.status_code == 200, first.content
    # Mismo error genérico que un token inválido: ya no hay rama "Email is already verified."
    assert again.status_code == 400
    assert again.json() == VERIFY_ERROR


@links
def test_normal_verification_and_reset_flows_still_work(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    on_acme = client_on(HOST_A)

    verify = on_acme.post(VERIFY_CONFIRM, verification_token(HOST_A, user), format="json")
    user.refresh_from_db()
    assert verify.status_code == 200, verify.content
    assert verify.json() == {"message": "Email verified successfully.", "email": user.email, "email_verified": True}
    assert user.email_verified is True

    reset = on_acme.post(RESET_CONFIRM, {**reset_token(HOST_A, user), **RESET_EXTRA}, format="json")
    user.refresh_from_db()
    assert reset.status_code == 200, reset.content
    assert user.check_password(NEW_PASSWORD)


def test_verification_generator_has_its_own_salt_and_hashes_the_verified_flag(public_schema):
    from django.contrib.auth.tokens import default_token_generator

    from apps.users.tokens import email_verification_token

    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None, email_verified=False)
    token = email_verification_token.make_token(user)

    assert email_verification_token.key_salt != default_token_generator.key_salt
    assert email_verification_token.check_token(user, token)
    assert not default_token_generator.check_token(user, token)
    user.email_verified = True
    assert not email_verification_token.check_token(user, token)


# ---------------------------------------------------------------------------
# Parte B — verify-email/send sin oráculo
# ---------------------------------------------------------------------------


def _unknown(tenants):
    return HOST_A, "nadie@acme.test"


def _verified(tenants):
    UserFactory(email="verificado@acme.test", tenant=tenants[0], email_verified=True)
    return HOST_A, "verificado@acme.test"


def _inactive(tenants):
    UserFactory(email="inactivo@acme.test", tenant=tenants[0], email_verified=False, is_active=False)
    return HOST_A, "inactivo@acme.test"


def _other_tenant(tenants):
    UserFactory(email="cajero@acme.test", tenant=tenants[0], email_verified=False)
    return HOST_B, "cajero@acme.test"


def _tenant_user_on_public_host(tenants):
    UserFactory(email="cajero@acme.test", tenant=tenants[0], email_verified=False)
    return PUBLIC_HOST, "cajero@acme.test"


def _platform_superuser(tenants):
    User.objects.create_user(
        username="plataforma-r32", email="plataforma-r32@crediflux.test", password="x",
        is_superuser=True, is_staff=True, email_verified=False,
    )
    return HOST_A, "plataforma-r32@crediflux.test"


@links
@pytest.mark.parametrize("case", [
    _unknown, _verified, _inactive, _other_tenant, _tenant_user_on_public_host, _platform_superuser,
], ids=lambda case: case.__name__.strip("_"))
def test_send_answers_the_same_and_sends_nothing(tenants, case):
    host, email = case(tenants)
    reference = send(host, "nadie-nunca@acme.test")

    response = send(host, email)

    assert response.status_code == reference.status_code == 200
    assert response.content == reference.content
    assert response.json() == SEND_GENERIC
    assert mail.outbox == []


@links
def test_send_to_unverified_user_on_its_tenant_host_answers_the_same_and_sends_the_link(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    reference = send(HOST_A, "nadie-nunca@acme.test")

    response = send(HOST_A, user.email)

    assert response.status_code == 200
    assert response.content == reference.content
    assert [message.to for message in mail.outbox] == [[user.email]]
    assert link_in(mail.outbox[0], "/verify-email").netloc == HOST_A


@links
def test_send_to_user_without_tenant_only_from_the_public_host(tenants):
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None, email_verified=False)

    assert send(HOST_A, user.email).json() == SEND_GENERIC
    assert mail.outbox == []

    assert send(PUBLIC_HOST, user.email).json() == SEND_GENERIC
    assert [message.to for message in mail.outbox] == [[user.email]]
    assert link_in(mail.outbox[0], "/verify-email").netloc == BASE


def test_send_with_invalid_email_format_is_a_field_error(tenants):
    response = send(HOST_A, "no-es-un-correo")

    assert response.status_code == 400
    assert list(response.json()) == ["email"]
    assert mail.outbox == []


@links
def test_send_with_case_variant_emails_in_two_tenants_only_mails_the_host_user(tenants):
    """`email` es único, pero sólo distinguiendo mayúsculas: dos tenants pueden tener `Ana@` y `ana@`.

    La búsqueda es exacta, como la del reset; si hubiera varios candidatos se elige el que pasa la
    regla de host, nunca un 500.
    """
    acme, beta = tenants
    UserFactory(email="Ana@dup.test", tenant=acme, email_verified=False)
    on_beta = UserFactory(email="ana@dup.test", tenant=beta, email_verified=False)

    wrong_case = send(HOST_B, "Ana@dup.test")
    assert wrong_case.status_code == 200 and wrong_case.json() == SEND_GENERIC
    assert mail.outbox == []

    right = send(HOST_B, "ana@dup.test")
    assert right.status_code == 200 and right.json() == SEND_GENERIC
    assert [message.to for message in mail.outbox] == [[on_beta.email]]


@links
def test_send_with_several_candidates_picks_the_one_on_the_request_host(tenants):
    """Si la tabla tuviera varios usuarios con el mismo correo, ni 500 ni envío al de otro tenant."""
    from apps.users import serializers as user_serializers

    acme, beta = tenants
    on_acme = UserFactory(email="ana@acme.test", tenant=acme, email_verified=False)
    on_beta = UserFactory(email="ana@beta.test", tenant=beta, email_verified=False)
    both = User.objects.filter(pk__in=[on_acme.pk, on_beta.pk]).order_by("pk")

    with mock.patch.object(user_serializers, "_verification_candidates", return_value=both):
        response = send(HOST_B, "ana@cualquiera.test")

    assert response.status_code == 200 and response.json() == SEND_GENERIC
    assert [message.to for message in mail.outbox] == [[on_beta.email]]


@links
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="127.0.0.1", EMAIL_PORT=1,
    EMAIL_TIMEOUT=2,
)
def test_smtp_failure_gives_the_same_response(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    reference = send(HOST_A, "nadie-nunca@acme.test")

    response = send(HOST_A, user.email)

    assert response.status_code == 200
    assert response.content == reference.content


# ---------------------------------------------------------------------------
# Throttle propio
# ---------------------------------------------------------------------------


def throttled_settings(rate="2/hour"):
    rf = dict(api_settings.user_settings)
    rf["DEFAULT_THROTTLE_RATES"] = {"verify_email_send": rate}
    return override_settings(REST_FRAMEWORK=rf)


def test_send_view_uses_its_own_scope():
    from django.conf import settings

    from apps.users.views import EmailVerificationSendView, VerifyEmailSendThrottle

    assert list(EmailVerificationSendView.throttle_classes) == [VerifyEmailSendThrottle]
    assert VerifyEmailSendThrottle.scope == "verify_email_send"
    assert "verify_email_send" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]


@links
def test_send_is_throttled_per_client_ip(tenants):
    # Usuarios reales sin verificar en su host: BASE también les responde 200, así que en BASE
    # el test falla justo por la falta del 429.
    acme, beta = tenants
    uno = UserFactory(email="uno@acme.test", tenant=acme, email_verified=False)
    dos = UserFactory(email="dos@beta.test", tenant=beta, email_verified=False)
    tres = UserFactory(email="tres@acme.test", tenant=acme, email_verified=False)

    with throttled_settings():
        # Correos distintos: el throttle cuenta por IP, no por correo.
        statuses = [send(HOST_A, uno.email).status_code, send(HOST_B, dos.email).status_code]
        third = send(HOST_A, tres.email)
        # Otra IP conserva su cupo.
        other_ip = send(HOST_A, tres.email, REMOTE_ADDR="198.51.100.7")

    assert third.status_code == 429
    assert statuses == [200, 200]
    assert other_ip.status_code == 200


# ---------------------------------------------------------------------------
# Ronda 32.1 — sin request no se envía nada y enfriamiento por destinatario
# ---------------------------------------------------------------------------


def test_send_without_request_in_context_sends_nothing(public_schema):
    from apps.users.serializers import EmailVerificationSendSerializer

    # Usuario sin tenant: sin la guarda pasaría `user_on_request_host` con request None.
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None, email_verified=False)
    serializer = EmailVerificationSendSerializer(data={"email": user.email})
    assert serializer.is_valid(), serializer.errors

    assert serializer.save() == SEND_GENERIC
    assert mail.outbox == []


@links
def test_second_send_within_the_cooldown_sends_nothing_and_answers_the_same(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    other = UserFactory(email="otro@acme.test", tenant=acme, email_verified=False)

    first = send(HOST_A, user.email)
    second = send(HOST_A, user.email, REMOTE_ADDR="198.51.100.7")  # otra IP: el enfriamiento es por usuario
    third = send(HOST_A, other.email)

    assert first.status_code == second.status_code == third.status_code == 200
    assert first.content == second.content == third.content
    assert [message.to for message in mail.outbox] == [[user.email], [other.email]]

    # Pasado el enfriamiento (aquí, borrando su clave) vuelve a enviarse.
    cache.delete(f"verify_email_send_cooldown:{user.pk}")
    assert send(HOST_A, user.email).content == first.content
    assert [message.to for message in mail.outbox][-1] == [user.email]
    assert len(mail.outbox) == 3


# ---------------------------------------------------------------------------
# Ronda 33.1 — un envío fallido libera el enfriamiento
# ---------------------------------------------------------------------------


@links
def test_failed_send_releases_the_cooldown_and_answers_the_same(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)
    reference = send(HOST_A, "nadie-nunca@acme.test")

    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="127.0.0.1", EMAIL_PORT=1,
        EMAIL_TIMEOUT=2,
    ):
        failed = send(HOST_A, user.email)

    assert failed.status_code == 200
    assert failed.content == reference.content
    assert cache.get(f"verify_email_send_cooldown:{user.pk}") is None
    # El siguiente intento, ya con SMTP, sí envía: el fallo no lo bloquea 10 minutos.
    assert send(HOST_A, user.email).content == reference.content
    assert [message.to for message in mail.outbox] == [[user.email]]


@links
def test_send_mail_returning_zero_releases_the_cooldown(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme, email_verified=False)

    with mock.patch("apps.users.serializers.send_mail", return_value=0) as fake:
        response = send(HOST_A, user.email)

    assert fake.call_count == 1
    assert response.json() == SEND_GENERIC
    assert cache.get(f"verify_email_send_cooldown:{user.pk}") is None
