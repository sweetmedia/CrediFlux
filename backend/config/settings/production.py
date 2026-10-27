"""
Production settings for CrediFlux project.
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *

if not DATABASES['default'].get('PASSWORD'):
    raise ImproperlyConfigured('DB_PASSWORD or DATABASE_URL is required')

# Sin clave propia, los secretos cifrados en BD dependen de SECRET_KEY: rotarla los perdería.
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured('FIELD_ENCRYPTION_KEY is required in production')

DEBUG = False

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# AWS S3 Configuration (if using S3 for static/media files)
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3:
    # S3 settings
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_LOCATION = 'static'
    # Objetos privados; las URLs del storage van prefirmadas. Los archivos de
    # usuario se entregan sólo por /media/s/<firma>/ (apps.core.media_views).
    AWS_DEFAULT_ACL = 'private'
    AWS_QUERYSTRING_AUTH = True

    # Static and media files
    STATICFILES_STORAGE = 'apps.core.storage_s3.PublicStaticS3Storage'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'

# Sentry Configuration (Error tracking)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        # Datos de prestatarios: sin cabeceras, cookies ni usuario en los eventos salvo que se pida.
        send_default_pii=config('SENTRY_SEND_PII', default=False, cast=bool),
        environment=config('SENTRY_ENVIRONMENT', default='production'),
    )

# En contenedores el log va a stdout (docker logs). El handler 'file' de base apunta a un
# directorio que la imagen no tiene y haría fallar django.setup(); ningún logger lo usa.
LOGGING['handlers'].pop('file', None)