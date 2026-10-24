"""URLs firmadas para archivos privados.

Los serializers no exponen la URL directa del storage: devuelven
``/media/s/<firma>/``, que ``SignedMediaView`` sólo sirve en el host del
tenant que la emitió (o en cualquiera si el schema firmado es ``public`` y el
archivo está bajo ``public/``) y mientras no caduque
(``MEDIA_SIGNED_URL_MAX_AGE``).
"""
import base64

from django.core import signing
from django.db import connection, models
from django.urls import reverse
from rest_framework import serializers

MEDIA_SIGNER_SALT = 'media'
PUBLIC_SCHEMA = 'public'
# Primer segmento de los nombres antiguos de media, anteriores a `<schema>/<prefijo>/...`.
LEGACY_TOP_DIRS = frozenset({
    'avatars', 'billing', 'collateral_documents', 'collateral_photos', 'collector_visits',
    'contract_templates', 'contracts', 'customer_documents', 'customer_photos',
    'guarantor_documents', 'loan_contracts', 'payment_receipts', 'tenants',
})
# apps/tenants/serializers.py los reserva como nombres de tenant: un schema con uno de
# estos nombres saltaría el chequeo schema/archivo de SignedMediaView.


def _signer():
    return signing.TimestampSigner(salt=MEDIA_SIGNER_SALT)


def _b64encode(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')


def _b64decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)).decode()


def sign_media(name, schema):
    """Firma ``'<schema>|<name>'``, en base64 url-safe para que quepa en un segmento de ruta."""
    return _signer().sign(_b64encode(f'{schema}|{name}'))


def unsign_media(value, max_age):
    """Devuelve ``(schema, name)``; lanza ``BadSignature`` o ``SignatureExpired``."""
    payload = _signer().unsign(value, max_age=max_age)
    try:
        schema, name = _b64decode(payload).split('|', 1)
    except (ValueError, UnicodeDecodeError) as exc:
        raise signing.BadSignature('payload inválido') from exc
    return schema, name


def signed_media_url(name, schema):
    """Ruta firmada (``/media/s/<firma>/``) del archivo ``name`` del ``schema``."""
    return reverse('signed-media', args=[sign_media(name, schema)])


class SignedFileMixin:
    """``to_representation`` devuelve la URL firmada, o ``None`` sin archivo.

    ``schema`` fija el schema firmado; por defecto, el activo al serializar.
    Es absoluta si hay ``request`` en el contexto, como el ``FileField`` de DRF.
    La subida (``to_internal_value``) no cambia.
    """

    def __init__(self, *args, schema=None, **kwargs):
        self.schema = schema
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        name = getattr(value, 'name', None)
        if not value or not name:
            return None
        url = signed_media_url(name, self.schema or connection.schema_name)
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request is not None else url


class SignedFileField(SignedFileMixin, serializers.FileField):
    pass


class SignedImageField(SignedFileMixin, serializers.ImageField):
    pass


class SignedFilesModelSerializer(serializers.ModelSerializer):
    """ModelSerializer cuyos campos de archivo autogenerados devuelven URL firmada."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.FileField: SignedFileField,
        models.ImageField: SignedImageField,
    }
