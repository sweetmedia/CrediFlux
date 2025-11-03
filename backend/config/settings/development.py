"""
Development settings for CrediFlux project.
"""
from .base import *

DEBUG = True

# Add development-only apps
INSTALLED_APPS += [
    # 'debug_toolbar',  # Temporarily disabled due to namespace issue
    'django_extensions',
]

# Add development middleware
MIDDLEWARE += [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',  # Temporarily disabled
]

# Debug Toolbar Configuration
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Email backend for development - Using MailHog
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=1025, cast=int)
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@crediflux.local')

# Disable password validation in development
AUTH_PASSWORD_VALIDATORS = []

# Logging
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Swagger settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
}
