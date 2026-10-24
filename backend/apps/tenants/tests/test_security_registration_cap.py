"""Registro de tenants: el tope diario se cobra por intento de aprovisionamiento (run-2).

Cubre: un correo cuyo prefijo ya es el username de otro usuario registra igual (username
único) en vez de aprovisionar y revertir; un intento que falla tras aprovisionar gasta
el tope aunque la transacción se revierta.
"""
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.tenants.models import Domain, Tenant
from apps.users.models import User

from .test_security_registration import GENERIC, URL, payload

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def no_schema(monkeypatch):
    # Sin CREATE SCHEMA + migraciones: lo que se prueba es el tope, no el aprovisionamiento.
    monkeypatch.setattr(Tenant, "auto_create_schema", False)


@pytest.fixture
def no_recent_tenants(public_schema):
    """Los tenants de la sesión de pruebas no cuentan en la ventana de 24 h (se revierte)."""
    Tenant.objects.update(created_on=timezone.now() - timedelta(days=2))


def test_username_collision_does_not_abort_after_provisioning(public_client, no_schema, user_factory):
    user_factory(username="ana", email="ana@otra-empresa.test")
    response = public_client.post(URL, payload(), format="json")
    assert response.status_code == 201, response.content
    owner = User.objects.get(email="ana@nueva.test")
    assert owner.username != "ana"
    assert owner.username.startswith("ana")


@override_settings(MAX_TENANTS_PER_DAY=1)
def test_failed_provisioning_attempt_spends_the_daily_cap(public_client, no_schema, no_recent_tenants, monkeypatch):
    real_create = Domain.objects.create

    def boom(*args, **kwargs):
        raise RuntimeError("fallo tras aprovisionar")

    monkeypatch.setattr(Domain.objects, "create", boom)
    assert public_client.post(URL, payload(), format="json").status_code == 400
    assert not Tenant.objects.filter(name="financiera-nueva").exists()  # revertido

    monkeypatch.setattr(Domain.objects, "create", real_create)
    calls = []
    real_tenant_create = Tenant.objects.create
    monkeypatch.setattr(Tenant.objects, "create", lambda **kw: calls.append(kw) or real_tenant_create(**kw))
    response = public_client.post(
        URL, payload(tenant_name="otra-financiera", subdomain="otra-financiera", owner_email="luis@otra.test"),
        format="json",
    )
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert calls == []  # rechazado antes de aprovisionar


def _register(client, n, ip):
    data = payload(tenant_name=f"financiera-{n}", subdomain=f"financiera-{n}", owner_email=f"dueno{n}@nueva.test")
    return client.post(URL, data, format="json", REMOTE_ADDR=ip)


@override_settings(MAX_TENANTS_PER_DAY=100, MAX_TENANTS_PER_IP_PER_DAY=2)
def test_one_client_cannot_spend_the_whole_daily_cap(public_client, no_schema):
    attacker, legit = "198.51.100.20", "203.0.113.50"
    assert _register(public_client, 1, attacker).status_code == 201
    assert _register(public_client, 2, attacker).status_code == 201
    response = _register(public_client, 3, attacker)
    assert response.status_code == 400
    assert GENERIC in str(response.json())
    assert _register(public_client, 4, legit).status_code == 201


@override_settings(MAX_TENANTS_PER_DAY=2, MAX_TENANTS_PER_IP_PER_DAY=1)
def test_client_over_its_budget_does_not_spend_the_global_cap(public_client, no_schema, no_recent_tenants):
    attacker = "198.51.100.20"
    assert _register(public_client, 1, attacker).status_code == 201
    for n in (2, 3):  # el throttle de 3/hora por IP corta antes de un 4.º intento
        assert _register(public_client, n, attacker).status_code == 400
    assert _register(public_client, 9, "203.0.113.50").status_code == 201
