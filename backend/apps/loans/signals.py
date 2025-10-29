"""
Signals for loan module
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import LoanPayment, Loan, LoanSchedule
from moneyed import Money
from decimal import Decimal


def distribute_payment_to_schedules(payment):
    """
    Distribute a payment across loan schedules in chronological order.

    If payment has a linked schedule, start from there.
    Otherwise, start from the earliest pending/partial/overdue schedule.

    If payment exceeds a schedule's remaining balance, mark it as paid
    and apply the excess to the next schedule(s).
    """
    loan = payment.loan
    remaining_amount = payment.amount.amount  # Get Decimal value

    # Get schedules to apply payment to
    if payment.schedule:
        # Start from the linked schedule
        schedules = loan.payment_schedules.filter(
            installment_number__gte=payment.schedule.installment_number,
            status__in=['pending', 'partial', 'overdue']
        ).order_by('installment_number')
    else:
        # Start from earliest unpaid schedule
        schedules = loan.payment_schedules.filter(
            status__in=['pending', 'partial', 'overdue']
        ).order_by('installment_number')

    # Distribute payment across schedules
    for schedule in schedules:
        if remaining_amount <= 0:
            break

        # Calculate how much is still owed on this schedule
        amount_owed = schedule.total_amount.amount - schedule.paid_amount.amount

        if amount_owed <= 0:
            continue  # Already paid, skip

        # Apply as much as possible to this schedule
        amount_to_apply = min(remaining_amount, amount_owed)

        # Update schedule paid amount
        schedule.paid_amount += Money(Decimal(str(amount_to_apply)), schedule.paid_amount.currency)

        # Update schedule status
        if schedule.paid_amount >= schedule.total_amount:
            schedule.status = 'paid'
            schedule.paid_date = payment.payment_date
        elif schedule.paid_amount > Money(Decimal('0'), schedule.paid_amount.currency):
            schedule.status = 'partial'

        schedule.save()

        # Reduce remaining amount
        remaining_amount -= amount_to_apply

        # Link payment to first schedule if not already linked
        if not payment.schedule and schedules.first() == schedule:
            payment.schedule = schedule
            payment.save(update_fields=['schedule'])


@receiver(post_save, sender=LoanPayment)
def update_loan_on_payment(sender, instance, created, **kwargs):
    """
    Update loan balances and schedules when a payment is made
    """
    if created and instance.status == 'completed':
        loan = instance.loan

        # Update total paid
        loan.total_paid += instance.amount
        loan.total_interest_paid += instance.interest_paid

        # Update outstanding balance
        loan.outstanding_balance -= instance.principal_paid

        # Check if loan is fully paid - compare with Money object
        zero_amount = Money(Decimal('0'), loan.outstanding_balance.currency)
        if loan.outstanding_balance <= zero_amount:
            loan.status = 'paid'
            loan.outstanding_balance = zero_amount

        loan.save()

        # Distribute payment across schedules
        distribute_payment_to_schedules(instance)


def recalculate_schedules_from_payments(loan):
    """
    Recalculate all schedule statuses based on all completed payments for the loan.

    This is used when a payment is deleted to ensure schedules are accurate.
    """
    # Reset all schedules
    for schedule in loan.payment_schedules.all():
        schedule.paid_amount = Money(Decimal('0'), schedule.total_amount.currency)
        schedule.status = 'pending'
        schedule.paid_date = None
        schedule.save()

    # Get all completed payments for this loan (ordered chronologically)
    payments = loan.payments.filter(status='completed').order_by('payment_date', 'id')

    # Reapply each payment to schedules
    for payment in payments:
        remaining_amount = payment.amount.amount

        # Get unpaid schedules
        schedules = loan.payment_schedules.filter(
            status__in=['pending', 'partial', 'overdue']
        ).order_by('installment_number')

        for schedule in schedules:
            if remaining_amount <= 0:
                break

            # Calculate amount owed
            amount_owed = schedule.total_amount.amount - schedule.paid_amount.amount

            if amount_owed <= 0:
                continue

            # Apply payment
            amount_to_apply = min(remaining_amount, amount_owed)
            schedule.paid_amount += Money(Decimal(str(amount_to_apply)), schedule.paid_amount.currency)

            # Update status
            if schedule.paid_amount >= schedule.total_amount:
                schedule.status = 'paid'
                schedule.paid_date = payment.payment_date
            elif schedule.paid_amount > Money(Decimal('0'), schedule.paid_amount.currency):
                schedule.status = 'partial'

            schedule.save()
            remaining_amount -= amount_to_apply

    # Check for overdue schedules
    today = timezone.now().date()
    overdue_schedules = loan.payment_schedules.filter(
        due_date__lt=today,
        status__in=['pending', 'partial']
    )
    for schedule in overdue_schedules:
        schedule.status = 'overdue'
        schedule.save()


@receiver(post_delete, sender=LoanPayment)
def revert_loan_on_payment_delete(sender, instance, **kwargs):
    """
    Revert loan balances and recalculate schedules when a payment is deleted
    """
    if instance.status == 'completed':
        loan = instance.loan

        # Revert totals
        loan.total_paid -= instance.amount
        loan.total_interest_paid -= instance.interest_paid
        loan.outstanding_balance += instance.principal_paid

        # Update status
        if loan.status == 'paid':
            loan.status = 'active'

        loan.save()

        # Recalculate all schedules from remaining payments
        recalculate_schedules_from_payments(loan)


@receiver(post_save, sender=Loan)
def update_loan_status(sender, instance, created, **kwargs):
    """
    Update loan status based on conditions
    """
    if not created and instance.status == 'active':
        # Check for overdue payments
        overdue_schedules = instance.payment_schedules.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partial']
        )

        # Update overdue schedules
        for schedule in overdue_schedules:
            schedule.status = 'overdue'
            schedule.save()
