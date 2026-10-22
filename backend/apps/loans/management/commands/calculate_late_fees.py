"""
Management command to calculate and update late fees for overdue schedules.

La regla de mora (y cómo conviven la configuración del Tenant con la Constance
LATE_PAYMENT_FEE / LATE_PAYMENT_GRACE_DAYS) está documentada en apps.loans.late_fees.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context
from apps.tenants.models import Tenant
from apps.loans.models import LoanSchedule
from apps.loans.late_fees import calculate_late_fee, policy_for


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
        policy = policy_for(tenant)

        # Cuotas vencidas sin saldar (las parciales también generan mora)
        overdue_schedules = LoanSchedule.objects.filter(
            status__in=['pending', 'partial', 'overdue'],
            due_date__lt=today
        ).select_related('loan')

        updated_count = 0

        for schedule in overdue_schedules:
            days_overdue = (today - schedule.due_date).days
            if days_overdue <= 0:
                continue

            late_fee = calculate_late_fee(schedule.balance, days_overdue, policy)

            if (
                late_fee != schedule.late_fee_amount
                or schedule.days_overdue != days_overdue
                or schedule.status != 'overdue'
            ):
                schedule.late_fee_amount = late_fee
                schedule.days_overdue = days_overdue
                schedule.status = 'overdue'
                schedule.save(update_fields=['late_fee_amount', 'days_overdue', 'status', 'updated_at'])
                updated_count += 1

                self.stdout.write(
                    f'    - Schedule #{schedule.installment_number} '
                    f'(Loan: {schedule.loan.loan_number}): '
                    f'{days_overdue} days overdue → Late fee: {late_fee}'
                )

        return updated_count

    def _calculate_late_fee(self, balance, days_overdue, tenant):
        """Mora para un saldo según la configuración del tenant (ver apps.loans.late_fees)."""
        return calculate_late_fee(balance, days_overdue, policy_for(tenant))
