"""El login del admin gasta un único presupuesto por cuenta, escriba como escriba el correo (run-3).

Django normaliza el usuario con NFKC antes de autenticar: un correo con letras de ancho
completo (U+FF21-U+FF5A) abre la misma cuenta que el ASCII. El rate limit por usuario y el
contador compartido `login_fail:<email>` deben tratarlas como una sola cuenta.
"""
import pytest
from django.core.cache import cache
from django.test import Client

from apps.users import lockout

pytestmark = pytest.mark.django_db
PASSWORD = "clave-de-prueba-123"
HOST = "tenant.test.localhost"
LOGIN_URL = "/admin/login/"
EMAIL = "staffer@crediflux.test"


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staffer(user_factory):
    return user_factory(email=EMAIL, role="manager", is_staff=True)


def _fullwidth(text, every=1):
    """Pasa a ancho completo una de cada `every` letras ASCII (NFKC la devuelve a ASCII)."""
    out = []
    letters = 0
    for ch in text:
        if ch.isascii() and ch.isalpha():
            if letters % every == 0:
                ch = chr(ord(ch) + 0xFEE0)
            letters += 1
        out.append(ch)
    return "".join(out)


def _post(client, username, password, ip="10.9.0.1"):
    return client.post(
        LOGIN_URL, {"username": username, "password": password, "next": "/admin/"}, REMOTE_ADDR=ip
    )


def _is_logged_in(client):
    return "_auth_user_id" in client.session


def test_fullwidth_spelling_normalizes_to_the_same_email():
    assert _fullwidth(EMAIL) != EMAIL
    import unicodedata

    assert unicodedata.normalize("NFKC", _fullwidth(EMAIL)) == EMAIL
    assert unicodedata.normalize("NFKC", _fullwidth(EMAIL, every=2)) == EMAIL


@pytest.mark.parametrize("every", [1, 2, 3])
def test_compatible_spelling_does_not_get_a_fresh_budget(staffer, every):
    client = Client(HTTP_HOST=HOST)
    for i in range(lockout.LOGIN_FAIL_LIMIT):
        assert _post(client, EMAIL, f"incorrecta-{i}").status_code == 200
    assert not _is_logged_in(client)

    response = _post(client, _fullwidth(EMAIL, every=every), PASSWORD)
    assert response.status_code in (200, 403)
    assert not _is_logged_in(client)
    assert Client(HTTP_HOST=HOST).get("/admin/").status_code == 302


def test_wrong_admin_logins_spend_the_shared_account_counter(staffer):
    client = Client(HTTP_HOST=HOST)
    _post(client, EMAIL, "incorrecta-1")
    _post(client, _fullwidth(EMAIL), "incorrecta-2", ip="10.9.0.2")
    assert cache.get(f"login_fail:{EMAIL}") == 2


def test_admin_door_honours_failures_from_the_jwt_door(staffer, rf):
    # Fallos previos en la puerta JWT (u otra) bloquean también el admin, aunque la
    # clave del rate limit de django-ratelimit siga vacía (otra IP, otro ancho).
    request = rf.post("/api/tenants/login/", REMOTE_ADDR="10.9.9.9")
    for _ in range(lockout.LOGIN_FAIL_LIMIT):
        lockout.check_and_count(EMAIL, request)
    client = Client(HTTP_HOST=HOST)
    response = _post(client, EMAIL, PASSWORD, ip="10.9.0.3")
    assert response.status_code == 200
    assert lockout.LOCKOUT_MESSAGE in response.content.decode()
    assert not _is_logged_in(client)


def test_successful_admin_login_resets_the_account_counter(staffer):
    client = Client(HTTP_HOST=HOST)
    _post(client, EMAIL, "incorrecta-1")
    _post(client, EMAIL, "incorrecta-2")
    assert cache.get(f"login_fail:{EMAIL}") == 2
    response = _post(client, EMAIL, PASSWORD)
    assert response.status_code == 302
    assert _is_logged_in(client)
    assert cache.get(f"login_fail:{EMAIL}") is None
