"""
User authentication and management URLs
"""
from django.urls import path
from rest_framework.routers import SimpleRouter

from .views_roles import PermissionCatalogView, RoleViewSet
from .views import (
    # Email Verification
    EmailVerificationSendView,
    EmailVerificationConfirmView,
    # Password Reset
    PasswordResetRequestView,
    PasswordResetConfirmView,
    # Logout
    LogoutView,
    # Profile Management
    ProfileView,
    ProfileUpdateView,
    PasswordChangeView,
    # Team Management
    TeamMemberListView,
    TeamMemberCreateView,
    TeamMemberDetailView,
    # Two-Factor Authentication
    TwoFactorSetupView,
    TwoFactorVerifyView,
    TwoFactorLoginVerifyView,
    TwoFactorDisableView,
    TwoFactorBackupCodesView,
)

app_name = 'users'

router = SimpleRouter()
router.register('roles', RoleViewSet, basename='role')

urlpatterns = [
    # ========================================================================
    # EMAIL VERIFICATION
    # ========================================================================
    path('auth/verify-email/send/', EmailVerificationSendView.as_view(), name='verify-email-send'),
    path('auth/verify-email/confirm/', EmailVerificationConfirmView.as_view(), name='verify-email-confirm'),

    # ========================================================================
    # PASSWORD RESET
    # ========================================================================
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # ========================================================================
    # LOGOUT
    # ========================================================================
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # ========================================================================
    # PROFILE MANAGEMENT
    # ========================================================================
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('profile/change-password/', PasswordChangeView.as_view(), name='change-password'),

    # ========================================================================
    # TEAM MANAGEMENT
    # ========================================================================
    path('team/', TeamMemberListView.as_view(), name='team-list'),
    path('team/create/', TeamMemberCreateView.as_view(), name='team-create'),
    path('team/<int:pk>/', TeamMemberDetailView.as_view(), name='team-detail'),

    # ========================================================================
    # ROLES Y CATÁLOGO DE PERMISOS (D6)
    # ========================================================================
    path('permissions/catalog/', PermissionCatalogView.as_view(), name='permissions-catalog'),

    # ========================================================================
    # TWO-FACTOR AUTHENTICATION
    # ========================================================================
    path('auth/2fa/setup/', TwoFactorSetupView.as_view(), name='2fa-setup'),
    path('auth/2fa/verify/', TwoFactorVerifyView.as_view(), name='2fa-verify'),
    path('auth/2fa/login/', TwoFactorLoginVerifyView.as_view(), name='2fa-login'),
    path('auth/2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
    path('auth/2fa/backup-codes/', TwoFactorBackupCodesView.as_view(), name='2fa-backup-codes'),
]

urlpatterns += router.urls
