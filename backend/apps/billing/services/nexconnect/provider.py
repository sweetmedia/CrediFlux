"""
``NexConnectProvider``: estrategia e-CF que emite vía la API de NexConnect.

NexConnect asigna el e-NCF, firma y envía a la DGII; CrediFlux solo manda los
datos de la factura y sigue el estado. El id de la factura en NexConnect se
guarda en ``Invoice.dgii_response['id']`` (junto a ``provider='nexconnect'``).
"""
import base64
import binascii
import logging

from django.utils import timezone

from ...models import ECFSubmission
from ..ecf_provider import ECFProvider, ECFProviderError
from . import mapping
from .client import NexConnectClient, NexConnectError
from .credentials import NexConnectCredentialsError, credentials_for_tenant

logger = logging.getLogger(__name__)

PROVIDER_KEY = 'nexconnect'

# Estados locales desde los que se puede emitir.
EMITTABLE_STATUSES = {'draft', 'generated'}


def nexconnect_invoice_id(invoice):
    """Id de la factura en NexConnect, o None si nunca se emitió por NexConnect."""
    data = invoice.dgii_response or {}
    if isinstance(data, dict) and data.get('provider') == PROVIDER_KEY:
        return data.get('id')
    return None


class NexConnectProvider(ECFProvider):

    def __init__(self, tenant, client: NexConnectClient = None):
        self.tenant = tenant
        self.environment = getattr(tenant, 'dgii_environment', 'testecf') or 'testecf'
        self._client = client

    @property
    def client(self) -> NexConnectClient:
        if self._client is None:
            try:
                self._client = NexConnectClient(credentials_for_tenant(self.tenant))
            except NexConnectCredentialsError as e:
                raise ECFProviderError(str(e)) from e
        return self._client

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def _log(self, invoice, action, *, status='', body=None, http_status=None, error=''):
        return ECFSubmission.objects.create(
            invoice=invoice,
            action=action,
            environment=self.environment,
            trackid=(body or {}).get('dgii_tracking_id') or '',
            response_status=status,
            response_body=body,
            http_status_code=http_status,
            error_message=error,
        )

    def _apply(self, invoice, data: dict, update_fields: list):
        """Vuelca la respuesta de NexConnect sobre la factura local."""
        nx_status = (data.get('status') or '').lower()
        previous = invoice.dgii_response if isinstance(invoice.dgii_response, dict) else {}
        invoice.dgii_response = {**previous, **mapping.slim_response(data), 'provider': PROVIDER_KEY}
        invoice.dgii_status = nx_status
        invoice.status = mapping.local_status(nx_status, invoice.status)
        invoice.dgii_trackid = data.get('dgii_tracking_id') or invoice.dgii_trackid or ''
        update_fields += ['dgii_response', 'dgii_status', 'status', 'dgii_trackid']
        invoice.save(update_fields=update_fields + ['updated_at'])

    # ------------------------------------------------------------------
    # ECFProvider
    # ------------------------------------------------------------------

    def submit_invoice(self, invoice) -> dict:
        existing_id = nexconnect_invoice_id(invoice)
        if existing_id:
            raise ECFProviderError(
                f'La factura ya fue emitida en NexConnect ({invoice.encf_number}); consulte su estado'
            )
        if invoice.status not in EMITTABLE_STATUSES:
            raise ECFProviderError(
                f'No se puede emitir una factura en estado "{invoice.get_status_display()}"'
            )

        try:
            payload = mapping.build_invoice_payload(invoice)
        except ValueError as e:
            raise ECFProviderError(str(e)) from e

        client = self.client
        try:
            data = client.create_invoice(payload, mapping.idempotency_key_for(invoice))
        except NexConnectError as e:
            message = str(e)
            if e.status_code == 409:
                message = (
                    'NexConnect ya recibió esta factura con otros datos (conflicto de '
                    'idempotencia). Revise la factura antes de reintentar.'
                )
            elif e.code == 'clave_de_pruebas':
                message = 'La API key de pruebas no puede emitir sobre un emisor de producción'
            self._log(invoice, 'submit', status='error', body=e.payload,
                      http_status=e.status_code, error=message)
            raise ECFProviderError(message) from e

        invoice.encf_number = data.get('ncf') or invoice.encf_number
        invoice.security_code = (data.get('codigo_seguridad') or invoice.security_code or '')[:6]
        invoice.dgii_submitted_at = timezone.now()
        update_fields = ['encf_number', 'security_code', 'dgii_submitted_at']
        signed_b64 = data.get('xml_signed_b64')
        if signed_b64:
            try:
                invoice.signed_xml = base64.b64decode(signed_b64).decode('utf-8')
                update_fields.append('signed_xml')
            except (binascii.Error, UnicodeDecodeError):
                logger.warning('xml_signed_b64 inválido para factura %s', invoice.id)
        self._apply(invoice, data, update_fields)
        self._log(invoice, 'submit', status=invoice.dgii_status,
                  body=mapping.slim_response(data), http_status=201)

        return {
            'trackid': invoice.dgii_trackid,
            'status': invoice.dgii_status,
            'ncf': invoice.encf_number,
            'message': 'Emitido vía NexConnect; el envío a la DGII sigue en segundo plano',
            'nexconnect_id': data.get('id'),
            'raw_response': mapping.slim_response(data),
        }

    def query_status(self, invoice) -> dict:
        nx_id = nexconnect_invoice_id(invoice)
        if not nx_id:
            raise ECFProviderError('La factura no ha sido emitida por NexConnect')

        try:
            data = self.client.get_invoice_status(nx_id)
        except NexConnectError as e:
            self._log(invoice, 'query_status', status='error', body=e.payload,
                      http_status=e.status_code, error=str(e))
            raise ECFProviderError(str(e)) from e

        self._apply(invoice, data, [])
        self._log(invoice, 'query_status', status=invoice.dgii_status,
                  body=mapping.slim_response(data), http_status=200)
        return {
            'status': invoice.dgii_status,
            'ncf': invoice.encf_number,
            'is_final': invoice.dgii_status not in mapping.PENDING_STATUSES,
            'dgii_response': mapping.slim_response(data),
        }

    def cancel_invoice(self, invoice, reason: str) -> dict:
        raise ECFProviderError(
            'En NexConnect un e-CF se anula emitiendo una Nota de Crédito (E34); aún no implementado'
        )

    def test_connection(self) -> dict:
        try:
            org = self.client.me()
        except ECFProviderError as e:
            return {'provider': 'NexConnect', 'status': 'not_configured', 'error': str(e)}
        except NexConnectError as e:
            return {
                'provider': 'NexConnect',
                'status': 'error' if e.status_code else 'offline',
                'http_code': e.status_code,
                'error': str(e),
            }
        return {
            'provider': 'NexConnect',
            'environment': self.environment,
            'status': 'online',
            'organization': org.get('legal_name'),
            'test_key': self.client.credentials.is_test_key,
        }
