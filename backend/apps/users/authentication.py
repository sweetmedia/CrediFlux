"""
Autenticación JWT que exige que el token siga vigente para la credencial.
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .tokens import PWD_TS_CLAIM, password_timestamp


def token_revoked():
    return AuthenticationFailed('Token revocado.', code='token_revoked')


class CrediFluxJWTAuthentication(JWTAuthentication):
    """JWTAuthentication + `pwd_ts` igual al `password_changed_at` del usuario.

    Un token sin `pwd_ts` (emitido antes de esta regla), con un `pwd_ts`
    distinto o de un usuario inactivo se rechaza como revocado (401).
    """

    def get_user(self, validated_token):
        if PWD_TS_CLAIM not in validated_token:
            raise token_revoked()
        try:
            user = super().get_user(validated_token)  # usuario existente y activo
        except AuthenticationFailed as exc:
            if exc.get_codes() == 'user_inactive':
                raise token_revoked() from exc
            raise
        if validated_token[PWD_TS_CLAIM] != password_timestamp(user):
            raise token_revoked()
        return user
