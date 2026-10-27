"""Confirmación de correo de allauth atada al host del tenant del usuario (ronda 30).

`CustomConfirmEmailView` (`api/auth/registration/account-confirm-email/<key>/`, montada en las dos URL
confs) confirma una `EmailConfirmation` / `EmailConfirmationHMAC` en GET. Desde la ronda 30 aplica la
misma regla de host que los confirm de reset y verificación (ronda 29.1):

* un usuario de tenant sólo confirma en el host de su tenant;
* un usuario sin tenant (también el de plataforma) sólo en el host público, y sólo si está activo;
* en cualquier otro caso, la misma redirección `verified=invalid` que una clave inválida.

La redirección de éxito va al frontend del tenant del usuario, y el enlace del correo (adapter) se
construye con el dominio del tenant del usuario, no con el host del admin que lo envía.
"""
import re
from urllib.parse import urlparse

import pytest
from allauth.account.models import EmailAddress, EmailConfirmation, EmailConfirmationHMAC
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone

from apps.tenants.models import Domain, Tenant
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

BASE = "crediflux.test"
HOST_A = f"acme.{BASE}"
HOST_B = f"beta.{BASE}"
PUBLIC_HOST = "localhost"  # dominio del tenant público en conftest
CONFIRM = "/api/auth/registration/account-confirm-email/{key}/"

ANON_URL = f"https://{BASE}/login?verified=true"
AUTH_URL = f"https://{BASE}/dashboard?verified=true"
INVALID_URL = f"{ANON_URL}&verified=invalid"

urls = override_settings(
    FRONTEND_URL=f"https://{BASE}",
    BACKEND_URL=f"https://api.{BASE}",
    TENANT_BASE_DOMAIN=BASE,
    ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL=ANON_URL,
    ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL=AUTH_URL,
)


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


def client_on(host):
    from rest_framework.test import APIClient

    return APIClient(HTTP_HOST=host)


def email_address(user):
    return EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=False)


def make_key(address, kind):
    """Clave de confirmación de allauth: firmada (HMAC) o guardada en BD."""
    if kind == "hmac":
        return EmailConfirmationHMAC(address).key
    confirmation = EmailConfirmation.create(address)
    confirmation.sent = timezone.now()  # lo pone `send()`; sin él la clave cuenta como vencida
    confirmation.save(update_fields=["sent"])
    return confirmation.key


def confirm(host, key):
    return client_on(host).get(CONFIRM.format(key=key))


def verified(address):
    address.refresh_from_db()
    return address.verified


KINDS = pytest.mark.parametrize("kind", ["hmac", "db"])


# ---------------------------------------------------------------------------
# Usuario de tenant
# ---------------------------------------------------------------------------


@urls
@KINDS
def test_tenant_user_confirms_on_its_own_host_and_lands_on_its_frontend(tenants, kind):
    acme, _ = tenants
    address = email_address(UserFactory(email="cajero@acme.test", tenant=acme))

    response = confirm(HOST_A, make_key(address, kind))

    assert response.status_code == 302
    assert response["Location"] == f"https://{HOST_A}/login?verified=true"
    assert verified(address)


@urls
@KINDS
def test_tenant_user_key_on_another_tenants_host_is_invalid(tenants, kind):
    acme, _ = tenants
    address = email_address(UserFactory(email="cajero@acme.test", tenant=acme))

    response = confirm(HOST_B, make_key(address, kind))

    assert response.status_code == 302
    assert response["Location"] == INVALID_URL
    assert not verified(address)


@urls
@KINDS
def test_tenant_user_key_on_the_public_host_is_invalid(tenants, kind):
    acme, _ = tenants
    address = email_address(UserFactory(email="cajero@acme.test", tenant=acme))

    response = confirm(PUBLIC_HOST, make_key(address, kind))

    assert response["Location"] == INVALID_URL
    assert not verified(address)


@urls
@KINDS
def test_inactive_tenant_user_does_not_confirm_on_its_own_host(tenants, kind):
    acme, _ = tenants
    address = email_address(UserFactory(email="baja@acme.test", tenant=acme, is_active=False))

    response = confirm(HOST_A, make_key(address, kind))

    assert response["Location"] == INVALID_URL
    assert not verified(address)


@urls
@KINDS
def test_wrong_host_and_invalid_key_give_the_exact_same_redirect(tenants, kind):
    acme, _ = tenants
    address = email_address(UserFactory(email="cajero@acme.test", tenant=acme))

    wrong_host = confirm(HOST_B, make_key(address, kind))
    bad_key_hmac = confirm(HOST_B, "MQ:1tY4Ab:no-es-una-firma")
    bad_key_db = confirm(HOST_B, "no-existe-esta-clave")
    bad_key_own_host = confirm(HOST_A, "no-existe-esta-clave")

    locations = {r["Location"] for r in (wrong_host, bad_key_hmac, bad_key_db, bad_key_own_host)}
    assert locations == {INVALID_URL}
    assert {r.status_code for r in (wrong_host, bad_key_hmac, bad_key_db, bad_key_own_host)} == {302}


@urls
def test_authenticated_tenant_user_lands_on_its_tenant_dashboard(tenants):
    acme, _ = tenants
    user = UserFactory(email="cajero@acme.test", tenant=acme)
    address = email_address(user)
    client = client_on(HOST_A)
    client.force_login(user)

    response = client.get(CONFIRM.format(key=make_key(address, "hmac")))

    assert response["Location"] == f"https://{HOST_A}/dashboard?verified=true"
    assert verified(address)


# ---------------------------------------------------------------------------
# Usuario sin tenant (también el de plataforma)
# ---------------------------------------------------------------------------


@urls
@KINDS
def test_user_without_tenant_confirms_only_on_the_public_host(tenants, kind):
    address = email_address(UserFactory(email="sin-tenant@crediflux.test", tenant=None))
    key = make_key(address, kind)

    on_tenant = confirm(HOST_A, key)
    assert on_tenant["Location"] == INVALID_URL
    assert not verified(address)

    on_public = confirm(PUBLIC_HOST, key)
    assert on_public["Location"] == ANON_URL
    assert verified(address)


@urls
@KINDS
def test_platform_superuser_confirms_only_on_the_public_host(tenants, kind):
    address = email_address(UserFactory(
        email="plataforma@crediflux.test", tenant=None, is_superuser=True, is_staff=True,
    ))
    key = make_key(address, kind)

    assert confirm(HOST_A, key)["Location"] == INVALID_URL
    assert not verified(address)
    assert confirm(PUBLIC_HOST, key)["Location"] == ANON_URL
    assert verified(address)


@urls
@KINDS
def test_inactive_user_without_tenant_does_not_confirm_on_the_public_host(tenants, kind):
    address = email_address(UserFactory(email="baja@crediflux.test", tenant=None, is_active=False))

    response = confirm(PUBLIC_HOST, make_key(address, kind))

    assert response["Location"] == INVALID_URL
    assert not verified(address)


# ---------------------------------------------------------------------------
# Adapter: el enlace del correo va al dominio del tenant del usuario
# ---------------------------------------------------------------------------


def sent_confirm_link():
    assert mail.outbox, "no se envió ningún correo"
    match = re.search(r"(https?://\S+/account-confirm-email/\S+/)", mail.outbox[-1].body)
    assert match, mail.outbox[-1].body
    return urlparse(match.group(1))


@urls
@KINDS
def test_link_sent_from_the_public_host_uses_the_users_tenant_domain(tenants, kind):
    """El admin de plataforma reenvía la verificación desde el host público: el enlace va al de A."""
    acme, _ = tenants
    address = email_address(UserFactory(email="cajero@acme.test", tenant=acme))
    request = RequestFactory(HTTP_HOST=PUBLIC_HOST).get("/admin/")
    confirmation = EmailConfirmationHMAC(address) if kind == "hmac" else EmailConfirmation.create(address)

    confirmation.send(request)

    link = sent_confirm_link()
    assert link.scheme == "https"  # el de BACKEND_URL
    assert link.netloc == HOST_A
    assert link.path == CONFIRM.format(key=confirmation.key)

    # Y ese enlace confirma en su host.
    assert confirm(HOST_A, confirmation.key)["Location"] == f"https://{HOST_A}/login?verified=true"
    assert verified(address)


@override_settings(BACKEND_URL="http://localhost:8100", FRONTEND_URL="http://localhost:3100")
def test_link_keeps_scheme_and_port_of_backend_url(public_schema):
    tenant = make_tenant("puerto", "puerto.localhost")
    address = email_address(UserFactory(email="cajero@puerto.test", tenant=tenant))
    request = RequestFactory(HTTP_HOST=PUBLIC_HOST).get("/admin/")

    EmailConfirmationHMAC(address).send(request)

    link = sent_confirm_link()
    assert link.scheme == "http"
    assert link.netloc == "puerto.localhost:8100"


@urls
def test_link_of_user_without_tenant_keeps_the_request_host(tenants):
    """Sin tenant, el enlace sigue en el host de la petición (el público, desde el admin de plataforma)."""
    address = email_address(UserFactory(email="sin-tenant@crediflux.test", tenant=None))
    request = RequestFactory(HTTP_HOST=PUBLIC_HOST).get("/admin/")

    EmailConfirmationHMAC(address).send(request)

    assert sent_confirm_link().netloc == PUBLIC_HOST
