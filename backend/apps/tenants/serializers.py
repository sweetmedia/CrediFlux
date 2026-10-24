"""
Serializers for Tenant API endpoints
"""
import logging
import re
import secrets
from datetime import timedelta

from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import schema_exists
from apps.core.media import LEGACY_TOP_DIRS, PUBLIC_SCHEMA, SignedImageField, signed_media_url
from apps.core.net import client_ip
from apps.users import lockout
from apps.users.tokens import issue_tokens
from .models import Tenant, Domain

User = get_user_model()
logger = logging.getLogger(__name__)

# Mensaje único para cualquier dato ya existente o reservado: no revela si
# lo que choca es el correo, el nombre del tenant o el subdominio.
REGISTRATION_REJECTED = 'No se pudo completar el registro con estos datos.'

RESERVED_TENANT_NAMES = {
    'public', 'pg-catalog', 'pg-toast', 'information-schema', 'www', 'admin',
    'api', 'app', 'mail', 'ftp', 'localhost', 'test', 'media', 'static',
    # Carpetas antiguas de media (customer_documents → customer-documents, etc.).
    *(name.replace('_', '-') for name in LEGACY_TOP_DIRS),
}
_RESERVED_SCHEMAS = {name.replace('-', '_') for name in RESERVED_TENANT_NAMES}

# Nombre del tenant = schema de PostgreSQL: letra inicial, máximo 63 caracteres.
TENANT_NAME_RE = re.compile(r'[a-z][a-z0-9-]{0,62}')
TENANT_NAME_FORMAT_ERROR = (
    'El nombre del tenant debe empezar con una letra minúscula y contener sólo letras '
    'minúsculas, números y guiones (máximo 63 caracteres).'
)


def schema_name_for(tenant_name):
    """Schema de PostgreSQL derivado del nombre del tenant (guiones → guiones bajos)."""
    return tenant_name.replace('-', '_')


def _schema_unavailable(schema_name):
    return (
        schema_name in _RESERVED_SCHEMAS
        or schema_name.startswith('pg_')
        or Tenant.objects.filter(schema_name=schema_name).exists()
        or schema_exists(schema_name)
    )


def _available_username(email):
    """Prefijo del correo como username; si ya existe, con un sufijo aleatorio.

    El login es por correo: el username sólo debe ser único. Comprobarlo antes de crear
    el tenant evita aprovisionar un schema entero para revertirlo por un IntegrityError.
    """
    base = email.split('@')[0][:140]
    candidate = base
    for _ in range(10):
        if not User.objects.filter(username__iexact=candidate).exists():
            return candidate
        candidate = f'{base}-{secrets.token_hex(3)}'
    raise serializers.ValidationError(REGISTRATION_REJECTED)


def _spend_daily_budget(key, ttl=60 * 60 * 25):
    """Suma un intento al contador del día en la caché y devuelve el total.

    La caché no participa de la transacción: un alta que falla y se revierte después de
    aprovisionar el schema sigue contando.
    """
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:  # la clave caducó entre add e incr
        cache.set(key, 1, ttl)
        return 1


class TenantRegistrationSerializer(serializers.Serializer):
    """
    Serializer for registering a new tenant (company) with owner user.

    This creates:
    - A new Tenant
    - A Domain for the tenant
    - An owner User for the tenant
    """

    # Tenant Information
    business_name = serializers.CharField(
        max_length=255,
        help_text="Business/Company name"
    )
    tenant_name = serializers.CharField(
        max_length=100,
        help_text="Unique identifier for the tenant (e.g., 'acme-corp')"
    )
    tax_id = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Tax ID or business registration number"
    )
    email = serializers.EmailField(
        help_text="Company email address"
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Company phone number"
    )

    # Address Information
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Company address"
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    state = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    postal_code = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    # Domain Information
    subdomain = serializers.CharField(
        max_length=100,
        help_text="Subdomain for this tenant (e.g., 'acme' for acme.crediflux.com)"
    )

    # Owner User Information
    owner_first_name = serializers.CharField(
        max_length=150,
        help_text="Owner's first name"
    )
    owner_last_name = serializers.CharField(
        max_length=150,
        help_text="Owner's last name"
    )
    owner_email = serializers.EmailField(
        help_text="Owner's email address (will be used for login)"
    )
    owner_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Owner's password (minimum 8 characters)"
    )
    owner_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        help_text="Owner's phone number"
    )

    # Subscription Plan
    subscription_plan = serializers.ChoiceField(
        choices=['basic', 'professional', 'enterprise'],
        default='basic',
        help_text="Subscription plan for the tenant"
    )

    def validate_tenant_name(self, value):
        """Formato del nombre (la existencia se comprueba en `validate`, con mensaje genérico).

        Es también el nombre del schema (guiones → guiones bajos): PostgreSQL limita los
        identificadores a 63 caracteres y uno que empieza por dígito no sirve sin comillas.
        Se valida antes de crear nada para no fallar a mitad del CREATE SCHEMA.
        """
        value = (value or '').strip().lower()
        if not TENANT_NAME_RE.fullmatch(value):
            raise serializers.ValidationError(TENANT_NAME_FORMAT_ERROR)
        return value

    def validate_subdomain(self, value):
        """Formato del subdominio (la existencia se comprueba en `validate`)."""
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens."
            )
        return value.lower()

    def validate_owner_password(self, value):
        """Aplica los validadores de fortaleza (incluida la similitud con nombre y correo)."""
        data = self.initial_data
        candidate = User(
            email=data.get('owner_email', ''),
            first_name=data.get('owner_first_name', ''),
            last_name=data.get('owner_last_name', ''),
        )
        lockout.validate_strength(value, user=candidate)
        return value

    def validate(self, attrs):
        """Existencia y nombres reservados, todos con el mismo error no atribuible."""
        tenant_name = attrs['tenant_name']
        subdomain = attrs['subdomain']
        if (
            tenant_name in RESERVED_TENANT_NAMES
            or subdomain in RESERVED_TENANT_NAMES
            or _schema_unavailable(schema_name_for(tenant_name))
            or Tenant.objects.filter(name=tenant_name).exists()
            or Domain.objects.filter(domain__icontains=subdomain).exists()
            or User.objects.filter(email__iexact=attrs['owner_email']).exists()
        ):
            raise serializers.ValidationError(REGISTRATION_REJECTED)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Create tenant, domain, and owner user in a transaction.
        """
        # Extract data
        # Generate schema_name from tenant_name (replace hyphens with underscores for PostgreSQL)
        tenant_name = validated_data['tenant_name']
        schema_name = schema_name_for(tenant_name)

        tenant_data = {
            'name': tenant_name,
            'schema_name': schema_name,
            'business_name': validated_data['business_name'],
            'email': validated_data['email'],
            'tax_id': validated_data.get('tax_id', ''),
            'phone': validated_data.get('phone', ''),
            'address': validated_data.get('address', ''),
            'city': validated_data.get('city', ''),
            'state': validated_data.get('state', ''),
            'country': validated_data.get('country', ''),
            'postal_code': validated_data.get('postal_code', ''),
            'subscription_plan': validated_data.get('subscription_plan', 'basic'),
            'is_active': True,
        }

        subdomain = validated_data['subdomain']

        owner_data = {
            'first_name': validated_data['owner_first_name'],
            'last_name': validated_data['owner_last_name'],
            'email': validated_data['owner_email'],
            'password': validated_data['owner_password'],
            'phone': validated_data.get('owner_phone', ''),
        }

        # Force connection to public schema for tenant creation
        connection.set_schema_to_public()

        # Tope global diario y re-comprobación dentro de la transacción
        # (otra petición pudo crear el mismo schema tras `validate`).
        since = timezone.now() - timedelta(days=1)
        if Tenant.objects.filter(created_on__gte=since).count() >= settings.MAX_TENANTS_PER_DAY:
            raise serializers.ValidationError(REGISTRATION_REJECTED)
        if _schema_unavailable(schema_name) or Tenant.objects.filter(name=tenant_name).exists():
            raise serializers.ValidationError(REGISTRATION_REJECTED)
        username = _available_username(owner_data['email'])

        # Presupuesto por cliente antes del global: un solo cliente no agota el tope de
        # todos, y quien ya gastó el suyo no sigue gastando el global.
        day = f'{timezone.now():%Y%m%d}'
        ip = client_ip(self.context.get('request'))
        if _spend_daily_budget(f'tenant_provisioning_ip:{ip}:{day}') > settings.MAX_TENANTS_PER_IP_PER_DAY:
            raise serializers.ValidationError(REGISTRATION_REJECTED)
        # Cada aprovisionamiento gasta el tope del día, también si luego se revierte.
        if _spend_daily_budget(f'tenant_provisioning:{day}') > settings.MAX_TENANTS_PER_DAY:
            logger.warning('Tope diario de registros de tenants alcanzado (MAX_TENANTS_PER_DAY=%s)',
                           settings.MAX_TENANTS_PER_DAY)
            raise serializers.ValidationError(REGISTRATION_REJECTED)

        # 1. Create Tenant
        tenant = Tenant.objects.create(**tenant_data)

        # 2. Create Domain
        # Use localhost for development, or configure based on environment
        base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
        domain_name = f"{subdomain}.{base_domain}" if base_domain != 'localhost' else subdomain

        domain = Domain.objects.create(
            domain=domain_name,
            tenant=tenant,
            is_primary=True
        )

        # 3. Create Owner User (username libre elegido antes de aprovisionar)
        owner = User.objects.create_user(
            username=username,
            email=owner_data['email'],
            password=owner_data['password'],
            first_name=owner_data['first_name'],
            last_name=owner_data['last_name'],
            phone=owner_data['phone'],
            tenant=tenant,
            is_tenant_owner=True,
            role='admin',
            is_staff=True,  # Allow access to admin panel
            is_active=True,
            email_verified=False,  # Will need email verification
        )

        return {
            'tenant': tenant,
            'domain': domain,
            'owner': owner,
        }

    def to_representation(self, instance):
        """
        Return formatted response with tenant and user information
        """
        return {
            'tenant': {
                'id': instance['tenant'].id,
                'name': instance['tenant'].name,
                'business_name': instance['tenant'].business_name,
                'email': instance['tenant'].email,
                'subscription_plan': instance['tenant'].subscription_plan,
                'is_active': instance['tenant'].is_active,
            },
            'domain': {
                'domain': instance['domain'].domain,
                'is_primary': instance['domain'].is_primary,
            },
            'owner': {
                'id': instance['owner'].id,
                'email': instance['owner'].email,
                'first_name': instance['owner'].first_name,
                'last_name': instance['owner'].last_name,
                'is_tenant_owner': instance['owner'].is_tenant_owner,
            },
            'message': 'Tenant registered successfully! Please check your email to verify your account.',
            'next_steps': [
                'Verify your email address',
                'Login to your tenant admin panel',
                'Start creating loans and managing customers'
            ]
        }


class TenantSerializer(serializers.ModelSerializer):
    """Basic tenant serializer for read operations"""
    logo = SignedImageField(read_only=True, schema=PUBLIC_SCHEMA)
    has_ai_api_key = serializers.SerializerMethodField()
    has_whatsapp_token = serializers.SerializerMethodField()
    has_whatsapp_verify_token = serializers.SerializerMethodField()
    has_smtp_password = serializers.SerializerMethodField()
    has_imap_password = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            # Basic Info
            'id', 'name', 'schema_name', 'business_name', 'tax_id',
            'email', 'phone', 'address', 'city', 'state', 'country',
            'postal_code', 'is_active', 'max_users', 'subscription_plan',
            'logo', 'primary_color', 'created_on', 'updated_on',

            # Loan Configuration
            'default_interest_rate', 'min_interest_rate', 'max_interest_rate',
            'min_loan_amount', 'min_loan_amount_currency',
            'max_loan_amount', 'max_loan_amount_currency',
            'default_loan_term_months', 'min_loan_term_months', 'max_loan_term_months',
            'default_payment_frequency', 'default_loan_type',
            'require_collateral_default', 'collateral_required_above', 'collateral_required_above_currency',
            'enable_auto_approval', 'auto_approval_max_amount', 'auto_approval_max_amount_currency',
            'default_grace_period_days', 'require_disbursement_approval', 'allow_partial_disbursement',

            # Enabled Loan Types
            'enabled_loan_types',

            # Payment Methods
            'accepted_payment_methods', 'enable_cash_payments', 'enable_check_payments',
            'enable_bank_transfer_payments', 'enable_card_payments', 'enable_mobile_payments',

            # Credit Score Requirements
            'require_credit_score', 'minimum_credit_score', 'credit_score_for_auto_approval',

            # Currency Settings
            'default_currency', 'currency_symbol', 'allow_multiple_currencies', 'supported_currencies',

            # Document Requirements
            'require_id_document', 'require_proof_of_income', 'require_proof_of_address',
            'require_bank_statement', 'require_employment_letter',
            'enhanced_verification_amount', 'enhanced_verification_amount_currency',
            'enhanced_verification_documents',

            # Additional Loan Settings
            'allow_early_repayment', 'early_repayment_penalty',
            'require_guarantor', 'guarantor_required_above', 'guarantor_required_above_currency',
            'max_active_loans_per_customer',

            # Late Fee Configuration
            'late_fee_type', 'late_fee_percentage', 'late_fee_fixed_amount',
            'late_fee_fixed_amount_currency', 'late_fee_frequency', 'grace_period_days',

            # Notification Configuration
            'enable_email_reminders', 'enable_sms_reminders', 'enable_whatsapp_reminders',
            'reminder_days_before', 'notification_email_from',

            # AI Assistant Configuration
            'enable_ai_assistant', 'ai_provider', 'ai_model', 'has_ai_api_key',

            # WhatsApp API Configuration
            'whatsapp_phone_id', 'has_whatsapp_token', 'whatsapp_business_account_id',
            'has_whatsapp_verify_token',

            # SMTP/IMAP Email Configuration
            'smtp_host', 'smtp_port', 'smtp_username', 'has_smtp_password', 'smtp_use_tls', 'smtp_use_ssl',
            'imap_host', 'imap_port', 'imap_username', 'has_imap_password', 'imap_use_ssl',
        ]
        read_only_fields = ['id', 'schema_name', 'created_on', 'updated_on']

    def get_has_ai_api_key(self, obj):
        return bool(obj.ai_api_key)

    def get_has_whatsapp_token(self, obj):
        return bool(obj.whatsapp_token)

    def get_has_whatsapp_verify_token(self, obj):
        return bool(obj.whatsapp_verify_token)

    def get_has_smtp_password(self, obj):
        return bool(obj.smtp_password)

    def get_has_imap_password(self, obj):
        return bool(obj.imap_password)


class TenantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tenant settings"""
    logo = SignedImageField(required=False, allow_null=True, schema=PUBLIC_SCHEMA)

    class Meta:
        model = Tenant
        fields = [
            # Basic Info
            'business_name', 'tax_id', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'logo', 'primary_color',

            # Loan Configuration
            'default_interest_rate', 'min_interest_rate', 'max_interest_rate',
            'min_loan_amount', 'max_loan_amount',
            'default_loan_term_months', 'min_loan_term_months', 'max_loan_term_months',
            'default_payment_frequency', 'default_loan_type',
            'require_collateral_default', 'collateral_required_above',
            'enable_auto_approval', 'auto_approval_max_amount',
            'default_grace_period_days', 'require_disbursement_approval', 'allow_partial_disbursement',

            # Enabled Loan Types
            'enabled_loan_types',

            # Payment Methods
            'accepted_payment_methods', 'enable_cash_payments', 'enable_check_payments',
            'enable_bank_transfer_payments', 'enable_card_payments', 'enable_mobile_payments',

            # Credit Score Requirements
            'require_credit_score', 'minimum_credit_score', 'credit_score_for_auto_approval',

            # Currency Settings
            'default_currency', 'currency_symbol', 'allow_multiple_currencies', 'supported_currencies',

            # Document Requirements
            'require_id_document', 'require_proof_of_income', 'require_proof_of_address',
            'require_bank_statement', 'require_employment_letter',
            'enhanced_verification_amount', 'enhanced_verification_documents',

            # Additional Loan Settings
            'allow_early_repayment', 'early_repayment_penalty',
            'require_guarantor', 'guarantor_required_above',
            'max_active_loans_per_customer',

            # Late Fee Configuration
            'late_fee_type', 'late_fee_percentage', 'late_fee_fixed_amount',
            'late_fee_frequency', 'grace_period_days',

            # Notification Configuration
            'enable_email_reminders', 'enable_sms_reminders', 'enable_whatsapp_reminders',
            'reminder_days_before', 'notification_email_from',

            # AI Assistant Configuration
            'enable_ai_assistant', 'ai_provider', 'ai_model', 'ai_api_key',

            # WhatsApp API Configuration
            'whatsapp_phone_id', 'whatsapp_token', 'whatsapp_business_account_id',
            'whatsapp_verify_token',

            # SMTP/IMAP Email Configuration
            'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls', 'smtp_use_ssl',
            'imap_host', 'imap_port', 'imap_username', 'imap_password', 'imap_use_ssl',
        ]
        # La unicidad de whatsapp_phone_id la valida validate_whatsapp_phone_id
        # (normaliza vacío a NULL y responde en español).
        extra_kwargs = {'whatsapp_phone_id': {'validators': []}}

    def validate_email(self, value):
        """Validate email format"""
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_business_name(self, value):
        """Validate business name"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Business name must be at least 2 characters long.")
        return value

    def validate_whatsapp_phone_id(self, value):
        """Vacío se guarda como NULL; un phone_number_id sólo puede pertenecer a un tenant."""
        value = (value or '').strip()
        if not value:
            return None
        others = Tenant.objects.filter(whatsapp_phone_id=value)
        if self.instance is not None:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError('Este phone_number_id ya está en uso.')
        return value

    def validate_primary_color(self, value):
        """Validate hex color format"""
        if value:
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
                raise serializers.ValidationError("Primary color must be a valid hex color (e.g., #6366f1).")
        return value

    POLICY_RANGES = (
        ('min_interest_rate', 'max_interest_rate', 'La tasa mínima no puede ser mayor que la tasa máxima.'),
        ('min_loan_amount', 'max_loan_amount', 'El monto mínimo no puede ser mayor que el monto máximo.'),
        ('min_loan_term_months', 'max_loan_term_months', 'El plazo mínimo no puede ser mayor que el plazo máximo.'),
    )
    NON_NEGATIVE_AMOUNTS = (
        'min_loan_amount', 'max_loan_amount', 'collateral_required_above',
        'guarantor_required_above', 'auto_approval_max_amount', 'enhanced_verification_amount',
    )

    def validate(self, attrs):
        """Coherencia de la política de originación (los valores ausentes salen de la instancia)."""
        def current(field):
            if field in attrs:
                value = attrs[field]
            else:
                value = getattr(self.instance, field, None)
            return getattr(value, 'amount', value)

        errors = {}
        for field in self.NON_NEGATIVE_AMOUNTS:
            value = current(field)
            if value is not None and value < 0:
                errors[field] = 'El monto no puede ser negativo.'

        for low_field, high_field, message in self.POLICY_RANGES:
            low, high = current(low_field), current(high_field)
            if low_field not in errors and low is not None and high is not None and low > high:
                errors[low_field] = message

        max_loans = current('max_active_loans_per_customer')
        if max_loans is not None and max_loans < 1:
            errors['max_active_loans_per_customer'] = 'Debe permitir al menos 1 préstamo activo por cliente.'

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def update(self, instance, validated_data):
        """Custom update to handle logo deletion and schema switching"""
        from django.db import connection

        # Handle logo deletion explicitly
        if 'logo' in validated_data:
            logo_value = validated_data.get('logo')
            # Check if logo is being deleted (None or empty string)
            if logo_value is None or logo_value == '':
                if instance.logo:
                    # Delete the old logo file
                    try:
                        instance.logo.delete(save=False)
                    except Exception:
                        pass  # File may not exist
                # Set logo to None (not empty string)
                instance.logo = None
                validated_data.pop('logo')

        # Switch to public schema to update tenant
        # Tenants can only be updated from public schema
        connection.set_schema_to_public()

        try:
            # Update other fields
            return super().update(instance, validated_data)
        finally:
            # Switch back to tenant schema
            if instance.schema_name:
                connection.set_schema(instance.schema_name)


class TenantLoginSerializer(serializers.Serializer):
    """
    Serializer for tenant user login with JWT tokens.

    Validates user credentials and ensures:
    - User exists and credentials are correct
    - User is active
    - User belongs to an active tenant
    - Returns JWT tokens and user/tenant information
    """

    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        help_text="User's password"
    )

    # Read-only fields returned in response
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    tenant = serializers.SerializerMethodField()

    def get_user(self, obj):
        """Return user information"""
        user = obj.get('user')
        if user:
            return {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'role': user.role,
                'is_tenant_owner': user.is_tenant_owner,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_2fa_enabled': user.is_2fa_enabled,
            }
        return None

    def get_tenant(self, obj):
        """Return tenant information"""
        tenant = obj.get('tenant')
        if tenant:
            # Get primary domain
            domain = tenant.get_primary_domain()
            domain_name = domain.domain if domain else None

            return {
                'id': tenant.id,
                'name': tenant.name,
                'business_name': tenant.business_name,
                'subscription_plan': tenant.subscription_plan,
                'is_active': tenant.is_active,
                'domain': domain_name,
                'logo': signed_media_url(tenant.logo.name, PUBLIC_SCHEMA) if tenant.logo else None,
                'primary_color': tenant.primary_color,
            }
        return None

    def validate(self, attrs):
        """
        Validate user credentials and tenant status.

        SECURITY: Ensures user can only login to their assigned tenant domain.
        """
        import logging
        logger = logging.getLogger(__name__)

        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        # Cuenta el intento y aplica el límite por cuenta y por IP (antes de authenticate)
        request = self.context.get('request')
        lockout.check_and_count(email, request)

        # Authenticate user
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        lockout.reset(email, request)

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError(
                "This account has been deactivated. Please contact support."
            )

        # Check if user has a tenant (not a system admin)
        if not user.tenant and not user.is_superuser:
            raise serializers.ValidationError(
                "Your account is not associated with any tenant. Please contact support."
            )

        # Check if tenant is active (if user has a tenant)
        if user.tenant and not user.tenant.is_active:
            raise serializers.ValidationError(
                "Your tenant account has been deactivated. Please contact support."
            )

        # ========================================================================
        # CRITICAL SECURITY CHECK: Verify user belongs to current tenant
        # ========================================================================
        # Get current tenant from request context
        request = self.context.get('request')
        current_tenant = getattr(request, 'tenant', None)

        # Sin correo ni schema en WARNING: este es el camino de cada login (Global Constraint).
        if user.is_superuser and user.tenant is None:
            pass  # Los admins de plataforma (sin tenant) pueden entrar por cualquier dominio.
        else:
            # Validate user belongs to current tenant
            if current_tenant and user.tenant != current_tenant:
                logger.info(
                    'Login bloqueado: el usuario %s no pertenece al tenant %s',
                    user.pk, current_tenant.pk,
                )
                raise serializers.ValidationError(
                    "Invalid credentials for this organization. "
                    "Please ensure you are using the correct login portal."
                )

            # If no tenant in request (public schema), only allow system admins
            if not current_tenant and user.tenant is not None:
                logger.info('Login bloqueado: usuario %s de tenant en el schema público', user.pk)
                raise serializers.ValidationError(
                    "Invalid credentials for this portal. "
                    "Please use your organization's specific domain."
                )

        # Check if user has 2FA enabled
        if user.is_2fa_enabled:
            import secrets
            from django.core.cache import cache

            # Generate temporary token for 2FA verification
            temp_token = secrets.token_urlsafe(32)

            # Store user ID in cache for 5 minutes
            cache.set(f'2fa_pending_{temp_token}', str(user.pk), timeout=300)

            logger.debug("Login: segundo factor requerido")

            return {
                'requires_2fa': True,
                'temp_token': temp_token,
                'user': user,
                'tenant': user.tenant,
            }

        # Generate JWT tokens (no 2FA required)
        refresh = issue_tokens(user)

        # Update last login
        from django.utils import timezone
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])

        return {
            'user': user,
            'tenant': user.tenant,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        }

    def to_representation(self, instance):
        """
        Return formatted response with tokens and user/tenant info.
        If 2FA is required, returns temp_token instead of JWT tokens.
        """
        # Check if 2FA is required
        if instance.get('requires_2fa'):
            return {
                'requires_2fa': True,
                'temp_token': instance.get('temp_token'),
                'message': 'Two-factor authentication required. Please provide your verification code.',
            }

        # Normal login response
        return {
            'access_token': instance.get('access_token'),
            'refresh_token': instance.get('refresh_token'),
            'user': self.get_user(instance),
            'tenant': self.get_tenant(instance),
            'message': 'Login successful',
        }
