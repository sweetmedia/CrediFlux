"""
Management command to seed Caproinsa tenant with test customers and loans
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random
from apps.tenants.models import Tenant
from apps.loans.models import Customer, Loan
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed Caproinsa tenant with test customers and loans'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Seeding Caproinsa with test data...'))

        try:
            # Get Caproinsa tenant
            tenant = Tenant.objects.get(schema_name='caproinsa')
            self.stdout.write(f'Found tenant: {tenant.business_name}')

            # Get a loan officer (first superuser or staff user)
            loan_officer = User.objects.filter(is_staff=True).first()
            if not loan_officer:
                self.stdout.write(self.style.WARNING('No staff user found. Creating loan officer...'))
                loan_officer = User.objects.create_user(
                    email='officer@caproinsa.com',
                    password='password123',
                    first_name='Carlos',
                    last_name='Martinez',
                    is_staff=True
                )

            # Dominican names and data
            first_names_male = ['Juan', 'Carlos', 'José', 'Luis', 'Miguel', 'Rafael', 'Pedro', 'Manuel']
            first_names_female = ['María', 'Ana', 'Carmen', 'Rosa', 'Isabel', 'Juana', 'Teresa', 'Laura']
            last_names = ['García', 'Rodríguez', 'Martínez', 'Pérez', 'González', 'Sánchez', 'Ramírez', 'Torres',
                         'Díaz', 'Vargas', 'Castro', 'Fernández', 'Méndez', 'Cruz', 'Reyes']

            cities = ['Santo Domingo', 'Santiago', 'La Vega', 'San Cristóbal', 'Puerto Plata', 'San Pedro de Macorís']
            states = ['Distrito Nacional', 'Santiago', 'La Vega', 'San Cristóbal', 'Puerto Plata', 'San Pedro de Macorís']
            occupations = ['Empleado', 'Comerciante', 'Profesor', 'Conductor', 'Vendedor', 'Técnico', 'Administrador', 'Ingeniero']

            customers_created = []

            # Switch to tenant schema to create tenant-specific data
            with schema_context(tenant.schema_name):
                # Create 15 customers
                for i in range(15):
                    gender = random.choice(['male', 'female', 'other'])
                    if gender == 'male':
                        first_name = random.choice(first_names_male)
                    else:
                        first_name = random.choice(first_names_female)

                    last_name = f"{random.choice(last_names)} {random.choice(last_names)}"

                    # Generate random cedula (11 digits for Dominican Republic)
                    cedula = f"{random.randint(100, 999):03d}-{random.randint(1000000, 9999999):07d}-{random.randint(0, 9):01d}"

                    # Random age between 25 and 65
                    age = random.randint(25, 65)
                    date_of_birth = timezone.now().date() - timedelta(days=age*365)

                    city = random.choice(cities)
                    state = states[cities.index(city)]

                    # Employment status weighted towards employed
                    employment_status = random.choices(
                        ['employed', 'self_employed', 'unemployed', 'retired'],
                        weights=[60, 25, 10, 5]
                    )[0]

                    # Monthly income between RD$15,000 and RD$150,000
                    monthly_income = Decimal(random.randint(15000, 150000))

                    # Credit score between 400 and 800
                    credit_score = random.randint(400, 800)

                    # Status weighted towards active
                    status = random.choices(
                        ['active', 'inactive', 'blacklisted'],
                        weights=[85, 10, 5]
                    )[0]

                    customer = Customer.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=date_of_birth,
                        gender=gender,
                        email=f"{first_name.lower()}.{last_name.split()[0].lower()}@email.com",
                        phone=f"+1809{random.randint(2000000, 9999999):07d}",
                        alternate_phone=f"+1829{random.randint(2000000, 9999999):07d}" if random.random() > 0.3 else None,
                        address_line1=f"Calle {random.randint(1, 100)} #{random.randint(1, 500)}",
                        city=city,
                        state=state,
                        country='República Dominicana',
                        postal_code=f"{random.randint(10000, 99999):05d}",
                        id_type='cedula',
                        id_number=cedula,
                        employment_status=employment_status,
                        employer_name=f"Empresa {random.choice(['ABC', 'XYZ', 'Global', 'Nacional', 'Dominicana'])}" if employment_status == 'employed' else None,
                        occupation=random.choice(occupations) if employment_status in ['employed', 'self_employed'] else None,
                        monthly_income=monthly_income,
                        credit_score=credit_score,
                        status=status,
                        notes=f"Cliente de prueba #{i+1}",
                        created_by=loan_officer
                    )

                    customers_created.append(customer)
                    self.stdout.write(f"  ✓ Created customer: {customer.first_name} {customer.last_name}")

                self.stdout.write(self.style.SUCCESS(f'\n✓ Created {len(customers_created)} customers'))

                # Now create loans with different statuses
                loans_created = []
                loan_types = ['personal', 'business', 'auto', 'education']

                # Create 25 loans
                total_loans = 25

                # Define how many loans per status
                status_distribution = {
                    'active': 10,       # 10 active loans
                    'paid': 6,          # 6 paid loans
                    'pending': 3,       # 3 pending approval
                    'approved': 2,      # 2 approved but not disbursed
                    'defaulted': 3,     # 3 defaulted
                    'written_off': 1,   # 1 written off
                }

                for status, count in status_distribution.items():
                    for _ in range(count):
                        # Select random customer (active customers preferred for active loans)
                        if status in ['active', 'approved']:
                            eligible_customers = [c for c in customers_created if c.status == 'active']
                            if not eligible_customers:
                                eligible_customers = customers_created
                        else:
                            eligible_customers = customers_created

                        customer = random.choice(eligible_customers)

                        # Loan amount between RD$10,000 and RD$300,000
                        principal = Decimal(random.randint(10000, 300000))

                        # Interest rate between 10% and 25%
                        interest_rate = Decimal(random.uniform(10.0, 25.0)).quantize(Decimal('0.01'))

                        # Term between 6 and 48 months
                        term_months = random.choice([6, 12, 18, 24, 36, 48])

                        # Random loan type
                        loan_type = random.choice(loan_types)

                        # Payment frequency (mostly monthly)
                        payment_frequency = random.choices(
                            ['monthly', 'biweekly', 'weekly'],
                            weights=[80, 15, 5]
                        )[0]

                        # Calculate payment amount (simplified)
                        # Monthly payment = P * (r * (1 + r)^n) / ((1 + r)^n - 1)
                        monthly_rate = interest_rate / Decimal('100') / Decimal('12')
                        if monthly_rate > 0:
                            payment_amount = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
                        else:
                            payment_amount = principal / term_months

                        payment_amount = payment_amount.quantize(Decimal('0.01'))

                        # Application date (within last 2 years)
                        days_ago = random.randint(30, 730)
                        application_date = timezone.now().date() - timedelta(days=days_ago)

                        # Create loan based on status
                        loan_data = {
                            'customer': customer,
                            'loan_type': loan_type,
                            'principal_amount': principal,
                            'interest_rate': interest_rate,
                            'term_months': term_months,
                            'payment_frequency': payment_frequency,
                            'payment_amount': payment_amount,
                            'status': status,
                            'application_date': application_date,
                            'loan_officer': loan_officer,
                            'created_by': loan_officer,
                        }

                        # Set dates and balances based on status
                        if status == 'pending':
                            # Just submitted, no approval yet
                            pass

                        elif status == 'approved':
                            # Approved but not disbursed yet
                            loan_data['approval_date'] = application_date + timedelta(days=random.randint(1, 7))
                            loan_data['approved_by'] = loan_officer

                        elif status in ['active', 'paid', 'defaulted', 'written_off']:
                            # These have been disbursed
                            approval_date = application_date + timedelta(days=random.randint(1, 7))
                            disbursement_date = approval_date + timedelta(days=random.randint(1, 5))
                            first_payment_date = disbursement_date + timedelta(days=30)
                            maturity_date = first_payment_date + timedelta(days=30 * term_months)

                            loan_data['approval_date'] = approval_date
                            loan_data['approved_by'] = loan_officer
                            loan_data['disbursement_date'] = disbursement_date
                            loan_data['first_payment_date'] = first_payment_date
                            loan_data['maturity_date'] = maturity_date

                            # Calculate how much has been paid based on status and time
                            if status == 'paid':
                                # Loan is fully paid
                                total_to_pay = payment_amount * term_months
                                loan_data['outstanding_balance'] = Decimal('0.00')
                                loan_data['total_paid'] = total_to_pay
                                loan_data['total_interest_paid'] = total_to_pay - principal
                                loan_data['late_fees'] = Decimal('0.00')

                            elif status == 'active':
                                # Calculate based on time elapsed
                                days_since_disbursement = (timezone.now().date() - disbursement_date).days
                                months_elapsed = min(days_since_disbursement // 30, term_months - 1)

                                paid_so_far = payment_amount * months_elapsed
                                loan_data['total_paid'] = paid_so_far
                                loan_data['outstanding_balance'] = (payment_amount * term_months) - paid_so_far
                                loan_data['total_interest_paid'] = (paid_so_far - (principal * months_elapsed / term_months)).quantize(Decimal('0.01'))
                                loan_data['late_fees'] = Decimal('0.00')

                            elif status == 'defaulted':
                                # Stopped paying after some months
                                months_paid = random.randint(3, term_months // 2)
                                paid_so_far = payment_amount * months_paid
                                loan_data['total_paid'] = paid_so_far
                                loan_data['outstanding_balance'] = (payment_amount * term_months) - paid_so_far
                                loan_data['total_interest_paid'] = (paid_so_far - (principal * months_paid / term_months)).quantize(Decimal('0.01'))
                                # Add late fees (5% monthly as configured)
                                months_late = random.randint(3, 6)
                                loan_data['late_fees'] = (payment_amount * Decimal('0.05') * months_late).quantize(Decimal('0.01'))
                                loan_data['outstanding_balance'] += loan_data['late_fees']

                            elif status == 'written_off':
                                # Similar to defaulted but written off
                                months_paid = random.randint(1, term_months // 3)
                                paid_so_far = payment_amount * months_paid
                                loan_data['total_paid'] = paid_so_far
                                loan_data['outstanding_balance'] = (payment_amount * term_months) - paid_so_far
                                loan_data['total_interest_paid'] = (paid_so_far - (principal * months_paid / term_months)).quantize(Decimal('0.01'))
                                months_late = random.randint(6, 12)
                                loan_data['late_fees'] = (payment_amount * Decimal('0.05') * months_late).quantize(Decimal('0.01'))
                                loan_data['outstanding_balance'] += loan_data['late_fees']
                                loan_data['notes'] = 'Préstamo castigado por falta de pago prolongada'

                        loan = Loan.objects.create(**loan_data)
                        loans_created.append(loan)

                        status_emoji = {
                            'active': '🟢',
                            'paid': '✅',
                            'pending': '🟡',
                            'approved': '🔵',
                            'defaulted': '🔴',
                            'written_off': '⚫'
                        }

                        self.stdout.write(
                            f"  {status_emoji.get(status, '•')} Created {status} loan: "
                            f"{loan.loan_number} - {customer.first_name} {customer.last_name} - "
                            f"DOP {principal:,.2f}"
                        )

                self.stdout.write(self.style.SUCCESS(f'\n✓ Created {len(loans_created)} loans'))

                # Summary statistics
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('📊 Summary Statistics:'))
                self.stdout.write(f'  • Total Customers: {len(customers_created)}')
                self.stdout.write(f'  • Total Loans: {len(loans_created)}')
                self.stdout.write('')

                # Loans by status
                self.stdout.write('  Loans by Status:')
                for status, count in status_distribution.items():
                    self.stdout.write(f'    - {status.title()}: {count}')

                # Total amounts
                total_principal = sum(loan.principal_amount.amount for loan in loans_created)
                total_outstanding = sum(loan.outstanding_balance.amount for loan in loans_created)
                total_paid = sum(loan.total_paid.amount for loan in loans_created)

                self.stdout.write('')
                self.stdout.write('  Financial Summary:')
                self.stdout.write(f'    - Total Principal Disbursed: DOP {total_principal:,.2f}')
                self.stdout.write(f'    - Total Outstanding Balance: DOP {total_outstanding:,.2f}')
                self.stdout.write(f'    - Total Collected: DOP {total_paid:,.2f}')

        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR('Error: Caproinsa tenant not found!'))
            self.stdout.write('Available tenants:')
            for t in Tenant.objects.exclude(schema_name='public'):
                self.stdout.write(f'  - {t.schema_name} ({t.business_name})')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
