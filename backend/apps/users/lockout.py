"""
Límite de intentos de login por cuenta y por IP, y validación de fortaleza de contraseñas.

Flujo en los serializers de login:
    check_and_count(email, request)   # antes de authenticate(): cuenta el intento y lanza
                                      # si la cuenta o la IP superan su límite (atómico: incr)
    reset(email, request)             # tras un authenticate() exitoso

`reset` borra el contador de la cuenta y descuenta el intento exitoso del contador de
la IP: así la IP sólo acumula fallos, y un login correcto no borra fallos ajenos.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.core.net import client_ip

LOGIN_FAIL_LIMIT = 5  # por cuenta
LOGIN_FAIL_IP_LIMIT = 20  # por IP (varias personas detrás de un mismo NAT)
LOGIN_FAIL_WINDOW = 300  # segundos

LOCKOUT_MESSAGE = 'Demasiados intentos. Intenta de nuevo en unos minutos.'


def _email_key(email):
    return f'login_fail:{(email or "").strip().lower()}'


def _ip_key(request):
    # IP real del cliente según NUM_PROXIES: detrás del proxy, REMOTE_ADDR es el proxy
    # y un contador por REMOTE_ADDR lo compartirían todos los clientes.
    return f'login_fail_ip:{client_ip(request)}'


def _increment(key):
    cache.add(key, 0, LOGIN_FAIL_WINDOW)
    try:
        return cache.incr(key)
    except ValueError:
        # La clave caducó entre add e incr: arranca de nuevo la ventana.
        cache.set(key, 1, LOGIN_FAIL_WINDOW)
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
    """Usuario normalizado: allauth autentica sin distinguir mayúsculas en el correo."""
    return (request.POST.get('username') or '').strip().lower()


def _admin_ip_key(group, request):
    return client_ip(request)


def ratelimit_admin_login():
    """Envuelve `admin.site.login` con django-ratelimit: 5 POST por usuario y 20 por IP cada 5 min.

    También instala el formulario con segundo factor (`admin_forms.TwoFactorAdminAuthenticationForm`).

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
