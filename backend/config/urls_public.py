"""
Public URLs - accessible without tenant context.

These URLs are available on the public schema and don't require
a tenant to be set. Used for tenant registration, login, and health checks.
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Tenant management (public endpoints)
    path('api/tenants/', include('apps.tenants.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
