"""Entrega de archivos privados por URL firmada (``/media/s/<firma>/``)."""
import mimetypes
import os

from django.conf import settings
from django.core import signing
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .media import PUBLIC_SCHEMA, unsign_media

DEFAULT_MAX_AGE = 3600
INLINE_CONTENT_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'application/pdf'}
# Activos de plataforma que se firman con schema `public` (el logo del tenant);
# `tenants/logos/` es la ruta antigua del logo, anterior a `public/tenant_logos/`.
PUBLIC_PREFIXES = ('public/', 'tenants/logos/')


def _quiet(status):
    """Respuesta sin cuerpo que Django no registra (la ruta lleva la firma)."""
    response = HttpResponse(status=status)
    response._has_been_logged = True
    return response


class SignedMediaView(APIView):
    """Sirve un archivo del ``default_storage`` si la firma es válida y del tenant del host.

    La firma es la credencial: sin autenticación, sin permisos de DRF. Se acepta
    si el schema firmado es el del host, si es ``public`` y el archivo es un
    activo público (desde cualquier host), o si quien pide es un superusuario con sesión en el host
    público. 403 si la firma es inválida, caducó o no corresponde; 404 si el
    archivo no existe.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request, signed):
        max_age = getattr(settings, 'MEDIA_SIGNED_URL_MAX_AGE', DEFAULT_MAX_AGE)
        try:
            schema, name = unsign_media(signed, max_age=max_age)
        except signing.BadSignature:  # incluye SignatureExpired
            return _quiet(403)

        if not name or name.startswith(('/', '\\')) or '..' in name or '\x00' in name:
            return _quiet(403)
        if not self._allowed(request, schema, name):
            return _quiet(403)

        try:
            if not default_storage.exists(name):
                return _quiet(404)
            handle = default_storage.open(name, 'rb')
        except SuspiciousFileOperation:
            return _quiet(403)

        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        response = FileResponse(
            handle,
            content_type=content_type,
            as_attachment=content_type not in INLINE_CONTENT_TYPES,
            filename=os.path.basename(name),
        )
        response['Cache-Control'] = 'private, max-age=300'
        return response

    @staticmethod
    def _allowed(request, schema, name):
        tenant = getattr(request, 'tenant', None)
        host_schema = getattr(tenant, 'schema_name', None)
        if host_schema is not None and schema == host_schema:
            return True
        if schema == PUBLIC_SCHEMA and name.startswith(PUBLIC_PREFIXES):
            return True
        # Superusuario de plataforma con sesión en el host público (admin).
        user = getattr(request._request, 'user', None)
        return bool(
            host_schema == PUBLIC_SCHEMA
            and user is not None
            and user.is_authenticated
            and user.is_superuser
        )
