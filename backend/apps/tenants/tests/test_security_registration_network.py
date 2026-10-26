"""Registro de tenants: un solo solicitante no deja sin registro a los demás (run-5).

Con el tope global de pendientes como rechazo para todos, ~110 identidades baratas (110 IPv4
o 110 /56 de una sola /48) llenaban los 20 aprovisionados y los 200 pendientes del día y
cualquier otro registrante recibía el 400 genérico. Ahora los pendientes se presupuestan por
red de registro (IPv4 o IPv6 /48) guardada en la fila y contada en la base; el tope global de
pendientes sólo dispara una alarma y lo que rechaza es un techo de cordura mucho mayor.
El subdominio ya no choca con cualquier dominio que lo contenga: se compara el dominio exacto.
"""
import logging
from collections import Counter
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.tenants.models import Domain, Tenant
from apps.users.models import User

from .test_security_registration import GENERIC, URL, payload

pytestmark = pytest.mark.django_db

ALARM_LOGGER = "apps.tenants.serializers"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def no_schema(monkeypatch):
    # Sin CREATE SCHEMA + migraciones: lo que se prueba son los topes, no el aprovisionamiento.
    monkeypatch.setattr(Tenant, "auto_create_schema", False)


@pytest.fixture
def no_recent_tenants(public_schema):
    Tenant.objects.update(created_on=timezone.now() - timedelta(days=2))


def _register(client, name, ip, subdomain=None):
    data = payload(tenant_name=name, subdomain=subdomain or name, owner_email=f"{name}@nueva.test")
    return client.post(URL, data, format="json", REMOTE_ADDR=ip)


def _counts():
    return Tenant.objects.count(), User.objects.count(), Domain.objects.count()


def _fill_provisioning_cap(client):
    """Los 20 aprovisionamientos del día, desde 10 IPv4 ajenas (2 cada una)."""
    for n in range(20):
        assert _register(client, f"previa-{n}", f"192.0.2.{n // 2}").status_code == 201


# --- (1) una /48 no deja fuera a nadie ----------------------------------------------------

def test_one_ipv6_48_cannot_lock_out_other_registrants(public_client, no_schema, no_recent_tenants, settings):
    assert (settings.MAX_TENANTS_PER_DAY, settings.MAX_TENANTS_PER_IP_PER_DAY) == (20, 2)
    _fill_provisioning_cap(public_client)

    # 220 registros desde 110 redes /56 distintas de una misma /48 (2 por /56).
    statuses = [
        _register(public_client, f"atacante-{n}", f"2001:db8:abcd:{n // 2:02x}00::1").status_code
        for n in range(220)
    ]

    assert statuses[:2] == [202, 202]
    assert Counter(statuses[2:]) == {400: 218}
    assert Tenant.objects.filter(registration_network="2001:db8:abcd::/48").count() == 2
    response = _register(public_client, "victima", "203.0.113.77")
    assert response.status_code == 202, response.content


# --- (2) 110 IPv4: el tope global de pendientes es una alarma, no un rechazo --------------

def test_110_ipv4_cannot_lock_out_other_registrants(public_client, no_schema, no_recent_tenants, settings, caplog):
    assert settings.MAX_PENDING_REGISTRATIONS_PER_DAY == 200
    ips = [f"198.51.100.{i}" for i in range(100)] + [f"203.0.113.{i}" for i in range(10)]
    statuses = Counter(
        _register(public_client, f"atacante-{n}", ips[n // 2]).status_code for n in range(220)
    )
    assert statuses == {201: 20, 202: 200}
    assert Tenant.objects.filter(provisioning_pending=True).count() == 200

    with caplog.at_level(logging.ERROR, logger=ALARM_LOGGER):
        response = _register(public_client, "victima", "192.0.2.77")

    assert response.status_code == 202, response.content
    assert Tenant.objects.get(name="victima").provisioning_pending is True
    assert any(
        r.levelno == logging.ERROR and "MAX_PENDING_REGISTRATIONS_PER_DAY" in r.getMessage()
        for r in caplog.records
    )


# --- (3) el techo duro sí rechaza ---------------------------------------------------------

@override_settings(MAX_TENANTS_PER_DAY=0, MAX_PENDING_REGISTRATIONS_PER_DAY=1,
                   MAX_PENDING_REGISTRATIONS_HARD_CEILING=2)
def test_hard_ceiling_rejects_above_it(public_client, no_schema, no_recent_tenants):
    assert _register(public_client, "uno", "198.51.100.1").status_code == 202
    assert _register(public_client, "dos", "198.51.100.2").status_code == 202  # sobre el tope: alarma
    before = _counts()
    response = _register(public_client, "tres", "198.51.100.3")
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert _counts() == before


# --- (4) presupuesto de pendientes por red ------------------------------------------------

@override_settings(MAX_TENANTS_PER_DAY=0, MAX_TENANTS_PER_IP_PER_DAY=100)
def test_pending_budget_is_per_registration_network(public_client, no_schema, no_recent_tenants, settings):
    assert settings.MAX_PENDING_PER_NETWORK_PER_DAY == 2
    assert _register(public_client, "uno", "198.51.100.5").status_code == 202
    assert _register(public_client, "dos", "198.51.100.5").status_code == 202
    before = _counts()
    response = _register(public_client, "tres", "198.51.100.5")
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert _counts() == before
    # Sólo esa red: otra sigue registrando.
    assert _register(public_client, "cuatro", "198.51.100.6").status_code == 202


# --- (5) la red se guarda en la fila y la cuenta sobrevive a un flush de la caché ---------

@override_settings(MAX_TENANTS_PER_DAY=0, MAX_TENANTS_PER_IP_PER_DAY=100)
def test_pending_network_is_persisted_and_counted_in_the_database(public_client, no_schema, no_recent_tenants):
    assert _register(public_client, "uno", "2001:db8:abcd:1::5").status_code == 202
    assert _register(public_client, "dos", "2001:db8:abcd:1::6").status_code == 202
    assert set(Tenant.objects.filter(name__in=["uno", "dos"]).values_list("registration_network", flat=True)) == {
        "2001:db8:abcd::/48"
    }
    cache.clear()
    response = _register(public_client, "tres", "2001:db8:abcd:200::5")  # otra /56, misma /48
    assert response.status_code == 400
    assert GENERIC in str(response.json())


@override_settings(MAX_TENANTS_PER_DAY=100, MAX_TENANTS_PER_IP_PER_DAY=2)
def test_client_budget_is_counted_in_the_database(public_client, no_schema, no_recent_tenants):
    assert _register(public_client, "uno", "198.51.100.9").status_code == 201
    assert _register(public_client, "dos", "198.51.100.9").status_code == 201
    assert Tenant.objects.get(name="uno").registration_network == "198.51.100.9"
    cache.clear()  # un flush de Redis no regala otro presupuesto
    response = _register(public_client, "tres", "198.51.100.9")
    assert response.status_code == 400
    assert GENERIC in str(response.json())


# --- (6) subdominio: comparación exacta ---------------------------------------------------

def test_subdomain_is_compared_exactly(public_client, no_schema):
    assert _register(public_client, "acme-financiera", "198.51.100.30").status_code == 201
    # Antes: rechazado porque "acme" está contenido en "acme-financiera".
    response = _register(public_client, "acme", "198.51.100.31")
    assert response.status_code == 201, response.content
    response = _register(public_client, "otra-acme", "198.51.100.32", subdomain="acme-financiera")
    assert response.status_code == 400
    assert GENERIC in str(response.json())


@override_settings(TENANT_BASE_DOMAIN="crediflux.test")
def test_subdomain_is_compared_exactly_with_a_base_domain(public_client, no_schema):
    assert _register(public_client, "acme-financiera", "198.51.100.30").status_code == 201
    assert Domain.objects.filter(domain="acme-financiera.crediflux.test").exists()
    assert _register(public_client, "acme", "198.51.100.31").status_code == 201
    response = _register(public_client, "otra-acme", "198.51.100.32", subdomain="acme-financiera")
    assert response.status_code == 400
    assert GENERIC in str(response.json())
