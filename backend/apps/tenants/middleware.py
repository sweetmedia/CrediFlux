"""
Middleware for tenant access control.
Ensures users can only access tenants they have permission to access.
"""
from functools import lru_cache

from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponseNotFound, JsonResponse
from django.utils.module_loading import import_string
from rest_framework.exceptions import AuthenticationFailed

from apps.core.permissions import TenantMatches, user_matches_tenant

ADMIN_AUTH_PATHS = ('/admin/login/', '/admin/logout/')


@lru_cache(maxsize=1)
def _jwt_authentication_class():
    """Primera clase JWT de DEFAULT_AUTHENTICATION_CLASSES (la que usa DRF)."""
    for path in settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', []):
        if 'JWT' in path.rsplit('.', 1)[-1]:
            return import_string(path)
    return None


def _bearer_user(request):
    """Usuario del JWT `Authorization: Bearer`, o None si no hay uno válido.

    Un token ausente o inválido no se rechaza aquí: DRF responde 401 después.
    """
    if not request.META.get('HTTP_AUTHORIZATION'):
        return None
    auth_class = _jwt_authentication_class()
    if auth_class is None:
        return None
    try:
        result = auth_class().authenticate(request)
    except AuthenticationFailed:
        return None
    return result[0] if result else None


class TenantAccessControlMiddleware:
    """
    Middleware to control tenant access based on user permissions.

    Rules:
    - Every authenticated credential on the request (session and/or JWT
      bearer) must belong to the host's tenant; platform superusers with
      tenant=None are valid on any host. Both are checked because DRF prefers
      the bearer over the session, so a matching session must not cover a
      foreign token. The JWT check lives here, and not only in the DRF
      `TenantMatches` default permission, because many views declare their own
      `permission_classes` and would skip the default.
    - Only staff users can access /admin/.
    - Anonymous requests pass through (login, webhooks, public signing...).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ADMIN_AUTH_PATHS:
            return self.get_response(request)

        principals = []
        if request.user.is_authenticated:
            principals.append(request.user)
        bearer_user = _bearer_user(request)
        if bearer_user is not None:
            principals.append(bearer_user)

        tenant = getattr(request, 'tenant', None)
        if any(not user_matches_tenant(user, tenant) for user in principals):
            if request.path.startswith('/api/'):
                return JsonResponse({'detail': TenantMatches.message}, status=403)
            return HttpResponseForbidden(TenantMatches.message)

        if request.user.is_authenticated and request.path.startswith('/admin/'):
            # Superusers and staff can access admin
            if request.user.is_superuser or request.user.is_staff:
                return self.get_response(request)

            # Non-staff users cannot access admin
            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>You don't have permission to access the admin panel.</p>"
                "<p>Only staff users can access this area.</p>"
            )

        return self.get_response(request)


class PendingTenantMiddleware:
    """
    Un tenant con registro pendiente (sin schema) no sirve peticiones en su dominio: 404.

    Va justo después de TenantMainMiddleware. Sin schema, el search_path del tenant caería
    en las tablas del schema público.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant is not None and getattr(tenant, 'provisioning_pending', False):
            if request.path.startswith('/api/'):
                return JsonResponse({'detail': 'No encontrado.'}, status=404)
            return HttpResponseNotFound()
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
