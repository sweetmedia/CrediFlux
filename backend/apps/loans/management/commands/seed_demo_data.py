"""
Seed demo data for CrediFlux demo environment.
Creates sample customers, loans, schedules, payments, and guarantors.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from djmoney.money import Money

from apps.loans.models import Customer, Loan, LoanSchedule, LoanPayment
from apps.loans.models_guarantors import Guarantor


DEMO_CUSTOMERS = [
    {
        'first_name': 'María', 'last_name': 'Pérez Gómez',
        'email': 'maria.perez@demo.com', 'phone': '+18095551001',
        'id_type': 'cedula', 'id_number': '00112345678',
        'date_of_birth': '1985-03-15', 'gender': 'F',
        'address_line1': 'Av. Winston Churchill #45', 'city': 'Santo Domingo',
        'state': 'Distrito Nacional', 'postal_code': '10101',
        'employment_status': 'employed', 'employer_name': 'Grupo Ramos',
        'occupation': 'Contadora', 'monthly_income': 65000,
    },
    {
        'first_name': 'Juan Carlos', 'last_name': 'Rodríguez Marte',
        'email': 'jc.rodriguez@demo.com', 'phone': '+18295552002',
        'id_type': 'cedula', 'id_number': '00212345679',
        'date_of_birth': '1990-07-22', 'gender': 'M',
        'address_line1': 'Calle El Sol #12', 'city': 'Santiago',
        'state': 'Santiago', 'postal_code': '51000',
        'employment_status': 'self_employed', 'employer_name': 'Taller Rodríguez',
        'occupation': 'Mecánico', 'monthly_income': 45000,
    },
    {
        'first_name': 'Ana', 'last_name': 'Martínez Santana',
        'email': 'ana.martinez@demo.com', 'phone': '+18495553003',
        'id_type': 'cedula', 'id_number': '00312345680',
        'date_of_birth': '1988-11-03', 'gender': 'F',
        'address_line1': 'Calle Duarte #78', 'city': 'La Vega',
        'state': 'La Vega', 'postal_code': '41000',
        'employment_status': 'employed', 'employer_name': 'Hospital Regional',
        'occupation': 'Enfermera', 'monthly_income': 55000,
    },
    {
        'first_name': 'Pedro', 'last_name': 'García Méndez',
        'email': 'pedro.garcia@demo.com', 'phone': '+18095554004',
        'id_type': 'cedula', 'id_number': '00412345681',
        'date_of_birth': '1978-01-30', 'gender': 'M',
        'address_line1': 'Av. Independencia #234', 'city': 'San Cristóbal',
        'state': 'San Cristóbal', 'postal_code': '91000',
        'employment_status': 'self_employed', 'employer_name': 'Colmado Don Pedro',
        'occupation': 'Comerciante', 'monthly_income': 80000,
    },
    {
        'first_name': 'Luisa', 'last_name': 'De los Santos Reyes',
        'email': 'luisa.santos@demo.com', 'phone': '+18295555005',
        'id_type': 'cedula', 'id_number': '00512345682',
        'date_of_birth': '1992-05-18', 'gender': 'F',
        'address_line1': 'Calle Mella #56', 'city': 'Puerto Plata',
        'state': 'Puerto Plata', 'postal_code': '57000',
        'employment_status': 'employed', 'employer_name': 'Barceló Hotels',
        'occupation': 'Recepcionista', 'monthly_income': 35000,
    },
    {
        'first_name': 'Rafael', 'last_name': 'Peña Castillo',
        'email': 'rafael.pena@demo.com', 'phone': '+18495556006',
        'id_type': 'cedula', 'id_number': '00612345683',
        'date_of_birth': '1982-09-12', 'gender': 'M',
        'address_line1': 'Calle Sánchez #89', 'city': 'San Pedro de Macorís',
        'state': 'San Pedro de Macorís', 'postal_code': '21000',
        'employment_status': 'employed', 'employer_name': 'Central Romana',
        'occupation': 'Ingeniero', 'monthly_income': 95000,
    },
    {
        'first_name': 'Carmen', 'last_name': 'Núñez Feliz',
        'email': 'carmen.nunez@demo.com', 'phone': '+18095557007',
        'id_type': 'cedula', 'id_number': '00712345684',
        'date_of_birth': '1995-12-25', 'gender': 'F',
        'address_line1': 'Av. 27 de Febrero #123', 'city': 'Santo Domingo Este',
        'state': 'Santo Domingo', 'postal_code': '11604',
        'employment_status': 'employed', 'employer_name': 'Claro RD',
        'occupation': 'Ejecutiva de Ventas', 'monthly_income': 50000,
    },
    {
        'first_name': 'Miguel', 'last_name': 'Torres Bautista',
        'email': 'miguel.torres@demo.com', 'phone': '+18295558008',
        'id_type': 'cedula', 'id_number': '00812345685',
        'date_of_birth': '1975-06-08', 'gender': 'M',
        'address_line1': 'Calle Principal #45', 'city': 'Higüey',
        'state': 'La Altagracia', 'postal_code': '23000',
        'employment_status': 'self_employed', 'employer_name': 'Transporte Torres',
        'occupation': 'Transportista', 'monthly_income': 70000,
    },
    {
        'first_name': 'Francisca', 'last_name': 'Espinal Vargas',
        'email': 'francisca.espinal@demo.com', 'phone': '+18495559009',
        'id_type': 'cedula', 'id_number': '00912345686',
        'date_of_birth': '1987-04-02', 'gender': 'F',
        'address_line1': 'Calle Las Mercedes #67', 'city': 'Bonao',
        'state': 'Monseñor Nouel', 'postal_code': '42000',
        'employment_status': 'employed', 'employer_name': 'Falconbridge',
        'occupation': 'Administrativa', 'monthly_income': 40000,
    },
    {
        'first_name': 'Roberto', 'last_name': 'Jiménez Rosario',
        'email': 'roberto.jimenez@demo.com', 'phone': '+18095550010',
        'id_type': 'cedula', 'id_number': '01012345687',
        'date_of_birth': '1983-08-20', 'gender': 'M',
        'address_line1': 'Av. Máximo Gómez #156', 'city': 'Santo Domingo',
        'state': 'Distrito Nacional', 'postal_code': '10204',
        'employment_status': 'employed', 'employer_name': 'Banco Popular',
        'occupation': 'Analista Financiero', 'monthly_income': 85000,
    },
]


class Command(BaseCommand):
    help = 'Seed demo data for CrediFlux (customers, loans, payments, guarantors)'

    def handle(self, *args, **options):
        if Customer.objects.filter(email='maria.perez@demo.com').exists():
            self.stdout.write(self.style.WARNING('Demo data already exists. Skipping.'))
            return

        self.stdout.write('Creating demo customers...')
        customers = []
        for data in DEMO_CUSTOMERS:
            income = data.pop('monthly_income')
            c = Customer.objects.create(
                **data,
                country='Dominican Republic',
                monthly_income=Money(Decimal(str(income)), 'DOP'),
            )
            customers.append(c)
            self.stdout.write(f'  ✓ {c.first_name} {c.last_name}')

        self.stdout.write('Creating demo loans...')
        today = date.today()

        loan_configs = [
            {
                'customer': customers[0], 'loan_type': 'personal',
                'principal': 150000, 'rate': 24, 'term': 12, 'status': 'active',
                'disbursement_date': today - timedelta(days=90),
            },
            {
                'customer': customers[1], 'loan_type': 'business',
                'principal': 500000, 'rate': 18, 'term': 24, 'status': 'active',
                'disbursement_date': today - timedelta(days=60),
            },
            {
                'customer': customers[2], 'loan_type': 'personal',
                'principal': 75000, 'rate': 30, 'term': 6, 'status': 'paid',
                'disbursement_date': today - timedelta(days=200),
            },
            {
                'customer': customers[3], 'loan_type': 'auto',
                'principal': 800000, 'rate': 15, 'term': 36, 'status': 'active',
                'disbursement_date': today - timedelta(days=120),
            },
            {
                'customer': customers[4], 'loan_type': 'personal',
                'principal': 50000, 'rate': 36, 'term': 6, 'status': 'pending',
                'disbursement_date': None,
            },
        ]

        loans = []
        for cfg in loan_configs:
            monthly_payment = (cfg['principal'] * (1 + cfg['rate'] / 100)) / cfg['term']
            disb = cfg['disbursement_date']
            first_pay = (disb + timedelta(days=30)) if disb else None

            loan = Loan.objects.create(
                customer=cfg['customer'],
                loan_type=cfg['loan_type'],
                principal_amount=Money(Decimal(str(cfg['principal'])), 'DOP'),
                interest_rate=Decimal(str(cfg['rate'])),
                term_months=cfg['term'],
                payment_frequency='monthly',
                payment_amount=Money(Decimal(str(round(monthly_payment, 2))), 'DOP'),
                status=cfg['status'],
                application_date=disb - timedelta(days=7) if disb else today,
                approval_date=disb - timedelta(days=2) if disb else None,
                disbursement_date=disb,
                first_payment_date=first_pay,
                maturity_date=(disb + timedelta(days=30 * cfg['term'])) if disb else None,
                outstanding_balance=Money(Decimal(str(cfg['principal'])), 'DOP'),
                total_paid=Money(Decimal('0'), 'DOP'),
            )
            loans.append(loan)
            self.stdout.write(f'  ✓ {loan.loan_number} - {cfg["customer"].first_name} ({cfg["status"]})')

            # Create payment schedule
            if disb:
                for i in range(1, cfg['term'] + 1):
                    due = disb + timedelta(days=30 * i)
                    principal_portion = Decimal(str(cfg['principal'])) / cfg['term']
                    interest_portion = Decimal(str(round(monthly_payment - float(principal_portion), 2)))
                    sched_status = 'pending'
                    if cfg['status'] == 'paid':
                        sched_status = 'paid'
                    elif due < today and cfg['status'] == 'active':
                        sched_status = 'paid' if i <= 2 else ('overdue' if due < today - timedelta(days=5) else 'pending')

                    LoanSchedule.objects.create(
                        loan=loan,
                        installment_number=i,
                        due_date=due,
                        principal_amount=Money(Decimal(str(round(float(principal_portion), 2))), 'DOP'),
                        interest_amount=Money(max(interest_portion, Decimal('0')), 'DOP'),
                        total_amount=Money(Decimal(str(round(monthly_payment, 2))), 'DOP'),
                        status=sched_status,
                        paid_amount=Money(Decimal(str(round(monthly_payment, 2))), 'DOP') if sched_status == 'paid' else Money(Decimal('0'), 'DOP'),
                        paid_date=due if sched_status == 'paid' else None,
                    )

        self.stdout.write('Creating demo payments...')
        # Payments for first loan (María)
        for i, loan in enumerate(loans[:2]):
            schedules = LoanSchedule.objects.filter(loan=loan, status='paid').order_by('installment_number')[:2]
            for sched in schedules:
                LoanPayment.objects.create(
                    loan=loan,
                    amount=sched.total_amount,
                    payment_date=sched.due_date,
                    payment_method='bank_transfer' if i == 0 else 'cash',
                    reference_number=f'PAY-DEMO-{random.randint(10000, 99999)}',
                    notes='Pago demo generado automáticamente',
                )
                self.stdout.write(f'  ✓ Payment for {loan.loan_number} - cuota {sched.installment_number}')

        self.stdout.write('Creating demo guarantor...')
        Guarantor.objects.create(
            loan=loans[1],
            first_name='Carlos',
            last_name='Medina Fernández',
            id_type='cedula',
            id_number='40212345699',
            phone='+18095551234',
            email='carlos.medina@demo.com',
            relationship='business_partner',
            employer_name='Ferretería Medina',
            monthly_income=Money(Decimal('90000'), 'DOP'),
            address_line1='Calle Restauración #34',
            city='Santiago',
            state='Santiago',
            country='Dominican Republic',
        )
        self.stdout.write(f'  ✓ Guarantor: Carlos Medina Fernández')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Demo data created: {len(customers)} customers, {len(loans)} loans, payments, 1 guarantor'
        ))
