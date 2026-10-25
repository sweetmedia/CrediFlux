"""Ejecutor de `migrate_schemas` que salta los tenants sin schema (registros pendientes).

django-tenants migra cada fila de Tenant que no sea la pública. Un registro pendiente no
tiene schema: `run_migrations` haría `set_schema(<inexistente>, include_public=False)` y
`MigrationRecorder.ensure_schema()` fallaría con "no schema has been selected to create in",
tumbando `manage.py migrate` (que corre al arrancar el backend). Se conecta con el setting
`GET_EXECUTOR_FUNCTION`.
"""
from django.db import connections
from django_tenants.migration_executors import get_executor as default_get_executor
from django_tenants.utils import get_public_schema_name, get_tenant_database_alias


def _existing_schemas():
    with connections[get_tenant_database_alias()].cursor() as cursor:
        cursor.execute('SELECT schema_name FROM information_schema.schemata')
        return {row[0] for row in cursor.fetchall()}


def _skip_missing(schema_names):
    """Conserva el público y los schemas que existen."""
    schema_names = list(schema_names or [])
    existing = _existing_schemas()
    public = get_public_schema_name()
    return [name for name in schema_names if name == public or name in existing]


class _SkipMissingSchemasMixin:
    def run_migrations(self, tenants=None):
        return super().run_migrations(tenants=_skip_missing(tenants))

    def run_multi_type_migrations(self, tenants):
        tenants = list(tenants or [])
        keep = set(_skip_missing(t[0] for t in tenants))
        return super().run_multi_type_migrations(tenants=[t for t in tenants if t[0] in keep])


_CLASSES = {}


def get_executor(codename=None):
    """Misma selección que django-tenants (`EXECUTOR`), con el filtro de schemas inexistentes."""
    base = default_get_executor(codename)
    if base not in _CLASSES:
        _CLASSES[base] = type(f'SkipMissing{base.__name__}', (_SkipMissingSchemasMixin, base), {})
    return _CLASSES[base]
