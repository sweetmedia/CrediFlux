"""
Celery tasks for the Billing app.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='billing.check_pending_submissions')
def check_pending_submissions():
    """
    Consulta el estado de todas las facturas enviadas a DGII
    que aún no tienen respuesta definitiva.
    """
    from .models import Invoice
    from .services.dgii_client import DGIIClient, DGIIClientError

    pending = Invoice.objects.filter(
        status='submitted',
        dgii_trackid__isnull=False,
    ).exclude(dgii_trackid='')

    logger.info(f'Consultando estado de {pending.count()} facturas pendientes')

    results = {'checked': 0, 'accepted': 0, 'rejected': 0, 'errors': 0}

    for invoice in pending:
        try:
            cert = invoice.certificate
            if not cert:
                logger.warning(f'Factura {invoice.encf_number} sin certificado')
                continue

            client = DGIIClient(
                environment='testecf',  # TODO: obtener del tenant config
                certificate_path=cert.certificate_file.path if cert.certificate_file else None,
                certificate_password=cert.certificate_password,
            )
            result = client.query_result(invoice)
            results['checked'] += 1

            if invoice.status == 'accepted':
                results['accepted'] += 1
            elif invoice.status == 'rejected':
                results['rejected'] += 1

        except DGIIClientError as e:
            logger.error(f'Error consultando {invoice.encf_number}: {e}')
            results['errors'] += 1
        except Exception as e:
            logger.error(f'Error inesperado consultando {invoice.encf_number}: {e}')
            results['errors'] += 1

    logger.info(f'Resultado consulta pendientes: {results}')
    return results


@shared_task(name='billing.generate_payment_invoice')
def generate_payment_invoice(payment_id):
    """
    Genera automáticamente una factura electrónica para un pago de préstamo.
    
    Args:
        payment_id: UUID del LoanPayment
    """
    from django.utils import timezone
    from .models import Invoice, InvoiceItem, FiscalSequence

    try:
        from apps.loans.models import LoanPayment
        payment = LoanPayment.objects.select_related('loan', 'loan__customer').get(id=payment_id)
        loan = payment.loan
        customer = loan.customer

        # Verificar si ya existe factura para este pago
        if Invoice.objects.filter(payment=payment).exists():
            logger.info(f'Ya existe factura para pago {payment_id}')
            return None

        # Crear factura
        invoice = Invoice.objects.create(
            loan=loan,
            payment=payment,
            customer=customer,
            ecf_type='31',  # Crédito fiscal por defecto
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            payment_method='02',  # Transferencia
            comprador_rnc=customer.tax_id or '',
            comprador_razon_social=f'{customer.first_name} {customer.last_name}',
            status='draft',
        )

        # Crear línea de detalle
        InvoiceItem.objects.create(
            invoice=invoice,
            line_number=1,
            description=f'Pago préstamo #{loan.id} - Cuota',
            quantity=1,
            unit_price=payment.amount,
            itbis_rate='0',  # Servicios financieros exentos de ITBIS
        )

        # Calcular totales
        invoice.subtotal = payment.amount
        invoice.total_itbis = 0
        invoice.total = payment.amount
        invoice.save()

        logger.info(f'Factura creada para pago {payment_id}: {invoice.id}')
        return str(invoice.id)

    except Exception as e:
        logger.error(f'Error generando factura para pago {payment_id}: {e}')
        raise
