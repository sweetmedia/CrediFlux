"""Consulta de cédula: esquema calificado, auditoría, sexo/lugar y errores sin filtrar detalles."""
from unittest import mock

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.audit.models import AuditLog
from apps.loans.models import Customer

pytestmark = pytest.mark.django_db

URL = "/api/validate-cedula/"
EXISTENTE = "00100000019"
INEXISTENTE = "00199999991"


@pytest.fixture
def padron(tenant_schema):
    """Inserta una fila en public.padron_jce (la vista corre en el esquema del tenant)."""
    with connection.cursor() as cur:
        cur.execute(
            "INSERT INTO public.padron_jce "
            "(cedula, nombres, apellido1, apellido2, fecha_nacimiento, sexo, estado_civil, lugar_nacimiento) "
            "VALUES (%s, 'MARIA DEL CARMEN', 'PEREZ', 'GOMEZ', '1980-05-01', 'F', 'C', 'SANTO DOMINGO, R.D.') "
            "ON CONFLICT (cedula) DO NOTHING",
            [EXISTENTE],
        )


def _officer(api_client, user_factory):
    user = user_factory(role="loan_officer")
    api_client.force_authenticate(user=user)
    return user


def test_encontrada_devuelve_sexo_lugar_y_audita(api_client, user_factory, padron):
    user = _officer(api_client, user_factory)
    response = api_client.get(URL, {"cedula": EXISTENTE})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["sexo"] == "F"
    assert data["estado_civil"] == "C"
    assert data["lugar_nacimiento"] == "SANTO DOMINGO, R.D."
    assert data["nombre_completo"] == "Maria Del Carmen Perez Gomez"
    log = AuditLog.objects.get(action="cedula_lookup", user=user)
    assert log.model_name == "PadronJCE"
    assert log.extra_data == {"cedula": EXISTENTE, "found": True}
    assert "Maria" not in str(log.extra_data) and "PEREZ" not in str(log.extra_data)


def test_inexistente_200_found_false_y_se_audita(api_client, user_factory, padron):
    user = _officer(api_client, user_factory)
    response = api_client.get(URL, {"cedula": INEXISTENTE})
    assert response.status_code == 200
    assert response.json()["found"] is False
    log = AuditLog.objects.get(action="cedula_lookup", user=user)
    assert log.extra_data == {"cedula": INEXISTENTE, "found": False}


def test_no_deja_search_path_en_public(api_client, user_factory, padron, tenant_schema):
    _officer(api_client, user_factory)
    with CaptureQueriesContext(connection) as ctx:
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
    sqls = [q["sql"].lower() for q in ctx.captured_queries]
    i = next(n for n, q in enumerate(sqls) if "public.padron_jce" in q)
    # el middleware fija 'public' para resolver el dominio, pero la vista no debe volver a hacerlo
    assert not any(q.startswith("set search_path = 'public'") for q in sqls[i - 1:])
    with connection.cursor() as cur:
        cur.execute("SHOW search_path")
        search_path = cur.fetchone()[0]
    assert search_path.split(",")[0].strip().strip('"') == tenant_schema.schema_name
    assert Customer.objects.count() == 0  # consulta de modelo del tenant sigue funcionando


def test_error_de_bd_responde_500_sin_detalle(api_client, user_factory):
    _officer(api_client, user_factory)
    with mock.patch("apps.core.views._buscar_en_padron", side_effect=RuntimeError("secreto-interno")):
        response = api_client.get(URL, {"cedula": EXISTENTE})
    assert response.status_code == 500
    assert response.json() == {"detail": "No se pudo consultar el padrón."}
    assert "secreto-interno" not in response.content.decode()


def test_viewer_recibe_403(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role="viewer"))
    assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 403


# --- Run-8 M1: topes diarios por usuario y por financiera; L3: sólo 11 dígitos ---------------

from django.conf import settings as dj_settings  # noqa: E402
from django.core.cache import cache  # noqa: E402
from django.test import override_settings  # noqa: E402


@pytest.fixture
def cache_limpio():
    cache.clear()
    yield
    cache.clear()


def _tasas(**cambios):
    """REST_FRAMEWORK con las tasas de base.py y `cambios` encima (api_settings se recarga)."""
    rest = dict(dj_settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest["DEFAULT_THROTTLE_RATES"], **cambios}
    return override_settings(REST_FRAMEWORK=rest)


def test_topes_diarios_por_defecto():
    from apps.core import views

    tasas = dj_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert tasas["cedula_lookup_day"] == "300/day"
    assert tasas["cedula_lookup_tenant_day"] == "2000/day"
    nombres = {c.__name__ for c in views.validate_cedula_view.cls.throttle_classes}
    assert nombres == {"TopesPadronThrottle"}


def test_tope_diario_por_usuario(api_client, user_factory, padron, cache_limpio):
    with _tasas(cedula_lookup_day="2/day"):
        _officer(api_client, user_factory)
        for _ in range(2):
            assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 429
        # Otro usuario de la misma financiera sigue pudiendo (el tope es por usuario).
        _officer(api_client, user_factory)
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200


def test_tope_diario_por_financiera(api_client, user_factory, padron, cache_limpio):
    with _tasas(cedula_lookup_tenant_day="3/day"):
        for _ in range(2):
            _officer(api_client, user_factory)
            assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
        # Cuarta consulta de la financiera (segunda del segundo usuario): 429.
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 429
    assert AuditLog.objects.filter(action="cedula_lookup").count() == 3


@pytest.mark.parametrize(
    "cedula", ["A" * 5000, "0010000001", "001000000199", "00100000O19", "123"],
    ids=["5000-letras", "10-digitos", "12-digitos", "con-letra", "corta"],
)
def test_cedula_que_no_es_de_11_digitos_da_400_sin_auditar(api_client, user_factory, cedula, cache_limpio):
    _officer(api_client, user_factory)
    with mock.patch("apps.core.views._buscar_en_padron") as buscar:
        response = api_client.get(URL, {"cedula": cedula})
    assert response.status_code == 400
    body = response.json()
    assert "detail" in body and "error" not in body
    buscar.assert_not_called()
    assert not AuditLog.objects.filter(action="cedula_lookup").exists()


def test_cedula_con_guiones_y_espacios_se_normaliza(api_client, user_factory, padron, cache_limpio):
    _officer(api_client, user_factory)
    response = api_client.get(URL, {"cedula": " 001-0000001-9 "})
    assert response.status_code == 200
    assert response.json()["found"] is True


# --- R22: un rechazo no consume los topes que sí lo dejaban pasar; tasa faltante falla ----------


def test_rechazos_por_minuto_no_gastan_el_tope_de_la_financiera(api_client, user_factory, padron, cache_limpio):
    with _tasas(cedula_lookup="2/min", cedula_lookup_tenant_day="3/day"):
        _officer(api_client, user_factory)
        for _ in range(2):
            assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
        for _ in range(5):
            assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 429
        # La financiera sólo gastó 2 de 3: otro usuario todavía puede consultar.
        _officer(api_client, user_factory)
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200


def test_rechazos_del_tope_del_usuario_no_gastan_el_de_la_financiera(api_client, user_factory, padron, cache_limpio):
    with _tasas(cedula_lookup_day="1/day", cedula_lookup_tenant_day="2/day"):
        _officer(api_client, user_factory)
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200
        for _ in range(5):
            assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 429
        _officer(api_client, user_factory)
        assert api_client.get(URL, {"cedula": EXISTENTE}).status_code == 200


@pytest.mark.parametrize("scope", ["cedula_lookup", "cedula_lookup_day", "cedula_lookup_tenant_day"])
def test_sin_tasa_configurada_falla_en_vez_de_apagar_el_tope(api_client, user_factory, padron, cache_limpio, scope):
    from django.core.exceptions import ImproperlyConfigured

    rest = dict(dj_settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {k: v for k, v in rest["DEFAULT_THROTTLE_RATES"].items() if k != scope}
    with override_settings(REST_FRAMEWORK=rest):
        _officer(api_client, user_factory)
        with pytest.raises(ImproperlyConfigured):
            api_client.get(URL, {"cedula": EXISTENTE})
