"""
Celery tasks for loan operations including WhatsApp reminders
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from celery import shared_task
from django.db.models import Q
from django_tenants.utils import schema_context

from apps.tenants.models import Tenant
from .models import LoanSchedule, Loan
from .utils_whatsapp import get_whatsapp_service

logger = logging.getLogger(__name__)


@shared_task(name='loans.send_payment_reminders')
def send_payment_reminders():
    """
    Daily task to send payment reminders for upcoming and overdue payments.
    Runs for all tenants that have WhatsApp reminders enabled.
    """
    logger.info("Starting payment reminders task")

    # Get all active tenants with WhatsApp reminders enabled
    tenants = Tenant.objects.filter(
        is_active=True,
        enable_whatsapp_reminders=True
    )

    total_sent = 0
    total_failed = 0

    for tenant in tenants:
        logger.info(f"Processing payment reminders for tenant: {tenant.name}")

        try:
            with schema_context(tenant.schema_name):
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

    today = date.today()
    sent_count = 0
    failed_count = 0

    # Define reminder windows based on tenant settings
    reminder_days_before = getattr(tenant, 'reminder_days_before', [7, 3, 1])  # Default: 7, 3, 1 day before
    reminder_days_after = getattr(tenant, 'reminder_days_after', [1, 3, 7])    # Default: 1, 3, 7 days after

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

    # Get pending schedules with due dates matching reminder dates
    schedules = LoanSchedule.objects.filter(
        status__in=['pending', 'partial'],
        due_date__in=reminder_dates,
        loan__status='active'
    ).select_related('loan', 'loan__customer')

    logger.info(f"Found {schedules.count()} schedules to process for {tenant.name}")

    for schedule in schedules:
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

            # Send reminder
            success = whatsapp_service.send_payment_reminder(
                loan=schedule.loan,
                phone=phone,
                days_until_due=days_until_due,
                amount_due=amount_due.amount if hasattr(amount_due, 'amount') else amount_due
            )

            if success:
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
