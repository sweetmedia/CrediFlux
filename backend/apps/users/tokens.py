"""
Emisión y revocación de JWT ligados al estado de la credencial.

Cada refresh lleva el claim `pwd_ts` (segundos de `user.password_changed_at`);
el access derivado lo hereda. Mover `password_changed_at` invalida todos los
tokens emitidos antes (lo comprueban `CrediFluxJWTAuthentication` y la vista de
refresh), y además se ponen en lista negra los refresh pendientes.

También vive aquí el generador de los enlaces de verificación de correo
(`email_verification_token`), separado del de reset de contraseña.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

PWD_TS_CLAIM = 'pwd_ts'


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token de `/verify-email`: sólo verifica el correo y sólo una vez.

    `key_salt` propio: un token de verificación no vale como token de reset
    (`default_token_generator`) ni al revés. `email_verified` entra en el hash: al
    verificar, el token deja de valer. Vence con `PASSWORD_RESET_TIMEOUT`, como el de reset.
    """

    key_salt = 'apps.users.tokens.EmailVerificationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        return f'{super()._make_hash_value(user, timestamp)}{user.email_verified}'


email_verification_token = EmailVerificationTokenGenerator()


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
