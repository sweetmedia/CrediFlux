"""
Management command to create demo data for a tenant
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import random

from apps.tenants.models import Tenant
from apps.loans.models import Customer, Loan, LoanSchedule, LoanPayment
from apps.users.models import User


class Command(BaseCommand):
    help = 'Create demo data for a tenant (customers, loans, payments)'

    def add_arguments(self, parser):
        parser.add_argument(
            'tenant_schema',
            type=str,
            help='Schema name of the tenant (e.g., democompany)'
        )

    def handle(self, *args, **options):
        tenant_schema = options['tenant_schema']

        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Tenant "{tenant_schema}" not found'))
            return

        # Switch to tenant schema
        connection.set_tenant(tenant)

        self.stdout.write(self.style.SUCCESS(f'Creating demo data for tenant: {tenant.business_name}'))
        self.stdout.write('=' * 60)

        # Clean up existing loans (if any) to avoid duplicates
        existing_loans_count = Loan.objects.count()
        if existing_loans_count > 0:
            self.stdout.write(f'Deleting {existing_loans_count} existing loans...')
            Loan.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleaned up existing loans\n'))

        # Get a user to assign as created_by
        demo_user = User.objects.filter(is_tenant_owner=True).first()
        if not demo_user:
            demo_user = User.objects.filter(is_staff=True).first()

        if not demo_user:
            self.stdout.write(self.style.ERROR('No users found in this tenant. Please create a user first.'))
            return

        # Create customers
        customers_data = [
            {
                'first_name': 'Juan', 'last_name': 'Pérez',
                'id_type': 'cedula', 'id_number': '001-0123456-7',
                'phone': '+18095550101', 'email': 'juan.perez@example.com',
                'address_line1': 'Calle Principal #123', 'city': 'Santo Domingo',
                'state': 'Distrito Nacional', 'postal_code': '10101',
                'date_of_birth': timezone.now().date() - timedelta(days=365*35),
                'monthly_income': Decimal('45000.00'), 'credit_score': 720,
                'employment_status': 'employed', 'employer_name': 'Empresa ABC'
            },
            {
                'first_name': 'María', 'last_name': 'García',
                'id_type': 'cedula', 'id_number': '001-0234567-8',
                'phone': '+18095550102', 'email': 'maria.garcia@example.com',
                'address_line1': 'Av. Independencia #456', 'city': 'Santiago',
                'state': 'Santiago', 'postal_code': '51000',
                'date_of_birth': timezone.now().date() - timedelta(days=365*28),
                'monthly_income': Decimal('35000.00'), 'credit_score': 680,
                'employment_status': 'self_employed', 'occupation': 'Comerciante'
            },
            {
                'first_name': 'Carlos', 'last_name': 'Rodríguez',
                'id_type': 'cedula', 'id_number': '001-0345678-9',
                'phone': '+18095550103', 'email': 'carlos.rodriguez@example.com',
                'address_line1': 'Calle Duarte #789', 'city': 'La Vega',
                'state': 'La Vega', 'postal_code': '41000',
                'date_of_birth': timezone.now().date() - timedelta(days=365*42),
                'monthly_income': Decimal('55000.00'), 'credit_score': 750,
                'employment_status': 'employed', 'employer_name': 'Banco Popular'
            },
            {
                'first_name': 'Ana', 'last_name': 'Martínez',
                'id_type': 'cedula', 'id_number': '001-0456789-0',
                'phone': '+18095550104', 'email': 'ana.martinez@example.com',
                'address_line1': 'Av. 27 de Febrero #321', 'city': 'Santo Domingo',
                'state': 'Distrito Nacional', 'postal_code': '10203',
                'date_of_birth': timezone.now().date() - timedelta(days=365*25),
                'monthly_income': Decimal('28000.00'), 'credit_score': 620,
                'employment_status': 'employed', 'employer_name': 'Tienda XYZ'
            },
            {
                'first_name': 'Pedro', 'last_name': 'Santos',
                'id_type': 'cedula', 'id_number': '001-0567890-1',
                'phone': '+18095550105', 'email': 'pedro.santos@example.com',
                'address_line1': 'Calle Mella #654', 'city': 'San Pedro de Macorís',
                'state': 'San Pedro de Macorís', 'postal_code': '21000',
                'date_of_birth': timezone.now().date() - timedelta(days=365*38),
                'monthly_income': Decimal('40000.00'), 'credit_score': 690,
                'employment_status': 'self_employed', 'occupation': 'Mecánico'
            },
            {
                'first_name': 'Laura', 'last_name': 'Fernández',
                'id_type': 'cedula', 'id_number': '001-0678901-2',
                'phone': '+18095550106', 'email': 'laura.fernandez@example.com',
                'address_line1': 'Av. Núñez de Cáceres #987', 'city': 'Santo Domingo',
                'state': 'Distrito Nacional', 'postal_code': '10405',
                'date_of_birth': timezone.now().date() - timedelta(days=365*31),
                'monthly_income': Decimal('50000.00'), 'credit_score': 710,
                'employment_status': 'employed', 'employer_name': 'Hospital Central'
            },
            {
                'first_name': 'Roberto', 'last_name': 'Díaz',
                'id_type': 'cedula', 'id_number': '001-0789012-3',
                'phone': '+18095550107', 'email': 'roberto.diaz@example.com',
                'address_line1': 'Calle Restauración #147', 'city': 'Puerto Plata',
                'state': 'Puerto Plata', 'postal_code': '57000',
                'date_of_birth': timezone.now().date() - timedelta(days=365*29),
                'monthly_income': Decimal('32000.00'), 'credit_score': 650,
                'employment_status': 'employed', 'occupation': 'Conductor'
            },
            {
                'first_name': 'Carmen', 'last_name': 'López',
                'id_type': 'cedula', 'id_number': '001-0890123-4',
                'phone': '+18095550108', 'email': 'carmen.lopez@example.com',
                'address_line1': 'Av. España #258', 'city': 'La Romana',
                'state': 'La Romana', 'postal_code': '22000',
                'date_of_birth': timezone.now().date() - timedelta(days=365*33),
                'monthly_income': Decimal('38000.00'), 'credit_score': 670,
                'employment_status': 'self_employed', 'occupation': 'Estilista'
            },
        ]

        customers = []
        for data in customers_data:
            customer, created = Customer.objects.get_or_create(
                id_number=data['id_number'],
                defaults={
                    **data,
                    'created_by': demo_user,
                    'status': 'active'
                }
            )
            customers.append(customer)
            if created:
                self.stdout.write(f'  ✓ Created customer: {customer.get_full_name()}')
            else:
                self.stdout.write(f'  - Customer exists: {customer.get_full_name()}')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Created/verified {len(customers)} customers\n'))

        # Create loans
        now = timezone.now().date()
        loans_created = 0
        payments_created = 0

        # Loan 1: Active, al día (good customer)
        loan1 = self._create_loan(
            customer=customers[0],
            user=demo_user,
            amount=Decimal('150000.00'),
            interest_rate=Decimal('18.0'),
            term_months=12,
            disbursement_date=now - timedelta(days=90),
            status='active',
            purpose='Negocio'
        )
        if loan1:
            loans_created += 1
            # Create 3 on-time payments
            payments_created += self._create_payments(loan1, 3, on_time=True)

        # Loan 2: Active, al día (excellent customer)
        loan2 = self._create_loan(
            customer=customers[2],
            user=demo_user,
            amount=Decimal('250000.00'),
            interest_rate=Decimal('16.0'),
            term_months=24,
            disbursement_date=now - timedelta(days=150),
            status='active',
            purpose='Vivienda'
        )
        if loan2:
            loans_created += 1
            payments_created += self._create_payments(loan2, 5, on_time=True)

        # Loan 3: Overdue 15 days (cliente moroso leve)
        loan3 = self._create_loan(
            customer=customers[1],
            user=demo_user,
            amount=Decimal('80000.00'),
            interest_rate=Decimal('20.0'),
            term_months=12,
            disbursement_date=now - timedelta(days=120),
            status='active',
            purpose='Personal'
        )
        if loan3:
            loans_created += 1
            # Paid first 2, but 3rd is 15 days late
            payments_created += self._create_payments(loan3, 2, on_time=True)
            payments_created += self._create_payments(loan3, 1, on_time=False, days_late=15)

        # Loan 4: Overdue 45 days (cliente moroso severo)
        loan4 = self._create_loan(
            customer=customers[3],
            user=demo_user,
            amount=Decimal('60000.00'),
            interest_rate=Decimal('22.0'),
            term_months=6,
            disbursement_date=now - timedelta(days=180),
            status='active',
            purpose='Educación'
        )
        if loan4:
            loans_created += 1
            # Paid first 3, but last one is 45 days late
            payments_created += self._create_payments(loan4, 3, on_time=True)
            payments_created += self._create_payments(loan4, 1, on_time=False, days_late=45)

        # Loan 5: Active, recent, just started
        loan5 = self._create_loan(
            customer=customers[4],
            user=demo_user,
            amount=Decimal('100000.00'),
            interest_rate=Decimal('19.0'),
            term_months=18,
            disbursement_date=now - timedelta(days=30),
            status='active',
            purpose='Vehículo'
        )
        if loan5:
            loans_created += 1
            payments_created += self._create_payments(loan5, 1, on_time=True)

        # Loan 6: Paid off completely (good history)
        loan6 = self._create_loan(
            customer=customers[5],
            user=demo_user,
            amount=Decimal('50000.00'),
            interest_rate=Decimal('17.0'),
            term_months=6,
            disbursement_date=now - timedelta(days=210),
            status='paid_off',
            purpose='Personal'
        )
        if loan6:
            loans_created += 1
            # Pay all 6 installments
            payments_created += self._create_payments(loan6, 6, on_time=True)

        # Loan 7: Overdue 60+ days (cliente muy moroso)
        loan7 = self._create_loan(
            customer=customers[6],
            user=demo_user,
            amount=Decimal('70000.00'),
            interest_rate=Decimal('24.0'),
            term_months=12,
            disbursement_date=now - timedelta(days=150),
            status='active',
            purpose='Negocio'
        )
        if loan7:
            loans_created += 1
            # Paid first 2, then stopped paying (2+ months overdue)
            payments_created += self._create_payments(loan7, 2, on_time=True)

        # Loan 8: Active, slight delay but paying
        loan8 = self._create_loan(
            customer=customers[7],
            user=demo_user,
            amount=Decimal('120000.00'),
            interest_rate=Decimal('18.5'),
            term_months=15,
            disbursement_date=now - timedelta(days=100),
            status='active',
            purpose='Consolidación'
        )
        if loan8:
            loans_created += 1
            # Paid with some delays
            payments_created += self._create_payments(loan8, 2, on_time=True)
            payments_created += self._create_payments(loan8, 1, on_time=False, days_late=7)

        self.stdout.write(self.style.SUCCESS(f'\n✓ Created {loans_created} loans'))
        self.stdout.write(self.style.SUCCESS(f'✓ Created {payments_created} payments'))
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('Demo data created successfully!'))
        self.stdout.write('\nSummary:')
        self.stdout.write(f'  - Customers: {len(customers)}')
        self.stdout.write(f'  - Loans: {loans_created}')
        self.stdout.write(f'    • Active & current: 4')
        self.stdout.write(f'    • Overdue (15 days): 1')
        self.stdout.write(f'    • Overdue (45 days): 1')
        self.stdout.write(f'    • Overdue (60+ days): 1')
        self.stdout.write(f'    • Paid off: 1')
        self.stdout.write(f'  - Payments: {payments_created}')

    def _create_loan(self, customer, user, amount, interest_rate, term_months,
                     disbursement_date, status, purpose):
        """Create a loan with schedules"""
        try:
            # Calculate payment amount using amortization formula
            monthly_rate = (interest_rate / Decimal('100')) / Decimal('12')
            numerator = amount * monthly_rate * ((1 + monthly_rate) ** term_months)
            denominator = ((1 + monthly_rate) ** term_months) - 1
            payment_amount = numerator / denominator if denominator != 0 else amount / term_months

            loan = Loan.objects.create(
                customer=customer,
                principal_amount=amount,
                interest_rate=interest_rate,
                term_months=term_months,
                payment_frequency='monthly',
                payment_amount=payment_amount.quantize(Decimal('0.01')),
                loan_type='personal',
                application_date=disbursement_date - timedelta(days=7),
                approval_date=disbursement_date - timedelta(days=2),
                disbursement_date=disbursement_date,
                first_payment_date=disbursement_date + timedelta(days=30),
                status=status,
                approved_by=user,
                created_by=user,
            )
            self.stdout.write(f'  ✓ Created loan #{loan.loan_number} for {customer.get_full_name()} - ${amount:,.2f} @ {interest_rate}%')

            # Generate payment schedules for this loan
            schedules_created = self._generate_payment_schedule(loan)
            self.stdout.write(f'    Generated {schedules_created} payment schedules')

            return loan
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error creating loan: {e}'))
            import traceback
            traceback.print_exc()
            return None

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
            status = 'pending'

            # Calculate days overdue for pending installments
            days_overdue = 0
            if status == 'pending' and current_date < today:
                days_overdue = (today - current_date).days

            LoanSchedule.objects.create(
                loan=loan,
                installment_number=i,
                due_date=current_date,
                total_amount=payment_amount,
                principal_amount=principal_per_payment,
                interest_amount=interest_per_payment,
                status=status,
                paid_amount=Decimal('0'),
                paid_date=None,
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

    def _create_payments(self, loan, count, on_time=True, days_late=0):
        """Create payments for a loan"""
        payments_created = 0
        schedules = loan.payment_schedules.order_by('due_date')[:count]

        self.stdout.write(f'    Trying to create {count} payments for loan {loan.loan_number}. Found {schedules.count()} schedules.')

        for schedule in schedules:
            if on_time:
                payment_date = schedule.due_date
            else:
                payment_date = schedule.due_date + timedelta(days=days_late)

            try:
                payment = LoanPayment.objects.create(
                    loan=loan,
                    schedule=schedule,
                    amount=schedule.total_amount,
                    payment_date=payment_date,
                    payment_method='cash',
                    status='confirmed',
                    notes=f'Pago cuota #{schedule.installment_number}'
                )

                # Update schedule status
                schedule.status = 'paid'
                schedule.paid_amount = schedule.total_amount
                schedule.paid_date = payment_date
                schedule.save()

                payments_created += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ! Error creating payment: {e}'))

        return payments_created
