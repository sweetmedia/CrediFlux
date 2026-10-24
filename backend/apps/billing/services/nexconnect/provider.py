"""
``NexConnectProvider``: estrategia e-CF que emite vía la API de NexConnect.

NexConnect asigna el e-NCF, firma y envía a la DGII; CrediFlux solo manda los
datos de la factura y sigue el estado. El id de la factura en NexConnect se
guarda en ``Invoice.dgii_response['id']`` (junto a ``provider='nexconnect'``).
"""
import base64
import binascii
import logging

from django.db import transaction
from django.utils import timezone

from ...models import ECFSubmission, Invoice, InvoiceItem
# Estados emitibles y anulables: los mismos guardas que el resto de proveedores.
from ..ecf_provider import CANCELLABLE_STATUSES, EMITTABLE_STATUSES, ECFProvider, ECFProviderError
from . import mapping
from .client import NexConnectClient, NexConnectError
from .credentials import NexConnectCredentialsError, credentials_for_tenant

logger = logging.getLogger(__name__)

PROVIDER_KEY = 'nexconnect'


# Una NC de anulación que terminó así ya no cuenta: se puede intentar otra.
DEAD_NOTE_STATUSES = {'rejected', 'cancelled'}

CREDIT_NOTE_TYPE = '34'


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
        if (str(invoice.ecf_type) == CREDIT_NOTE_TYPE and invoice.reference_invoice_id
                and invoice.status in CANCELLABLE_STATUSES):
            self._mark_reference_cancelled(invoice)

    # ------------------------------------------------------------------
    # Notas de crédito (E34)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_cancellation_note(note, reference) -> bool:
        return mapping.credit_note_indicator(
            list(note.items.all()), list(reference.items.all()),
        ) == mapping.INDICADOR_NC_ANULACION

    def _mark_reference_cancelled(self, note):
        """La E34 de anulación quedó aceptada: la original pasa a anulada.

        NexConnect también manda ``invoice.cancelled`` de la original (webhook);
        esto cubre el polling, que no vuelve a consultar facturas ya aceptadas.
        """
        original = note.reference_invoice
        if original is None or original.status == 'cancelled':
            return
        if not self._is_cancellation_note(note, original):
            return
        previous = original.dgii_response if isinstance(original.dgii_response, dict) else {}
        original.dgii_response = {**previous, 'cancelled_by_ncf': note.encf_number}
        original.status = 'cancelled'
        original.dgii_status = 'cancelled'
        original.save(update_fields=['dgii_response', 'dgii_status', 'status', 'updated_at'])
        self._log(original, 'cancel', status='cancelled',
                  body={'nota_credito': note.encf_number, 'nota_credito_id': str(note.id)})

    def _live_cancellation_note(self, original):
        """La E34 de anulación de ``original`` que sigue viva, si la hay."""
        candidates = (
            Invoice.objects
            .filter(reference_invoice=original, ecf_type=CREDIT_NOTE_TYPE)
            .exclude(status__in=DEAD_NOTE_STATUSES)
            .order_by('created_at')
        )
        for note in candidates:
            if self._is_cancellation_note(note, original):
                return note
        return None

    @staticmethod
    def _credit_note_buyer(original):
        """Comprador de la E34: el de la original o, si no tenía, el cliente.

        NexConnect exige comprador en toda E34. Si la original lo identificaba,
        NexConnect usa el de la original firmada e ignora este; si era una E32 de
        consumo anónima, este es el que sale en la nota.
        """
        rnc, name = original.comprador_rnc, original.comprador_razon_social
        if (not rnc or not name) and original.customer_id:
            customer = original.customer
            rnc = rnc or ''.join(ch for ch in (customer.id_number or '') if ch.isdigit())[:11]
            name = name or customer.get_full_name()
        return rnc or '', (name or '')[:255]

    @classmethod
    def _build_cancellation_note(cls, original, reason: str):
        """E34 local que acredita la original completa (mismas líneas)."""
        comprador_rnc, comprador_razon_social = cls._credit_note_buyer(original)
        note = Invoice.objects.create(
            ecf_type=CREDIT_NOTE_TYPE,
            reference_invoice=original,
            customer_id=original.customer_id,
            loan_id=original.loan_id,
            payment_id=original.payment_id,
            emisor_rnc=original.emisor_rnc,
            emisor_razon_social=original.emisor_razon_social,
            comprador_rnc=comprador_rnc,
            comprador_razon_social=comprador_razon_social,
            issue_date=timezone.localdate(),
            # NexConnect solo acepta la E34 al contado.
            payment_method='01',
            subtotal=original.subtotal,
            total_itbis=original.total_itbis,
            total_discount=original.total_discount,
            total=original.total,
            status='draft',
            notes=f'Anulación de {original.encf_number}: {reason}'[:mapping.CANCELLATION_REASON_MAX],
        )
        InvoiceItem.objects.bulk_create([
            InvoiceItem(
                invoice=note,
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
                itbis_rate=item.itbis_rate,
                itbis_amount=item.itbis_amount,
                total=item.total,
            )
            for item in original.items.all().order_by('line_number')
        ])
        return note

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
        """Anula un e-CF emitiendo una Nota de Crédito (E34) por el total.

        Idempotente: si ya hay una E34 de anulación viva para la factura no se
        crea otra; si quedó en borrador (falló el envío) se reintenta con el
        mismo Idempotency-Key. La original pasa a ``cancelled`` cuando la E34
        queda aceptada (webhook o polling), no al emitirla.
        """
        reason = (reason or '').strip()
        if not reason:
            raise ECFProviderError('Indique el motivo de la anulación')
        if str(invoice.ecf_type) == CREDIT_NOTE_TYPE:
            raise ECFProviderError(
                'Una nota de crédito no se anula con otra; emita una nota de débito (E33)'
            )
        if not nexconnect_invoice_id(invoice):
            raise ECFProviderError('La factura no ha sido emitida por NexConnect')
        if invoice.status == 'cancelled':
            raise ECFProviderError(f'La factura {invoice.encf_number} ya está anulada')
        if invoice.status not in CANCELLABLE_STATUSES:
            raise ECFProviderError(
                f'Solo se puede anular una factura aceptada por la DGII '
                f'(estado actual: "{invoice.get_status_display()}")'
            )

        with transaction.atomic():
            # Candado sobre la original: dos anulaciones simultáneas no crean dos E34.
            original = Invoice.objects.select_for_update().get(pk=invoice.pk)
            note = self._live_cancellation_note(original)
            created = note is None
            if created:
                note = self._build_cancellation_note(original, reason)

        if nexconnect_invoice_id(note):
            return {
                'status': note.dgii_status,
                'ncf': note.encf_number,
                'credit_note_id': str(note.id),
                'created': False,
                'message': f'La anulación ya está en curso con la nota de crédito {note.encf_number}',
            }

        result = self.submit_invoice(note)
        self._log(invoice, 'cancel', status=note.dgii_status,
                  body={'nota_credito': note.encf_number, 'nota_credito_id': str(note.id),
                        'motivo': reason})
        return {
            'status': note.dgii_status,
            'ncf': note.encf_number,
            'credit_note_id': str(note.id),
            'created': created,
            'message': (f'Nota de crédito {note.encf_number} emitida; la factura queda anulada '
                        f'cuando la DGII la acepte'),
            'nexconnect_id': result.get('nexconnect_id'),
        }

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
