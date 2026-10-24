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
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from apps.core.media import SignedFilesModelSerializer
from apps.core.permissions import user_matches_tenant
from . import lockout
from .authentication import token_revoked
from .tokens import PWD_TS_CLAIM, issue_tokens, password_timestamp, revoke_user_credentials
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
        # Cuenta el intento y aplica el límite por cuenta y por IP antes de validar credenciales
        request = self.context.get('request')
        login_id = attrs.get('email') or attrs.get('username') or ''
        lockout.check_and_count(login_id, request)

        # First, validate credentials using parent class
        attrs = super().validate(attrs)
        lockout.reset(login_id, request)

        # Get authenticated user
        user = attrs.get('user')

        # Get current tenant from request
        current_tenant = getattr(request, 'tenant', None)

        # Superusers with no tenant can access any domain (system admins)
        if user.is_superuser and user.tenant is None:
            return attrs

        # Validate user belongs to current tenant
        if current_tenant and user.tenant != current_tenant:
            raise serializers.ValidationError(
                "Invalid credentials for this organization. "
                "Please ensure you are using the correct login portal."
            )

        # If no tenant in request (public schema), only allow system admins
        if not current_tenant and user.tenant is not None:
            raise serializers.ValidationError(
                "Invalid credentials for this portal. "
                "Please use your organization's specific domain."
            )

        return attrs


class UserSerializer(SignedFilesModelSerializer):
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

        response = {
            'email': user.email,
            'message': 'Verification email sent successfully.',
        }

        return response


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

            response = {
                'message': 'If an account exists with this email, a password reset link has been sent.',
            }

            return response

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

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uid': 'Invalid user ID.'
            })

        try:
            lockout.validate_strength(attrs['new_password'], user=user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.detail})

        attrs['user'] = user
        return attrs

    def save(self):
        """Set new password"""
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']

        user.set_password(new_password)
        user.save()
        revoke_user_credentials(user)

        return {
            'message': 'Password has been reset successfully. You can now login with your new password.',
            'email': user.email,
        }


# ============================================================================
# TOKEN REFRESH
# ============================================================================

class TenantAwareTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh que exige que la credencial siga vigente en el tenant del host.

    Rechaza (401 `token_revoked`) si el usuario no existe o está inactivo, si
    `pwd_ts` falta o no coincide con `password_changed_at`, o si el usuario no
    puede operar en `request.tenant`. Rota siempre: el refresh usado queda en
    lista negra y se emite un par nuevo con `issue_tokens`. Responde con la
    misma forma que simplejwt (`access`, `refresh`).
    """

    def validate(self, attrs):
        # Firma, expiración y lista negra (TokenError -> 401 en la vista).
        refresh = self.token_class(attrs['refresh'])

        user = User.objects.select_related('tenant').filter(
            **{jwt_settings.USER_ID_FIELD: refresh.get(jwt_settings.USER_ID_CLAIM)}
        ).first()
        request = self.context.get('request')
        if (
            user is None
            or not user.is_active
            or PWD_TS_CLAIM not in refresh
            or refresh[PWD_TS_CLAIM] != password_timestamp(user)
            or not user_matches_tenant(user, getattr(request, 'tenant', None))
        ):
            raise token_revoked()

        refresh.blacklist()
        new_refresh = issue_tokens(user)
        return {'access': str(new_refresh.access_token), 'refresh': str(new_refresh)}


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

class ProfileUpdateSerializer(SignedFilesModelSerializer):
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

        try:
            lockout.validate_strength(attrs['new_password'], user=user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.detail})

        return attrs

    def save(self):
        """Update password"""
        user = self.context['request'].user
        new_password = self.validated_data['new_password']

        user.set_password(new_password)
        user.save()
        revoke_user_credentials(user)

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

    def validate_password(self, value):
        """Aplica los validadores de fortaleza de contraseña."""
        data = self.initial_data
        candidate = User(
            email=data.get('email', ''),
            username=data.get('username', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
        )
        lockout.validate_strength(value, user=candidate)
        return value

    def validate(self, attrs):
        """Respeta el cupo de usuarios activos del plan (Tenant.max_users)."""
        tenant = self.context.get('tenant') or self.context['request'].user.tenant
        if tenant is not None:
            active_users = User.objects.filter(tenant=tenant, is_active=True).count()
            if active_users >= tenant.max_users:
                raise serializers.ValidationError('Límite de usuarios del plan alcanzado.')
        return attrs

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

        # Reactivar ocupa un cupo del plan (la vista bloquea la fila del tenant).
        if value and not instance.is_active:
            tenant = self.context.get('tenant') or instance.tenant
            if tenant is not None:
                active_users = User.objects.filter(tenant=tenant, is_active=True).count()
                if active_users >= tenant.max_users:
                    raise serializers.ValidationError('Límite de usuarios del plan alcanzado.')

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
        from .totp import verify_totp_once

        user = self.context['request'].user
        code = attrs['code']

        if not user.totp_secret:
            raise serializers.ValidationError({
                'code': 'Please setup 2FA first by calling the setup endpoint.'
            })

        # Verify TOTP code (un solo uso por paso)
        if not verify_totp_once(user, code):
            raise serializers.ValidationError({
                'code': 'Invalid verification code. Please try again.'
            })

        return attrs

    def save(self):
        """Enable 2FA and generate backup codes"""
        from .backup_codes import generate_backup_codes

        user = self.context['request'].user

        # 10 códigos: en claro sólo en esta respuesta; en BD, hashes.
        backup_codes, hashed = generate_backup_codes()

        # Enable 2FA
        user.is_2fa_enabled = True
        user.backup_codes = hashed
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
        from django.core.cache import cache

        from .lockout import check_and_count_2fa, reset_2fa
        from .totp import verify_totp_once

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

        if not user.is_active or (user.tenant and not user.tenant.is_active):
            cache.delete(f'2fa_pending_{temp_token}')
            raise serializers.ValidationError({
                'temp_token': 'This account or its organization has been deactivated.'
            })

        # Límite de intentos de segundo factor: al superarlo se invalida el temp_token,
        # así hay que volver a hacer login (y gastar el contador de login).
        try:
            check_and_count_2fa(user)
        except serializers.ValidationError:
            cache.delete(f'2fa_pending_{temp_token}')
            raise

        # Verify TOTP code
        if code:
            if len(code) != 6 or not code.isdigit():
                raise serializers.ValidationError({
                    'code': 'Code must be 6 digits.'
                })

            if not verify_totp_once(user, code):
                raise serializers.ValidationError({
                    'code': 'Invalid verification code.'
                })

        # Verify backup code
        elif backup_code:
            from .backup_codes import consume_backup_code

            # Compara contra los hashes y lo gasta bajo select_for_update (un solo uso).
            if not consume_backup_code(user, backup_code):
                raise serializers.ValidationError({
                    'backup_code': 'Invalid backup code.'
                })

        reset_2fa(user)

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
        from .lockout import check_and_count_2fa, reset_2fa
        from .totp import verify_totp_once

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
            check_and_count_2fa(user)
            if not verify_totp_once(user, code):
                raise serializers.ValidationError({
                    'code': 'Invalid verification code.'
                })
            reset_2fa(user)

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
    """Serializer for regenerating backup codes (contraseña + TOTP vigente)."""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    code = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text='Código TOTP vigente de la app autenticadora.',
    )

    def validate_password(self, value):
        """Verify password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def validate(self, attrs):
        """Exige el segundo factor: con solo la contraseña no se regeneran los códigos."""
        from .lockout import check_and_count_2fa, reset_2fa
        from .totp import verify_totp_once

        user = self.context['request'].user
        code = (attrs.get('code') or '').strip()
        check_and_count_2fa(user)
        if not (len(code) == 6 and code.isdigit()) or not verify_totp_once(user, code):
            raise serializers.ValidationError({'code': 'Código de verificación inválido.'})
        reset_2fa(user)
        return attrs

    def save(self):
        """Generate new backup codes"""
        from .backup_codes import generate_backup_codes

        user = self.context['request'].user

        if not user.is_2fa_enabled:
            raise serializers.ValidationError({
                'non_field_errors': '2FA is not enabled for this account.'
            })

        # 10 códigos nuevos: en claro sólo en esta respuesta; en BD, hashes.
        backup_codes, hashed = generate_backup_codes()

        user.backup_codes = hashed
        user.save(update_fields=['backup_codes'])

        return {
            'message': 'Backup codes regenerated successfully.',
            'backup_codes': backup_codes,
        }
