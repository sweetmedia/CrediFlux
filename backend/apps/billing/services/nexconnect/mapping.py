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

# indicador_nota_credito de una E34. NexConnect solo anula la original con el 1
# (DEVOLUCION_MERCANCIA → motivo "anulacion"); cualquier otro es un ajuste de
# montos (motivo "descuento", CodigoModificacion=3).
INDICADOR_NC_ANULACION = 1
INDICADOR_NC_DESCUENTO = 2
CANCELLATION_REASON_MAX = 500

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


def line_total_cents(item) -> int:
    """Total de una línea en centavos (base − descuento + ITBIS)."""
    base = (Decimal(item.quantity) * Decimal(getattr(item.unit_price, 'amount', item.unit_price))
            - Decimal(getattr(item.discount_amount, 'amount', item.discount_amount)))
    rate = Decimal(str(item.itbis_rate or '0')) / Decimal('100')
    return to_cents(base + base * rate)


def items_total_cents(items) -> int:
    return sum(line_total_cents(item) for item in items)


def credit_note_indicator(items, reference_items) -> int:
    """Una E34 que acredita el total de la original la anula; si no, es un descuento.

    Se deriva de las líneas (y no de un parámetro) para que el payload sea el
    mismo en cada reintento: el Idempotency-Key exige el mismo cuerpo.
    """
    if items_total_cents(items) == items_total_cents(reference_items):
        return INDICADOR_NC_ANULACION
    return INDICADOR_NC_DESCUENTO


def build_invoice_payload(invoice, items=None, reference_items=None) -> dict:
    """Invoice de CrediFlux → cuerpo de ``POST /v1/invoices``.

    No mandamos totales: NexConnect los calcula de las líneas (y rechaza totales
    que no cuadren), así que la fuente de verdad son las líneas.
    """
    if items is None:
        items = list(invoice.items.all().order_by('line_number'))
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
        if ecf_type == '34':
            if reference_items is None:
                reference_items = list(reference.items.all())
            indicador = credit_note_indicator(items, reference_items)
            payload['indicador_nota_credito'] = indicador
            if indicador == INDICADOR_NC_ANULACION and invoice.notes:
                payload['cancellation_reason'] = invoice.notes[:CANCELLATION_REASON_MAX]
    return payload


def local_status(nexconnect_status: str, default: str) -> str:
    return STATUS_MAP.get((nexconnect_status or '').lower(), default)


def slim_response(data: dict) -> dict:
    """Respuesta de NexConnect sin los campos pesados, para ``dgii_response``."""
    return {k: v for k, v in (data or {}).items() if k not in _HEAVY_FIELDS}
