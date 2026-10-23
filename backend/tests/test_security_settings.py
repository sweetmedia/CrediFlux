"""Settings de seguridad: credenciales de BD, NUM_PROXIES y bootstrap sin contraseña fija.

Los tests recargan el módulo ``config.settings.base`` con el entorno manipulado;
no tocan ``django.conf.settings`` (ya configurado con ``config.settings.test``).
Al terminar se recarga el módulo con el entorno original.
"""

import importlib
from pathlib import Path

import pytest

import config.settings.base as base_settings

DB_VARS = ('DATABASE_URL', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT')


@pytest.fixture
def reload_base(monkeypatch):
    """Devuelve una función que recarga ``config.settings.base`` sin variables de BD."""
    for var in DB_VARS + ('DRF_NUM_PROXIES',):
        monkeypatch.delenv(var, raising=False)

    def _reload():
        return importlib.reload(base_settings)

    yield _reload
    monkeypatch.undo()
    importlib.reload(base_settings)


def test_database_url_se_usa_cuando_existe(reload_base, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgres://u:p@h:5/d')
    db = reload_base().DATABASES['default']
    assert db['USER'] == 'u'
    assert db['HOST'] == 'h'
    assert db['PASSWORD'] == 'p'
    assert db['NAME'] == 'd'
    assert db['ENGINE'] == 'django_tenants.postgresql_backend'


def test_sin_variables_la_contrasena_queda_vacia(reload_base):
    db = reload_base().DATABASES['default']
    assert db['PASSWORD'] == ''
    assert db['ENGINE'] == 'django_tenants.postgresql_backend'


def test_num_proxies_por_defecto_es_uno(reload_base):
    assert reload_base().REST_FRAMEWORK['NUM_PROXIES'] == 1


SKIP_DIRS = {'.venv', 'venv', 'node_modules', '__pycache__', '.git', 'media', 'static',
             'staticfiles', 'logs', '.pytest_cache', '.ruff_cache'}
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.toml', '.cfg', '.ini', '.json', '.yml', '.yaml',
                 '.html', '.sh', '.example', '.env'}


def test_no_hay_contrasena_admin_fija_en_el_backend():
    backend_dir = Path(__file__).resolve().parent.parent
    needle = 'admin' + '2026'  # construida para que este archivo no se detecte a sí mismo
    offenders = []
    for path in backend_dir.rglob('*'):
        if any(part in SKIP_DIRS for part in path.relative_to(backend_dir).parts):
            continue
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if needle in path.read_text(encoding='utf-8', errors='ignore'):
            offenders.append(str(path.relative_to(backend_dir)))
    assert offenders == []
