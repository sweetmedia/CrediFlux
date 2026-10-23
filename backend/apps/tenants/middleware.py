"""
Middleware for tenant access control.
Ensures users can only access tenants they have permission to access.
"""
from django.http import HttpResponseForbidden, JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.permissions import TenantMatches, user_matches_tenant


def _bearer_user(request):
    """Usuario del JWT `Authorization: Bearer`, o None si no hay uno válido.

    Un token ausente o inválido no se rechaza aquí: DRF responde 401 después.
    """
    if not request.META.get('HTTP_AUTHORIZATION'):
        return None
    try:
        result = JWTAuthentication().authenticate(request)
    except AuthenticationFailed:
        return None
    return result[0] if result else None


class TenantAccessControlMiddleware:
    """
    Middleware to control tenant access based on user permissions.

    Rules:
    - An authenticated credential (session or JWT bearer) is only valid on the
      host of the user's own tenant; platform superusers with tenant=None are
      valid on any host. The JWT check lives here, and not only in the DRF
      `TenantMatches` default permission, because many views declare their own
      `permission_classes` and would skip the default.
    - Only staff users can access /admin/.
    - Anonymous requests pass through (login, webhooks, public signing...).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip login/logout
        if '/admin/login/' in request.path or '/admin/logout/' in request.path:
            return self.get_response(request)

        if request.user.is_authenticated:
            user = request.user
        else:
            user = _bearer_user(request)
            if user is None:
                return self.get_response(request)

        if not user_matches_tenant(user, getattr(request, 'tenant', None)):
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
