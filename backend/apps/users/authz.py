"""Resolutor de permisos por rol editable (D6).

`user_permissions(user)` devuelve los códigos del catálogo que el usuario puede ejercer:
superusuario y dueño de la financiera, todos; el resto, los de su `Role` (tenant + clave en
`User.role`). `PermissionRequired` los exige en DRF y responde 403 con `required_permission`,
que es lo que lee el frontend (lib/api/client.ts).
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models_roles import Role
from .permissions_catalog import ALL_CODES

MENSAJE_DENEGADO = 'No tienes permiso para esta acción.'


def user_permissions(user) -> frozenset:
    """Códigos de permiso del usuario. Se memoiza en `user._cf_perms`.

    DRF crea una instancia de usuario nueva por request, así que el memo no cruza requests y
    una edición del rol se ve en la siguiente. Códigos que ya no están en el catálogo se ignoran;
    un rol inexistente (borrado) no concede nada.
    """
    if user is None or not getattr(user, 'is_authenticated', False) or not user.is_active:
        return frozenset()
    memo = getattr(user, '_cf_perms', None)
    if memo is not None:
        return memo
    if user.is_superuser or getattr(user, 'is_tenant_owner', False):
        permisos = frozenset(ALL_CODES)
    else:
        codigos = Role.objects.filter(tenant_id=user.tenant_id, key=user.role).values_list(
            'permissions', flat=True
        ).first()
        permisos = frozenset(codigos or ()) & ALL_CODES
    user._cf_perms = permisos
    return permisos


def has_perm(user, code) -> bool:
    return code in user_permissions(user)


class PermissionRequired(BasePermission):
    """Exige un código del catálogo según el método HTTP o la acción del viewset.

    Se configura con `PermissionRequired.for_methods({'GET': 'customers.view', ...})` o
    `PermissionRequired.for_actions({'approve': 'loans.approve', ...})`. Lo que el mapa no
    nombra se NIEGA (método o acción desconocidos); HEAD usa el código de GET. Sin sesión
    devuelve False (DRF responde 401/403 de autenticación); sin el permiso lanza 403 con
    `{'detail', 'required_permission'}`.
    """

    method_map: dict = {}
    action_map: dict = {}

    @classmethod
    def for_methods(cls, mapa):
        return type('PermissionRequiredPorMetodo', (cls,), {'method_map': dict(mapa)})

    @classmethod
    def for_actions(cls, mapa):
        return type('PermissionRequiredPorAccion', (cls,), {'action_map': dict(mapa)})

    def _code(self, request, view):
        if self.action_map:
            return self.action_map.get(getattr(view, 'action', None))
        metodo = request.method.upper()
        if metodo == 'HEAD' and 'HEAD' not in self.method_map:
            metodo = 'GET'
        return self.method_map.get(metodo)

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        code = self._code(request, view)
        if code is not None and has_perm(user, code):
            return True
        detalle = {'detail': MENSAJE_DENEGADO}
        if code is not None:
            detalle['required_permission'] = code
        raise PermissionDenied(detalle)
