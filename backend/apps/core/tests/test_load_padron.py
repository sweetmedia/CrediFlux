"""D5: comando load_padron_jce, carga todo o nada sobre public.padron_jce."""
import os
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
    '|A|B| |1980-05-01|M|S|X',                # cédula vacía (NULL en COPY csv)
])
def test_filas_invalidas_fallan_todo_o_nada(public_schema, tmp_path, linea):
    _previa()
    ruta = _archivo(tmp_path, '00100000035|OK|OK| |1980-05-01|M|S|X\n' + linea + '\n')
    with pytest.raises(CommandError, match='1'):
        call_command('load_padron_jce', ruta)
    assert [f[0] for f in _filas()] == ['99900000011']


MALOS_EN_INSERT = {
    'fecha_texto': '00100000019|A|B| |no-es-fecha|M|S|X\n',
    'fecha_imposible': '00100000019|A|B| |2023-02-30|M|S|X\n',
    'cedula_duplicada': '00100000019|A|B| |1980-05-01|M|S|X\n00100000019|C|D| |1981-05-01|F|S|X\n',
    'estado_civil_largo': '00100000019|A|B| |1980-05-01|M|SS|X\n',
}


@pytest.mark.django_db
@pytest.mark.parametrize('dry', [False, True])
@pytest.mark.parametrize('caso', list(MALOS_EN_INSERT))
def test_errores_de_insert_fallan_con_y_sin_dry_run(public_schema, tmp_path, caso, dry):
    _previa()
    ruta = _archivo(tmp_path, MALOS_EN_INSERT[caso])
    args = ['--dry-run'] if dry else []
    with pytest.raises(CommandError):
        call_command('load_padron_jce', ruta, *args)
    assert [f[0] for f in _filas()] == ['99900000011']


@pytest.mark.django_db
def test_error_no_encadena_la_excepcion_de_la_bd(public_schema, tmp_path):
    ruta = _archivo(tmp_path, MALOS_EN_INSERT['fecha_imposible'])
    with pytest.raises(CommandError) as ei:
        call_command('load_padron_jce', ruta)
    assert ei.value.__cause__ is None and ei.value.__suppress_context__


@pytest.mark.django_db
def test_archivo_corto_se_rechaza_salvo_force(public_schema, tmp_path):
    with connection.cursor() as cur:
        cur.execute('DELETE FROM public.padron_jce')
        cur.execute(
            "INSERT INTO public.padron_jce (cedula, nombres, apellido1) "
            "SELECT lpad(g::text, 11, '9'), 'N', 'A' FROM generate_series(1, 10) g"
        )
    ruta = _archivo(tmp_path, '00100000019|A|B| |1980-05-01|M|S|X\n')
    with pytest.raises(CommandError, match='10'):
        call_command('load_padron_jce', ruta)
    assert len(_filas()) == 10
    call_command('load_padron_jce', ruta, '--force')
    assert [f[0] for f in _filas()] == ['00100000019']


@pytest.mark.django_db
def test_archivo_sin_permiso(public_schema, tmp_path):
    ruta = _archivo(tmp_path, '00100000019|A|B| |1980-05-01|M|S|X\n')
    os.chmod(ruta, 0)
    if os.access(ruta, os.R_OK):
        pytest.skip('se ejecuta como root: chmod 0 no impide leer')
    with pytest.raises(CommandError, match='No se pudo leer'):
        call_command('load_padron_jce', ruta)


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


@pytest.mark.django_db
def test_byte_nulo_cuenta_como_vacio(public_schema, tmp_path):
    """El extracto real (bcp de SQL Server) marca con 0x00 el segundo apellido o el lugar de
    nacimiento vacíos; Postgres rechaza ese byte en texto UTF-8."""
    p = tmp_path / 'nulos.csv'
    p.write_bytes(
        b'00100000019|ANA|PEREZ|\x00|1990-01-02|F|S|\x00\n'
        b'00200000027|LUIS|GOMEZ|DIAZ|1985-03-04|M|C|SANTIAGO, R.D.\n'
    )
    call_command('load_padron_jce', str(p))
    filas = _filas()
    assert [f[0] for f in filas] == ['00100000019', '00200000027']
    assert filas[0][3] is None and filas[0][7] is None
    assert filas[1][3] == 'DIAZ'


@pytest.mark.django_db
def test_origen_cp850_repara_enes_tildes_y_el_lugar(public_schema, tmp_path, capsys):
    p = _archivo(
        tmp_path,
        '00100000019|MARÖA|PE¥A|\x00|1990-01-02|F|S|MONSE|OR NOUEL\n'
        '00200000027|JOÇO|LEBRàN|GšIRA|1985-03-04|M|C|SANTIAGO, R.D.\n'
        '00300000035|RAMIRO|ENCARNACI|N||1923-04-12|M|S|VALLEJUELO\n',
    )
    call_command('load_padron_jce', p, '--origen-cp850')
    filas = _filas()
    assert [f[0] for f in filas] == ['00100000019', '00200000027']
    assert filas[0][1:4] == ('MARÍA', 'PEÑA', None)
    assert filas[0][7] == 'MONSEÑOR NOUEL'
    assert filas[1][1:4] == ('JOÃO', 'LEBRÓN', 'GÜIRA')
    assert '1 línea(s) omitidas' in capsys.readouterr().out


@pytest.mark.django_db
def test_origen_cp850_aborta_si_sobran_columnas_en_muchas_lineas(public_schema, tmp_path):
    _previa()
    malas = ''.join(f'00{i:09d}|A|B|C|D|1990-01-02|F|S|X\n' for i in range(150))
    with pytest.raises(CommandError, match='no parece'):
        call_command('load_padron_jce', _archivo(tmp_path, malas), '--origen-cp850')
    assert [f[0] for f in _filas()] == ['99900000011']


@pytest.mark.django_db
def test_sin_origen_cp850_no_toca_los_caracteres(public_schema, tmp_path):
    call_command('load_padron_jce', _archivo(tmp_path, '00100000019|ÑOÑO|PEÑA||1990-01-02|M|S|\n'))
    assert _filas()[0][1:3] == ('ÑOÑO', 'PEÑA')
