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


# --- client_network_key: identidad para presupuestos por cliente --------------------------

from apps.core.net import client_network_key  # noqa: E402


@pytest.mark.parametrize("remote, expected", [
    ("198.51.100.7", "198.51.100.7"),
    ("2001:db8:7:7::1", "2001:db8:7::/56"),
    ("2001:db8:7:7:abcd:ef01:2345:6789", "2001:db8:7::/56"),
    ("2001:db8:7:ff::1", "2001:db8:7::/56"),  # otra /64 de la misma /56: mismo cliente
    ("2001:db8:7:100::1", "2001:db8:7:100::/56"),  # otra /56: otro cliente
    ("::ffff:198.51.100.7", "198.51.100.7"),  # IPv4 mapeada: la IPv4, no una /56 compartida
    ("no-es-una-ip", "no-es-una-ip"),
    ("", ""),
])
def test_client_network_key(remote, expected):
    with _proxies(0):
        assert client_network_key(_request(remote=remote)) == expected


def test_client_network_key_respects_num_proxies():
    with _proxies(1):
        assert client_network_key(_request("2001:db8:1:2::99")) == "2001:db8:1::/56"


def test_client_network_key_groups_ipv6_by_56():
    with _proxies(0):
        same = {client_network_key(_request(remote=ip)) for ip in ("2001:db8:5:0::1", "2001:db8:5:3f::9", "2001:db8:5:ff:ffff::1")}
        assert len(same) == 1
        assert client_network_key(_request(remote="2001:db8:5:100::1")) not in same
        assert client_network_key(_request(remote="2001:db8:6::1")) not in same
        # IPv4 sin cambios: cada dirección es su propio cliente.
        assert client_network_key(_request(remote="198.51.100.7")) != client_network_key(_request(remote="198.51.100.8"))


def test_client_network_key_none_request():
    assert client_network_key(None) == ""


# --- client_registration_key: presupuestos de registro (IPv6 por /48, run-5) -------------

from apps.core.net import client_registration_key  # noqa: E402


@pytest.mark.parametrize("remote, expected", [
    ("198.51.100.7", "198.51.100.7"),
    ("2001:db8:abcd:7::1", "2001:db8:abcd::/48"),
    ("2001:db8:abcd:ff00::1", "2001:db8:abcd::/48"),  # otra /56 de la misma /48: mismo registrante
    ("2001:db8:abce::1", "2001:db8:abce::/48"),  # otra /48: otro registrante
    ("::ffff:198.51.100.7", "198.51.100.7"),
    ("", ""),
])
def test_client_registration_key(remote, expected):
    with _proxies(0):
        assert client_registration_key(_request(remote=remote)) == expected


def test_client_registration_key_respects_num_proxies():
    with _proxies(1):
        assert client_registration_key(_request("2001:db8:1:2::99")) == "2001:db8:1::/48"


@pytest.mark.parametrize("raw", ["no-es-una-ip", "x" * 300, "1.2.3.4.5, basura"])
def test_client_registration_key_hashes_non_ip_values(raw):
    # Ronda 26.1: un valor que no es IP se guarda en Tenant.registration_network (64 caracteres).
    with _proxies(0):
        key = client_registration_key(_request(remote=raw))
        assert key.startswith("raw:") and len(key) <= 64
        assert key == client_registration_key(_request(remote=raw))  # misma identidad
        assert key != client_registration_key(_request(remote=raw + "y"))


def test_client_registration_key_none_request():
    assert client_registration_key(None) == ""
