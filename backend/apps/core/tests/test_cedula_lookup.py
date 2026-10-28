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
