"""
Mapeo entre ``billing.Invoice`` y la API de NexConnect.

El payload debe ser determinista para una misma factura: NexConnect guarda el
hash del cuerpo junto al ``Idempotency-Key`` y responde 409 si la misma key
llega con otro cuerpo.
"""
from datetime import datetime, time
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

DR_TZ = ZoneInfo('America/Santo_Domingo')

# Tipo de ingresos DGII. Lo que factura un prestamista (intereses, mora,
# comisiones) es ingreso financiero.
TIPO_INGRESOS_FINANCIEROS = 2

TIPO_PAGO_CONTADO = 1
TIPO_PAGO_CREDITO = 2

# PAYMENT_METHOD_CHOICES '04' = Venta a Crédito.
PAYMENT_METHOD_CREDITO = '04'

# Tipos de e-CF que NexConnect solo acepta al contado.
ECF_TYPES_SOLO_CONTADO = {'33', '34', '41', '43'}

# Estado NexConnect → Invoice.status de CrediFlux.
STATUS_MAP = {
    'signed': 'signed',
    'submitted': 'submitted',
    'delivered_to_receiver': 'submitted',
    'queued_offline': 'submitted',
    'accepted': 'accepted',
    'accepted_conditional': 'conditionally_accepted',
    'rejected': 'rejected',
    'cancelled': 'cancelled',
}

# Estados que todavía pueden cambiar (hay que seguir consultando).
PENDING_STATUSES = {'signed', 'submitted', 'delivered_to_receiver', 'queued_offline'}

# Campos pesados que no guardamos en Invoice.dgii_response.
_HEAVY_FIELDS = {'xml_signed_b64', 'lines'}


def to_cents(amount) -> int:
    """Decimal/Money → centavos enteros (redondeo comercial)."""
    amount = getattr(amount, 'amount', amount)
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def idempotency_key_for(invoice) -> str:
    """Una key estable por factura: reintentos nunca emiten dos e-CF."""
    return f'crediflux-invoice-{invoice.id}'


def issued_at_for(invoice) -> str:
    """Fecha de emisión a medianoche de RD (determinista y nunca en el futuro)."""
    return datetime.combine(invoice.issue_date, time.min, tzinfo=DR_TZ).isoformat()


def build_line(item) -> dict:
    exento = str(item.itbis_rate) == '0'
    return {
        'description': item.description,
        'quantity': str(item.quantity),
        'unit_price_cents': to_cents(item.unit_price),
        'discount_cents': to_cents(item.discount_amount),
        'itbis_rate': 0 if exento else int(item.itbis_rate),
        'is_exento': exento,
        # Lo que factura un prestamista son servicios (intereses, cargos).
        'item_type': 'servicio',
    }


def build_invoice_payload(invoice, items=None) -> dict:
    """Invoice de CrediFlux → cuerpo de ``POST /v1/invoices``.

    No mandamos totales: NexConnect los calcula de las líneas (y rechaza totales
    que no cuadren), así que la fuente de verdad son las líneas.
    """
    if items is None:
        items = invoice.items.all().order_by('line_number')
    lines = [build_line(item) for item in items]
    if not lines:
        raise ValueError('La factura no tiene líneas')

    ecf_type = str(invoice.ecf_type)
    credito = (
        invoice.payment_method == PAYMENT_METHOD_CREDITO
        and ecf_type not in ECF_TYPES_SOLO_CONTADO
    )

    payload = {
        'ecf_type': int(ecf_type),
        'issued_at': issued_at_for(invoice),
        'tipo_ingresos': TIPO_INGRESOS_FINANCIEROS,
        'tipo_pago': TIPO_PAGO_CREDITO if credito else TIPO_PAGO_CONTADO,
        'lines': lines,
        'metadata': {'crediflux_invoice_id': str(invoice.id)},
    }
    if credito and invoice.due_date:
        payload['fecha_limite_pago'] = invoice.due_date.isoformat()
    if invoice.comprador_rnc:
        payload['customer_rnc'] = invoice.comprador_rnc
    if invoice.comprador_razon_social:
        payload['customer_legal_name'] = invoice.comprador_razon_social
    reference = getattr(invoice, 'reference_invoice', None)
    if reference is not None and reference.encf_number:
        payload['ncf_modificado'] = reference.encf_number
    return payload


def local_status(nexconnect_status: str, default: str) -> str:
    return STATUS_MAP.get((nexconnect_status or '').lower(), default)


def slim_response(data: dict) -> dict:
    """Respuesta de NexConnect sin los campos pesados, para ``dgii_response``."""
    return {k: v for k, v in (data or {}).items() if k not in _HEAVY_FIELDS}
