"""
User authentication and management URLs
"""
from django.urls import path
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
)

app_name = 'users'

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
]
