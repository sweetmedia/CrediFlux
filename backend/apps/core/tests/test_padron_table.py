"""D5: la tabla del padrón JCE vive en el esquema público con 8 columnas."""
import pytest
from django.db import connection

COLUMNAS = {
    'cedula', 'nombres', 'apellido1', 'apellido2', 'fecha_nacimiento',
    'sexo', 'estado_civil', 'lugar_nacimiento',
}


def _columnas(schema):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = 'padron_jce'",
            [schema],
        )
        return {r[0] for r in cur.fetchall()}


@pytest.mark.django_db
def test_padron_existe_en_public_con_8_columnas(public_schema):
    assert _columnas('public') == COLUMNAS


@pytest.mark.django_db
def test_cedula_es_clave_primaria_char11(public_schema):
    with connection.cursor() as cur:
        cur.execute(
            "SELECT data_type, character_maximum_length FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='padron_jce' AND column_name='cedula'"
        )
        assert cur.fetchone() == ('character', 11)
        cur.execute(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_schema='public' AND table_name='padron_jce' "
            "AND constraint_type='PRIMARY KEY'"
        )
        assert cur.fetchone() is not None


@pytest.mark.django_db
def test_tenant_no_tiene_padron_propio(tenant_schema):
    assert _columnas(tenant_schema.schema_name) == set()
