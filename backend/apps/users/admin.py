"""
User admin configuration with Unfold best practices
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Admin interface for User model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'email', 'show_email_verified', 'first_name', 'last_name', 'show_tenant',
        'show_role', 'show_owner', 'show_active', 'created_at'
    ]
    list_filter = ['is_active', 'role', 'is_tenant_owner', 'tenant', 'email_verified', 'created_at', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username', 'tenant__name', 'tenant__business_name']
    ordering = ['-created_at']
    list_per_page = 25

    @display(description="Tenant", label=True)
    def show_tenant(self, obj):
        """Display tenant with color badge"""
        if obj.tenant:
            return 'info', obj.tenant.business_name or obj.tenant.name
        return 'secondary', 'System Admin'

    @display(description="Role", label=True)
    def show_role(self, obj):
        """Display role with color badge"""
        colors = {
            'admin': 'danger',
            'manager': 'warning',
            'loan_officer': 'info',
            'accountant': 'info',
            'cashier': 'success',
            'viewer': 'secondary',
        }
        return colors.get(obj.role, 'info'), obj.get_role_display()

    @display(description="Owner", label={True: "success", False: "secondary"})
    def show_owner(self, obj):
        """Display if user is tenant owner"""
        if obj.is_tenant_owner:
            return True, 'Owner'
        return False, 'Staff'

    @display(description="Active", label=True)
    def show_active(self, obj):
        """Display active status with color badge"""
        if obj.is_active:
            return 'success', 'Active'
        return 'danger', 'Inactive'

    @display(description="Email Verified", label=True)
    def show_email_verified(self, obj):
        """Display email verification status with color badge"""
        try:
            email_address = EmailAddress.objects.get(user=obj, email=obj.email)
            if email_address.verified:
                return 'success', '✓ Verificado'
            return 'warning', '⏳ Pendiente'
        except EmailAddress.DoesNotExist:
            return 'danger', '✗ Sin verificar'

    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'email', 'password')
        }),
        ('Tenant Association', {
            'fields': ('tenant', 'is_tenant_owner'),
            'description': 'Tenant this user belongs to. Leave empty for system administrators.'
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone', 'avatar', 'bio')
        }),
        ('Professional Information', {
            'fields': ('job_title', 'department', 'role')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('email_verified', 'receive_notifications')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'last_login_at', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'tenant', 'is_tenant_owner', 'password1', 'password2', 'role'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at', 'last_login', 'date_joined']
    actions = ['resend_verification_email']

    @action(description="Reenviar email de verificación", permissions=['change'])
    def resend_verification_email(self, request, queryset):
        """
        Admin action to resend email verification to selected users.
        Only sends to users who have not verified their email.
        """
        sent_count = 0
        already_verified = 0
        error_count = 0

        for user in queryset:
            # Check if user email is already verified
            try:
                email_address = EmailAddress.objects.get(user=user, email=user.email)

                if email_address.verified:
                    already_verified += 1
                    continue

                # Send verification email
                send_email_confirmation(request, user)
                sent_count += 1

            except EmailAddress.DoesNotExist:
                # Create EmailAddress record if it doesn't exist
                try:
                    email_address = EmailAddress.objects.create(
                        user=user,
                        email=user.email,
                        primary=True,
                        verified=False
                    )
                    send_email_confirmation(request, user)
                    sent_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request,
                        f"Error al procesar {user.email}: {str(e)}",
                        level=messages.ERROR
                    )
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Error al enviar email a {user.email}: {str(e)}",
                    level=messages.ERROR
                )

        # Show summary message
        if sent_count > 0:
            self.message_user(
                request,
                f"Se enviaron {sent_count} email(s) de verificación exitosamente.",
                level=messages.SUCCESS
            )

        if already_verified > 0:
            self.message_user(
                request,
                f"{already_verified} usuario(s) ya tienen su email verificado.",
                level=messages.INFO
            )

        if error_count > 0:
            self.message_user(
                request,
                f"Ocurrieron {error_count} error(es) al procesar algunos usuarios.",
                level=messages.WARNING
            )

    def get_queryset(self, request):
        """
        Filter users based on tenant ownership.
        - Superusers see all users
        - Tenant owners/admins see only users from their tenant
        """
        qs = super().get_queryset(request)

        # Superusers with no tenant can see everyone
        if request.user.is_superuser and request.user.tenant is None:
            return qs

        # Tenant owners/admins can only see users from their tenant
        if request.user.tenant:
            return qs.filter(tenant=request.user.tenant)

        # Default: no users
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Limit tenant selection based on user permissions.
        - Superusers can select any tenant
        - Tenant owners can only select their own tenant
        """
        if db_field.name == "tenant":
            # Superusers can select any tenant
            if request.user.is_superuser and request.user.tenant is None:
                pass  # Show all tenants
            # Tenant owners can only select their own tenant
            elif request.user.tenant:
                kwargs["queryset"] = request.user.tenant.__class__.objects.filter(pk=request.user.tenant.pk)
            else:
                # No tenant available
                kwargs["queryset"] = db_field.related_model.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request):
        """
        Only allow adding users if:
        - User is a superuser (system admin), OR
        - User is a tenant owner/admin
        """
        return request.user.is_superuser or request.user.can_manage_users()

    def has_change_permission(self, request, obj=None):
        """
        Allow changing users if:
        - User is a superuser (system admin), OR
        - User belongs to the same tenant and can manage users
        """
        if request.user.is_superuser and request.user.tenant is None:
            return True

        if obj and request.user.tenant:
            return obj.tenant == request.user.tenant and request.user.can_manage_users()

        return request.user.can_manage_users()

    def has_delete_permission(self, request, obj=None):
        """
        Allow deleting users if:
        - User is a superuser (system admin), OR
        - User belongs to the same tenant, can manage users, and obj is not the owner
        """
        if request.user.is_superuser and request.user.tenant is None:
            return True

        if obj and request.user.tenant:
            # Can't delete tenant owners (including yourself)
            if obj.is_tenant_owner:
                return False
            return obj.tenant == request.user.tenant and request.user.can_manage_users()

        return False
