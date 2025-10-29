"""
User admin configuration with Unfold best practices
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import display
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
        'email', 'first_name', 'last_name', 'show_tenant',
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
