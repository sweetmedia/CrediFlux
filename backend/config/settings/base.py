"""
Base settings for CrediFlux project.
"""
import os
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
from django.templatetags.static import static
from config.settings.utils import get_sidebar_navigation

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost', cast=Csv())

# Application definition
SHARED_APPS = [
    'django_tenants',  # Must be first
    'unfold',  # Django Unfold admin - must be before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'unfold.contrib.constance',  # Unfold Constance integration
    'constance',
    'djmoney',
    'phonenumber_field',
    'django_celery_beat',

    # Core apps (shared across all tenants)
    'apps.core',
    'apps.tenants',
    'apps.users',  # User model must be shared for allauth
]

TENANT_APPS = [
    # Tenant-specific apps
    'apps.loans',
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'constance.context_processors.config',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME', default='crediflux_db'),
        'USER': config('DB_USER', default='crediflux_user'),
        'PASSWORD': config('DB_PASSWORD', default='crediflux_pass'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Multi-Tenant Configuration
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
PUBLIC_SCHEMA_NAME = 'public'
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'  # URLs accessible without tenant
TENANT_BASE_DOMAIN = config('TENANT_BASE_DOMAIN', default='localhost')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Sites framework
SITE_ID = 1

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=config('JWT_REFRESH_TOKEN_LIFETIME', default=1440, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Django Allauth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = config('FRONTEND_URL', default='http://localhost:3000') + '/login?verified=true'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = config('FRONTEND_URL', default='http://localhost:3000') + '/dashboard?verified=true'

# Backend URL for email links (used by django.contrib.sites)
BACKEND_URL = config('BACKEND_URL', default='http://localhost:8000')
# Extract protocol from BACKEND_URL
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if BACKEND_URL.startswith('https') else 'http'

# Use custom adapter to ensure email confirmation URLs use Site domain
ACCOUNT_ADAPTER = 'apps.users.adapters.CustomAccountAdapter'

# CORS Settings
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Celery Beat - Use Database Scheduler (django-celery-beat)
# This allows managing periodic tasks from the Django Admin
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Constance - Dynamic Settings
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = {
    # Company Settings
    'COMPANY_NAME': (
        config('COMPANY_NAME', default='CrediFlux'),
        'Company name displayed throughout the application',
        str
    ),
    'COMPANY_EMAIL': (
        'info@crediflux.com',
        'Primary company email address for notifications and contact',
        str
    ),
    'COMPANY_PHONE': (
        '+1-555-0100',
        'Primary company phone number',
        str
    ),
    'COMPANY_ADDRESS': (
        '123 Main St, City, Country',
        'Company physical address',
        str
    ),

    # Currency & Financial Settings
    'DEFAULT_CURRENCY': (
        config('DEFAULT_CURRENCY', default='USD'),
        'Default currency code (ISO 4217 format)',
        str
    ),
    'CURRENCY_SYMBOL': (
        '$',
        'Currency symbol to display',
        str
    ),
    'DECIMAL_PLACES': (
        2,
        'Number of decimal places for currency amounts',
        int
    ),

    # Loan Settings
    'LOAN_INTEREST_RATE': (
        10.0,
        'Default annual interest rate for new loans (%)',
        float
    ),
    'MIN_LOAN_AMOUNT': (
        100.0,
        'Minimum loan amount allowed',
        float
    ),
    'MAX_LOAN_AMOUNT': (
        100000.0,
        'Maximum loan amount allowed',
        float
    ),
    'MIN_LOAN_TERM': (
        1,
        'Minimum loan term in months',
        int
    ),
    'MAX_LOAN_TERM': (
        60,
        'Maximum loan term in months',
        int
    ),

    # Payment & Fees Settings
    'LATE_PAYMENT_FEE': (
        25.0,
        'Late payment fee amount charged after grace period',
        float
    ),
    'LATE_PAYMENT_GRACE_DAYS': (
        5,
        'Number of days grace period before charging late fee',
        int
    ),
    'PAYMENT_REMINDER_DAYS': (
        3,
        'Days before due date to send payment reminder',
        int
    ),
    'EARLY_PAYMENT_DISCOUNT': (
        0.0,
        'Discount percentage for early payments (%)',
        float
    ),

    # Notification Settings
    'ENABLE_EMAIL_NOTIFICATIONS': (
        True,
        'Enable email notifications for important events',
        bool
    ),
    'ENABLE_SMS_NOTIFICATIONS': (
        False,
        'Enable SMS notifications (requires SMS service configuration)',
        bool
    ),
    'ADMIN_EMAIL': (
        'admin@crediflux.com',
        'Email address to receive admin notifications',
        str
    ),

    # System Settings
    'MAINTENANCE_MODE': (
        False,
        'Enable maintenance mode (only admins can access)',
        bool
    ),
    'MAX_UPLOAD_SIZE_MB': (
        5,
        'Maximum file upload size in megabytes',
        int
    ),
    'SESSION_TIMEOUT_MINUTES': (
        30,
        'User session timeout in minutes',
        int
    ),

    # UI Theme Settings
    'UI_THEME': (
        'v1',
        'UI Theme version: v1 (Blue/Purple) or v2 (Green - Inter Tight)',
        str
    ),

    # DGII/RNC Database Settings
    'DGII_RNC_DATABASE_URL': (
        'https://dgii.gov.do/app/WebApps/Consultas/RNC/RNC_CONTRIBUYENTES.zip',
        'URL to download DGII RNC database ZIP file',
        str
    ),
    'DGII_RNC_CACHE_TIMEOUT_DAYS': (
        7,
        'Number of days to cache RNC database before refresh',
        int
    ),
    'DGII_RNC_AUTO_UPDATE': (
        True,
        'Automatically update RNC database on schedule',
        bool
    ),
    'DGII_RNC_UPDATE_HOUR': (
        2,
        'Hour of day (0-23) to auto-update RNC database',
        int
    ),
    'DGII_RNC_ENABLED': (
        True,
        'Enable DGII RNC validation features',
        bool
    ),
}

# Constance Fieldsets - Organize settings into groups
CONSTANCE_CONFIG_FIELDSETS = {
    'Company Information': (
        'COMPANY_NAME',
        'COMPANY_EMAIL',
        'COMPANY_PHONE',
        'COMPANY_ADDRESS',
    ),
    'Currency & Financial': (
        'DEFAULT_CURRENCY',
        'CURRENCY_SYMBOL',
        'DECIMAL_PLACES',
    ),
    'Loan Configuration': (
        'LOAN_INTEREST_RATE',
        'MIN_LOAN_AMOUNT',
        'MAX_LOAN_AMOUNT',
        'MIN_LOAN_TERM',
        'MAX_LOAN_TERM',
    ),
    'Payments & Fees': (
        'LATE_PAYMENT_FEE',
        'LATE_PAYMENT_GRACE_DAYS',
        'PAYMENT_REMINDER_DAYS',
        'EARLY_PAYMENT_DISCOUNT',
    ),
    'Notifications': (
        'ENABLE_EMAIL_NOTIFICATIONS',
        'ENABLE_SMS_NOTIFICATIONS',
        'ADMIN_EMAIL',
    ),
    'System Settings': (
        'MAINTENANCE_MODE',
        'MAX_UPLOAD_SIZE_MB',
        'SESSION_TIMEOUT_MINUTES',
        'UI_THEME',
    ),
    'DGII/RNC Database': (
        'DGII_RNC_ENABLED',
        'DGII_RNC_DATABASE_URL',
        'DGII_RNC_CACHE_TIMEOUT_DAYS',
        'DGII_RNC_AUTO_UPDATE',
        'DGII_RNC_UPDATE_HOUR',
    ),
}

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Django Unfold Admin Configuration
UNFOLD = {
    # Site Information
    "SITE_TITLE": "CrediFlux Admin",
    "SITE_HEADER": "CrediFlux",
    "SITE_URL": "/",
    "SITE_ICON": {
        "light": lambda request: static("admin/img/crediflux-icon.svg"),  # Light theme icon
        "dark": lambda request: static("admin/img/crediflux-icon.svg"),   # Dark theme icon
    },
    "SITE_LOGO": {
        "light": lambda request: static("admin/img/crediflux-logo.svg"),  # Light theme logo
        "dark": lambda request: static("admin/img/crediflux-logo-dark.svg"),   # Dark theme logo
    },
    "SITE_SYMBOL": "account_balance",

    # UI Features
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,

    # Environment Badge
    "ENVIRONMENT": "config.settings.utils.environment_callback",

    # Tenant Switcher Dropdown - Static configuration
    # "SITE_DROPDOWN": [
    #     {
    #         "icon": "business",
    #         "title": ("Main Admin (System)"),
    #         "link": "/admin/",
    #     },
    # ],

    # Dashboard Callback for dynamic content
    "DASHBOARD_CALLBACK": "config.settings.utils.dashboard_callback",

    # Sidebar Navigation
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": get_sidebar_navigation(),
    },

    # Tabs Configuration for Models
    "TABS": [
        {
            "models": [
                "loans.loan",
            ],
            "items": [
                {
                    "title": "General",
                    "link": "general",
                },
                {
                    "title": "Schedule",
                    "link": "schedule",
                },
                {
                    "title": "Payments",
                    "link": "payments",
                },
                {
                    "title": "Collateral",
                    "link": "collateral",
                },
            ],
        },
        {
            "models": [
                "loans.customer",
            ],
            "items": [
                {
                    "title": "Personal Info",
                    "link": "personal",
                },
                {
                    "title": "Contact & Address",
                    "link": "contact",
                },
                {
                    "title": "Financial",
                    "link": "financial",
                },
                {
                    "title": "Loans",
                    "link": "loans",
                },
            ],
        },
    ],
}

# Money/Currency settings
CURRENCIES = ('USD', 'EUR', 'DOP')
DEFAULT_CURRENCY = config('DEFAULT_CURRENCY', default='USD')

# Frontend URL (for email verification and password reset links)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')
