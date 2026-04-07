"""
Serializers for user authentication and management
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer

User = get_user_model()


# ============================================================================
# AUTHENTICATION - TENANT-AWARE LOGIN
# ============================================================================

class TenantAwareLoginSerializer(BaseLoginSerializer):
    """
    Custom login serializer that validates user belongs to the current tenant.

    This prevents users from one tenant logging into another tenant's domain.
    Example: A user from caproinsa.localhost cannot login to amsfin.localhost
    """

    def validate(self, attrs):
        """
        Validate credentials and ensure user belongs to current tenant.
        """
        import logging
        logger = logging.getLogger(__name__)

        # First, validate credentials using parent class
        attrs = super().validate(attrs)

        # Get authenticated user
        user = attrs.get('user')

        # Get current tenant from request
        request = self.context.get('request')
        current_tenant = getattr(request, 'tenant', None)

        # DEBUG LOGGING
        logger.warning(f"🔐 TENANT LOGIN VALIDATION")
        logger.warning(f"   User: {user.email}")
        logger.warning(f"   User's Tenant: {user.tenant.schema_name if user.tenant else 'None (System Admin)'}")
        logger.warning(f"   Current Request Tenant: {current_tenant.schema_name if current_tenant else 'None (Public Schema)'}")

        # Superusers with no tenant can access any domain (system admins)
        if user.is_superuser and user.tenant is None:
            logger.warning(f"   ✅ ALLOWED: System admin can access any tenant")
            return attrs

        # Validate user belongs to current tenant
        if current_tenant and user.tenant != current_tenant:
            logger.warning(f"   ❌ BLOCKED: Tenant mismatch!")
            logger.warning(f"   User tenant: {user.tenant.schema_name if user.tenant else None}")
            logger.warning(f"   Request tenant: {current_tenant.schema_name}")
            raise serializers.ValidationError(
                "Invalid credentials for this organization. "
                "Please ensure you are using the correct login portal."
            )

        # If no tenant in request (public schema), only allow system admins
        if not current_tenant and user.tenant is not None:
            logger.warning(f"   ❌ BLOCKED: Tenant user trying to access public schema")
            raise serializers.ValidationError(
                "Invalid credentials for this portal. "
                "Please use your organization's specific domain."
            )

        logger.warning(f"   ✅ ALLOWED: User belongs to this tenant")
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for displaying user information"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    tenant_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar', 'bio', 'job_title', 'department', 'role',
            'tenant', 'tenant_name', 'is_tenant_owner', 'is_staff',
            'is_superuser', 'email_verified', 'receive_notifications',
            'is_2fa_enabled', 'created_at', 'last_login_at'
        ]
        read_only_fields = [
            'id', 'email', 'username', 'tenant', 'is_tenant_owner',
            'is_staff', 'is_superuser', 'email_verified', 'is_2fa_enabled',
            'created_at', 'last_login_at'
        ]


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

class EmailVerificationSendSerializer(serializers.Serializer):
    """Serializer to request email verification"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate that user exists"""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        if user.email_verified:
            raise serializers.ValidationError("Email is already verified.")

        return value

    def save(self):
        """Generate verification token and send email"""
        from urllib.parse import urlparse, urlunparse

        email = self.validated_data['email']
        user = User.objects.get(email=email)

        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Create verification URL with tenant subdomain
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

        # If user belongs to a tenant, add subdomain to URL
        if user.tenant:
            parsed = urlparse(frontend_url)
            tenant_host = f"{user.tenant.schema_name}.{parsed.netloc}"
            frontend_url = urlunparse((
                parsed.scheme,
                tenant_host,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

        verification_url = f"{frontend_url}/verify-email?uid={uid}&token={token}"

        # Send email
        subject = 'Verify your email - CrediFlux'
        message = f"""
        Hello {user.get_full_name()},

        Please click the link below to verify your email address:

        {verification_url}

        If you did not create an account, please ignore this email.

        Best regards,
        The CrediFlux Team
        """

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER or 'noreply@crediflux.com',
            [user.email],
            fail_silently=False,
        )

        return {
            'email': user.email,
            'message': 'Verification email sent successfully.',
            'uid': uid,
            'token': token,  # Only for development/testing
        }


class EmailVerificationConfirmSerializer(serializers.Serializer):
    """Serializer to verify email with token"""
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate token and uid"""
        try:
            # Decode uid
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)

            # Validate token
            if not default_token_generator.check_token(user, attrs['token']):
                raise serializers.ValidationError({
                    'token': 'Invalid or expired verification token.'
                })

            # Check if already verified
            if user.email_verified:
                raise serializers.ValidationError({
                    'email': 'Email is already verified.'
                })

            attrs['user'] = user
            return attrs

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uid': 'Invalid user ID.'
            })

    def save(self):
        """Mark email as verified"""
        user = self.validated_data['user']
        user.email_verified = True
        user.save(update_fields=['email_verified'])

        return {
            'message': 'Email verified successfully.',
            'email': user.email,
            'email_verified': True,
        }


# ============================================================================
# PASSWORD RESET
# ============================================================================

class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer to request password reset"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate that user exists"""
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Don't reveal that user doesn't exist for security
            pass

        return value

    def save(self):
        """Generate reset token and send email"""
        from urllib.parse import urlparse, urlunparse

        email = self.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset URL with tenant subdomain
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

            # If user belongs to a tenant, add subdomain to URL
            if user.tenant:
                parsed = urlparse(frontend_url)
                # Add tenant subdomain to the host
                tenant_host = f"{user.tenant.schema_name}.{parsed.netloc}"
                frontend_url = urlunparse((
                    parsed.scheme,
                    tenant_host,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))

            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"

            # Send email
            subject = 'Reset your password - CrediFlux'
            message = f"""
            Hello {user.get_full_name()},

            You requested to reset your password. Click the link below to create a new password:

            {reset_url}

            If you did not request a password reset, please ignore this email.

            This link will expire in 24 hours.

            Best regards,
            The CrediFlux Team
            """

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER or 'noreply@crediflux.com',
                [user.email],
                fail_silently=False,
            )

            return {
                'message': 'If an account exists with this email, a password reset link has been sent.',
                'uid': uid,
                'token': token,  # Only for development/testing
            }

        except User.DoesNotExist:
            # Return same message for security (don't reveal user doesn't exist)
            return {
                'message': 'If an account exists with this email, a password reset link has been sent.',
            }


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer to confirm password reset with new password"""
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    class Meta:
        ref_name = 'CustomPasswordResetConfirm'

    def validate(self, attrs):
        """Validate token, uid, and password match"""
        # Check passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })

        try:
            # Decode uid
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)

            # Validate token
            if not default_token_generator.check_token(user, attrs['token']):
                raise serializers.ValidationError({
                    'token': 'Invalid or expired reset token.'
                })

            # Check if user is active
            if not user.is_active:
                raise serializers.ValidationError({
                    'non_field_errors': 'This account has been deactivated.'
                })

            attrs['user'] = user
            return attrs

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uid': 'Invalid user ID.'
            })

    def save(self):
        """Set new password"""
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']

        user.set_password(new_password)
        user.save()

        return {
            'message': 'Password has been reset successfully. You can now login with your new password.',
            'email': user.email,
        }


# ============================================================================
# LOGOUT
# ============================================================================

class LogoutSerializer(serializers.Serializer):
    """Serializer to logout user by blacklisting refresh token"""
    refresh_token = serializers.CharField(required=True)

    def validate_refresh_token(self, value):
        """Validate that refresh token is valid"""
        try:
            token = RefreshToken(value)
            # Try to blacklist (will raise error if invalid)
            return value
        except TokenError as e:
            raise serializers.ValidationError(f"Invalid or expired token: {str(e)}")

    def save(self):
        """Blacklist the refresh token"""
        try:
            token = RefreshToken(self.validated_data['refresh_token'])
            token.blacklist()

            return {
                'message': 'Successfully logged out.',
            }
        except Exception as e:
            raise serializers.ValidationError(f"Failed to logout: {str(e)}")


# ============================================================================
# PROFILE MANAGEMENT
# ============================================================================

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer to update user profile"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'avatar',
            'bio', 'job_title', 'department', 'receive_notifications'
        ]

    def validate_phone(self, value):
        """Validate phone number format"""
        # PhoneNumberField handles validation automatically
        # Just return the value, Django will handle the conversion
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer to change password (when user is logged in)"""
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    class Meta:
        ref_name = 'CustomPasswordChange'

    def validate(self, attrs):
        """Validate passwords"""
        # Check new passwords match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })

        # Check current password
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({
                'current_password': 'Current password is incorrect.'
            })

        # Check new password is different
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from current password.'
            })

        return attrs

    def save(self):
        """Update password"""
        user = self.context['request'].user
        new_password = self.validated_data['new_password']

        user.set_password(new_password)
        user.save()

        return {
            'message': 'Password changed successfully.',
        }


# ============================================================================
# TEAM MANAGEMENT
# ============================================================================

class TeamMemberCreateSerializer(serializers.ModelSerializer):
    """Serializer for tenant owners to create staff users"""
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'phone',
            'password', 'role', 'job_title', 'department'
        ]

    def validate_email(self, value):
        """Validate email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        """Validate username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_role(self, value):
        """Validate role - staff users can't be admins unless explicitly allowed"""
        request_user = self.context['request'].user

        # Only tenant owners and system admins can create admin users
        if value == 'admin' and not (request_user.is_tenant_owner or request_user.is_superuser):
            raise serializers.ValidationError(
                "Only tenant owners can create users with admin role."
            )

        return value

    def create(self, validated_data):
        """Create new staff user"""
        password = validated_data.pop('password')
        request_user = self.context['request'].user

        # Set tenant from request user
        validated_data['tenant'] = request_user.tenant
        validated_data['is_tenant_owner'] = False
        validated_data['is_staff'] = True  # Allow access to admin panel
        validated_data['email_verified'] = False  # Require email verification

        # Create user
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        return user


class TeamMemberUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating team member information"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'role',
            'job_title', 'department', 'is_active'
        ]

    def validate_role(self, value):
        """Validate role changes"""
        request_user = self.context['request'].user
        instance = self.instance

        # Can't change role of tenant owner
        if instance.is_tenant_owner and value != instance.role:
            raise serializers.ValidationError(
                "Cannot change role of tenant owner."
            )

        # Only tenant owners can set admin role
        if value == 'admin' and not (request_user.is_tenant_owner or request_user.is_superuser):
            raise serializers.ValidationError(
                "Only tenant owners can assign admin role."
            )

        return value

    def validate_is_active(self, value):
        """Validate deactivation"""
        instance = self.instance

        # Can't deactivate tenant owner
        if instance.is_tenant_owner and not value:
            raise serializers.ValidationError(
                "Cannot deactivate tenant owner. Transfer ownership first."
            )

        return value


class TeamMemberListSerializer(serializers.ModelSerializer):
    """Serializer for listing team members"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'job_title', 'department', 'is_tenant_owner',
            'is_active', 'email_verified', 'last_login_at', 'created_at'
        ]
        read_only_fields = fields


# ============================================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================================

class TwoFactorSetupSerializer(serializers.Serializer):
    """
    Serializer for initiating 2FA setup.
    Returns QR code and secret for Google Authenticator.
    """

    def create(self, validated_data):
        """Generate TOTP secret and QR code"""
        import pyotp
        import qrcode
        import io
        import base64

        user = self.context['request'].user

        # Generate new secret
        secret = pyotp.random_base32()

        # Create TOTP provisioning URI for Google Authenticator
        totp = pyotp.TOTP(secret)
        issuer = 'CrediFlux'
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=issuer
        )

        # Generate QR code as base64 image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Store secret temporarily (not enabled yet)
        user.totp_secret = secret
        user.save(update_fields=['totp_secret'])

        return {
            'secret': secret,
            'qr_code': f'data:image/png;base64,{qr_base64}',
            'provisioning_uri': provisioning_uri,
        }


class TwoFactorVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying TOTP code during 2FA setup.
    Once verified, 2FA is enabled for the user.
    """
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        """Validate TOTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits.")
        return value

    def validate(self, attrs):
        """Verify the TOTP code against user's secret"""
        import pyotp

        user = self.context['request'].user
        code = attrs['code']

        if not user.totp_secret:
            raise serializers.ValidationError({
                'code': 'Please setup 2FA first by calling the setup endpoint.'
            })

        # Verify TOTP code
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(code):
            raise serializers.ValidationError({
                'code': 'Invalid verification code. Please try again.'
            })

        return attrs

    def save(self):
        """Enable 2FA and generate backup codes"""
        import secrets

        user = self.context['request'].user

        # Generate 10 backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Enable 2FA
        user.is_2fa_enabled = True
        user.backup_codes = backup_codes
        user.save(update_fields=['is_2fa_enabled', 'backup_codes'])

        return {
            'message': 'Two-factor authentication enabled successfully.',
            'backup_codes': backup_codes,
        }


class TwoFactorLoginSerializer(serializers.Serializer):
    """
    Serializer for verifying 2FA code during login.
    Supports both TOTP codes and backup codes.
    """
    code = serializers.CharField(required=False, allow_blank=True)
    backup_code = serializers.CharField(required=False, allow_blank=True)
    temp_token = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate either TOTP code or backup code"""
        import pyotp
        from django.core.cache import cache

        code = attrs.get('code', '').strip()
        backup_code = attrs.get('backup_code', '').strip()
        temp_token = attrs['temp_token']

        if not code and not backup_code:
            raise serializers.ValidationError({
                'code': 'Please provide either a verification code or backup code.'
            })

        # Get user ID from temp token (stored in cache during login)
        user_id = cache.get(f'2fa_pending_{temp_token}')
        if not user_id:
            raise serializers.ValidationError({
                'temp_token': 'Invalid or expired session. Please login again.'
            })

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'temp_token': 'Invalid session. Please login again.'
            })

        # Verify TOTP code
        if code:
            if len(code) != 6 or not code.isdigit():
                raise serializers.ValidationError({
                    'code': 'Code must be 6 digits.'
                })

            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(code):
                raise serializers.ValidationError({
                    'code': 'Invalid verification code.'
                })

        # Verify backup code
        elif backup_code:
            backup_code = backup_code.upper()
            if backup_code not in user.backup_codes:
                raise serializers.ValidationError({
                    'backup_code': 'Invalid backup code.'
                })

            # Remove used backup code
            user.backup_codes.remove(backup_code)
            user.save(update_fields=['backup_codes'])

        # Clear temp token from cache
        cache.delete(f'2fa_pending_{temp_token}')

        attrs['user'] = user
        return attrs


class TwoFactorDisableSerializer(serializers.Serializer):
    """Serializer for disabling 2FA"""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_code(self, value):
        """Validate TOTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits.")
        return value

    def validate(self, attrs):
        """Verify password and TOTP code"""
        import pyotp

        user = self.context['request'].user
        password = attrs['password']
        code = attrs['code']

        # Verify password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Incorrect password.'
            })

        # Verify TOTP code
        if user.totp_secret:
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(code):
                raise serializers.ValidationError({
                    'code': 'Invalid verification code.'
                })

        return attrs

    def save(self):
        """Disable 2FA"""
        user = self.context['request'].user

        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = []
        user.save(update_fields=['is_2fa_enabled', 'totp_secret', 'backup_codes'])

        return {
            'message': 'Two-factor authentication disabled successfully.',
        }


class BackupCodesRegenerateSerializer(serializers.Serializer):
    """Serializer for regenerating backup codes"""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_password(self, value):
        """Verify password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def save(self):
        """Generate new backup codes"""
        import secrets

        user = self.context['request'].user

        if not user.is_2fa_enabled:
            raise serializers.ValidationError({
                'non_field_errors': '2FA is not enabled for this account.'
            })

        # Generate 10 new backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        user.backup_codes = backup_codes
        user.save(update_fields=['backup_codes'])

        return {
            'message': 'Backup codes regenerated successfully.',
            'backup_codes': backup_codes,
        }
