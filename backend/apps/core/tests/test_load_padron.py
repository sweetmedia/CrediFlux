"""D5: comando load_padron_jce, carga todo o nada sobre public.padron_jce."""
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

SAMPLE = Path(__file__).parent / 'fixtures' / 'padron_sample.csv'


def _filas():
    with connection.cursor() as cur:
        cur.execute(
            'SELECT cedula, nombres, apellido1, apellido2, fecha_nacimiento, sexo, '
            'estado_civil, lugar_nacimiento FROM public.padron_jce ORDER BY cedula'
        )
        return cur.fetchall()


def _previa():
    with connection.cursor() as cur:
        cur.execute('DELETE FROM public.padron_jce')
        cur.execute(
            "INSERT INTO public.padron_jce (cedula, nombres, apellido1, apellido2) "
            "VALUES ('99900000011', 'PREVIA', 'FILA', 'UNO')"
        )


def _archivo(tmp_path, contenido):
    p = tmp_path / 'p.csv'
    p.write_text(contenido, encoding='utf-8')
    return str(p)


@pytest.mark.django_db
def test_carga_el_ejemplo(public_schema, capsys):
    call_command('load_padron_jce', str(SAMPLE))
    filas = _filas()
    assert len(filas) == 3
    por_ced = {f[0]: f for f in filas}
    # Apellido2 = espacio -> NULL; comas y comillas dentro del nombre intactas
    assert por_ced['00100000027'][1] == 'JUAN "EL GRANDE", JR'
    assert por_ced['00100000027'][3] is None
    assert por_ced['00100000019'][7] == 'SANTO DOMINGO, R.D.'
    # Sin fecha, estado civil ni lugar -> NULL
    assert por_ced['00100000035'][4:] == (None, 'F', None, None)
    assert '3' in capsys.readouterr().out


@pytest.mark.django_db
def test_carga_desde_otro_schema(tenant_schema):
    call_command('load_padron_jce', str(SAMPLE))
    connection.set_schema_to_public()
    assert len(_filas()) == 3


@pytest.mark.django_db
def test_recarga_reemplaza_la_tabla(public_schema):
    _previa()
    call_command('load_padron_jce', str(SAMPLE))
    assert '99900000011' not in {f[0] for f in _filas()}


@pytest.mark.django_db
def test_linea_con_7_columnas_falla_y_conserva_lo_previo(public_schema, tmp_path):
    _previa()
    ruta = _archivo(tmp_path, '00100000019|A|B| |1980-05-01|F|C\n')
    with pytest.raises(CommandError):
        call_command('load_padron_jce', ruta)
    assert [f[0] for f in _filas()] == ['99900000011']


@pytest.mark.django_db
@pytest.mark.parametrize('linea', [
    '1234|A|B| |1980-05-01|M|S|X',            # cédula corta
    '0010000002X|A|B| |1980-05-01|M|S|X',     # cédula no numérica
    '00100000019|A|B| |1980-05-01|Z|S|X',     # sexo inválido
])
def test_filas_invalidas_fallan_todo_o_nada(public_schema, tmp_path, linea):
    _previa()
    ruta = _archivo(tmp_path, '00100000035|OK|OK| |1980-05-01|M|S|X\n' + linea + '\n')
    with pytest.raises(CommandError, match='1'):
        call_command('load_padron_jce', ruta)
    assert [f[0] for f in _filas()] == ['99900000011']


@pytest.mark.django_db
def test_fecha_invalida_falla_sin_tocar_la_tabla(public_schema, tmp_path):
    _previa()
    ruta = _archivo(tmp_path, '00100000019|A|B| |no-es-fecha|M|S|X\n')
    with pytest.raises(CommandError):
        call_command('load_padron_jce', ruta)
    assert [f[0] for f in _filas()] == ['99900000011']


@pytest.mark.django_db
def test_dry_run_no_cambia_la_tabla(public_schema, capsys):
    _previa()
    call_command('load_padron_jce', str(SAMPLE), '--dry-run')
    assert [f[0] for f in _filas()] == ['99900000011']
    assert '3' in capsys.readouterr().out


@pytest.mark.django_db
def test_archivo_inexistente(public_schema):
    with pytest.raises(CommandError):
        call_command('load_padron_jce', '/no/existe.csv')
