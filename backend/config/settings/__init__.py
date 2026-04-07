"""
Django settings for CrediFlux project.
Import settings based on DJANGO_ENVIRONMENT variable.
"""
import os
from decouple import config

ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'development':
    from .development import *
else:
    from .base import *
