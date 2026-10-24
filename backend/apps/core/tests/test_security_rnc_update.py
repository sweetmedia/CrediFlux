"""Actualización del RNC: URL fija en hosts de la DGII y disparo sólo para superusuarios."""
from io import StringIO
from unittest import mock

import pytest
from constance.test import override_config
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.core.management.commands import update_rnc_database as cmd

pytestmark = pytest.mark.django_db

REQUESTS_GET = "apps.core.management.commands.update_rnc_database.requests.get"
DELAY = "apps.core.tasks.update_rnc_database.delay"


# --- Descarga: sólo https en hosts de la DGII --------------------------------

@override_config(DGII_RNC_ENABLED=True, DGII_RNC_DATABASE_URL="http://127.0.0.1:1/x.zip")
def test_command_rejects_internal_url_before_network():
    with mock.patch(REQUESTS_GET) as get:
        with pytest.raises(ValueError, match="no permitida"):
            call_command("update_rnc_database", force=True, stdout=StringIO())
    get.assert_not_called()


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:1/x.zip",
    "http://www.dgii.gov.do/x.zip",
    "https://evil.example/x.zip",
    "https://dgii.gov.do@evil.example/x.zip",
    "https://user@dgii.gov.do/x.zip",
    "https://dgii.gov.do.evil.example/x.zip",
    "https://www.dgii.gov.do:8443/x.zip",
    "https:///x.zip",
    "",
])
def test_download_rejects_disallowed_urls(url):
    with mock.patch(REQUESTS_GET) as get:
        with pytest.raises(ValueError, match="no permitida"):
            cmd._download_rnc_file(url)
    get.assert_not_called()


def _response(status=200, content=b"zip"):
    return mock.MagicMock(status_code=status, content=content)


@pytest.mark.parametrize("url", [
    "https://www.dgii.gov.do/app/WebApps/Consultas/RNC/RNC_CONTRIBUYENTES.zip",
    "https://dgii.gov.do:443/app/WebApps/Consultas/RNC/RNC_CONTRIBUYENTES.zip",
    "https://WWW.DGII.GOV.DO/x.zip",
])
def test_download_allowed_url_does_not_follow_redirects(url):
    with mock.patch(REQUESTS_GET, return_value=_response()) as get:
        assert cmd._download_rnc_file(url) == b"zip"
    get.assert_called_once()
    assert get.call_args.args[0] == url
    assert get.call_args.kwargs["allow_redirects"] is False
    assert get.call_args.kwargs["timeout"]


def test_download_treats_redirect_as_error():
    with mock.patch(REQUESTS_GET, return_value=_response(status=302)):
        with pytest.raises(ValueError):
            cmd._download_rnc_file("https://www.dgii.gov.do/x.zip")


def test_celery_task_uses_the_same_download():
    from apps.core import tasks

    with mock.patch(
        "apps.core.tasks._download_rnc_file",
        side_effect=ValueError("URL de descarga del RNC no permitida"),
    ) as dl:
        result = tasks.update_rnc_database.apply().get()
    dl.assert_called_once()
    assert result["status"] == "error"


# --- Vista del admin: sólo superusuario de plataforma, asíncrona --------------

def _admin_client(user, host="localhost"):
    client = Client(HTTP_HOST=host)
    client.force_login(user)
    return client


def _platform_superuser():
    from tests.factories import UserFactory

    return UserFactory(tenant=None, is_superuser=True, is_staff=True)


@pytest.fixture
def url(public_schema):
    return reverse("admin:constance_update_rnc_database")


def test_tenant_admin_gets_403(url, user_factory):
    user = user_factory(role="admin", is_staff=True)
    with mock.patch(DELAY) as delay:
        resp = _admin_client(user).post(url, {"force": "true"})
    assert resp.status_code == 403
    delay.assert_not_called()


@pytest.mark.parametrize("extra", [{}, {"is_superuser": True}])
def test_tenant_staff_on_own_host_gets_403(url, user_factory, extra):
    # En su propio host el middleware de tenant lo deja pasar; la vista debe negar.
    user = user_factory(role="admin", is_staff=True, **extra)
    with mock.patch(DELAY) as delay, mock.patch(REQUESTS_GET) as get:
        resp = _admin_client(user, host="tenant.test.localhost").post(url, {"force": "true"})
    assert resp.status_code == 403
    delay.assert_not_called()
    get.assert_not_called()


@override_config(DGII_RNC_ENABLED=True)
def test_platform_superuser_enqueues_task(url):
    client = _admin_client(_platform_superuser())
    with mock.patch(DELAY) as delay:
        resp = client.post(url, {"force": "true"})
    assert resp.status_code == 302
    delay.assert_called_once_with()
    assert client.get(url).status_code == 200


@override_config(DGII_RNC_ENABLED=True)
def test_enqueue_error_is_not_leaked(url):
    client = _admin_client(_platform_superuser())
    with mock.patch(DELAY, side_effect=RuntimeError("redis://secret@host")):
        resp = client.post(url)
    assert resp.status_code == 302
    texts = [str(m) for m in get_messages(resp.wsgi_request)]
    assert texts and not any("secret" in t for t in texts)
