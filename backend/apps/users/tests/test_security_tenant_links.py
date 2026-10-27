"""Enlaces de reset y de verificación: van al dominio del tenant, nunca a `<schema_name>.<host>` (ronda 29).

Escenario del paso 1 del brief: la víctima `acme` (schema `acme`) se registró con el subdominio
`acmefin`; un registrante anónimo crea `evil` con el subdominio `acme`. Si el enlace del usuario de
`acme` se construye con el schema, el token viaja a `acme.<base>`, que resuelve al tenant `evil`.
"""
import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from apps.tenants.models import Domain, Tenant
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

BASE = "crediflux.test"
PUBLIC_HOST = "localhost"  # dominio del tenant público en conftest
RESET_REQUEST = "/api/users/auth/password-reset/request/"
RESET_CONFIRM = "/api/users/auth/password-reset/confirm/"
VERIFY_SEND = "/api/users/auth/verify-email/send/"
VERIFY_CONFIRM = "/api/users/auth/verify-email/confirm/"
REGISTER = "/api/tenants/register/"
GENERIC = "No se pudo completar el registro con estos datos."
NEW_PASSWORD = "Zq8!nWv#4rTy6uPo"

links = override_settings(FRONTEND_URL=f"https://{BASE}", TENANT_BASE_DOMAIN=BASE)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def make_tenant(name, *domains, primary=0, **fields):
    """Tenant sin schema propio (sólo resuelve hosts y es FK de usuarios)."""
    tenant = Tenant(
        schema_name=name.replace("-", "_"), name=name, business_name=f"{name} SRL", email=f"admin@{name}.test",
        **fields,
    )
    tenant.auto_create_schema = False
    tenant.save(verbosity=0)
    for index, domain in enumerate(domains):
        Domain.objects.create(domain=domain, tenant=tenant, is_primary=index == primary)
    return tenant


def sent_link(path):
    """URL del último correo enviado que contiene `path`."""
    assert mail.outbox, "no se envió ningún correo"
    match = re.search(r"(https?://\S+" + re.escape(path) + r"\S*)", mail.outbox[-1].body)
    assert match, mail.outbox[-1].body
    return urlparse(match.group(1))


def request_reset(client, email):
    response = client.post(RESET_REQUEST, {"email": email}, format="json")
    assert response.status_code == 200, response.content
    return sent_link("/reset-password")


def request_verification(host, email):
    """Desde la ronda 32 el enlace sólo se envía si se pide desde el host del tenant del usuario
    (sin tenant, desde el público)."""
    response = client_on(host).post(VERIFY_SEND, {"email": email}, format="json")
    assert response.status_code == 200, response.content
    return sent_link("/verify-email")


def registration(**overrides):
    data = {
        "business_name": "Evil SRL",
        "tenant_name": "evil",
        "email": "contacto@evil.test",
        "subdomain": "evil",
        "owner_first_name": "Eva",
        "owner_last_name": "Mala",
        "owner_email": "eva@evil.test",
        "owner_password": "Kx9!vRt#2mQw7zLp",
        "subscription_plan": "basic",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Paso 1 — verificación
# ---------------------------------------------------------------------------


@links
def test_a_reset_and_verify_links_use_the_tenant_domain_not_its_schema(public_client):
    """(a) Tenant con `name` distinto del subdominio y guión en el nombre."""
    tenant = make_tenant("financiera-sol", f"solfin.{BASE}")
    user = UserFactory(email="cajero@sol.test", tenant=tenant, email_verified=False)

    reset = request_reset(public_client, user.email)
    verify = request_verification(f"solfin.{BASE}", user.email)

    assert reset.netloc == f"solfin.{BASE}"
    assert verify.netloc == f"solfin.{BASE}"
    assert reset.scheme == verify.scheme == "https"


@links
def test_b_registration_rejects_a_subdomain_equal_to_another_tenants_schema(public_client):
    """(b) `acme` vive en `acmefin.<base>`; un anónimo pide el subdominio `acme`."""
    make_tenant("acme", f"acmefin.{BASE}")
    before = (Tenant.objects.count(), Domain.objects.count())

    with override_settings(MAX_TENANTS_PER_DAY=0):  # pendiente: sin CREATE SCHEMA
        response = public_client.post(REGISTER, registration(subdomain="acme"), format="json")

    assert response.status_code == 400, response.content
    assert response.json() == {"non_field_errors": [GENERIC]}
    assert (Tenant.objects.count(), Domain.objects.count()) == before


@links
def test_c_victim_link_does_not_point_to_the_attackers_domain(public_client):
    """(c) Con (a)+(b) en BASE: el enlace del usuario de `acme` iría a `acme.<base>`, el dominio de `evil`."""
    victim = make_tenant("acme", f"acmefin.{BASE}")
    make_tenant("evil", f"acme.{BASE}")  # lo que (b) deja registrar en BASE
    user = UserFactory(email="duena@acme.test", tenant=victim, email_verified=False)

    reset = request_reset(public_client, user.email)
    verify = request_verification(f"acmefin.{BASE}", user.email)

    attacker_domain = Domain.objects.get(tenant__name="evil").domain
    assert reset.netloc != attacker_domain
    assert verify.netloc != attacker_domain
    assert reset.netloc == verify.netloc == f"acmefin.{BASE}"


@links
def test_d_victim_token_redeemed_on_the_attackers_host(public_client):
    """(d) Canje del token de un usuario de `acme` en el host de `evil` (documenta el resultado)."""
    from rest_framework.test import APIClient

    victim = make_tenant("acme", f"acmefin.{BASE}")
    make_tenant("evil", f"acme.{BASE}")
    user = UserFactory(email="duena@acme.test", tenant=victim)

    link = request_reset(public_client, user.email)
    query = parse_qs(link.query)
    on_evil = APIClient(HTTP_HOST=f"acme.{BASE}")
    response = on_evil.post(
        RESET_CONFIRM,
        {"uid": query["uid"][0], "token": query["token"][0],
         "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        format="json",
    )

    user.refresh_from_db()
    assert response.status_code == 400, response.content
    assert response.json() == {"token": ["Invalid or expired reset token."]}
    assert not user.check_password(NEW_PASSWORD)


# ---------------------------------------------------------------------------
# Paso 2 — enlaces desde el Domain del tenant
# ---------------------------------------------------------------------------


@links
def test_links_of_user_without_tenant_keep_frontend_url(public_client):
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None, email_verified=False)

    assert request_reset(public_client, user.email).netloc == BASE
    assert request_verification(PUBLIC_HOST, user.email).netloc == BASE


@links
def test_tenant_without_domain_falls_back_to_frontend_url_with_warning(public_client, caplog):
    tenant = make_tenant("sin-dominio")
    user = UserFactory(email="cajero@sin-dominio.test", tenant=tenant, email_verified=False)

    # Sin Domain ningún host resuelve a este tenant, así que el envío por API no le llega
    # (ronda 32): el enlace de verificación se construye con el serializer y un request del tenant.
    from django.test import RequestFactory

    from apps.users.serializers import EmailVerificationSendSerializer

    request = RequestFactory().post(VERIFY_SEND)
    request.tenant = tenant
    serializer = EmailVerificationSendSerializer(data={"email": user.email}, context={"request": request})
    assert serializer.is_valid(), serializer.errors

    with caplog.at_level("WARNING", logger="apps.tenants.links"):
        reset = request_reset(public_client, user.email)
        serializer.save()
        verify = sent_link("/verify-email")

    assert reset.netloc == verify.netloc == BASE
    assert "sin_dominio" not in reset.geturl() and "sin-dominio" not in reset.geturl()
    assert [r for r in caplog.records if r.name == "apps.tenants.links" and r.levelname == "WARNING"]


@override_settings(FRONTEND_URL="http://localhost:3100")
def test_primary_domain_keeps_scheme_and_port_of_frontend_url(public_client):
    tenant = make_tenant("puerto-sa", "puerto.localhost")
    user = UserFactory(email="cajero@puerto.test", tenant=tenant, email_verified=False)

    reset = request_reset(public_client, user.email)
    verify = request_verification("puerto.localhost", user.email)

    assert reset.scheme == verify.scheme == "http"
    assert reset.netloc == verify.netloc == "puerto.localhost:3100"
    assert reset.path == "/reset-password"


@links
def test_primary_domain_wins_over_other_domains(public_client):
    tenant = make_tenant("varios", f"viejo.{BASE}", f"nuevo.{BASE}", f"alias.{BASE}", primary=1)
    user = UserFactory(email="cajero@varios.test", tenant=tenant, email_verified=False)

    assert request_reset(public_client, user.email).netloc == f"nuevo.{BASE}"
    assert request_verification(f"nuevo.{BASE}", user.email).netloc == f"nuevo.{BASE}"


@links
def test_without_primary_the_first_domain_by_pk_is_used():
    from apps.tenants.links import tenant_frontend_url

    tenant = make_tenant("sin-primario", f"uno.{BASE}", f"dos.{BASE}", primary=None)

    assert urlparse(tenant_frontend_url(tenant)).netloc == f"uno.{BASE}"


def test_admin_dropdown_fallback_never_uses_schema_name(public_schema):
    from django.test import RequestFactory

    from apps.users.models import User
    from config.settings.utils import get_tenant_dropdown

    make_tenant("solo-alias", "alias-r29.localhost", primary=None)
    make_tenant("sin-host-r29")
    request = RequestFactory(HTTP_HOST="localhost:8000").get("/admin/")
    request.user = User.objects.create_user(
        username="plataforma-r29", email="plataforma-r29@crediflux.test", password="x",
        is_superuser=True, is_staff=True,
    )

    links_ = {item["title"]: item["link"] for item in get_tenant_dropdown(request)}

    assert links_["solo-alias SRL"] == "http://alias-r29.localhost/admin/"
    assert "sin-host-r29 SRL" not in links_
    assert not any("solo_alias" in link or "sin_host_r29" in link for link in links_.values())


# ---------------------------------------------------------------------------
# Paso 2 — reserva cruzada en el registro
# ---------------------------------------------------------------------------


def register_pending(client, **overrides):
    with override_settings(MAX_TENANTS_PER_DAY=0):  # pendiente: sin CREATE SCHEMA
        return client.post(REGISTER, registration(**overrides), format="json")


@links
@pytest.mark.parametrize("name, schema, subdomain", [
    ("acme-corp", "acmecorp_x", "acme-corp"),   # = name de otro tenant
    ("Acme Corporativo", "acme_corp", "acme-corp"),  # = schema de otro tenant (guión ↔ guión bajo)
    ("Acme Corporativo", "acmecorp", "acmecorp"),  # = schema de otro tenant, literal
])
def test_subdomain_equal_to_another_tenants_name_or_schema_is_rejected(public_client, name, schema, subdomain):
    other = Tenant(schema_name=schema, name=name, business_name="Otro SRL", email="admin@otro.test")
    other.auto_create_schema = False
    other.save(verbosity=0)
    Domain.objects.create(domain=f"otrofin.{BASE}", tenant=other, is_primary=True)
    before = (Tenant.objects.count(), Domain.objects.count())

    response = register_pending(public_client, subdomain=subdomain)

    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}
    assert (Tenant.objects.count(), Domain.objects.count()) == before


@links
def test_subdomain_equal_to_a_pending_tenants_schema_is_rejected(public_client):
    from django.utils import timezone

    make_tenant("pendiente", f"pendfin.{BASE}", is_active=False, provisioning_pending=True,
                pending_since=timezone.now())

    response = register_pending(public_client, subdomain="pendiente")

    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}


@links
def test_tenant_name_equal_to_a_taken_subdomain_is_rejected(public_client):
    make_tenant("financiera-luna", f"luna.{BASE}")

    response = register_pending(public_client, tenant_name="luna", subdomain="luna-nueva")

    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [GENERIC]}


CROSS_CONFLICTS = [
    pytest.param({"subdomain": "acme"}, id="subdominio=schema-de-otro"),
    pytest.param({"tenant_name": "acmefin", "subdomain": "acmefin-nuevo"}, id="tenant_name=subdominio-tomado"),
]


def registration_serializer():
    from rest_framework.test import APIRequestFactory

    from apps.tenants.serializers import TenantRegistrationSerializer

    def build(**overrides):
        request = APIRequestFactory().post(REGISTER, REMOTE_ADDR="203.0.113.29")
        return TenantRegistrationSerializer(data=registration(**overrides), context={"request": request})

    return build


@links
@pytest.mark.parametrize("overrides", CROSS_CONFLICTS)
def test_cross_reservation_is_enforced_by_validate(public_schema, overrides):
    """Sólo `validate` (sin llegar a `create`): quitar el chequeo de validate lo hace fallar."""
    make_tenant("acme", f"acmefin.{BASE}")

    serializer = registration_serializer()(**overrides)

    assert serializer.is_valid() is False
    assert serializer.errors == {"non_field_errors": [GENERIC]}


@links
@override_settings(MAX_TENANTS_PER_DAY=0)  # si la re-comprobación faltara, quedaría pendiente (sin schema)
@pytest.mark.parametrize("overrides", CROSS_CONFLICTS)
def test_cross_reservation_is_rechecked_inside_create(public_schema, overrides):
    """El conflicto aparece entre `validate` y `create`: sólo la re-comprobación de `create` lo para."""
    from rest_framework import serializers as drf_serializers

    serializer = registration_serializer()(**overrides)
    assert serializer.is_valid(), serializer.errors
    make_tenant("acme", f"acmefin.{BASE}")  # otra petición lo creó después de validate
    before = (Tenant.objects.count(), Domain.objects.count())

    with pytest.raises(drf_serializers.ValidationError) as exc:
        serializer.save()

    assert exc.value.detail == [GENERIC]
    assert (Tenant.objects.count(), Domain.objects.count()) == before


@links
def test_normal_registration_is_still_accepted(public_client):
    make_tenant("acme", f"acmefin.{BASE}")

    response = register_pending(public_client, tenant_name="evil", subdomain="evil")

    assert response.status_code == 202, response.content
    assert Domain.objects.get(tenant__name="evil").domain == f"evil.{BASE}"


# ---------------------------------------------------------------------------
# Paso 2 — los confirm sólo canjean en el host del tenant del usuario
# ---------------------------------------------------------------------------


def token_body(user, generator=None, **extra):
    """uid y token de reset (o del `generator` dado) para `user`."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    generator = generator or default_token_generator
    body = {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": generator.make_token(user)}
    body.update(extra)
    return body


def verify_body(user, **extra):
    """uid y token de verificación: desde la ronda 32 sale de su propio generador."""
    from apps.users.tokens import email_verification_token

    return token_body(user, generator=email_verification_token, **extra)


RESET_EXTRA = {"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}
RESET_ERROR = {"token": ["Invalid or expired reset token."]}
VERIFY_ERROR = {"token": ["Invalid or expired verification token."]}


def client_on(host):
    from rest_framework.test import APIClient

    return APIClient(HTTP_HOST=host)


@pytest.fixture
def victim(public_schema):
    tenant = make_tenant("acme", f"acmefin.{BASE}")
    make_tenant("evil", f"acme.{BASE}")
    return UserFactory(email="duena@acme.test", tenant=tenant, email_verified=False)


def test_verify_confirm_on_the_wrong_host_gives_the_generic_error(victim):
    response = client_on(f"acme.{BASE}").post(VERIFY_CONFIRM, verify_body(victim), format="json")

    victim.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == VERIFY_ERROR
    assert victim.email_verified is False


def test_both_confirms_work_on_the_users_tenant_host(victim):
    on_acme = client_on(f"acmefin.{BASE}")

    verify = on_acme.post(VERIFY_CONFIRM, verify_body(victim), format="json")
    reset = on_acme.post(RESET_CONFIRM, token_body(victim, **RESET_EXTRA), format="json")

    victim.refresh_from_db()
    assert verify.status_code == 200, verify.content
    assert reset.status_code == 200, reset.content
    assert victim.email_verified is True
    assert victim.check_password(NEW_PASSWORD)


def test_user_without_tenant_redeems_only_on_the_public_host(public_client, tenant):
    user = UserFactory(email="sin-tenant@crediflux.test", tenant=None, email_verified=False)

    on_tenant = client_on("tenant.test.localhost")
    assert on_tenant.post(RESET_CONFIRM, token_body(user, **RESET_EXTRA), format="json").json() == RESET_ERROR
    assert on_tenant.post(VERIFY_CONFIRM, verify_body(user), format="json").json() == VERIFY_ERROR
    user.refresh_from_db()
    assert not user.check_password(NEW_PASSWORD) and user.email_verified is False

    # Verificación antes que reset: el token de Django cambia con la contraseña.
    assert public_client.post(VERIFY_CONFIRM, verify_body(user), format="json").status_code == 200
    assert public_client.post(RESET_CONFIRM, token_body(user, **RESET_EXTRA), format="json").status_code == 200


def test_platform_superuser_redeems_only_on_the_public_host(public_client, tenant):
    from apps.users.models import User

    admin = User.objects.create_user(
        username="plataforma-r291", email="plataforma-r291@crediflux.test", password="x",
        is_superuser=True, is_staff=True, email_verified=False,
    )
    on_tenant = client_on("tenant.test.localhost")
    bad_token = on_tenant.post(RESET_CONFIRM, {**token_body(admin, **RESET_EXTRA), "token": "abc-123"}, format="json")

    reset = on_tenant.post(RESET_CONFIRM, token_body(admin, **RESET_EXTRA), format="json")
    verify = on_tenant.post(VERIFY_CONFIRM, verify_body(admin), format="json")

    admin.refresh_from_db()
    assert reset.status_code == verify.status_code == 400
    assert reset.content == bad_token.content and reset.json() == RESET_ERROR
    assert verify.json() == VERIFY_ERROR
    assert not admin.check_password(NEW_PASSWORD) and admin.email_verified is False

    assert public_client.post(VERIFY_CONFIRM, verify_body(admin), format="json").status_code == 200
    assert public_client.post(RESET_CONFIRM, token_body(admin, **RESET_EXTRA), format="json").status_code == 200
    admin.refresh_from_db()
    assert admin.email_verified is True and admin.check_password(NEW_PASSWORD)


def test_inactive_user_gets_the_generic_error_on_its_own_host(victim):
    victim.is_active = False
    victim.save(update_fields=["is_active"])

    response = client_on(f"acmefin.{BASE}").post(RESET_CONFIRM, token_body(victim, **RESET_EXTRA), format="json")

    assert response.status_code == 400
    assert response.json() == RESET_ERROR


@pytest.mark.parametrize("path, body, extra, error", [
    (RESET_CONFIRM, token_body, RESET_EXTRA, RESET_ERROR),
    (VERIFY_CONFIRM, verify_body, {}, VERIFY_ERROR),
])
def test_wrong_host_bad_token_and_bad_uid_are_indistinguishable(victim, path, body, extra, error):
    good = body(victim, **extra)
    wrong_host = client_on(f"acme.{BASE}").post(path, good, format="json")
    on_acme = client_on(f"acmefin.{BASE}")
    bad_token = on_acme.post(path, {**good, "token": "abc-123"}, format="json")
    bad_uid = on_acme.post(path, {**good, "uid": "MTIzNDU2Nzg5"}, format="json")  # pk inexistente
    garbage_uid = on_acme.post(path, {**good, "uid": "%%%"}, format="json")

    for response in (wrong_host, bad_token, bad_uid, garbage_uid):
        assert response.status_code == 400
        assert response.content == wrong_host.content
    assert wrong_host.json() == error
