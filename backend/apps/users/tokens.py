"""
Emisión y revocación de JWT ligados al estado de la credencial.

Cada refresh lleva el claim `pwd_ts` (segundos de `user.password_changed_at`);
el access derivado lo hereda. Mover `password_changed_at` invalida todos los
tokens emitidos antes (lo comprueban `CrediFluxJWTAuthentication` y la vista de
refresh), y además se ponen en lista negra los refresh pendientes.
"""
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

PWD_TS_CLAIM = 'pwd_ts'


def password_timestamp(user) -> int:
    """Valor de `pwd_ts` vigente para `user`."""
    return int(user.password_changed_at.timestamp())


def issue_tokens(user) -> RefreshToken:
    """RefreshToken para `user` con `pwd_ts`; `refresh.access_token` lo hereda."""
    refresh = RefreshToken.for_user(user)
    refresh[PWD_TS_CLAIM] = password_timestamp(user)
    return refresh


def revoke_user_credentials(user) -> None:
    """Invalida todos los JWT emitidos hasta ahora para `user`."""
    # `set_password` ya mueve el sello; aquí se vuelve a mover para cubrir las
    # revocaciones sin cambio de contraseña (p. ej. desactivar el tenant).
    user.stamp_password_change()
    user.save(update_fields=['password_changed_at'])

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
