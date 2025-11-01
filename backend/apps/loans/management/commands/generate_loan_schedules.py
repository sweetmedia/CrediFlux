"""
Management command to generate missing loan schedules
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.tenants.models import Tenant
from apps.loans.models import Loan, LoanSchedule
from django_tenants.utils import schema_context
from dateutil.relativedelta import relativedelta


class Command(BaseCommand):
    help = 'Generate payment schedules for loans that are missing them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name (optional, processes all if not specified)',
        )

    def handle(self, *args, **options):
        tenant_filter = options.get('tenant')

        if tenant_filter:
            tenants = Tenant.objects.filter(schema_name=tenant_filter)
        else:
            # Process all tenants except public
            tenants = Tenant.objects.exclude(schema_name='public')

        total_loans_processed = 0
        total_schedules_created = 0

        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.business_name} ({tenant.schema_name})')

            with schema_context(tenant.schema_name):
                # Find loans without schedules
                loans_without_schedules = Loan.objects.filter(
                    payment_schedules__isnull=True,
                    status__in=['active', 'paid', 'defaulted', 'written_off']
                ).distinct()

                loans_count = loans_without_schedules.count()
                self.stdout.write(f'  Found {loans_count} loans without schedules')

                for loan in loans_without_schedules:
                    try:
                        schedules_created = self._generate_payment_schedule(loan)
                        total_schedules_created += schedules_created
                        total_loans_processed += 1

                        self.stdout.write(
                            f'  ✓ Generated {schedules_created} schedules for loan {loan.loan_number}'
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Error processing loan {loan.loan_number}: {str(e)}')
                        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Completed!'))
        self.stdout.write(f'  • Loans processed: {total_loans_processed}')
        self.stdout.write(f'  • Schedules created: {total_schedules_created}')

    def _generate_payment_schedule(self, loan):
        """Generate payment schedule for a loan"""
        schedules_created = 0

        # Calculate period based on payment frequency
        frequency_map = {
            'daily': {'days': 1},
            'weekly': {'weeks': 1},
            'biweekly': {'weeks': 2},
            'monthly': {'months': 1},
            'quarterly': {'months': 3},
        }

        period_delta = frequency_map.get(loan.payment_frequency, {'months': 1})

        # Calculate number of payments
        if loan.payment_frequency == 'monthly':
            num_payments = loan.term_months
        elif loan.payment_frequency == 'quarterly':
            num_payments = loan.term_months // 3
        elif loan.payment_frequency == 'weekly':
            num_payments = loan.term_months * 4
        elif loan.payment_frequency == 'biweekly':
            num_payments = loan.term_months * 2
        elif loan.payment_frequency == 'daily':
            num_payments = loan.term_months * 30
        else:
            num_payments = loan.term_months

        # Simple interest calculation
        total_interest = loan.principal_amount.amount * (loan.interest_rate / Decimal('100')) * (Decimal(loan.term_months) / Decimal('12'))
        total_amount = loan.principal_amount.amount + total_interest

        payment_amount = total_amount / Decimal(num_payments)
        principal_per_payment = loan.principal_amount.amount / Decimal(num_payments)
        interest_per_payment = total_interest / Decimal(num_payments)

        # Determine starting date
        if loan.first_payment_date:
            current_date = loan.first_payment_date
        elif loan.disbursement_date:
            # First payment is 30 days after disbursement
            current_date = loan.disbursement_date + timedelta(days=30)
        else:
            # Use application date + 30 days as fallback
            current_date = loan.application_date + timedelta(days=30)

        # Today's date for status determination
        today = timezone.now().date()

        # Create schedule entries
        for i in range(1, int(num_payments) + 1):
            # Determine status based on loan status and payment progress
            if loan.status == 'paid':
                status = 'paid'
            elif loan.status in ['defaulted', 'written_off']:
                # Check if this installment would have been paid based on total_paid
                installments_paid = int((loan.total_paid.amount / payment_amount).quantize(Decimal('1')))
                if i <= installments_paid:
                    status = 'paid'
                else:
                    status = 'pending'
            elif loan.status == 'active':
                # Check if this installment would have been paid
                installments_paid = int((loan.total_paid.amount / payment_amount).quantize(Decimal('1')))
                if i <= installments_paid:
                    status = 'paid'
                elif current_date < today:
                    # Past due date but not paid
                    status = 'pending'
                else:
                    status = 'pending'
            else:
                status = 'pending'

            # Calculate days overdue for pending installments
            days_overdue = 0
            if status == 'pending' and current_date < today:
                days_overdue = (today - current_date).days

            # Calculate paid amount and date for paid installments
            paid_amount = payment_amount if status == 'paid' else Decimal('0')
            paid_date = current_date if status == 'paid' else None

            LoanSchedule.objects.create(
                loan=loan,
                installment_number=i,
                due_date=current_date,
                total_amount=payment_amount,
                principal_amount=principal_per_payment,
                interest_amount=interest_per_payment,
                status=status,
                paid_amount=paid_amount,
                paid_date=paid_date,
                days_overdue=days_overdue
            )

            schedules_created += 1

            # Move to next payment date
            current_date = current_date + relativedelta(**period_delta)

        # Update maturity date if not set
        if not loan.maturity_date:
            loan.maturity_date = current_date
            loan.save()

        return schedules_created
