"""
Management command to calculate and update late fees for overdue schedules.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context
from decimal import Decimal
from apps.tenants.models import Tenant
from apps.loans.models import LoanSchedule


class Command(BaseCommand):
    help = 'Calculate and update late fees for overdue payment schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name (e.g., caproinsa). If not provided, processes all tenants.'
        )

    def handle(self, *args, **options):
        tenant_schema = options.get('tenant')

        if tenant_schema:
            try:
                tenant = Tenant.objects.get(schema_name=tenant_schema)
                tenants = [tenant]
            except Tenant.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Tenant "{tenant_schema}" not found'))
                return
        else:
            tenants = Tenant.objects.exclude(schema_name='public')

        total_updated = 0

        for tenant in tenants:
            self.stdout.write(f'\nProcessing tenant: {tenant.name} ({tenant.schema_name})')

            with schema_context(tenant.schema_name):
                updated_count = self._calculate_late_fees_for_tenant(tenant)
                total_updated += updated_count
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated {updated_count} overdue schedule(s) for {tenant.name}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Total: Updated late fees for {total_updated} overdue schedule(s)'
            )
        )

    def _calculate_late_fees_for_tenant(self, tenant):
        """Calculate late fees for all overdue schedules in a tenant"""
        today = timezone.now().date()

        # Get all overdue schedules that haven't been paid
        overdue_schedules = LoanSchedule.objects.filter(
            status__in=['pending', 'overdue'],
            due_date__lt=today
        ).select_related('loan')

        updated_count = 0

        for schedule in overdue_schedules:
            # Calculate days overdue
            days_overdue = (today - schedule.due_date).days

            if days_overdue <= 0:
                continue

            # Calculate late fee based on tenant configuration
            late_fee = self._calculate_late_fee(
                schedule.balance,
                days_overdue,
                tenant
            )

            # Update the schedule if late fee has changed
            if late_fee != schedule.late_fee_amount:
                schedule.late_fee_amount = late_fee
                schedule.days_overdue = days_overdue
                schedule.status = 'overdue'
                schedule.save(update_fields=['late_fee_amount', 'days_overdue', 'status'])
                updated_count += 1

                self.stdout.write(
                    f'    - Schedule #{schedule.installment_number} '
                    f'(Loan: {schedule.loan.loan_number}): '
                    f'{days_overdue} days overdue → Late fee: {late_fee}'
                )

        return updated_count

    def _calculate_late_fee(self, balance, days_overdue, tenant):
        """Calculate late fee based on tenant configuration"""
        from djmoney.money import Money

        if days_overdue <= tenant.grace_period_days:
            return Money(0, 'USD')

        # Adjust days for grace period
        effective_days = days_overdue - tenant.grace_period_days

        if tenant.late_fee_type == 'percentage':
            # Calculate based on percentage and frequency
            if tenant.late_fee_frequency == 'per_day':
                periods = effective_days
            elif tenant.late_fee_frequency == 'per_week':
                periods = effective_days // 7
            elif tenant.late_fee_frequency == 'monthly':
                periods = effective_days // 30
            else:  # one_time
                periods = 1 if effective_days > 0 else 0

            # Calculate fee: balance * percentage * periods / 100
            fee_amount = balance.amount * (tenant.late_fee_percentage / Decimal('100')) * Decimal(periods)
            return Money(fee_amount, balance.currency.code)

        elif tenant.late_fee_type == 'fixed':
            # Fixed amount based on frequency
            if tenant.late_fee_frequency == 'per_day':
                periods = effective_days
            elif tenant.late_fee_frequency == 'per_week':
                periods = effective_days // 7
            elif tenant.late_fee_frequency == 'monthly':
                periods = effective_days // 30
            else:  # one_time
                periods = 1 if effective_days > 0 else 0

            return tenant.late_fee_fixed_amount * Decimal(periods)

        elif tenant.late_fee_type == 'hybrid':
            # Combine percentage and fixed
            percentage_fee = self._calculate_late_fee(balance, days_overdue,
                                                       self._create_percentage_tenant(tenant))
            fixed_fee = self._calculate_late_fee(balance, days_overdue,
                                                 self._create_fixed_tenant(tenant))
            return Money(percentage_fee.amount + fixed_fee.amount, balance.currency.code)

        return Money(0, 'USD')

    def _create_percentage_tenant(self, tenant):
        """Helper to create a virtual tenant with only percentage config"""
        class PercentageTenant:
            late_fee_type = 'percentage'
            late_fee_percentage = tenant.late_fee_percentage
            late_fee_frequency = tenant.late_fee_frequency
            grace_period_days = tenant.grace_period_days
        return PercentageTenant()

    def _create_fixed_tenant(self, tenant):
        """Helper to create a virtual tenant with only fixed config"""
        class FixedTenant:
            late_fee_type = 'fixed'
            late_fee_fixed_amount = tenant.late_fee_fixed_amount
            late_fee_frequency = tenant.late_fee_frequency
            grace_period_days = tenant.grace_period_days
        return FixedTenant()
