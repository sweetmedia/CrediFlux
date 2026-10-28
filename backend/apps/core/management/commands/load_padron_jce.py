"""Carga el padrón de la JCE en ``public.padron_jce`` (D5), todo o nada.

Archivo ``|``-delimitado, sin cabecera, 8 columnas:
``Cedula|Nombres|Apellido1|Apellido2|FechaNacimiento|IdSexo|IdEstadoCivil|LugarNacimiento``.

Pasos: COPY a una tabla temporal con columnas de texto (así el COPY no falla por tipos),
validación en SQL y, en la misma transacción, ``TRUNCATE`` + ``INSERT``. Si algo falla, la
tabla anterior queda intacta. Siempre usa nombres calificados: no depende del search_path.
"""
import os

import psycopg2
from django.core.management.base import BaseCommand, CommandError
from django.db import Error as DjangoDBError
from django.db import connection, transaction

STAGING = 'pg_temp.padron_jce_staging'

CREAR_STAGING = f"""
CREATE TEMP TABLE padron_jce_staging (
    cedula text, nombres text, apellido1 text, apellido2 text,
    fecha_nacimiento text, sexo text, estado_civil text, lugar_nacimiento text
)
"""

# QUOTE \x01 nunca aparece en los datos: comas y comillas dentro de los nombres no rompen el CSV.
COPIAR = (
    f"COPY {STAGING} FROM STDIN "
    "WITH (FORMAT csv, DELIMITER '|', QUOTE E'\\x01', ESCAPE E'\\x01')"
)

CONTAR_INVALIDAS = f"""
SELECT count(*) FROM {STAGING}
WHERE coalesce(btrim(cedula), '') !~ '^[0-9]{{11}}$'
   OR coalesce(btrim(sexo), '') NOT IN ('M', 'F', '')
   OR (coalesce(btrim(fecha_nacimiento), '') <> ''
       AND btrim(fecha_nacimiento) !~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$')
"""

INSERTAR = f"""
INSERT INTO public.padron_jce
    (cedula, nombres, apellido1, apellido2, fecha_nacimiento, sexo, estado_civil, lugar_nacimiento)
SELECT btrim(cedula),
       btrim(nombres),
       btrim(apellido1),
       NULLIF(btrim(apellido2), ''),
       NULLIF(btrim(fecha_nacimiento), '')::date,
       NULLIF(btrim(sexo), ''),
       NULLIF(btrim(estado_civil), ''),
       NULLIF(btrim(lugar_nacimiento), '')
FROM {STAGING}
"""


class _Ensayo(Exception):
    """Centinela: --dry-run hace la carga completa y la revierte lanzando esto."""

    def __init__(self, total):
        self.total = total


class Command(BaseCommand):
    help = 'Carga el padrón de la JCE (CSV con "|") en public.padron_jce, todo o nada.'

    def add_arguments(self, parser):
        parser.add_argument('ruta', help='Archivo del padrón (UTF-8, delimitado por |, sin cabecera).')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Hace la carga completa (validación, TRUNCATE e INSERT) y la revierte; la tabla no cambia.',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Permite cargar un archivo con menos del 90 %% de las filas actuales.',
        )

    def handle(self, *args, **opts):
        ruta = opts['ruta']
        if not os.path.isfile(ruta):
            raise CommandError(f'No existe el archivo: {ruta}')
        dry_run = opts['dry_run']
        try:
            try:
                cargadas = self._cargar(ruta, dry_run, opts['force'])
            except _Ensayo as e:
                cargadas = e.total
        except OSError as exc:
            raise CommandError(f'No se pudo leer {ruta}: {exc.strerror or type(exc).__name__}') from None
        except (psycopg2.Error, DjangoDBError) as exc:
            # Sólo la primera línea: el CONTEXT de la BD trae la línea completa (datos personales).
            detalle = str(exc).strip().splitlines()[0] if str(exc).strip() else ''
            raise CommandError(
                f'Carga abortada, la tabla no cambió ({type(exc).__name__}: {detalle})'
            ) from None
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'[dry-run] {cargadas} filas se cargarían; la tabla no se modificó.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f'{cargadas} filas cargadas en public.padron_jce.'))

    def _cargar(self, ruta, dry_run, force):
        with transaction.atomic():
            cur = connection.cursor()
            # La tabla temporal nace dentro de la transacción: si algo falla, el rollback la elimina.
            cur.execute('DROP TABLE IF EXISTS pg_temp.padron_jce_staging')
            cur.execute(CREAR_STAGING)
            with open(ruta, 'rb') as fh:
                cur.cursor.copy_expert(COPIAR, fh)
            cur.execute(f'SELECT count(*) FROM {STAGING}')
            total = cur.fetchone()[0]
            if total == 0:
                raise CommandError('El archivo no tiene filas.')
            cur.execute(CONTAR_INVALIDAS)
            malas = cur.fetchone()[0]
            if malas:
                raise CommandError(
                    f'{malas} fila(s) inválidas (cédula sin 11 dígitos, sexo distinto de M/F '
                    'o fecha mal formada). No se cargó nada.'
                )
            cur.execute('SELECT count(*) FROM public.padron_jce')
            previas = cur.fetchone()[0]
            if previas and total < previas * 0.9 and not force:
                raise CommandError(
                    f'El archivo trae {total} filas y la tabla tiene {previas} (menos del 90 %): '
                    'parece truncado. Usa --force si es intencional.'
                )
            cur.execute('TRUNCATE public.padron_jce')
            cur.execute(INSERTAR)
            cur.execute('DROP TABLE pg_temp.padron_jce_staging')
            if dry_run:
                raise _Ensayo(total)  # revierte TRUNCATE + INSERT
            return total
