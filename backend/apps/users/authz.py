"""Resolutor de permisos por rol editable (D6).

`user_permissions(user)` devuelve los códigos del catálogo que el usuario puede ejercer:
superusuario y dueño de la financiera, todos; el resto, los de su `Role` (tenant + clave en
`User.role`). `PermissionRequired` los exige en DRF y responde 403 con `required_permission`,
que es lo que lee el frontend (lib/api/client.ts).
"""
import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models_roles import Role
from .permissions_catalog import ALL_CODES

logger = logging.getLogger(__name__)

MENSAJE_DENEGADO = 'No tienes permiso para esta acción.'
# Un método o acción que el mapa no nombra es un hueco de configuración, no falta de permiso (R12).
MENSAJE_NO_CONFIGURADA = 'Acción no configurada.'


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


def invalidate_permissions(user) -> None:
    """Olvida el memo de `user_permissions` en esta instancia (tras cambiarle el rol o su Role)."""
    if user is not None:
        user.__dict__.pop('_cf_perms', None)


def puede_dar_admin(user) -> bool:
    """R4: el rol `admin` sólo lo da el dueño de la financiera o el superusuario. No es un
    código: el admin tiene todos y aun así no hace admin a otros."""
    return bool(getattr(user, 'is_tenant_owner', False) or getattr(user, 'is_superuser', False))


def codigo_que_falta(user, codigos):
    """Primer código (orden alfabético) de `codigos` que `user` no tiene, o None.

    Anti-escalada al asignar roles: nadie da un rol con permisos que él mismo no tiene. Sólo
    cuentan códigos del catálogo (los demás no conceden nada). El dueño y el superusuario
    tienen todos, así que para ellos siempre es None.
    """
    faltan = (set(codigos or ()) & ALL_CODES) - user_permissions(user)
    return min(faltan) if faltan else None


def denegar(code):
    """403 con el código que falta, igual que PermissionRequired."""
    raise PermissionDenied({'detail': MENSAJE_DENEGADO, 'required_permission': code})


# `None` explícito en un mapa de ViewPermissionRequired: la acción sólo exige estar autenticado.
ABIERTO = object()
_FALTA = object()


def _sin_manejador(request, view) -> bool:
    """¿DRF responderá 405? Mismo criterio que APIView.dispatch: método fuera de
    `http_method_names` o sin manejador (en un viewset, sin acción enrutada para ese método)."""
    metodo = request.method.lower()
    return metodo not in getattr(view, 'http_method_names', ()) or not hasattr(view, metodo)


class PermissionRequired(BasePermission):
    """Exige un código del catálogo según el método HTTP o la acción del viewset.

    Se configura con `PermissionRequired.for_methods({'GET': 'customers.view', ...})` o
    `PermissionRequired.for_actions({'approve': 'loans.approve', ...})`; HEAD usa el código de
    GET. Sin sesión devuelve False (DRF responde 401/403 de autenticación); sin el permiso lanza
    403 con `{'detail', 'required_permission'}`.

    Lo que el mapa no nombra (R12): OPTIONS pasa para cualquier autenticado (sólo describe el
    esquema); cualquier otro método o acción se NIEGA con «Acción no configurada.» y sin
    `required_permission`, y deja un warning con la vista y el método/acción, para que un hueco
    del mapa no parezca falta de permiso. Un método sin manejador pasa: DRF responde 405.
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
        return _codigo_por_metodo(self.method_map, request)

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if _sin_manejador(request, view):
            return True
        code = self._code(request, view)
        if code is ABIERTO:
            return True
        if code is None:
            return self._sin_mapear(request, view)
        if has_perm(user, code):
            return True
        raise PermissionDenied({'detail': MENSAJE_DENEGADO, 'required_permission': code})

    def _sin_mapear(self, request, view):
        metodo = request.method.upper()
        if metodo == 'OPTIONS':
            return True
        accion = getattr(view, 'action', None)
        if accion != 'metadata':
            # 'metadata' es el chequeo que hace OPTIONS por cada método de escritura (DRF
            # SimpleMetadata): se niega sin ruido y el esquema omite ese método.
            logger.warning(
                'Acción no configurada en %s: método %s, acción %s',
                type(view).__name__, metodo, accion,
            )
        raise PermissionDenied({'detail': MENSAJE_NO_CONFIGURADA})


def _codigo_por_metodo(mapa, request):
    metodo = request.method.upper()
    if metodo == 'HEAD' and 'HEAD' not in mapa:
        metodo = 'GET'
    return mapa.get(metodo)


class ViewPermissionRequired(PermissionRequired):
    """Como PermissionRequired, pero el mapa vive en la vista: `permission_codes`.

    En un viewset las claves son acciones (`{'list': 'loans.view', 'approve': ...}`); en una
    APIView, métodos HTTP. Así cada vista declara su mapa completo junto a su código.

    El valor de una clave puede ser:
    * un código del catálogo: se exige;
    * `None`: la acción sólo exige sesión, sin código (p. ej. la lectura de los ajustes de la
      financiera, que el shell de la app necesita para cualquier miembro, R13). Es explícito:
      una clave ausente sigue negándose con «Acción no configurada.»;
    * un dict método → código, para una acción que atiende varios métodos con códigos
      distintos (`{'config': {'GET': 'billing.view', 'PATCH': 'billing.config'}}`); un
      método que el dict no nombra se niega como cualquier hueco del mapa.
    """

    def _code(self, request, view):
        mapa = getattr(view, 'permission_codes', None) or {}
        if hasattr(view, 'action'):
            entrada = mapa.get(view.action, _FALTA)
        else:
            entrada = _buscar(mapa, request)
        if isinstance(entrada, dict):
            entrada = _buscar(entrada, request)
        if entrada is _FALTA:
            return None
        return ABIERTO if entrada is None else entrada


def _buscar(mapa, request):
    metodo = request.method.upper()
    if metodo == 'HEAD' and 'HEAD' not in mapa:
        metodo = 'GET'
    return mapa.get(metodo, _FALTA)
