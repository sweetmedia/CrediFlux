"""
URL Configuration for CrediFlux project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenVerifyView
from apps.billing.webhooks import NexConnectWebhookView
from apps.users.lockout import ratelimit_admin_login
from apps.core.media_views import SignedMediaView
from apps.users.views import CustomConfirmEmailView, TenantAwareTokenRefreshView

# Swagger/OpenAPI configuration
schema_view = get_schema_view(
    openapi.Info(
        title="CrediFlux API",
        default_version='v1',
        description="API Documentation for CrediFlux SaaS Platform",
        terms_of_service="https://www.crediflux.com/terms/",
        contact=openapi.Contact(email="contact@crediflux.com"),
        license=openapi.License(name="Proprietary License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Login del admin con límite de intentos (antes de que admin.site.urls construya las rutas)
ratelimit_admin_login()

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # Email confirmation link (allauth builds it from the 'account_confirm_email' URL name)
    re_path(
        r'^api/auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$',
        CustomConfirmEmailView.as_view(),
        name='account_confirm_email'
    ),

    # Authentication: only JWT refresh/verify. Login, password and registration
    # live in /api/tenants/login/, /api/users/auth/* and /api/tenants/register/.
    path('api/auth/token/refresh/', TenantAwareTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API endpoints
    path('api/', include('apps.core.urls')),
    path('api/loans/', include('apps.loans.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/tenants/', include('apps.tenants.urls')),
    path('api/communications/', include('apps.communications.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/billing/', include('apps.billing.urls')),
    path('api/cashbox/', include('apps.cashbox.urls')),
    path('api/ai/', include('apps.ai.urls')),

    # Archivos privados: sólo por URL firmada (no se sirve MEDIA_ROOT)
    path('media/s/<str:signed>/', SignedMediaView.as_view(), name='signed-media'),

    # Webhooks (públicos; autenticados por firma)
    path('api/webhooks/nexconnect/<slug:schema_name>/', NexConnectWebhookView.as_view(),
         name='nexconnect-webhook'),
]

# Static en desarrollo. MEDIA_ROOT nunca se sirve: los archivos van por /media/s/<firma>/
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
