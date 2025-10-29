"""
API views for user authentication and management
"""
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import get_user_model

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
)

User = get_user_model()


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

class EmailVerificationSendView(APIView):
    """
    Send email verification link to user.

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='send_email_verification',
        operation_description='Send email verification link',
        request_body=EmailVerificationSendSerializer,
        responses={
            200: openapi.Response(
                description='Verification email sent',
                examples={
                    'application/json': {
                        'email': 'user@example.com',
                        'message': 'Verification email sent successfully.',
                    }
                }
            ),
            400: 'Bad request - validation errors'
        },
        tags=['Authentication - Email Verification']
    )
    def post(self, request):
        """Send verification email"""
        serializer = EmailVerificationSendSerializer(data=request.data)

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
        serializer = EmailVerificationConfirmSerializer(data=request.data)

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

    **Authentication:** Not required (public endpoint)
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_id='request_password_reset',
        operation_description='Request password reset link via email',
        request_body=PasswordResetRequestSerializer,
        responses={
            200: openapi.Response(
                description='Reset email sent (if account exists)',
                examples={
                    'application/json': {
                        'message': 'If an account exists with this email, a password reset link has been sent.',
                    }
                }
            ),
            400: 'Bad request'
        },
        tags=['Authentication - Password Reset']
    )
    def post(self, request):
        """Request password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data)

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
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        serializer = TeamMemberListSerializer(team_members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

        serializer = TeamMemberCreateSerializer(
            data=request.data,
            context={'request': request}
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

    def get_object(self, request, pk):
        """Get team member or return error"""
        try:
            user = User.objects.get(pk=pk)

            # Check if the user is in the same tenant
            if user.tenant != request.user.tenant:
                return None, Response(
                    {'error': 'User not found in your tenant.'},
                    status=status.HTTP_404_NOT_FOUND
                )

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

        serializer = TeamMemberUpdateSerializer(
            user,
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                TeamMemberListSerializer(user).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

        serializer = TeamMemberUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                TeamMemberListSerializer(user).data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
