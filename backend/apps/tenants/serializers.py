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

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'schema_name', 'business_name', 'tax_id',
            'email', 'phone', 'address', 'city', 'state', 'country',
            'postal_code', 'is_active', 'max_users', 'subscription_plan',
            'created_on', 'updated_on'
        ]
        read_only_fields = ['id', 'schema_name', 'created_on', 'updated_on']


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
