"""
Credenciales de NexConnect.

Hoy: una key de emisor (``nxc_{live|test}_…``) por tenant, cifrada en
``Tenant.ecf_provider_api_key``.

Mañana: key de plataforma (``nxc_platform_…``, global) + ``account_id`` por
tenant, enviado en el header ``NexConnect-Account``. Para ese cambio basta con
que ``credentials_for_tenant`` construya las credenciales de otra forma; el
cliente y el proveedor solo ven ``NexConnectCredentials.headers()``.
"""
from dataclasses import dataclass
from typing import Optional

from apps.core.crypto import decrypt_secret, encrypt_secret

ACCOUNT_HEADER = 'NexConnect-Account'


class NexConnectCredentialsError(Exception):
    """El tenant no tiene credenciales de NexConnect utilizables."""


@dataclass(frozen=True)
class NexConnectCredentials:
    api_key: str
    account_id: Optional[str] = None

    def headers(self) -> dict:
        headers = {'Authorization': f'Bearer {self.api_key}'}
        if self.account_id:
            headers[ACCOUNT_HEADER] = self.account_id
        return headers

    @property
    def is_test_key(self) -> bool:
        return self.api_key.startswith('nxc_test_')

    def __repr__(self):
        # Nunca exponer la key en logs/tracebacks.
        return f'NexConnectCredentials(api_key={self.api_key[:9]}…, account_id={self.account_id!r})'


def credentials_for_tenant(tenant) -> NexConnectCredentials:
    """Credenciales de emisor guardadas (cifradas) en el tenant."""
    api_key = decrypt_secret(getattr(tenant, 'ecf_provider_api_key', '') or '').strip()
    if not api_key:
        raise NexConnectCredentialsError('API key de NexConnect no configurada para este tenant')
    if not api_key.startswith('nxc_'):
        raise NexConnectCredentialsError('La API key de NexConnect no tiene el formato nxc_…')
    return NexConnectCredentials(api_key=api_key)


def set_tenant_api_key(tenant, api_key: str, save: bool = True):
    """Guarda la key de emisor del tenant, cifrada."""
    api_key = (api_key or '').strip()
    if api_key and not api_key.startswith('nxc_'):
        raise NexConnectCredentialsError('La API key de NexConnect no tiene el formato nxc_…')
    tenant.ecf_provider_api_key = encrypt_secret(api_key) or None
    if save:
        tenant.save(update_fields=['ecf_provider_api_key'])


def webhook_secret_for_tenant(tenant) -> str:
    """Secret HMAC (hex) del webhook del tenant, o '' si no hay webhook registrado."""
    return decrypt_secret(getattr(tenant, 'nexconnect_webhook_secret', '') or '').strip()


def set_tenant_webhook(tenant, webhook_id: str, secret_hex: str, save: bool = True):
    """Guarda el id y el secret (cifrado) del webhook registrado en NexConnect."""
    secret_hex = (secret_hex or '').strip()
    if secret_hex:
        try:
            bytes.fromhex(secret_hex)
        except ValueError:
            raise NexConnectCredentialsError('El secret del webhook no es hexadecimal')
    tenant.nexconnect_webhook_id = str(webhook_id or '')
    tenant.nexconnect_webhook_secret = encrypt_secret(secret_hex)
    if save:
        tenant.save(update_fields=['nexconnect_webhook_id', 'nexconnect_webhook_secret'])
