"""
Public URLs - accessible without tenant context.

These URLs are available on the public schema and don't require
a tenant to be set. Used for tenant registration, login, and health checks.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from apps.communications.webhooks.views import WhatsAppWebhookView

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

urlpatterns = [
    # Admin (for system administration)
    path('admin/', admin.site.urls),

    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),

    # API endpoints
    path('api/', include('apps.core.urls')),
    path('api/tenants/', include('apps.tenants.urls')),
    path('api/users/', include('apps.users.urls')),

    # Webhooks (public, no authentication)
    path('api/webhooks/whatsapp/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
