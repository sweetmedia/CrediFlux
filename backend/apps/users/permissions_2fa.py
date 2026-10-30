"""
2FA obligatoria para dueño y administradores (F2, Task 15).

Revertir un pago exige el código TOTP del dueño o de un administrador
(`verify_totp_once`), así que todo dueño (`is_tenant_owner`) y todo usuario con
rol `admin` de una financiera debe tener 2FA. Mientras no la active, la API le
responde 403 `{"detail": …, "code": "2fa_required"}` en todo salvo la lista
blanca de abajo (lo justo para cerrar sesión, renovar el token, cargar el
shell y activar la 2FA).

No aplica a superusuarios de la plataforma (sin tenant), a los demás roles, al
admin de Django (sesión, fuera de DRF) ni a una financiera con
`Tenant.require_2fa` apagado (la demo; sólo lo cambia el admin de la plataforma).

Dónde se aplica: en `APIView.perform_authentication`, que DRF llama en
`APIView.initial` justo después de crear el `Request` y antes de permisos y
throttles. Un permiso en `DEFAULT_PERMISSION_CLASSES` no bastaba: casi todas las
vistas reemplazan `permission_classes` (y con ello los permisos por defecto), y
meterlo en `CrediFluxJWTAuthentication` tampoco lo veían las vistas con otra
autenticación ni `force_authenticate`. `perform_authentication` lo heredan
todas las vistas de DRF: `APIView`, genéricas, `ViewSet` y las de función con
`@api_view` (`WrappedAPIView` es subclase de `APIView`). Ninguna vista del
proyecto lo redefine. Se instala una vez en `UsersConfig.ready()`.
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

CODE = '2fa_required'
MESSAGE = 'Activa la verificación en dos pasos para continuar.'

ANY = None  # cualquier método

# (ruta exacta, métodos permitidos o ANY). Rutas de config/urls.py y apps/users/urls.py.
ALLOWLIST = {
    '/api/users/auth/logout/': {'POST'},
    '/api/auth/token/refresh/': {'POST'},
    '/api/users/profile/': {'GET'},
    '/api/users/auth/2fa/setup/': ANY,
    '/api/users/auth/2fa/verify/': ANY,
    '/api/users/auth/2fa/backup-codes/': ANY,
    '/api/config/': {'GET'},
    '/api/tenants/settings/': {'GET'},  # marca del shell (R13)
    '/api/users/permissions/catalog/': {'GET'},
}

SAFE_EXTRA = {'HEAD', 'OPTIONS'}


def requires_2fa_setup(user) -> bool:
    """¿Es dueño o admin de una financiera y todavía no tiene 2FA?"""
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'tenant_id', None) is None:  # superusuario de la plataforma
        return False
    privileged = getattr(user, 'is_tenant_owner', False) or getattr(user, 'role', None) == 'admin'
    if not privileged or getattr(user, 'is_2fa_enabled', False):
        return False
    return getattr(user.tenant, 'require_2fa', True)


def is_allowlisted(request) -> bool:
    path = request.path_info or request.path
    if path not in ALLOWLIST:
        return False
    methods = ALLOWLIST[path]
    if methods is ANY:
        return True
    method = request.method.upper()
    if method in SAFE_EXTRA and 'GET' in methods:
        return True
    return method in methods


def two_factor_required():
    return PermissionDenied({'detail': MESSAGE, 'code': CODE})


def enforce_2fa_for_privileged(request) -> None:
    """Lanza 403 `2fa_required` si el usuario autenticado debe activar la 2FA."""
    if requires_2fa_setup(request.user) and not is_allowlisted(request):
        raise two_factor_required()


def install() -> None:
    """Envuelve `APIView.perform_authentication` (idempotente)."""
    if getattr(APIView.perform_authentication, '_require_2fa', False):
        return
    original = APIView.perform_authentication

    def perform_authentication(self, request):
        original(self, request)  # autentica (request.user)
        enforce_2fa_for_privileged(request)

    perform_authentication._require_2fa = True
    perform_authentication.__wrapped__ = original
    APIView.perform_authentication = perform_authentication
