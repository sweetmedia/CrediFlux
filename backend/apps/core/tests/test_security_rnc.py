"""Consulta de RNC: O(1) por clave, sin scraping anónimo, throttle propio y cédula por rol."""
from unittest import mock

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle

from apps.core import views
from apps.core.services.rnc_lookup import (
    LEGACY_CACHE_KEY,
    RNCLookupService,
    store_rnc_records,
    validate_rnc,
)

pytestmark = pytest.mark.django_db

RNC_URL = "/api/validate-rnc/"
CEDULA_URL = "/api/validate-cedula/"
SCRAPER = "apps.core.services.rnc_lookup.scrape_dgii_rnc"
UNKNOWN_RNC = "99999999999"


def fake_registry(n=1000):
    return {
        f"{i:011d}": {
            "razon_social": f"EMPRESA {i}",
            "actividad_economica": "SERVICIOS",
            "fecha_inicio": "",
            "estado": "ACTIVO" if i % 2 else "SUSPENDIDO",
            "regimen_pago": "NORMAL",
        }
        for i in range(1, n + 1)
    }


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    # LocMemCache descarta entradas a partir de 300 (MAX_ENTRIES por defecto).
    monkeypatch.setattr(cache, "_max_entries", 10_000)
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def loaded_registry():
    store_rnc_records(fake_registry(), source="test")


# --- Caché por clave ---------------------------------------------------------

def test_loader_writes_per_record_keys_and_meta():
    cache.set(LEGACY_CACHE_KEY, '{"00000000001": {}}')
    count = store_rnc_records(fake_registry(1000), source="test")
    assert count == 1000
    assert cache.get("dgii_rnc:00000000007")["razon_social"] == "EMPRESA 7"
    meta = cache.get("dgii_rnc_database_meta")
    assert meta["count"] == 1000 and meta["source"] == "test" and meta["loaded_at"]
    assert cache.get(LEGACY_CACHE_KEY) is None
    assert RNCLookupService.is_database_loaded()


def test_lookup_with_1000_records_does_exactly_one_cache_get(loaded_registry):
    with mock.patch.object(cache, "get", wraps=cache.get) as spy:
        result = validate_rnc("00000000501", allow_scrape=False)
    assert result["exists"] is True
    assert result["data"]["razon_social"] == "EMPRESA 501"
    assert result["is_active"] is True
    assert spy.call_count == 1
    assert spy.call_args.args[0] == "dgii_rnc:00000000501"


@pytest.mark.parametrize("bad", ["abc", "12345", "123456789012", "12-34x"])
def test_invalid_format_never_touches_cache(loaded_registry, bad):
    with mock.patch.object(cache, "get", wraps=cache.get) as get_spy, \
            mock.patch.object(cache, "set", wraps=cache.set) as set_spy, \
            mock.patch(SCRAPER) as scraper:
        result = validate_rnc(bad, allow_scrape=True)
    assert result["is_valid"] is False
    assert get_spy.call_count == 0
    assert set_spy.call_count == 0
    scraper.assert_not_called()


def test_is_database_loaded_ignores_legacy_blob(caplog):
    cache.set(LEGACY_CACHE_KEY, '{"00000000001": {}}')
    with mock.patch.object(cache, "get", wraps=cache.get) as spy:
        assert RNCLookupService.is_database_loaded() is False
    assert LEGACY_CACHE_KEY not in [c.args[0] for c in spy.call_args_list]
    assert "update_rnc_database" in caplog.text


def test_scraped_result_is_cached_under_its_own_key(loaded_registry):
    scraped = {
        "rnc": UNKNOWN_RNC, "razon_social": "NUEVA SRL", "actividad_economica": "X",
        "fecha_inicio": "", "estado": "ACTIVO", "regimen_pago": "NORMAL", "is_active": True,
    }
    with mock.patch(SCRAPER, return_value=scraped):
        result = validate_rnc(UNKNOWN_RNC, allow_scrape=True)
    assert result["source"] == "dgii_scraper"
    assert cache.get(f"dgii_rnc:{UNKNOWN_RNC}")["razon_social"] == "NUEVA SRL"
    assert cache.get("dgii_rnc_database_meta")["count"] == 1000


# --- Scraping sólo autenticado -----------------------------------------------

def test_anonymous_unknown_rnc_does_not_scrape(api_client, loaded_registry):
    with mock.patch(SCRAPER) as scraper:
        response = api_client.post(RNC_URL, {"rnc": UNKNOWN_RNC}, format="json")
    assert response.status_code == 200
    assert response.data["exists"] is False
    scraper.assert_not_called()


def test_authenticated_unknown_rnc_scrapes(auth_client, loaded_registry):
    with mock.patch(SCRAPER, return_value=None) as scraper:
        response = auth_client.post(RNC_URL, {"rnc": UNKNOWN_RNC}, format="json")
    assert response.status_code == 200
    assert response.data["exists"] is False
    scraper.assert_called_once_with(UNKNOWN_RNC)


def test_anonymous_known_rnc_is_found_without_scraping(api_client, loaded_registry):
    with mock.patch(SCRAPER) as scraper:
        response = api_client.post(RNC_URL, {"rnc": "00000000003"}, format="json")
    assert response.status_code == 200
    assert response.data["exists"] is True
    scraper.assert_not_called()


def test_status_view_reports_meta(api_client, loaded_registry):
    response = api_client.get("/api/rnc-database-status/")
    assert response.status_code == 200
    assert response.data["loaded"] is True
    assert response.data["total_records"] == 1000


# --- Throttle propio ---------------------------------------------------------

@pytest.mark.parametrize("view", [views.validate_rnc_view, views.rnc_database_status])
def test_rnc_views_use_scoped_throttle(view):
    assert view.cls.throttle_scope == "validate_rnc"
    assert list(view.cls.throttle_classes) == [ScopedRateThrottle]
    assert "validate_rnc" in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]


def test_validate_rnc_is_throttled_per_client(api_client, loaded_registry):
    limit = int(ScopedRateThrottle.THROTTLE_RATES["validate_rnc"].split("/")[0])
    for _ in range(limit):
        assert api_client.post(RNC_URL, {"rnc": "00000000003"}, format="json").status_code == 200
    assert api_client.post(RNC_URL, {"rnc": "00000000003"}, format="json").status_code == 429


# --- Cédula por permiso: customers.create o customers.edit (cambio intencional D5, R8) --------

@pytest.mark.parametrize("role", ["viewer", "accountant", "cashier", "collector", "collection_supervisor"])
def test_roles_without_customer_write_cannot_query_cedula(api_client, user_factory, role):
    api_client.force_authenticate(user=user_factory(role=role))
    response = api_client.get(CEDULA_URL, {"cedula": "00112345678"})
    assert response.status_code == 403
    assert response.json()["required_permission"] == "customers.create"


def test_loan_officer_can_query_cedula(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role="loan_officer"))
    response = api_client.get(CEDULA_URL, {"cedula": "123"})
    assert response.status_code == 400  # pasa el permiso y llega a la validación


@pytest.mark.parametrize("codigo", ["customers.create", "customers.edit"])
def test_either_customer_write_code_allows_cedula(api_client, user_factory, tenant_schema, codigo):
    from apps.users.models import Role

    Role.objects.filter(tenant=tenant_schema, key="viewer").update(permissions=[codigo])
    api_client.force_authenticate(user=user_factory(role="viewer"))
    assert api_client.get(CEDULA_URL, {"cedula": "123"}).status_code == 400


def test_cedula_view_uses_scoped_throttle():
    view = views.validate_cedula_view
    assert view.cls.throttle_scope == "cedula_lookup"
    assert list(view.cls.throttle_classes) == [ScopedRateThrottle]
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["cedula_lookup"] == "30/minute"


def test_cedula_lookup_is_throttled_per_user(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role="loan_officer"))
    limit = int(ScopedRateThrottle.THROTTLE_RATES["cedula_lookup"].split("/")[0])
    assert limit == 30
    for _ in range(limit):
        # Cédula corta: 400, pero el throttle corre antes de la vista y cuenta igual.
        assert api_client.get(CEDULA_URL, {"cedula": "123"}).status_code == 400
    assert api_client.get(CEDULA_URL, {"cedula": "123"}).status_code == 429


# --- Fix round 1: claves sin relleno y TTL de registros > TTL del meta ---------

def _record(name):
    return {"razon_social": name, "actividad_economica": "", "fecha_inicio": "",
            "estado": "ACTIVO", "regimen_pago": "NORMAL"}


def test_nine_digit_rnc_and_padded_cedula_do_not_collide():
    store_rnc_records(
        {"101234567": _record("EMPRESA SRL"), "00101234567": _record("JUAN PEREZ")},
        source="test",
    )
    assert validate_rnc("101234567", allow_scrape=False)["data"]["razon_social"] == "EMPRESA SRL"
    assert validate_rnc("00101234567", allow_scrape=False)["data"]["razon_social"] == "JUAN PEREZ"
    assert validate_rnc("1-01-23456-7", allow_scrape=False)["data"]["razon_social"] == "EMPRESA SRL"
    assert cache.get("dgii_rnc_database_meta")["count"] == 2


def test_meta_count_is_number_of_distinct_keys():
    # "101-234567" y "101234567" son la misma clave tras quitar guiones.
    store_rnc_records(
        {"101-234567": _record("A"), "101234567": _record("B"), "00101234567": _record("C")},
        source="test",
    )
    assert cache.get("dgii_rnc_database_meta")["count"] == 2


def test_scraped_nine_digit_rnc_is_cached_under_unpadded_key(loaded_registry):
    scraped = {"rnc": "00130000001", "razon_social": "NUEVA SRL", "estado": "ACTIVO",
               "is_active": True}
    with mock.patch(SCRAPER, return_value=scraped):
        validate_rnc("130000001", allow_scrape=True)
    assert cache.get("dgii_rnc:130000001")["razon_social"] == "NUEVA SRL"
    assert cache.get("dgii_rnc:00130000001") is None


def test_records_outlive_meta():
    with mock.patch.object(cache, "set_many", wraps=cache.set_many) as set_many, \
            mock.patch.object(cache, "set", wraps=cache.set) as set_:
        store_rnc_records(fake_registry(10), source="test", timeout=7 * 24 * 3600)
    record_timeouts = {c.kwargs["timeout"] for c in set_many.call_args_list}
    meta_timeout = next(c.kwargs["timeout"] for c in set_.call_args_list
                        if c.args[0] == "dgii_rnc_database_meta")
    assert record_timeouts and all(t > meta_timeout for t in record_timeouts)
