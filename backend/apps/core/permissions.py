"""
Binding usuario <-> tenant.

Un usuario autenticado sólo puede operar en el tenant resuelto por el Host
(`request.tenant`, puesto por TenantMainMiddleware) al que pertenece. El
superusuario de plataforma (`tenant=None`) puede operar en cualquier host,
incluido el público.
"""
from rest_framework import permissions


def user_matches_tenant(user, tenant) -> bool:
    """True si `user` puede operar en `tenant` (el tenant del host)."""
    if user.is_superuser and user.tenant_id is None:
        return True
    if tenant is None or tenant.schema_name == 'public':
        return False
    return bool(
        user.tenant_id == tenant.id
        and user.is_active
        and tenant.is_active
    )


class TenantMatches(permissions.BasePermission):
    """Rechaza credenciales emitidas para un tenant distinto al del host."""

    message = 'Credenciales no válidas para esta organización.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            # Lo decide IsAuthenticated (o AllowAny en las vistas públicas).
            return True
        return user_matches_tenant(user, getattr(request, 'tenant', None))
