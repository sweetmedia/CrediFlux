"""
Límite de intentos de login por cuenta y por IP, y validación de fortaleza de contraseñas.

Flujo en los serializers de login:
    check_and_count(email, request)   # antes de authenticate(): cuenta el intento y lanza
                                      # si la cuenta o la IP superan su límite (atómico: incr)
    reset(email, request)             # tras un authenticate() exitoso

`reset` borra el contador de la cuenta y descuenta el intento exitoso del contador de
la IP: así la IP sólo acumula fallos, y un login correcto no borra fallos ajenos.
"""
import unicodedata

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.net import client_ip

LOGIN_FAIL_LIMIT = 5  # por cuenta
LOGIN_FAIL_IP_LIMIT = 20  # por IP (varias personas detrás de un mismo NAT)
LOGIN_FAIL_WINDOW = 300  # segundos

LOCKOUT_MESSAGE = 'Demasiados intentos. Intenta de nuevo en unos minutos.'


def normalize_login_identifier(value):
    """Forma canónica del usuario/correo para las claves de los límites de login.

    La misma que aplica el `UsernameField` de Django antes de autenticar (NFKC), más strip y
    casefold: todas las grafías que abren una cuenta caen en el mismo contador. La usan
    `_email_key` (contador compartido JWT/admin) y `_admin_username_key` (django-ratelimit),
    así las dos claves no pueden divergir.
    """
    return unicodedata.normalize('NFKC', value or '').strip().casefold()


def _email_key(email):
    return f'login_fail:{normalize_login_identifier(email)}'


def _ip_key(request):
    # IP real del cliente según NUM_PROXIES: detrás del proxy, REMOTE_ADDR es el proxy
    # y un contador por REMOTE_ADDR lo compartirían todos los clientes.
    return f'login_fail_ip:{client_ip(request)}'


def _increment(key, window=LOGIN_FAIL_WINDOW):
    cache.add(key, 0, window)
    try:
        return cache.incr(key)
    except ValueError:
        # La clave caducó entre add e incr: arranca de nuevo la ventana.
        cache.set(key, 1, window)
        return 1


def check_and_count(email, request):
    """Cuenta el intento y lanza ValidationError si la cuenta o la IP superan su límite.

    El mensaje es el mismo exista o no la cuenta.
    """
    email_count = _increment(_email_key(email))
    ip_count = _increment(_ip_key(request))
    if email_count > LOGIN_FAIL_LIMIT or ip_count > LOGIN_FAIL_IP_LIMIT:
        raise serializers.ValidationError(LOCKOUT_MESSAGE)


def reset(email, request=None):
    """Tras un login correcto: borra el contador de la cuenta y descuenta el intento de la IP."""
    cache.delete(_email_key(email))
    if request is not None:
        try:
            cache.decr(_ip_key(request))
        except ValueError:
            pass  # la clave ya caducó


TWO_FA_FAIL_LIMIT = 5  # códigos 2FA (TOTP o de respaldo) por usuario y ventana


def _twofa_key(user):
    return f'twofa_fail:{user.pk}'


def check_and_count_2fa(user):
    """Cuenta el intento de segundo factor antes de verificarlo y lanza si supera el límite.

    Mismo esquema atómico que el login (incr antes de verificar). Sin esto, quien tenga la
    contraseña puede pedir temp_tokens sin fin y adivinar los 6 dígitos.
    """
    if _increment(_twofa_key(user)) > TWO_FA_FAIL_LIMIT:
        raise serializers.ValidationError(LOCKOUT_MESSAGE)


def reset_2fa(user):
    """Tras un segundo factor correcto: borra el contador del usuario."""
    cache.delete(_twofa_key(user))


REVERT_AUTH_FAIL_LIMIT = 3  # códigos TOTP fallidos por autorizador de reversos
REVERT_AUTH_FAIL_WINDOW = 900  # segundos: 15 minutos de bloqueo
REVERT_AUTH_LOCK_MESSAGE = 'Autorización bloqueada 15 minutos por intentos fallidos.'


def _revert_auth_key(authorizer):
    return f'revert_auth_fail:{authorizer.pk}'


def count_authorizer_attempt(authorizer):
    """Cuenta el intento de autorizar un reverso ANTES de verificar el código y devuelve el total.

    Incr atómico antes de verificar (como el 2FA del login): dos peticiones simultáneas no
    pueden colarse por debajo del límite. Si el total supera REVERT_AUTH_FAIL_LIMIT, el
    autorizador está bloqueado (aunque el código sea bueno) hasta que caduque la ventana, que
    se reinicia a 15 minutos al alcanzar el límite y no se alarga con los intentos bloqueados
    (incr conserva el TTL). Tras un acierto,
    `reset_authorizer`; tras un fallo, el intento queda contado.
    """
    key = _revert_auth_key(authorizer)
    count = _increment(key, window=REVERT_AUTH_FAIL_WINDOW)
    if count == REVERT_AUTH_FAIL_LIMIT:
        # Al llegar al límite el bloqueo dura 15 minutos desde ese intento, no desde el primero.
        cache.touch(key, REVERT_AUTH_FAIL_WINDOW)
    return count


def authorizer_locked(authorizer):
    """¿El autorizador ya agotó sus intentos? Sólo mira, no cuenta."""
    return (cache.get(_revert_auth_key(authorizer)) or 0) >= REVERT_AUTH_FAIL_LIMIT


def reset_authorizer(authorizer):
    """Tras un código correcto: borra los fallos del autorizador."""
    cache.delete(_revert_auth_key(authorizer))


REAUTH_FAIL_LIMIT = 5  # contraseñas actuales por usuario y ventana (cambio de clave, 2FA)


def _reauth_key(user):
    # Por usuario y no por correo + IP: quien tenga el token de la víctima no la bloquea
    # en la puerta de login, sólo agota su propio presupuesto de re-autenticación.
    return f'reauth_fail:{user.pk}'


def check_reauth_password(user, password):
    """Cuenta el intento antes de verificar la contraseña actual de un usuario autenticado.

    Lanza ValidationError al superar el límite (aunque la contraseña sea correcta, hasta
    que caduque la ventana). Devuelve True si coincide (y borra el contador), False si no.
    """
    if _increment(_reauth_key(user)) > REAUTH_FAIL_LIMIT:
        raise serializers.ValidationError(LOCKOUT_MESSAGE)
    if not user.check_password(password):
        return False
    cache.delete(_reauth_key(user))
    return True


def validate_strength(password, user=None):
    """Aplica AUTH_PASSWORD_VALIDATORS y traduce el error al formato de DRF."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))


def _admin_username_key(group, request):
    """Usuario normalizado como lo hace el `UsernameField` de Django (NFKC) y sin mayúsculas.

    Sin NFKC, cada grafía compatible del correo (letras de ancho completo, etc.) abría su
    propio cubo del rate limit y autenticaba igualmente contra la misma cuenta.
    """
    return normalize_login_identifier(request.POST.get('username'))


def _admin_ip_key(group, request):
    return client_ip(request)


def ratelimit_admin_login():
    """Envuelve `admin.site.login` con django-ratelimit: 5 POST por usuario y 20 por IP cada 5 min.

    También instala el formulario con segundo factor (`admin_forms.TwoFactorAdminAuthenticationForm`),
    que además gasta el mismo contador por cuenta que la puerta JWT (`check_and_count`/`reset`).

    La IP es la del cliente según `NUM_PROXIES` (`apps.core.net.client_ip`), no `REMOTE_ADDR`.

    Idempotente: lo llaman `config/urls.py` y `config/urls_public.py` antes de incluir
    `admin.site.urls`. Al bloquear lanza `Ratelimited` (PermissionDenied) → 403.
    """
    from django.contrib import admin
    from django_ratelimit.decorators import ratelimit

    from .admin_forms import TwoFactorAdminAuthenticationForm

    # Segundo factor en la puerta del admin: sin esto, la contraseña sola abre una sesión.
    admin.site.login_form = TwoFactorAdminAuthenticationForm
    if getattr(admin.site.login, '_crediflux_ratelimited', False):
        return
    by_user = ratelimit(key=_admin_username_key, rate='5/5m', method='POST', block=True)
    by_ip = ratelimit(key=_admin_ip_key, rate='20/5m', method='POST', block=True)
    limited = by_ip(by_user(admin.site.login))
    limited._crediflux_ratelimited = True
    admin.site.login = limited
