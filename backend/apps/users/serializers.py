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

User = get_user_model()


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
            'created_at', 'last_login_at'
        ]
        read_only_fields = [
            'id', 'email', 'username', 'tenant', 'is_tenant_owner',
            'is_staff', 'is_superuser', 'email_verified', 'created_at',
            'last_login_at'
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
        email = self.validated_data['email']
        user = User.objects.get(email=email)

        # Generate token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Create verification URL (you can customize this based on your frontend)
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
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
        email = self.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
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
        if value and not value.is_valid():
            raise serializers.ValidationError("Invalid phone number format.")
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
