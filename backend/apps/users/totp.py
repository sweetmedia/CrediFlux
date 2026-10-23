"""Verificación TOTP de un solo uso por paso de 30 s.

pyotp acepta el mismo código durante todo su paso; aquí se recuerda el último
paso aceptado por usuario para que un código ya usado no sirva otra vez (ni en
otro temp_token, ni para desactivar 2FA o regenerar códigos de respaldo).

Se usa `valid_window=0` (el comportamiento que tenía el código), así que el
paso que coincide es siempre el paso actual. Se rechaza cualquier código cuyo
paso sea <= al último aceptado; además `cache.add` sobre una clave por paso hace
atómica la aceptación frente a dos peticiones simultáneas con el mismo código.
Nunca se registran códigos ni secretos.
"""

import time

import pyotp
from django.core.cache import cache

TOTP_INTERVAL = 30
TOTP_STEP_TTL = 90  # segundos


def _last_step_key(user):
    return f'totp_last_step_{user.pk}'


def verify_totp_once(user, code) -> bool:
    """True si `code` es el TOTP vigente de `user` y su paso no se ha usado antes."""
    if not user.totp_secret or not code:
        return False

    now = int(time.time())
    if not pyotp.TOTP(user.totp_secret).verify(str(code), for_time=now):
        return False

    step = now // TOTP_INTERVAL
    last_step = cache.get(_last_step_key(user))
    if last_step is not None and step <= int(last_step):
        return False
    # Reserva atómica del paso: si otra petición lo tomó primero, se rechaza.
    if not cache.add(f'{_last_step_key(user)}_{step}', 1, TOTP_STEP_TTL):
        return False
    cache.set(_last_step_key(user), step, TOTP_STEP_TTL)
    return True
