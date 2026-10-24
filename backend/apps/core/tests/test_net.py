"""client_ip: IP del cliente con la semántica de NUM_PROXIES de DRF."""

import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings

from apps.core.net import client_ip


def _proxies(num_proxies):
    return override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, "NUM_PROXIES": num_proxies})


def _request(xff=None, remote="192.168.1.10"):
    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return RequestFactory().get("/", **extra)


def test_one_proxy_uses_the_entry_the_proxy_wrote():
    with _proxies(1):
        assert client_ip(_request("1.1.1.1")) == "1.1.1.1"


def test_one_proxy_ignores_spoofed_leftmost_entries():
    # El proxy de borde añade la IP real al final; lo que el cliente inventó queda a la izquierda.
    with _proxies(1):
        assert client_ip(_request("9.9.9.9, 1.1.1.1")) == "1.1.1.1"


def test_two_proxies_take_the_second_from_the_right():
    with _proxies(2):
        assert client_ip(_request("1.1.1.1, 10.0.0.1")) == "1.1.1.1"


def test_more_proxies_than_entries_uses_the_leftmost():
    with _proxies(3):
        assert client_ip(_request("1.1.1.1, 10.0.0.1")) == "1.1.1.1"


@pytest.mark.parametrize("num_proxies", [0, None])
def test_no_proxies_ignores_xff(num_proxies):
    with _proxies(num_proxies):
        assert client_ip(_request("1.1.1.1, 10.0.0.1")) == "192.168.1.10"


def test_missing_xff_falls_back_to_remote_addr():
    with _proxies(1):
        assert client_ip(_request()) == "192.168.1.10"


def test_blank_entry_falls_back_to_remote_addr():
    with _proxies(1):
        assert client_ip(_request("1.1.1.1, ")) == "192.168.1.10"


def test_none_request_returns_empty_string():
    assert client_ip(None) == ""
