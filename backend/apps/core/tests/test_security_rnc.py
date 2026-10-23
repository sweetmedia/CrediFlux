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


# --- Cédula por rol ----------------------------------------------------------

@pytest.mark.parametrize("role", ["viewer", "accountant", "cashier"])
def test_non_collection_roles_cannot_query_cedula(api_client, user_factory, role):
    api_client.force_authenticate(user=user_factory(role=role))
    response = api_client.get(CEDULA_URL, {"cedula": "00112345678"})
    assert response.status_code == 403


def test_collector_can_query_cedula(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role="collector"))
    response = api_client.get(CEDULA_URL, {"cedula": "123"})
    assert response.status_code == 400  # pasa el permiso y llega a la validación
