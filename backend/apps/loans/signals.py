"""
Signals and reconciliation helpers for loan module
"""
from decimal import Decimal

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from moneyed import Money

from .models import Loan, LoanPayment


def _money_total(payments_or_schedules, attr, currency):
    total = Decimal('0.00')
    for item in payments_or_schedules:
        money_value = getattr(item, attr, None)
        if money_value:
            total += money_value.amount
    return Money(total, currency)


def _zero(currency):
    return Money(Decimal('0.00'), currency)


def recalculate_schedules_from_payments(loan):
    """
    Rebuild all schedule balances from completed payments.

    Source of truth for schedule progress = completed payments.
    Payment application priority inside a linked schedule is already calculated
    when the payment is created (late fee -> interest -> principal), but for the
    schedule progress itself we track how much of the installment total_amount has
    been covered. Late fees are tracked separately and should not inflate the
    installment paid_amount.
    """
    schedules = list(loan.payment_schedules.all().order_by('installment_number'))
    if not schedules:
        return

    # Reset all schedules
    for schedule in schedules:
        schedule.paid_amount = _zero(schedule.total_amount.currency)
        schedule.late_fee_paid = _zero(schedule.late_fee_amount.currency)
        schedule.status = 'pending'
        schedule.paid_date = None
        schedule.actual_payment_date = None
        schedule.days_overdue = 0
        schedule.save(update_fields=[
            'paid_amount',
            'late_fee_paid',
            'status',
            'paid_date',
            'actual_payment_date',
            'days_overdue',
            'updated_at',
        ])

    completed_payments = loan.payments.filter(status='completed').order_by('payment_date', 'id')

    for payment in completed_payments:
        remaining_schedule_amount = payment.amount.amount - payment.late_fee_paid.amount
        if remaining_schedule_amount < 0:
            remaining_schedule_amount = Decimal('0.00')

        base_queryset = loan.payment_schedules.filter(status__in=['pending', 'partial', 'overdue']).order_by('installment_number')
        if payment.schedule:
            base_queryset = base_queryset.filter(installment_number__gte=payment.schedule.installment_number)

        schedules_to_apply = list(base_queryset)
        first_schedule = schedules_to_apply[0] if schedules_to_apply else payment.schedule

        if first_schedule and payment.late_fee_paid.amount > 0:
            late_fee_to_apply = min(
                payment.late_fee_paid.amount,
                max(first_schedule.late_fee_amount.amount - first_schedule.late_fee_paid.amount, Decimal('0.00')),
            )
            if late_fee_to_apply > 0:
                first_schedule.late_fee_paid += Money(late_fee_to_apply, first_schedule.late_fee_paid.currency)
                if not first_schedule.actual_payment_date:
                    first_schedule.actual_payment_date = payment.payment_date
                first_schedule.save(update_fields=['late_fee_paid', 'actual_payment_date', 'updated_at'])

        for schedule in schedules_to_apply:
            if remaining_schedule_amount <= 0:
                break

            amount_owed = schedule.total_amount.amount - schedule.paid_amount.amount
            if amount_owed <= 0:
                continue

            amount_to_apply = min(remaining_schedule_amount, amount_owed)
            schedule.paid_amount += Money(amount_to_apply, schedule.paid_amount.currency)

            if not schedule.actual_payment_date:
                schedule.actual_payment_date = payment.payment_date

            if schedule.paid_amount >= schedule.total_amount:
                schedule.status = 'paid'
                schedule.paid_date = payment.payment_date
            elif schedule.paid_amount > _zero(schedule.paid_amount.currency):
                schedule.status = 'partial'

            schedule.save(update_fields=[
                'paid_amount',
                'actual_payment_date',
                'status',
                'paid_date',
                'updated_at',
            ])
            remaining_schedule_amount -= amount_to_apply

        if not payment.schedule and first_schedule:
            payment.schedule = first_schedule
            payment.save(update_fields=['schedule'])

    today = timezone.now().date()
    for schedule in loan.payment_schedules.all():
        if schedule.status in ['pending', 'partial'] and schedule.due_date < today:
            schedule.status = 'overdue'
            schedule.days_overdue = (today - schedule.due_date).days
            schedule.save(update_fields=['status', 'days_overdue', 'updated_at'])
        elif schedule.status == 'paid':
            new_days = max((schedule.actual_payment_date - schedule.due_date).days, 0) if schedule.actual_payment_date else 0
            if schedule.days_overdue != new_days:
                schedule.days_overdue = new_days
                schedule.save(update_fields=['days_overdue', 'updated_at'])


def reconcile_loan_state(loan):
    """
    Keep loan aggregates aligned with completed payments + schedule balances.

    Meaning of outstanding_balance in CrediFlux should be the remaining amount of
    the repayment schedule, not just remaining principal.
    """
    currency = loan.principal_amount.currency
    completed_payments = list(loan.payments.filter(status='completed'))
    schedules = list(loan.payment_schedules.all())

    loan.total_paid = _money_total(completed_payments, 'amount', currency)
    loan.total_interest_paid = _money_total(completed_payments, 'interest_paid', currency)

    if schedules:
        outstanding_total = sum(
            max(schedule.total_amount.amount - schedule.paid_amount.amount, Decimal('0.00'))
            for schedule in schedules
            if schedule.status != 'written_off'
        )
        loan.outstanding_balance = Money(outstanding_total, currency)
    else:
        principal_remaining = loan.principal_amount.amount - sum(payment.principal_paid.amount for payment in completed_payments)
        loan.outstanding_balance = Money(max(principal_remaining, Decimal('0.00')), currency)

    if loan.status not in ['pending', 'approved', 'rejected', 'written_off']:
        unpaid_exists = any(schedule.status in ['pending', 'partial', 'overdue'] for schedule in schedules)
        loan.status = 'paid' if not unpaid_exists and loan.outstanding_balance.amount <= Decimal('0.00') else 'active'

    loan.save(update_fields=['total_paid', 'total_interest_paid', 'outstanding_balance', 'status', 'updated_at'])


def reconcile_loan_from_payments(loan):
    recalculate_schedules_from_payments(loan)
    reconcile_loan_state(loan)


@receiver(post_save, sender=LoanPayment)
def update_loan_on_payment(sender, instance, created, **kwargs):
    """Update loan balances and schedules when a completed payment is created."""
    if created and instance.status == 'completed':
        reconcile_loan_from_payments(instance.loan)


@receiver(post_delete, sender=LoanPayment)
def revert_loan_on_payment_delete(sender, instance, **kwargs):
    """Recalculate loan state when a completed payment is deleted."""
    if instance.status == 'completed':
        reconcile_loan_from_payments(instance.loan)


@receiver(post_save, sender=Loan)
def update_loan_status(sender, instance, created, **kwargs):
    """Update overdue schedules for active loans."""
    if not created and instance.status == 'active':
        overdue_schedules = instance.payment_schedules.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partial']
        )

        for schedule in overdue_schedules:
            schedule.status = 'overdue'
            schedule.days_overdue = (timezone.now().date() - schedule.due_date).days
            schedule.save(update_fields=['status', 'days_overdue', 'updated_at'])
