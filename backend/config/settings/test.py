"""
Settings para la suite de pruebas (pytest).

Parte de `base` —no de `development`— para que las pruebas no dependan de
MailHog, django_extensions ni del logging DEBUG. Sólo cambia lo que hace la
suite rápida y determinista; la base de datos sigue siendo Postgres real
(django-tenants necesita schemas, SQLite no sirve).
"""

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["*"]

# Hash rápido: los tests crean muchos usuarios y PBKDF2 los hace lentos.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = []

# Correo en memoria: `django.core.mail.outbox` en los tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery síncrono: `.delay()` ejecuta la tarea en el mismo proceso.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Cache (y sesiones, que van en cache) en memoria: sin Redis para la suite.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "crediflux-tests",
    }
}

# Sin los throttles globales (anon/user): los tests de API hacen ráfagas de requests.
# OJO: las vistas con `throttle_classes` propias (registro de tenants, RNC, cédula,
# verify-email/send, password-reset/request) siguen limitadas con las tasas de base.py;
# sus tests limpian el cache por test y fijan la tasa con override_settings cuando
# prueban el 429.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
}

# La IA nunca sale a la red desde la suite.
AI_ENABLED = False

LOGGING["root"]["level"] = "WARNING"  # noqa: F405
