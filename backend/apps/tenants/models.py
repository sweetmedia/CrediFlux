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
