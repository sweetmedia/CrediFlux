"""
Cliente HTTP de la API e-CF de NexConnect (``/v1/*``).

Contrato (OpenAPI en ``GET /v1/schema``):
- Auth: ``Authorization: Bearer nxc_{live|test|platform}_…``.
- ``POST /v1/invoices`` → 201 (o 200 si es un reintento idempotente) con la
  factura ya firmada y con e-NCF; el envío a la DGII es asíncrono.
- ``GET /v1/invoices/{id}/status`` → estado ligero.
- Errores: ``{"detail": …, "code": …}`` o el dict de validación de DRF (400).
"""
import logging
from typing import Optional

import requests
from django.conf import settings

from .credentials import NexConnectCredentials

logger = logging.getLogger(__name__)


class NexConnectError(Exception):
    """Error devuelto por NexConnect o de conexión con su API."""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 code: Optional[str] = None, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.payload = payload

    @property
    def is_retryable(self) -> bool:
        """Errores de red o 5xx: reintentar con el mismo Idempotency-Key es seguro."""
        return self.status_code is None or self.status_code >= 500


def _error_message(data) -> str:
    """Aplana la respuesta de error de NexConnect a un texto legible."""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        parts = []
        for field, errors in data.items():
            if isinstance(errors, list):
                errors = '; '.join(str(e) for e in errors)
            parts.append(f'{field}: {errors}')
        return ' | '.join(parts)
    if isinstance(data, list):
        return '; '.join(str(e) for e in data)
    return str(data)


class NexConnectClient:
    def __init__(self, credentials: NexConnectCredentials,
                 base_url: Optional[str] = None, timeout: Optional[int] = None,
                 session: Optional[requests.Session] = None):
        self.credentials = credentials
        self.base_url = (base_url or settings.NEXCONNECT_BASE_URL).rstrip('/')
        self.timeout = timeout or getattr(settings, 'NEXCONNECT_TIMEOUT', 30)
        self.session = session or requests.Session()

    def _request(self, method: str, path: str, *, json=None,
                 headers: Optional[dict] = None) -> requests.Response:
        url = f'{self.base_url}{path}'
        all_headers = {'Accept': 'application/json', **self.credentials.headers()}
        if headers:
            all_headers.update(headers)
        try:
            response = self.session.request(
                method, url, json=json, headers=all_headers, timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise NexConnectError(f'Error de conexión con NexConnect: {e}') from e

        if response.ok:
            return response

        try:
            data = response.json()
        except ValueError:
            data = {'detail': response.text[:500] or f'HTTP {response.status_code}'}
        code = data.get('code') if isinstance(data, dict) else None
        message = _error_message(data)
        logger.warning('NexConnect %s %s → %s %s', method, path, response.status_code, code or '')
        raise NexConnectError(
            f'NexConnect {response.status_code}: {message}',
            status_code=response.status_code, code=code, payload=data,
        )

    def me(self) -> dict:
        """Organización dueña de la key (sirve como prueba de autenticación)."""
        return self._request('GET', '/v1/me').json()

    def create_invoice(self, payload: dict, idempotency_key: str) -> dict:
        """Emite un e-CF. Reintentar con la misma key y el mismo cuerpo es seguro."""
        if not idempotency_key:
            raise ValueError('idempotency_key es obligatorio para emitir')
        response = self._request(
            'POST', '/v1/invoices', json=payload,
            headers={'Idempotency-Key': idempotency_key},
        )
        return response.json()

    def get_invoice(self, invoice_id: str) -> dict:
        return self._request('GET', f'/v1/invoices/{invoice_id}').json()

    def get_invoice_status(self, invoice_id: str) -> dict:
        return self._request('GET', f'/v1/invoices/{invoice_id}/status').json()
