"""
Custom admin for django-allauth EmailAddress model
"""
from django.contrib import admin
from django.contrib import messages
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.account.utils import send_email_confirmation

# Unregister default allauth admin first
try:
    admin.site.unregister(EmailAddress)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(EmailConfirmation)
except admin.sites.NotRegistered:
    pass


@admin.register(EmailAddress)
class EmailAddressAdmin(ModelAdmin):
    """Admin interface for EmailAddress model with Unfold"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = ['email', 'user', 'show_verified', 'show_primary']
    list_filter = ['verified', 'primary']
    search_fields = ['email', 'user__email', 'user__first_name', 'user__last_name']
    ordering = ['email']
    list_per_page = 50
    actions = ['resend_verification', 'mark_as_verified']

    @display(description="Verified", label=True)
    def show_verified(self, obj):
        """Display verification status with color badge"""
        if obj.verified:
            return 'success', '✓ Verificado'
        return 'warning', '⏳ Pendiente'

    @display(description="Primary", label=True)
    def show_primary(self, obj):
        """Display primary status with color badge"""
        if obj.primary:
            return 'info', 'Primary'
        return 'secondary', 'Secondary'

    @action(description="Reenviar email de verificación", permissions=['change'])
    def resend_verification(self, request, queryset):
        """Resend verification email to selected email addresses"""
        sent_count = 0
        already_verified = 0

        for email_address in queryset:
            if email_address.verified:
                already_verified += 1
                continue

            try:
                send_email_confirmation(request, email_address.user, signup=False, email=email_address.email)
                sent_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error al enviar email a {email_address.email}: {str(e)}",
                    level=messages.ERROR
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"Se enviaron {sent_count} email(s) de verificación.",
                level=messages.SUCCESS
            )

        if already_verified > 0:
            self.message_user(
                request,
                f"{already_verified} email(s) ya están verificados.",
                level=messages.INFO
            )

    @action(description="Marcar como verificado", permissions=['change'])
    def mark_as_verified(self, request, queryset):
        """Manually mark email addresses as verified"""
        updated = queryset.filter(verified=False).update(verified=True)

        self.message_user(
            request,
            f"Se marcaron {updated} email(s) como verificados.",
            level=messages.SUCCESS
        )


@admin.register(EmailConfirmation)
class EmailConfirmationAdmin(ModelAdmin):
    """Admin interface for EmailConfirmation model with Unfold"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = ['email_address', 'key', 'created', 'sent']
    list_filter = ['sent']
    search_fields = ['email_address__email', 'key']
    readonly_fields = ['created', 'sent', 'key']
    ordering = ['-id']
    list_per_page = 50

    def has_add_permission(self, request):
        """Disable adding confirmations manually"""
        return False
