"""
Integración con la API e-CF de NexConnect (PSFE).

- ``client``: cliente HTTP de bajo nivel (auth, errores, idempotencia).
- ``credentials``: de dónde salen las credenciales de cada tenant.
- ``mapping``: Invoice de CrediFlux ⇄ payloads/estados de NexConnect.
- ``provider``: ``NexConnectProvider``, la estrategia registrada en ``ecf_provider``.
"""
from .client import NexConnectClient, NexConnectError
from .credentials import NexConnectCredentials, credentials_for_tenant

__all__ = [
    'NexConnectClient',
    'NexConnectError',
    'NexConnectCredentials',
    'credentials_for_tenant',
]
