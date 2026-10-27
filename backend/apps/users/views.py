"""
API views for user authentication and management
"""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.conf import settings
from django.db import transaction
from apps.core.net import client_network_key
from apps.tenants.models import Tenant
from allauth.account.views import ConfirmEmailView
from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    UserSerializer,
    EmailVerificationSendSerializer,
    EmailVerificationConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    PasswordChangeSerializer,
    TeamMemberCreateSerializer,
    TeamMemberUpdateSerializer,
    TeamMemberListSerializer,
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    TwoFactorLoginSerializer,
    TwoFactorDisableSerializer,
    BackupCodesRegenerateSerializer,
    TenantAwareTokenRefreshSerializer,
    VERIFICATION_SEND_MESSAGE,
    PASSWORD_RESET_REQUEST_MESSAGE,
    user_on_request_host,
)

User = get_user_model()


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

class ClientNetworkThrottle(SimpleRateThrottle):
    """Límite por red del cliente para los envíos de enlaces por correo, autenticado o no.

    La identidad sale de `client_network_key` (respeta NUM_PROXIES): la IPv4 o la red IPv6 /56,
    como el throttle del registro de tenants. Cada subclase fija su `scope`.
    """

    default_rate = '5/hour'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': client_network_key(request)}

    def get_rate(self):
        # Se lee en cada petición (no al importar) para respetar override_settings.
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope, self.default_rate)


class VerifyEmailSendThrottle(ClientNetworkThrottle):
    """Límite propio para pedir enlaces de verificación."""

    scope = 'verify_email_send'


class PasswordResetRequestThrottle(ClientNetworkThrottle):
    """Límite propio para pedir enlaces de reset de contraseña."""

    scope = 'password_reset_request'


class EmailVerificationSendView(APIView):
    """
    Send email verification link to user.

    Always answers the same generic 200 for a well-formed email; the link is only sent to an
    active, unverified user requested from their tenant's host (public host without tenant).

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]
    throttle_classes = [VerifyEmailSendThrottle]

    @swagger_auto_schema(
        operation_id='send_email_verification',
        operation_description=(
            'Request an email verification link. The response is the same whether or not the '
            'email belongs to an account that needs verification on this host.'
        ),
        request_body=EmailVerificationSendSerializer,
        responses={
            200: openapi.Response(
                description='Generic response (does not reveal whether the account exists)',
                examples={
                    'application/json': {
                        'message': VERIFICATION_SEND_MESSAGE,
                    }
                }
            ),
            400: 'Bad request - invalid email format',
            429: 'Too many requests',
        },
        tags=['Authentication - Email Verification']
    )
    def post(self, request):
        """Send verification email"""
        serializer = EmailVerificationSendSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationConfirmView(APIView):
    """
    Confirm email verification with token.

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='confirm_email_verification',
        operation_description='Verify email with token',
        request_body=EmailVerificationConfirmSerializer,
        responses={
            200: openapi.Response(
                description='Email verified successfully',
                examples={
                    'application/json': {
                        'message': 'Email verified successfully.',
                        'email': 'user@example.com',
                        'email_verified': True,
                    }
                }
            ),
            400: 'Bad request - invalid token'
        },
        tags=['Authentication - Email Verification']
    )
    def post(self, request):
        """Verify email with token"""
        serializer = EmailVerificationConfirmSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PASSWORD RESET
# ============================================================================

class PasswordResetRequestView(APIView):
    """
    Request password reset link.

    Always answers the same generic 200 for a well-formed email; the link is only sent to an
    active user requested from their tenant's host (public host without tenant).

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRequestThrottle]

    @swagger_auto_schema(
        operation_id='request_password_reset',
        operation_description=(
            'Request a password reset link via email. The response is the same whether or not the '
            'email belongs to an active account on this host.'
        ),
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                description='Generic response (does not reveal whether the account exists)',
                examples={
                    'application/json': {
                        'message': PASSWORD_RESET_REQUEST_MESSAGE,
                    }
                }
            ),
            400: 'Bad request - invalid email format',
            429: 'Too many requests',
        },
        tags=['Authentication - Password Reset']
    )
    def post(self, request):
        """Request password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with new password.

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='confirm_password_reset',
        operation_description='Reset password with token and new password',
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: openapi.Response(
                description='Password reset successful',
                examples={
                    'application/json': {
                        'message': 'Password has been reset successfully. You can now login with your new password.',
                        'email': 'user@example.com',
                    }
                }
            ),
            400: 'Bad request - invalid token or passwords do not match'
        },
        tags=['Authentication - Password Reset']
    )
    def post(self, request):
        """Reset password with token"""
        serializer = PasswordResetConfirmSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# TOKEN REFRESH
# ============================================================================

class TenantAwareTokenRefreshView(TokenRefreshView):
    """Refresh de JWT ligado a la credencial y al tenant del host."""
    serializer_class = TenantAwareTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except AuthenticationFailed as exc:
            # DRF no incluye el `code` en el cuerpo; el frontend lo usa para
            # avisar que la sesión se cerró por un cambio de contraseña.
            if exc.get_codes() != 'token_revoked':
                raise
            return Response(
                {'detail': str(exc.detail), 'code': 'token_revoked'},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# ============================================================================
# LOGOUT
# ============================================================================

class LogoutView(APIView):
    """
    Logout user by blacklisting their refresh token.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='logout',
        operation_description='Logout by blacklisting refresh token',
        request_body=LogoutSerializer,
        responses={
            200: openapi.Response(
                description='Logged out successfully',
                examples={
                    'application/json': {
                        'message': 'Successfully logged out.',
                    }
                }
            ),
            400: 'Bad request - invalid token'
        },
        tags=['Authentication - Logout']
    )
    def post(self, request):
        """Logout user"""
        serializer = LogoutSerializer(data=request.data)

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PROFILE MANAGEMENT
# ============================================================================

class ProfileView(APIView):
    """
    Get current user profile.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='get_profile',
        operation_description='Get current user profile information',
        responses={
            200: UserSerializer,
        },
        tags=['Profile Management']
    )
    def get(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
    """
    Update current user profile.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='update_profile',
        operation_description='Update current user profile information',
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: 'Bad request - validation errors'
        },
        tags=['Profile Management']
    )
    def put(self, request):
        """Update profile (full update)"""
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id='partial_update_profile',
        operation_description='Partially update current user profile',
        request_body=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: 'Bad request - validation errors'
        },
        tags=['Profile Management']
    )
    def patch(self, request):
        """Update profile (partial update)"""
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    Change password for authenticated user.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='change_password',
        operation_description='Change password (requires current password)',
        request_body=PasswordChangeSerializer,
        responses={
            200: openapi.Response(
                description='Password changed successfully',
                examples={
                    'application/json': {
                        'message': 'Password changed successfully.',
                    }
                }
            ),
            400: 'Bad request - validation errors'
        },
        tags=['Profile Management']
    )
    def post(self, request):
        """Change password"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# TEAM MANAGEMENT
# ============================================================================

class TeamMemberListView(APIView):
    """
    List all team members in the user's tenant.

    **Authentication:** Required
    **Permissions:** User must belong to a tenant
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='list_team_members',
        operation_description='List all users in the current user\'s tenant',
        responses={
            200: TeamMemberListSerializer(many=True),
            403: 'Forbidden - user has no tenant'
        },
        tags=['Team Management']
    )
    def get(self, request):
        """List team members"""
        from rest_framework.pagination import PageNumberPagination

        # Check if user belongs to a tenant
        if not request.user.tenant:
            return Response(
                {'error': 'You do not belong to any tenant.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get all users in the same tenant
        team_members = User.objects.filter(
            tenant=request.user.tenant
        ).order_by('-created_at')

        # Apply pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20  # Same as other endpoints
        paginated_queryset = paginator.paginate_queryset(team_members, request)

        serializer = TeamMemberListSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class TeamMemberCreateView(APIView):
    """
    Create a new team member (staff user).

    **Authentication:** Required
    **Permissions:** User must be tenant owner or have can_manage_users permission
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='create_team_member',
        operation_description='Create a new staff user in your tenant',
        request_body=TeamMemberCreateSerializer,
        responses={
            201: TeamMemberListSerializer,
            400: 'Bad request - validation errors',
            403: 'Forbidden - insufficient permissions'
        },
        tags=['Team Management']
    )
    def post(self, request):
        """Create team member"""
        # Check permissions
        if not request.user.can_manage_users():
            return Response(
                {'error': 'You do not have permission to create users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user belongs to a tenant
        if not request.user.tenant:
            return Response(
                {'error': 'You must belong to a tenant to create users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # El bloqueo de la fila del tenant serializa las altas concurrentes:
        # dos requests no pueden pasar a la vez el control de max_users.
        with transaction.atomic():
            tenant = Tenant.objects.select_for_update().get(pk=request.user.tenant_id)
            serializer = TeamMemberCreateSerializer(
                data=request.data,
                context={'request': request, 'tenant': tenant}
            )

            if serializer.is_valid():
                user = serializer.save()
                return Response(
                    TeamMemberListSerializer(user).data,
                    status=status.HTTP_201_CREATED
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TeamMemberDetailView(APIView):
    """
    Retrieve, update, or delete a team member.

    **Authentication:** Required
    **Permissions:** User must be in same tenant and have appropriate permissions
    """
    permission_classes = [IsAuthenticated]

    def _update(self, request, user, partial):
        # Mismo bloqueo que el alta: una reactivación no puede saltarse max_users.
        with transaction.atomic():
            tenant = Tenant.objects.select_for_update().get(pk=user.tenant_id) if user.tenant_id else None
            serializer = TeamMemberUpdateSerializer(
                user,
                data=request.data,
                partial=partial,
                context={'request': request, 'tenant': tenant}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    TeamMemberListSerializer(user).data,
                    status=status.HTTP_200_OK
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self, request, pk):
        """Get team member or return error"""
        if request.user.tenant_id is None:
            return None, Response(
                {'error': 'You do not belong to any tenant.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(pk=pk, tenant_id=request.user.tenant_id)
            return user, None

        except User.DoesNotExist:
            return None, Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_id='get_team_member',
        operation_description='Get details of a specific team member',
        responses={
            200: TeamMemberListSerializer,
            404: 'Not found'
        },
        tags=['Team Management']
    )
    def get(self, request, pk):
        """Get team member details"""
        user, error_response = self.get_object(request, pk)
        if error_response:
            return error_response

        serializer = TeamMemberListSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id='update_team_member',
        operation_description='Update a team member',
        request_body=TeamMemberUpdateSerializer,
        responses={
            200: TeamMemberListSerializer,
            400: 'Bad request - validation errors',
            403: 'Forbidden - insufficient permissions',
            404: 'Not found'
        },
        tags=['Team Management']
    )
    def put(self, request, pk):
        """Update team member (full update)"""
        # Check permissions
        if not request.user.can_manage_users():
            return Response(
                {'error': 'You do not have permission to update users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        user, error_response = self.get_object(request, pk)
        if error_response:
            return error_response

        return self._update(request, user, partial=False)

    @swagger_auto_schema(
        operation_id='partial_update_team_member',
        operation_description='Partially update a team member',
        request_body=TeamMemberUpdateSerializer,
        responses={
            200: TeamMemberListSerializer,
            400: 'Bad request - validation errors',
            403: 'Forbidden - insufficient permissions',
            404: 'Not found'
        },
        tags=['Team Management']
    )
    def patch(self, request, pk):
        """Update team member (partial update)"""
        # Check permissions
        if not request.user.can_manage_users():
            return Response(
                {'error': 'You do not have permission to update users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        user, error_response = self.get_object(request, pk)
        if error_response:
            return error_response

        return self._update(request, user, partial=True)

    @swagger_auto_schema(
        operation_id='delete_team_member',
        operation_description='Delete (deactivate) a team member',
        responses={
            200: openapi.Response(
                description='User deactivated',
                examples={
                    'application/json': {
                        'message': 'User has been deactivated.',
                    }
                }
            ),
            403: 'Forbidden - insufficient permissions or cannot delete tenant owner',
            404: 'Not found'
        },
        tags=['Team Management']
    )
    def delete(self, request, pk):
        """Delete (deactivate) team member"""
        # Check permissions
        if not request.user.can_manage_users():
            return Response(
                {'error': 'You do not have permission to delete users.'},
                status=status.HTTP_403_FORBIDDEN
            )

        user, error_response = self.get_object(request, pk)
        if error_response:
            return error_response

        # Can't delete tenant owner
        if user.is_tenant_owner:
            return Response(
                {'error': 'Cannot delete tenant owner. Transfer ownership first.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Can't delete yourself
        if user.id == request.user.id:
            return Response(
                {'error': 'You cannot delete your own account. Use profile settings instead.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Deactivate instead of deleting
        user.is_active = False
        user.save()

        return Response(
            {'message': 'User has been deactivated.'},
            status=status.HTTP_200_OK
        )


# ============================================================================
# TWO-FACTOR AUTHENTICATION (2FA)
# ============================================================================

class TwoFactorSetupView(APIView):
    """
    Setup two-factor authentication for the user.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='setup_2fa',
        operation_description='Generate QR code and secret for 2FA setup (Google Authenticator)',
        responses={
            200: openapi.Response(
                description='2FA setup data',
                examples={
                    'application/json': {
                        'secret': 'ABCDEFGHIJK...',
                        'qr_code': 'data:image/png;base64,...',
                        'provisioning_uri': 'otpauth://totp/...',
                    }
                }
            ),
            400: 'Bad request - 2FA already enabled'
        },
        tags=['Authentication - Two-Factor']
    )
    def post(self, request):
        """Generate 2FA setup QR code"""
        user = request.user

        # Check if 2FA is already enabled
        if user.is_2fa_enabled:
            return Response(
                {'error': 'Two-factor authentication is already enabled. Disable it first to reconfigure.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TwoFactorSetupSerializer(data={}, context={'request': request})
        if serializer.is_valid():
            result = serializer.create({})
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorVerifyView(APIView):
    """
    Verify TOTP code and enable 2FA.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='verify_2fa_setup',
        operation_description='Verify TOTP code to enable 2FA. Returns backup codes.',
        request_body=TwoFactorVerifySerializer,
        responses={
            200: openapi.Response(
                description='2FA enabled successfully',
                examples={
                    'application/json': {
                        'message': 'Two-factor authentication enabled successfully.',
                        'backup_codes': ['ABC123', 'DEF456', '...'],
                    }
                }
            ),
            400: 'Bad request - invalid code'
        },
        tags=['Authentication - Two-Factor']
    )
    def post(self, request):
        """Verify TOTP code and enable 2FA"""
        serializer = TwoFactorVerifySerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorLoginVerifyView(APIView):
    """
    Verify 2FA code during login process.

    **Authentication:** Not required (uses temp token)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='verify_2fa_login',
        operation_description='Verify 2FA code during login. Returns JWT tokens on success.',
        request_body=TwoFactorLoginSerializer,
        responses={
            200: openapi.Response(
                description='Login successful',
                examples={
                    'application/json': {
                        'access': 'eyJ...',
                        'refresh': 'eyJ...',
                        'user': {'id': 1, 'email': 'user@example.com', '...': '...'},
                    }
                }
            ),
            400: 'Bad request - invalid code or token'
        },
        tags=['Authentication - Two-Factor']
    )
    def post(self, request):
        """Verify 2FA code during login"""
        from .tokens import issue_tokens

        serializer = TwoFactorLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Generate JWT tokens
            refresh = issue_tokens(user)

            # Update last login
            from django.utils import timezone
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableView(APIView):
    """
    Disable two-factor authentication.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='disable_2fa',
        operation_description='Disable 2FA (requires password and current TOTP code)',
        request_body=TwoFactorDisableSerializer,
        responses={
            200: openapi.Response(
                description='2FA disabled',
                examples={
                    'application/json': {
                        'message': 'Two-factor authentication disabled successfully.',
                    }
                }
            ),
            400: 'Bad request - invalid password or code'
        },
        tags=['Authentication - Two-Factor']
    )
    def post(self, request):
        """Disable 2FA"""
        if not request.user.is_2fa_enabled:
            return Response(
                {'error': 'Two-factor authentication is not enabled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TwoFactorDisableSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorBackupCodesView(APIView):
    """
    Regenerate backup codes for 2FA.

    **Authentication:** Required
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='regenerate_backup_codes',
        operation_description='Regenerate backup codes (invalidates old codes)',
        request_body=BackupCodesRegenerateSerializer,
        responses={
            200: openapi.Response(
                description='New backup codes generated',
                examples={
                    'application/json': {
                        'message': 'Backup codes regenerated successfully.',
                        'backup_codes': ['ABC123', 'DEF456', '...'],
                    }
                }
            ),
            400: 'Bad request - invalid password or 2FA not enabled'
        },
        tags=['Authentication - Two-Factor']
    )
    def post(self, request):
        """Regenerate backup codes"""
        serializer = BackupCodesRegenerateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_id='get_backup_codes_count',
        operation_description='Get remaining backup codes count',
        responses={
            200: openapi.Response(
                description='Backup codes count',
                examples={
                    'application/json': {
                        'is_2fa_enabled': True,
                        'backup_codes_remaining': 8,
                    }
                }
            ),
        },
        tags=['Authentication - Two-Factor']
    )
    def get(self, request):
        """Get backup codes remaining count"""
        user = request.user
        return Response({
            'is_2fa_enabled': user.is_2fa_enabled,
            'backup_codes_remaining': len(user.backup_codes) if user.is_2fa_enabled else 0,
        }, status=status.HTTP_200_OK)


# ============================================================================
# EMAIL CONFIRMATION (ALLAUTH)
# ============================================================================

class CustomConfirmEmailView(ConfirmEmailView):
    """
    Custom email confirmation view that always redirects to frontend
    instead of rendering a template.

    Sólo confirma en el host del tenant del usuario (la misma regla que los confirm de reset y
    verificación, `user_on_request_host`): un usuario sin tenant, sólo en el host público y activo.
    Host ajeno, usuario inactivo, clave inválida, vencida o ya usada, y un `confirm()` sin efecto o
    con excepción dan la misma redirección `verified=invalid`, que
    se arma con la URL de settings y no revela a qué tenant pertenece la clave.

    Sigue en GET como allauth (`ACCOUNT_CONFIRM_EMAIL_ON_GET`): el prefetch de un cliente de correo
    podría confirmar, pero sólo marca el correo como verificado.
    """

    def get(self, request, *args, **kwargs):
        """
        Confirm email and redirect to frontend.
        Resolve the confirmation key explicitly so invalid/used keys never fall
        through to Django's HTML 404 page.
        """
        authenticated = request.user.is_authenticated
        if authenticated:
            settings_url = settings.ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL
        else:
            settings_url = settings.ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL

        invalid_url = _with_verified(settings_url, 'invalid')
        key = kwargs.get('key')
        if not key:
            return redirect(invalid_url)

        # `from_key` de allauth en los dos casos: sólo claves vigentes de correos sin verificar
        # (una clave de BD vencida o ya usada no se encuentra).
        confirmation = EmailConfirmationHMAC.from_key(key) or EmailConfirmation.from_key(key)
        if not confirmation:
            return redirect(invalid_url)

        user = confirmation.email_address.user
        if not user_on_request_host(user, request):
            return redirect(invalid_url)

        try:
            # None: vencida, ya verificada u otra cuenta ya verificó ese correo; no es un éxito.
            confirmed = confirmation.confirm(self.request)
        except Exception:
            return redirect(invalid_url)
        if not confirmed:
            return redirect(invalid_url)
        return redirect(self._success_url(user, authenticated, settings_url))

    @staticmethod
    def _success_url(user, authenticated, settings_url):
        """Frontend del tenant del usuario; para un usuario sin tenant, la URL de settings.

        En los dos casos con un único `verified=true`.
        """
        if not user.tenant_id:
            return _with_verified(settings_url, 'true')
        from apps.tenants.links import tenant_frontend_url
        page = '/dashboard' if authenticated else '/login'
        return _with_verified(tenant_frontend_url(user.tenant).rstrip('/') + page, 'true')


def _with_verified(url, value):
    """`url` con un único `verified=<value>`: quita cualquier `verified` de su query y conserva el
    resto de parámetros (las URL de settings ya traen `verified=true`; el frontend lee el primero).
    """
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != 'verified']
    query.append(('verified', value))
    return urlunsplit(parts._replace(query=urlencode(query)))
