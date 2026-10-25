"""
Celery tasks for loan operations including WhatsApp reminders
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.core.management import call_command
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.tenants.models import Tenant
from apps.tenants.timezones import tenant_now, use_tenant_timezone
from .models import LoanSchedule, Loan
from .utils_whatsapp import get_whatsapp_service

logger = logging.getLogger(__name__)


# Hora LOCAL de cada tenant a la que corre cada tarea diaria. Beat dispara las
# tareas cada hora y cada tenant se procesa cuando en su zona es esta hora.
LATE_FEES_LOCAL_HOUR = 0         # mora: 00:30 local
REMINDERS_LOCAL_HOUR = 9         # recordatorios: 09:00 local
OVERDUE_NOTICE_LOCAL_HOUR = 9    # avisos de mora: 09:30 local


def _is_local_hour(tenant, hour):
    return tenant_now(tenant).hour == hour


@shared_task(name='loans.calculate_late_fees')
def calculate_late_fees(force=False):
    """
    Recalcula la mora de las cuotas vencidas (comando `calculate_late_fees`;
    reglas en apps.loans.late_fees) en los tenants donde ahora es medianoche
    local, o en todos con `force=True`. Un tenant que falla no detiene a los demás.
    """
    processed, failed = [], []
    for tenant in Tenant.objects.provisioned():
        if not force and not _is_local_hour(tenant, LATE_FEES_LOCAL_HOUR):
            continue
        try:
            call_command('calculate_late_fees', tenant=tenant.schema_name)
            processed.append(tenant.schema_name)
        except Exception:
            logger.exception("Error calculando mora del tenant %s", tenant.schema_name)
            failed.append(tenant.schema_name)
    return {'processed': processed, 'failed': failed}


def _whatsapp_tenants():
    """Tenants con recordatorios por WhatsApp activos (nunca el schema público)."""
    return Tenant.objects.provisioned().filter(
        is_active=True,
        enable_whatsapp_reminders=True,
    )


def _already_sent(kind, tenant, schedule, today):
    """Evita repetir el mismo aviso el mismo día si la tarea se reintenta."""
    return cache.get(_sent_key(kind, tenant, schedule, today)) is not None


def _mark_sent(kind, tenant, schedule, today):
    cache.set(_sent_key(kind, tenant, schedule, today), 1, timeout=60 * 60 * 36)


def _sent_key(kind, tenant, schedule, today):
    return f'wa:{kind}:{tenant.schema_name}:{schedule.pk}:{today.isoformat()}'


@shared_task(name='loans.send_payment_reminders')
def send_payment_reminders(force=False):
    """
    Daily task to send payment reminders for upcoming and overdue payments.
    Runs for tenants with WhatsApp reminders enabled where it is now 09:xx
    local time (or all of them with force=True).
    """
    logger.info("Starting payment reminders task")

    # Get all active tenants with WhatsApp reminders enabled
    tenants = _whatsapp_tenants()

    total_sent = 0
    total_failed = 0

    for tenant in tenants:
        if not force and not _is_local_hour(tenant, REMINDERS_LOCAL_HOUR):
            continue
        logger.info(f"Processing payment reminders for tenant: {tenant.name}")

        try:
            with schema_context(tenant.schema_name), use_tenant_timezone(tenant):
                sent, failed = send_tenant_payment_reminders(tenant)
                total_sent += sent
                total_failed += failed
        except Exception as e:
            logger.error(f"Error processing reminders for tenant {tenant.name}: {str(e)}")
            total_failed += 1

    logger.info(
        f"Payment reminders task completed. Sent: {total_sent}, Failed: {total_failed}"
    )

    return {
        'total_sent': total_sent,
        'total_failed': total_failed,
        'tenants_processed': tenants.count()
    }


def send_tenant_payment_reminders(tenant: Tenant):
    """
    Send payment reminders for a specific tenant.

    Args:
        tenant: Tenant instance

    Returns:
        Tuple of (sent_count, failed_count)
    """
    whatsapp_service = get_whatsapp_service(tenant)

    if not whatsapp_service.is_configured():
        logger.warning(f"WhatsApp not configured for tenant {tenant.name}")
        return 0, 0

    today = timezone.localdate()
    sent_count = 0
    failed_count = 0

    # Define reminder windows based on tenant settings.
    # Tenant.reminder_days_before es un entero (días antes del vencimiento).
    days_before = getattr(tenant, 'reminder_days_before', None)
    if days_before is None:
        reminder_days_before = [7, 3, 1]
    elif isinstance(days_before, int):
        reminder_days_before = [days_before]
    else:
        reminder_days_before = list(days_before)
    reminder_days_after = getattr(tenant, 'reminder_days_after', [1, 3, 7])  # Default: 1, 3, 7 days after

    # Get schedules that need reminders
    reminder_dates = []

    # Add future reminder dates (before due date)
    for days in reminder_days_before:
        reminder_dates.append(today + timedelta(days=days))

    # Add past reminder dates (after due date - overdue)
    for days in reminder_days_after:
        reminder_dates.append(today - timedelta(days=days))

    # Also include today (due today)
    reminder_dates.append(today)

    # Unpaid schedules with due dates matching reminder dates ('overdue' incluido:
    # la tarea de mora de las 00:30 marca así las vencidas)
    schedules = LoanSchedule.objects.filter(
        status__in=['pending', 'partial', 'overdue'],
        due_date__in=reminder_dates,
        loan__status='active'
    ).select_related('loan', 'loan__customer')

    logger.info(f"Found {schedules.count()} schedules to process for {tenant.name}")

    for schedule in schedules:
        if _already_sent('reminder', tenant, schedule, today):
            continue
        try:
            # Calculate days until due
            days_until_due = (schedule.due_date - today).days

            # Get customer phone
            phone = schedule.loan.customer.phone

            if not phone:
                logger.warning(
                    f"No phone number for customer {schedule.loan.customer.get_full_name()} "
                    f"(Loan: {schedule.loan.loan_number})"
                )
                failed_count += 1
                continue

            # Calculate amount due (remaining amount)
            amount_due = schedule.total_amount - (schedule.paid_amount or Decimal('0'))

            # Send reminder (plantilla Utility; si ya venció, con la mora pendiente)
            late_fee_pending = schedule.late_fee_amount.amount - schedule.late_fee_paid.amount
            success = whatsapp_service.send_payment_reminder(
                loan=schedule.loan,
                phone=phone,
                days_until_due=days_until_due,
                amount_due=amount_due.amount if hasattr(amount_due, 'amount') else amount_due,
                due_date=schedule.due_date,
                late_fee=max(late_fee_pending, Decimal('0')),
            )

            if success:
                _mark_sent('reminder', tenant, schedule, today)
                sent_count += 1
                logger.info(
                    f"Sent reminder for loan {schedule.loan.loan_number} "
                    f"to {phone} ({days_until_due} days)"
                )
            else:
                failed_count += 1
                logger.warning(
                    f"Failed to send reminder for loan {schedule.loan.loan_number}"
                )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"Error sending reminder for schedule {schedule.id}: {str(e)}"
            )

    return sent_count, failed_count


@shared_task(name='loans.send_payment_confirmation')
def send_payment_confirmation(payment_id: str, tenant_schema: str):
    """
    Automatically send payment confirmation via WhatsApp after recording a payment.
    Called from the LoanPaymentViewSet after successful payment creation.
    """
    try:
        tenant = Tenant.objects.get(schema_name=tenant_schema)

        with schema_context(tenant_schema):
            from .models import LoanPayment
            payment = LoanPayment.objects.select_related('loan', 'loan__customer').get(id=payment_id)

            phone = payment.loan.customer.phone
            if not phone:
                logger.warning(f"No phone for customer {payment.loan.customer.get_full_name()}")
                return {'success': False, 'error': 'No phone number'}

            whatsapp_service = get_whatsapp_service(tenant)
            if not whatsapp_service.is_configured():
                return {'success': False, 'error': 'WhatsApp not configured'}

            success = whatsapp_service.send_payment_receipt(payment, phone)
            return {
                'success': success,
                'payment_number': payment.payment_number,
                'phone': str(phone),
            }

    except Exception as e:
        logger.error(f"Error sending payment confirmation: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task(name='loans.send_overdue_notice')
def send_overdue_notice(force=False):
    """
    Daily task to send overdue notices for significantly past-due payments.
    More urgent than reminders — sent for 15, 30, 60, 90 days overdue.
    Runs where it is now 09:xx local time (or everywhere with force=True).
    """
    logger.info("Starting overdue notices task")

    tenants = _whatsapp_tenants()

    total_sent = 0
    overdue_thresholds = [15, 30, 60, 90]

    for tenant in tenants:
        if not force and not _is_local_hour(tenant, OVERDUE_NOTICE_LOCAL_HOUR):
            continue
        try:
            with schema_context(tenant.schema_name), use_tenant_timezone(tenant):
                today = timezone.localdate()
                whatsapp_service = get_whatsapp_service(tenant)
                if not whatsapp_service.is_configured():
                    continue

                for threshold in overdue_thresholds:
                    target_date = today - timedelta(days=threshold)
                    schedules = LoanSchedule.objects.filter(
                        status__in=['pending', 'partial', 'overdue'],
                        due_date=target_date,
                        loan__status='active',
                    ).select_related('loan', 'loan__customer')

                    for schedule in schedules:
                        if _already_sent('overdue', tenant, schedule, today):
                            continue
                        phone = schedule.loan.customer.phone
                        if not phone:
                            continue

                        # Monto pendiente de la cuota más la mora sin pagar
                        balance = schedule.total_amount.amount - (
                            schedule.paid_amount.amount if schedule.paid_amount else Decimal('0')
                        )
                        late_fee = max(
                            schedule.late_fee_amount.amount - schedule.late_fee_paid.amount, Decimal('0')
                        )

                        try:
                            sent = whatsapp_service.send_overdue_notice(
                                schedule.loan, phone, days_overdue=threshold,
                                due_date=schedule.due_date, amount_due=balance + late_fee,
                            )
                        except Exception as e:
                            logger.error(f"Failed overdue notice for {schedule.loan.loan_number}: {e}")
                            continue
                        if sent:
                            _mark_sent('overdue', tenant, schedule, today)
                            total_sent += 1

        except Exception as e:
            logger.error(f"Error processing overdue notices for {tenant.name}: {e}")

    logger.info(f"Overdue notices completed. Sent: {total_sent}")
    return {'total_sent': total_sent}


@shared_task(name='loans.send_loan_approval_notification')
def send_loan_approval_notification(loan_id: str, tenant_schema: str):
    """
    Send loan approval notification via WhatsApp.

    Args:
        loan_id: UUID of the loan
        tenant_schema: Schema name of the tenant
    """
    try:
        # Get tenant
        tenant = Tenant.objects.get(schema_name=tenant_schema)

        with schema_context(tenant_schema):
            # Get loan
            loan = Loan.objects.select_related('customer').get(id=loan_id)

            # Get customer phone
            phone = loan.customer.phone

            if not phone:
                logger.warning(
                    f"No phone number for customer {loan.customer.get_full_name()} "
                    f"(Loan: {loan.loan_number})"
                )
                return {
                    'success': False,
                    'error': 'No phone number'
                }

            # Send notification
            whatsapp_service = get_whatsapp_service(tenant)
            success = whatsapp_service.send_loan_approved(loan, phone)

            if success:
                logger.info(
                    f"Sent loan approval notification for {loan.loan_number} to {phone}"
                )
                return {
                    'success': True,
                    'loan_number': loan.loan_number,
                    'phone': phone
                }
            else:
                logger.warning(
                    f"Failed to send loan approval notification for {loan.loan_number}"
                )
                return {
                    'success': False,
                    'error': 'WhatsApp service failed'
                }

    except Exception as e:
        logger.error(
            f"Error sending loan approval notification: {str(e)}"
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task(name='loans.send_contract_signature_reminder')
def send_contract_signature_reminder(contract_id: str, tenant_schema: str, phone: str, signature_url: str):
    """
    Send contract signature reminder via WhatsApp.

    Args:
        contract_id: UUID of the contract
        tenant_schema: Schema name of the tenant
        phone: Phone number to send to
        signature_url: Signature URL
    """
    try:
        from .models_contracts import Contract

        # Get tenant
        tenant = Tenant.objects.get(schema_name=tenant_schema)

        with schema_context(tenant_schema):
            # Get contract
            contract = Contract.objects.get(id=contract_id)

            # Send reminder
            whatsapp_service = get_whatsapp_service(tenant)
            success = whatsapp_service.send_contract_signature_link(
                contract, phone, signature_url
            )

            if success:
                logger.info(
                    f"Sent contract signature reminder for {contract.contract_number} to {phone}"
                )
                return {
                    'success': True,
                    'contract_number': contract.contract_number,
                    'phone': phone
                }
            else:
                logger.warning(
                    f"Failed to send contract signature reminder for {contract.contract_number}"
                )
                return {
                    'success': False,
                    'error': 'WhatsApp service failed'
                }

    except Exception as e:
        logger.error(
            f"Error sending contract signature reminder: {str(e)}"
        )
        return {
            'success': False,
            'error': str(e)
        }
