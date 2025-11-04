"""
Tenant models for multi-tenant architecture
"""
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from djmoney.models.fields import MoneyField
from decimal import Decimal


class Tenant(TenantMixin):
    """
    Tenant model representing a company/organization using the platform.
    Each tenant has its own isolated database schema.
    """
    name = models.CharField(max_length=100, unique=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Business information
    business_name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Address
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    # Settings
    is_active = models.BooleanField(default=True)
    max_users = models.IntegerField(default=10)
    subscription_plan = models.CharField(
        max_length=50,
        choices=[
            ('basic', 'Basic'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='basic'
    )

    # Logo and branding
    logo = models.ImageField(upload_to='tenants/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#6366f1')

    # ============================================================
    # LATE FEE CONFIGURATION (Configuración de Mora)
    # ============================================================
    late_fee_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Porcentaje del Saldo'),
            ('fixed', 'Monto Fijo'),
            ('none', 'Sin Mora'),
        ],
        default='percentage',
        help_text='Tipo de cargo por mora'
    )

    late_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text='Porcentaje de mora (ej: 5.00 = 5% del saldo vencido)'
    )

    late_fee_fixed_amount = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('0.00'),
        help_text='Monto fijo de mora'
    )

    late_fee_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Por Día'),
            ('monthly', 'Por Mes'),
            ('one_time', 'Único al Vencer'),
        ],
        default='monthly',
        help_text='Frecuencia de aplicación de mora'
    )

    grace_period_days = models.IntegerField(
        default=0,
        help_text='Días de gracia antes de aplicar mora (ej: 3 días)'
    )

    # ============================================================
    # NOTIFICATION CONFIGURATION (Configuración de Notificaciones)
    # ============================================================
    enable_email_reminders = models.BooleanField(
        default=True,
        help_text='Enviar recordatorios por email'
    )

    enable_sms_reminders = models.BooleanField(
        default=False,
        help_text='Enviar recordatorios por SMS (requiere configuración de API)'
    )

    enable_whatsapp_reminders = models.BooleanField(
        default=True,
        help_text='Enviar recordatorios por WhatsApp (requiere configuración de API)'
    )

    reminder_days_before = models.IntegerField(
        default=3,
        help_text='Días antes del vencimiento para enviar recordatorio'
    )

    # Email configuration
    notification_email_from = models.EmailField(
        blank=True,
        null=True,
        help_text='Email desde donde se envían notificaciones (opcional)'
    )

    # ============================================================
    # WHATSAPP API CONFIGURATION (Configuración de WhatsApp Cloud API)
    # ============================================================
    whatsapp_phone_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='WhatsApp Phone Number ID from Meta Business'
    )

    whatsapp_token = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='WhatsApp Access Token from Meta Business (encriptado)'
    )

    whatsapp_business_account_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='WhatsApp Business Account ID'
    )

    whatsapp_verify_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Webhook Verify Token (para validar webhooks)'
    )

    # ============================================================
    # PAYMENT GATEWAY CONFIGURATION (Pasarelas de Pago)
    # ============================================================
    enable_stripe = models.BooleanField(
        default=False,
        help_text='Habilitar pagos con Stripe (principalmente USA)'
    )

    stripe_public_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Stripe Publishable Key'
    )

    stripe_secret_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Stripe Secret Key (encriptada)'
    )

    enable_paypal = models.BooleanField(
        default=False,
        help_text='Habilitar pagos con PayPal (principalmente USA)'
    )

    paypal_client_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='PayPal Client ID'
    )

    paypal_client_secret = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='PayPal Client Secret (encriptada)'
    )

    paypal_mode = models.CharField(
        max_length=20,
        choices=[
            ('sandbox', 'Sandbox (Pruebas)'),
            ('live', 'Live (Producción)'),
        ],
        default='sandbox',
        help_text='Modo de operación de PayPal'
    )

    # ============================================================
    # AUTOMATED REPORTS (Reportes Automáticos)
    # ============================================================
    enable_automated_reports = models.BooleanField(
        default=False,
        help_text='Enviar reportes automáticos por email'
    )

    report_recipients = models.TextField(
        blank=True,
        null=True,
        help_text='Emails para recibir reportes (separados por coma)'
    )

    report_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Diario'),
            ('weekly', 'Semanal'),
            ('monthly', 'Mensual'),
        ],
        default='weekly',
        help_text='Frecuencia de envío de reportes'
    )

    # ============================================================
    # LOAN CONFIGURATION (Configuración de Préstamos)
    # ============================================================

    # Interest Rates (Tasas de Interés)
    default_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        help_text='Tasa de interés anual predeterminada (ej: 12.00 = 12%)'
    )

    min_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text='Tasa de interés anual mínima permitida'
    )

    max_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('36.00'),
        help_text='Tasa de interés anual máxima permitida'
    )

    # Loan Amounts (Montos de Préstamo)
    min_loan_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('100.00'),
        help_text='Monto mínimo de préstamo'
    )

    max_loan_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('50000.00'),
        help_text='Monto máximo de préstamo'
    )

    # Loan Terms (Plazos de Préstamo)
    default_loan_term_months = models.IntegerField(
        default=12,
        help_text='Plazo predeterminado del préstamo en meses'
    )

    min_loan_term_months = models.IntegerField(
        default=1,
        help_text='Plazo mínimo del préstamo en meses'
    )

    max_loan_term_months = models.IntegerField(
        default=60,
        help_text='Plazo máximo del préstamo en meses (5 años)'
    )

    # Payment Frequency (Frecuencia de Pago)
    default_payment_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Diario'),
            ('weekly', 'Semanal'),
            ('biweekly', 'Quincenal'),
            ('monthly', 'Mensual'),
        ],
        default='monthly',
        help_text='Frecuencia de pago predeterminada'
    )

    # Loan Type (Tipo de Préstamo)
    default_loan_type = models.CharField(
        max_length=20,
        choices=[
            ('personal', 'Personal'),
            ('business', 'Empresarial'),
            ('mortgage', 'Hipotecario'),
            ('auto', 'Vehicular'),
            ('education', 'Educativo'),
        ],
        default='personal',
        help_text='Tipo de préstamo predeterminado'
    )

    # Collateral Requirements (Requisitos de Garantía)
    require_collateral_default = models.BooleanField(
        default=False,
        help_text='Requerir colateral/garantía por defecto'
    )

    collateral_required_above = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('10000.00'),
        null=True,
        blank=True,
        help_text='Requerir colateral para préstamos mayores a este monto'
    )

    # Auto-Approval (Auto-aprobación)
    enable_auto_approval = models.BooleanField(
        default=False,
        help_text='Permitir auto-aprobación de préstamos bajo cierto monto'
    )

    auto_approval_max_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('1000.00'),
        null=True,
        blank=True,
        help_text='Monto máximo para auto-aprobación automática'
    )

    # Default Grace Period (Período de Gracia Predeterminado)
    default_grace_period_days = models.IntegerField(
        default=0,
        help_text='Días de gracia predeterminados antes del primer pago'
    )

    # Disbursement Settings (Configuración de Desembolso)
    require_disbursement_approval = models.BooleanField(
        default=True,
        help_text='Requiere aprobación adicional para desembolsar fondos'
    )

    allow_partial_disbursement = models.BooleanField(
        default=False,
        help_text='Permitir desembolsos parciales del préstamo'
    )

    # ============================================================
    # ENABLED LOAN TYPES (Tipos de Préstamo Habilitados)
    # ============================================================
    enabled_loan_types = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de tipos de préstamo habilitados (ej: ["personal", "business", "auto"])'
    )

    # ============================================================
    # ACCEPTED PAYMENT METHODS (Métodos de Pago Aceptados)
    # ============================================================
    accepted_payment_methods = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de métodos de pago aceptados (ej: ["cash", "bank_transfer", "card"])'
    )

    enable_cash_payments = models.BooleanField(
        default=True,
        help_text='Aceptar pagos en efectivo'
    )

    enable_check_payments = models.BooleanField(
        default=True,
        help_text='Aceptar pagos con cheque'
    )

    enable_bank_transfer_payments = models.BooleanField(
        default=True,
        help_text='Aceptar transferencias bancarias'
    )

    enable_card_payments = models.BooleanField(
        default=False,
        help_text='Aceptar pagos con tarjeta de crédito/débito'
    )

    enable_mobile_payments = models.BooleanField(
        default=False,
        help_text='Aceptar pagos móviles (ej: Yappy, ACH móvil)'
    )

    # ============================================================
    # CREDIT SCORE REQUIREMENTS (Requisitos de Score Crediticio)
    # ============================================================
    require_credit_score = models.BooleanField(
        default=False,
        help_text='Requerir score crediticio para aprobación'
    )

    minimum_credit_score = models.IntegerField(
        default=300,
        help_text='Score crediticio mínimo requerido (300-850)'
    )

    credit_score_for_auto_approval = models.IntegerField(
        default=700,
        null=True,
        blank=True,
        help_text='Score crediticio mínimo para auto-aprobación'
    )

    # ============================================================
    # CURRENCY SETTINGS (Configuración de Moneda)
    # ============================================================
    default_currency = models.CharField(
        max_length=3,
        default='USD',
        choices=[
            ('USD', 'US Dollar ($)'),
            ('DOP', 'Dominican Peso (RD$)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
        ],
        help_text='Moneda predeterminada para préstamos'
    )

    currency_symbol = models.CharField(
        max_length=10,
        default='$',
        help_text='Símbolo de la moneda (ej: $, RD$, €, £)'
    )

    allow_multiple_currencies = models.BooleanField(
        default=False,
        help_text='Permitir préstamos en múltiples monedas'
    )

    supported_currencies = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de monedas soportadas (ej: ["USD", "DOP", "EUR"])'
    )

    # ============================================================
    # DOCUMENT REQUIREMENTS (Requisitos de Documentos)
    # ============================================================
    require_id_document = models.BooleanField(
        default=True,
        help_text='Requerir documento de identificación'
    )

    require_proof_of_income = models.BooleanField(
        default=True,
        help_text='Requerir comprobante de ingresos'
    )

    require_proof_of_address = models.BooleanField(
        default=False,
        help_text='Requerir comprobante de domicilio'
    )

    require_bank_statement = models.BooleanField(
        default=False,
        help_text='Requerir estado de cuenta bancario'
    )

    require_employment_letter = models.BooleanField(
        default=False,
        help_text='Requerir carta de empleo'
    )

    # Document requirements by loan amount
    enhanced_verification_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('5000.00'),
        null=True,
        blank=True,
        help_text='Monto a partir del cual se requiere verificación adicional de documentos'
    )

    enhanced_verification_documents = models.JSONField(
        default=list,
        blank=True,
        help_text='Documentos adicionales requeridos para montos altos (ej: ["bank_statement", "tax_return"])'
    )

    # ============================================================
    # ADDITIONAL LOAN SETTINGS (Configuraciones Adicionales)
    # ============================================================
    allow_early_repayment = models.BooleanField(
        default=True,
        help_text='Permitir pago anticipado del préstamo'
    )

    early_repayment_penalty = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Penalidad por pago anticipado (porcentaje del saldo restante)'
    )

    require_guarantor = models.BooleanField(
        default=False,
        help_text='Requerir garante/fiador para préstamos'
    )

    guarantor_required_above = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=Decimal('10000.00'),
        null=True,
        blank=True,
        help_text='Requerir garante para préstamos mayores a este monto'
    )

    max_active_loans_per_customer = models.IntegerField(
        default=3,
        help_text='Número máximo de préstamos activos por cliente'
    )

    # Automatically create schema on save
    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_on']

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    """
    Domain model linking domains/subdomains to tenants.
    Example: company1.crediflux.com -> Company1 tenant
    """
    pass

    class Meta:
        db_table = 'tenant_domains'

    def __str__(self):
        return self.domain
