"""Rutas de subida por tenant.

Todo archivo nuevo se guarda como ``<schema>/<prefijo>/<token>/<nombre>``: el
schema separa los archivos de cada tenant y el token aleatorio hace la ruta
imposible de adivinar. Los nombres ya guardados no se tocan.
"""
import os
import secrets

from django.db import connection
from django.utils.deconstruct import deconstructible


@deconstructible
class TenantUploadTo:
    """Callable de ``upload_to`` serializable en migraciones.

    ``schema`` fija el schema (p. ej. ``'public'`` para activos de plataforma
    como el logo del tenant); sin él se usa el schema activo al subir.
    """

    def __init__(self, prefix, schema=None):
        self.prefix = prefix.strip('/')
        self.schema = schema

    def __call__(self, instance, filename):
        schema = self.schema or connection.schema_name
        token = secrets.token_urlsafe(16)
        return f'{schema}/{self.prefix}/{token}/{os.path.basename(filename)}'


def tenant_upload_to(prefix, schema=None):
    """``upload_to=tenant_upload_to('customer_documents')``."""
    return TenantUploadTo(prefix, schema=schema)
