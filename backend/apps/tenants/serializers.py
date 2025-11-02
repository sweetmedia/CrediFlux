"""
Serializers for Tenant API endpoints
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Tenant, Domain

User = get_user_model()


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
        """Validate that tenant name is unique and follows naming rules"""
        # Check if tenant already exists
        if Tenant.objects.filter(name=value).exists():
            raise serializers.ValidationError("A tenant with this name already exists.")

        # Check naming rules (lowercase alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "Tenant name must contain only lowercase letters, numbers, and hyphens."
            )

        return value

    def validate_subdomain(self, value):
        """Validate that subdomain is unique and follows naming rules"""
        # Check if domain already exists
        if Domain.objects.filter(domain__icontains=value).exists():
            raise serializers.ValidationError("This subdomain is already taken.")

        # Check naming rules (lowercase alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens."
            )

        # Reserved subdomains
        reserved = ['www', 'admin', 'api', 'app', 'mail', 'ftp', 'localhost', 'public']
        if value.lower() in reserved:
            raise serializers.ValidationError(f"The subdomain '{value}' is reserved.")

        return value.lower()

    def validate_owner_email(self, value):
        """Validate that owner email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Create tenant, domain, and owner user in a transaction.
        """
        # Extract data
        # Generate schema_name from tenant_name (replace hyphens with underscores for PostgreSQL)
        tenant_name = validated_data['tenant_name']
        schema_name = tenant_name.replace('-', '_')

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

        try:
            # Force connection to public schema for tenant creation
            from django.db import connection
            connection.set_schema_to_public()

            # 1. Create Tenant
            tenant = Tenant.objects.create(**tenant_data)

            # 2. Create Domain
            # Use localhost for development, or configure based on environment
            from django.conf import settings
            base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
            domain_name = f"{subdomain}.{base_domain}" if base_domain != 'localhost' else subdomain

            domain = Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )

            # 3. Create Owner User
            username = owner_data['email'].split('@')[0]  # Use email prefix as username

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

        except Exception as e:
            # Transaction will be rolled back automatically
            raise serializers.ValidationError(f"Failed to create tenant: {str(e)}")

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
    logo = serializers.ImageField(read_only=True)

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
        ]
        read_only_fields = ['id', 'schema_name', 'created_on', 'updated_on']


class TenantUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tenant settings"""
    logo = serializers.ImageField(required=False, allow_null=True)

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
        ]

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

    def validate_primary_color(self, value):
        """Validate hex color format"""
        if value:
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
                raise serializers.ValidationError("Primary color must be a valid hex color (e.g., #6366f1).")
        return value

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
                'logo': tenant.logo.url if tenant.logo else None,
                'primary_color': tenant.primary_color,
            }
        return None

    def validate(self, attrs):
        """
        Validate user credentials and tenant status
        """
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        # Authenticate user
        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

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

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

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
        Return formatted response with tokens and user/tenant info
        """
        return {
            'access_token': instance.get('access_token'),
            'refresh_token': instance.get('refresh_token'),
            'user': self.get_user(instance),
            'tenant': self.get_tenant(instance),
            'message': 'Login successful',
        }
