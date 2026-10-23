"""
Webhooks de NexConnect → CrediFlux (estado de facturas por push).

Contrato (docs NexConnect, ``api/concepts/webhooks``):
- ``POST`` con cuerpo JSON ``{"id": "evt_…", "type": …, "created_at": …, "data": {…}}``,
  serializado con ``sort_keys=True``.
- Header ``X-NexConnect-Signature: t={unix},v1={hex}``, donde
  ``v1 = HMAC-SHA256(bytes.fromhex(secret), f"{t}.{body}")``.
- Entrega at-least-once con reintentos (1 min … 6 h): hay que deduplicar por
  ``id`` y tolerar eventos fuera de orden.

El tenant sale de la URL (``/api/webhooks/nexconnect/<schema>/``) porque el
secret con el que se verifica la firma es por tenant. La factura sale del
evento: ``metadata.crediflux_invoice_id`` o, si no, el id de NexConnect guardado
en ``Invoice.dgii_response['id']``.

El polling (``billing.check_pending_submissions``) sigue como respaldo.
"""
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Optional

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime

from ...models import Invoice, NexConnectWebhookEvent
from . import mapping
from .provider import NexConnectProvider, nexconnect_invoice_id

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = 'X-NexConnect-Signature'
DEFAULT_TOLERANCE_SECONDS = 300

# Eventos sobre facturas que emitimos: traen ``data.object`` = la factura.
OUTBOUND_EVENTS = (
    'invoice.submitted',
    'invoice.delivered_to_receiver',
    'invoice.accepted',
    'invoice.accepted_conditional',
    'invoice.rejected',
    'invoice.receiver_rejected',
    'invoice.queued_offline',
    'invoice.cancelled',
    'invoice.commercial_approved',
    'invoice.commercial_rejected',
)

# Superficie receptora (e-CF que otros nos envían). CrediFlux no la usa: se
# acusan con 200 y se registran como ignorados.
RECEIVER_EVENTS = (
    'invoice.received',
    'invoice.received.auto_accepted',
    'invoice.received.manual_pending',
    'invoice.received.rejected',
    'invoice.received.volume_cap_warn',
    'invoice.received.volume_cap_critical',
)

ALL_EVENTS = OUTBOUND_EVENTS + RECEIVER_EVENTS

# Lo que se suscribe por defecto al registrar el webhook.
DEFAULT_SUBSCRIBED_EVENTS = OUTBOUND_EVENTS

# Resultados de ``process_event`` además de los de NexConnectWebhookEvent.
DUPLICATE = 'duplicate'


class WebhookSignatureError(Exception):
    """Firma ausente, malformada, vencida o que no coincide."""


class WebhookPayloadError(Exception):
    """El cuerpo no es un evento de NexConnect válido."""


# ----------------------------------------------------------------------
# Firma
# ----------------------------------------------------------------------

def compute_signature(secret_hex: str, timestamp, body: bytes) -> str:
    key = bytes.fromhex(secret_hex)
    signed = f'{timestamp}.'.encode() + body
    return hmac.new(key, signed, hashlib.sha256).hexdigest()


def parse_signature_header(header: str):
    """``t=…,v1=…[,v1=…]`` → (timestamp, [firmas v1])."""
    timestamp = None
    signatures = []
    for part in (header or '').split(','):
        key, sep, value = part.strip().partition('=')
        if not sep:
            continue
        if key == 't':
            try:
                timestamp = int(value)
            except ValueError:
                raise WebhookSignatureError('Timestamp de firma inválido')
        elif key == 'v1' and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise WebhookSignatureError(f'Header {SIGNATURE_HEADER} ausente o malformado')
    return timestamp, signatures


def verify_signature(secret_hex: str, header: str, body: bytes, *,
                     now: Optional[float] = None, tolerance: Optional[int] = None) -> int:
    """Verifica la firma del cuerpo crudo. Devuelve el timestamp firmado.

    Rechaza timestamps a más de ``tolerance`` segundos del reloj local (en
    cualquier sentido): es la defensa contra replay de entregas capturadas.
    """
    if not secret_hex:
        raise WebhookSignatureError('El tenant no tiene secret de webhook')
    if tolerance is None:
        tolerance = getattr(settings, 'NEXCONNECT_WEBHOOK_TOLERANCE', DEFAULT_TOLERANCE_SECONDS)
    timestamp, signatures = parse_signature_header(header)
    now = time.time() if now is None else now
    if abs(now - timestamp) > tolerance:
        raise WebhookSignatureError('Firma vencida (timestamp fuera de tolerancia)')
    expected = compute_signature(secret_hex, timestamp, body)
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise WebhookSignatureError('La firma no coincide')
    return timestamp


# ----------------------------------------------------------------------
# Evento
# ----------------------------------------------------------------------

def parse_event(body: bytes) -> dict:
    try:
        event = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise WebhookPayloadError('El cuerpo no es JSON')
    if not isinstance(event, dict):
        raise WebhookPayloadError('El evento debe ser un objeto JSON')
    event_id = event.get('id')
    if not isinstance(event_id, str) or not event_id.startswith('evt_'):
        raise WebhookPayloadError('El evento no trae un id evt_…')
    if not isinstance(event.get('type'), str) or not event['type']:
        raise WebhookPayloadError('El evento no trae type')
    if not isinstance(event.get('data'), dict):
        raise WebhookPayloadError('El evento no trae data')
    return event


def event_object(event: dict) -> dict:
    obj = (event.get('data') or {}).get('object')
    return obj if isinstance(obj, dict) else {}


def event_created_at(event: dict):
    value = event.get('created_at')
    return parse_datetime(value) if isinstance(value, str) else None


def slim_event(event: dict) -> dict:
    """El evento sin XML ni líneas, para guardarlo."""
    data = dict(event.get('data') or {})
    if isinstance(data.get('object'), dict):
        data['object'] = mapping.slim_response(data['object'])
    return {**event, 'data': data}


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def resolve_invoice(event: dict):
    """Factura local del evento → (invoice | None, motivo).

    motivo: ``'ok'``, ``'unmatched'`` o ``'mismatch'`` (la factura de la
    metadata ya está ligada a otro id de NexConnect: no se toca).
    Bloquea la fila encontrada (``select_for_update``) hasta el fin de la transacción.
    """
    obj = event_object(event)
    nx_id = str(obj.get('id') or '')
    metadata = obj.get('metadata') if isinstance(obj.get('metadata'), dict) else {}
    local_id = _as_uuid(metadata.get('crediflux_invoice_id'))
    invoices = Invoice.objects.select_for_update()

    if local_id is not None:
        invoice = invoices.filter(id=local_id).first()
        if invoice is not None:
            linked = nexconnect_invoice_id(invoice)
            if linked and nx_id and str(linked) != nx_id:
                return invoice, 'mismatch'
            return invoice, 'ok'

    if nx_id:
        invoice = invoices.filter(
            dgii_response__provider='nexconnect', dgii_response__id=nx_id,
        ).first()
        if invoice is not None:
            return invoice, 'ok'
    return None, 'unmatched'


def is_stale(invoice, nx_status: str, created_at) -> bool:
    """¿El evento es más viejo que lo que ya sabemos de la factura?

    Los reintentos pueden traer ``invoice.submitted`` después de
    ``invoice.accepted``. Se descarta si (a) es anterior al último evento
    aplicado o (b) devolvería a pendiente una factura ya en estado final
    (p. ej. porque el polling llegó antes).
    """
    previous = invoice.dgii_response if isinstance(invoice.dgii_response, dict) else {}
    last_at = parse_datetime(previous.get('webhook_event_at') or '')
    if last_at and created_at and created_at < last_at:
        return True
    current = (invoice.dgii_status or '').lower()
    if current and current not in mapping.PENDING_STATUSES and nx_status in mapping.PENDING_STATUSES:
        return True
    return False


def process_event(tenant, event: dict) -> str:
    """Aplica un evento ya verificado. Debe correr en el schema del tenant.

    Idempotente: el ``event_id`` se registra en la misma transacción que el
    cambio de la factura; si algo falla no queda registrado y el reintento de
    NexConnect lo vuelve a procesar.
    """
    event_type = event['type']
    created_at = event_created_at(event)
    obj = event_object(event)
    nx_id = str(obj.get('id') or '')[:64]

    with transaction.atomic():
        try:
            with transaction.atomic():
                record = NexConnectWebhookEvent.objects.create(
                    event_id=event['id'][:100],
                    event_type=event_type[:60],
                    event_created_at=created_at,
                    nexconnect_invoice_id=nx_id,
                    outcome='ignored',
                    payload=slim_event(event),
                )
        except IntegrityError:
            logger.info('Webhook NexConnect duplicado: %s', event['id'])
            return DUPLICATE

        nx_status = (obj.get('status') or '').lower()
        if event_type not in OUTBOUND_EVENTS or not nx_status:
            return record.outcome

        invoice, match = resolve_invoice(event)
        if invoice is None or match != 'ok':
            outcome = match
        elif is_stale(invoice, nx_status, created_at):
            outcome = 'stale'
        else:
            provider = NexConnectProvider(tenant)
            data = {**obj, 'webhook_event_id': event['id']}
            if created_at:
                data['webhook_event_at'] = created_at.isoformat()
            provider._apply(invoice, data, [])
            provider._log(invoice, 'webhook', status=invoice.dgii_status,
                          body={'event_id': event['id'], 'type': event_type,
                                **mapping.slim_response(obj)})
            outcome = 'applied'

        record.invoice = invoice
        record.outcome = outcome
        record.save(update_fields=['invoice', 'outcome', 'updated_at'])

    if outcome != 'applied':
        logger.warning('Webhook NexConnect %s (%s) no aplicado: %s', event['id'], event_type, outcome)
    return outcome
