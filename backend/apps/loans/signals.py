"""
Signals for loan module
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import LoanPayment, Loan, LoanSchedule


@receiver(post_save, sender=LoanPayment)
def update_loan_on_payment(sender, instance, created, **kwargs):
    """
    Update loan balances and schedules when a payment is made
    """
    if created and instance.status == 'completed':
        from moneyed import Money
        from decimal import Decimal

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

        # Update schedule if linked
        if instance.schedule:
            schedule = instance.schedule
            schedule.paid_amount += instance.amount

            if schedule.paid_amount >= schedule.total_amount:
                schedule.status = 'paid'
                schedule.paid_date = instance.payment_date
            else:
                # Compare with Money object
                zero_schedule = Money(Decimal('0'), schedule.paid_amount.currency)
                if schedule.paid_amount > zero_schedule:
                    schedule.status = 'partial'

            schedule.save()


@receiver(post_delete, sender=LoanPayment)
def revert_loan_on_payment_delete(sender, instance, **kwargs):
    """
    Revert loan balances when a payment is deleted
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
