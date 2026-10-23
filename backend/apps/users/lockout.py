"""
Límite de intentos de login por cuenta y por IP, y validación de fortaleza de contraseñas.

Flujo en los serializers de login:
    check_and_count(email, request)   # antes de authenticate(): lanza si ya se alcanzó el límite
    register_failure(email, request)  # tras un authenticate() fallido
    reset(email)                      # tras un authenticate() exitoso

El contador por IP no se reinicia con un login exitoso (si no, una cuenta propia
válida serviría para seguir probando contraseñas ajenas); caduca con la ventana.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

LOGIN_FAIL_LIMIT = 5
LOGIN_FAIL_WINDOW = 300  # segundos

LOCKOUT_MESSAGE = 'Demasiados intentos. Intenta de nuevo en unos minutos.'


def _email_key(email):
    return f'login_fail:{(email or "").strip().lower()}'


def _ip_key(request):
    ip = request.META.get('REMOTE_ADDR', '') if request is not None else ''
    return f'login_fail_ip:{ip}'


def _keys(email, request):
    return (_email_key(email), _ip_key(request))


def check_and_count(email, request):
    """Lanza ValidationError si la cuenta o la IP ya alcanzaron el límite de fallos.

    El mensaje es el mismo exista o no la cuenta.
    """
    counts = cache.get_many(_keys(email, request))
    if any((value or 0) >= LOGIN_FAIL_LIMIT for value in counts.values()):
        raise serializers.ValidationError(LOCKOUT_MESSAGE)


def register_failure(email, request):
    """Suma un fallo a los contadores de la cuenta y de la IP (ventana de LOGIN_FAIL_WINDOW)."""
    for key in _keys(email, request):
        cache.add(key, 0, LOGIN_FAIL_WINDOW)
        try:
            cache.incr(key)
        except ValueError:
            # La clave caducó entre add e incr: arranca de nuevo la ventana.
            cache.set(key, 1, LOGIN_FAIL_WINDOW)


def reset(email):
    """Borra el contador de fallos de la cuenta (tras un login correcto)."""
    cache.delete(_email_key(email))


def validate_strength(password, user=None):
    """Aplica AUTH_PASSWORD_VALIDATORS y traduce el error al formato de DRF."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))


def ratelimit_admin_login():
    """Envuelve `admin.site.login` con django-ratelimit (5 POST por usuario cada 5 min).

    Idempotente: lo llaman `config/urls.py` y `config/urls_public.py` antes de incluir
    `admin.site.urls`. Al bloquear lanza `Ratelimited` (PermissionDenied) → 403.
    """
    from django.contrib import admin
    from django_ratelimit.decorators import ratelimit

    if getattr(admin.site.login, '_crediflux_ratelimited', False):
        return
    limited = ratelimit(key='post:username', rate='5/5m', method='POST', block=True)(admin.site.login)
    limited._crediflux_ratelimited = True
    admin.site.login = limited
