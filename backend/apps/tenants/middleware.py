"""
Middleware for tenant access control.
Ensures users can only access tenants they have permission to access.
"""
from django.http import HttpResponseForbidden
from django.db import connection


class TenantAccessControlMiddleware:
    """
    Middleware to control tenant access based on user permissions.

    Rules:
    - Only blocks non-staff users from accessing /admin/
    - Everything else passes through (API, static files, etc.)
    - The dropdown controls tenant visibility for staff users
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check admin access for authenticated users
        # Everything else (API, static, media, swagger) passes through
        if request.user.is_authenticated and request.path.startswith('/admin/'):
            # Skip login/logout
            if '/admin/login/' in request.path or '/admin/logout/' in request.path:
                return self.get_response(request)

            # Superusers and staff can access admin
            if request.user.is_superuser or request.user.is_staff:
                return self.get_response(request)

            # Non-staff users cannot access admin
            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>You don't have permission to access the admin panel.</p>"
                "<p>Only staff users can access this area.</p>"
            )

        # Allow everything else to pass through
        return self.get_response(request)


class TenantTimezoneMiddleware:
    """
    Activa la zona horaria del tenant del request (va justo después de
    TenantMainMiddleware, que pone `request.tenant`).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.utils import timezone

        from .timezones import tenant_zone

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return self.get_response(request)
        timezone.activate(tenant_zone(tenant))
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
