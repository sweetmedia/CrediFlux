"""
Management command to setup test data for Caproinsa tenant
"""
from django.core.management.base import BaseCommand
from decimal import Decimal
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'Setup test loan configuration data for Caproinsa tenant'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Caproinsa test data...'))

        try:
            # Get Caproinsa tenant
            tenant = Tenant.objects.get(schema_name='caproinsa')
            self.stdout.write(f'Found tenant: {tenant.business_name}')

            # ============================================================
            # INTEREST RATES
            # ============================================================
            tenant.default_interest_rate = Decimal('15.00')  # 15% anual
            tenant.min_interest_rate = Decimal('8.00')       # 8% mínimo
            tenant.max_interest_rate = Decimal('30.00')      # 30% máximo

            # ============================================================
            # LOAN AMOUNTS & TERMS
            # ============================================================
            tenant.min_loan_amount = Decimal('5000.00')      # RD$5,000 mínimo
            tenant.max_loan_amount = Decimal('500000.00')    # RD$500,000 máximo
            tenant.default_loan_term_months = 12             # 1 año por defecto
            tenant.min_loan_term_months = 3                  # 3 meses mínimo
            tenant.max_loan_term_months = 60                 # 5 años máximo

            # ============================================================
            # LOAN DEFAULTS
            # ============================================================
            tenant.default_payment_frequency = 'monthly'     # Pagos mensuales
            tenant.default_loan_type = 'personal'            # Préstamos personales
            tenant.default_grace_period_days = 5             # 5 días de gracia
            tenant.enabled_loan_types = [
                'personal',
                'business',
                'auto',
                'education'
            ]

            # ============================================================
            # AUTO-APPROVAL
            # ============================================================
            tenant.enable_auto_approval = True
            tenant.auto_approval_max_amount = Decimal('25000.00')  # Auto-aprobar hasta RD$25,000

            # ============================================================
            # COLLATERAL & GUARANTOR
            # ============================================================
            tenant.require_collateral_default = False
            tenant.collateral_required_above = Decimal('100000.00')  # Colateral para >RD$100k
            tenant.require_guarantor = False
            tenant.guarantor_required_above = Decimal('200000.00')   # Garante para >RD$200k

            # ============================================================
            # DISBURSEMENT
            # ============================================================
            tenant.require_disbursement_approval = True
            tenant.allow_partial_disbursement = True

            # ============================================================
            # PAYMENT METHODS
            # ============================================================
            tenant.accepted_payment_methods = [
                'cash',
                'bank_transfer',
                'check',
                'card'
            ]
            tenant.enable_cash_payments = True
            tenant.enable_check_payments = True
            tenant.enable_bank_transfer_payments = True
            tenant.enable_card_payments = True
            tenant.enable_mobile_payments = False

            # ============================================================
            # CREDIT SCORE
            # ============================================================
            tenant.require_credit_score = False
            tenant.minimum_credit_score = 500
            tenant.credit_score_for_auto_approval = 650

            # ============================================================
            # CURRENCY
            # ============================================================
            tenant.default_currency = 'DOP'  # Peso Dominicano
            tenant.allow_multiple_currencies = True
            tenant.supported_currencies = ['DOP', 'USD']

            # ============================================================
            # DOCUMENT REQUIREMENTS
            # ============================================================
            tenant.require_id_document = True
            tenant.require_proof_of_income = True
            tenant.require_proof_of_address = True
            tenant.require_bank_statement = False
            tenant.require_employment_letter = False
            tenant.enhanced_verification_amount = Decimal('100000.00')  # >RD$100k
            tenant.enhanced_verification_documents = [
                'bank_statement',
                'employment_letter',
                'tax_return'
            ]

            # ============================================================
            # ADDITIONAL LOAN SETTINGS
            # ============================================================
            tenant.allow_early_repayment = True
            tenant.early_repayment_penalty = Decimal('2.00')  # 2% penalidad
            tenant.max_active_loans_per_customer = 3

            # ============================================================
            # LATE FEES
            # ============================================================
            tenant.late_fee_type = 'percentage'
            tenant.late_fee_percentage = Decimal('5.00')      # 5% de mora
            tenant.late_fee_fixed_amount = Decimal('0.00')
            tenant.late_fee_frequency = 'monthly'
            tenant.grace_period_days = 5                      # 5 días de gracia

            # ============================================================
            # NOTIFICATIONS
            # ============================================================
            tenant.enable_email_reminders = True
            tenant.enable_sms_reminders = True
            tenant.enable_whatsapp_reminders = True
            tenant.reminder_days_before = 3
            tenant.notification_email_from = 'prestamos@caproinsa.com'

            # Save all changes
            tenant.save()

            self.stdout.write(self.style.SUCCESS('✓ Successfully configured Caproinsa tenant with test data!'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Configuration Summary:'))
            self.stdout.write(f'  • Interest Rate: {tenant.min_interest_rate}% - {tenant.max_interest_rate}% (default: {tenant.default_interest_rate}%)')
            self.stdout.write(f'  • Loan Amount: {tenant.default_currency} {tenant.min_loan_amount.amount:,.2f} - {tenant.default_currency} {tenant.max_loan_amount.amount:,.2f}')
            self.stdout.write(f'  • Loan Terms: {tenant.min_loan_term_months} - {tenant.max_loan_term_months} months')
            self.stdout.write(f'  • Auto-Approval: Enabled up to {tenant.default_currency} {tenant.auto_approval_max_amount.amount:,.2f}')
            self.stdout.write(f'  • Payment Methods: {", ".join(tenant.accepted_payment_methods)}')
            self.stdout.write(f'  • Default Currency: {tenant.default_currency}')
            self.stdout.write(f'  • Late Fee: {tenant.late_fee_percentage}% per month')
            self.stdout.write(f'  • Notifications: Email, SMS, WhatsApp enabled')

        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR('Error: Caproinsa tenant not found!'))
            self.stdout.write('Available tenants:')
            for t in Tenant.objects.exclude(schema_name='public'):
                self.stdout.write(f'  - {t.schema_name} ({t.business_name})')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
