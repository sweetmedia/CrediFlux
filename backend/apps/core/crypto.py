"""
Cifrado simétrico (Fernet) para secretos guardados en DB.

Los valores cifrados llevan el prefijo ``enc:`` para distinguirlos de valores
legados en texto plano (que ``decrypt_secret`` devuelve tal cual).

La llave sale de ``settings.FIELD_ENCRYPTION_KEY`` (una llave Fernet) o, si no
está definida, se deriva de ``SECRET_KEY``.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

ENCRYPTED_PREFIX = 'enc:'


class SecretDecryptionError(Exception):
    """El valor cifrado no se pudo descifrar con la llave actual."""


def _fernet() -> Fernet:
    key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or ''
    if not key:
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def is_encrypted(value) -> bool:
    return bool(value) and str(value).startswith(ENCRYPTED_PREFIX)


def encrypt_secret(value: str) -> str:
    """Cifra ``value``. Vacío se queda vacío; lo ya cifrado no se re-cifra."""
    if not value or is_encrypted(value):
        return value or ''
    token = _fernet().encrypt(value.encode()).decode()
    return f'{ENCRYPTED_PREFIX}{token}'


def decrypt_secret(value: str) -> str:
    """Descifra ``value``. Texto plano legado se devuelve sin cambios."""
    if not value:
        return ''
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(ENCRYPTED_PREFIX):].encode()).decode()
    except InvalidToken as e:
        raise SecretDecryptionError(
            'No se pudo descifrar el secreto (¿cambió FIELD_ENCRYPTION_KEY o SECRET_KEY?)'
        ) from e
