"""
Tenant admin configuration with Unfold best practices
"""
from django.contrib import admin
from django import forms
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Tenant, Domain
from .widgets import EditableSchemaNameWidget


class TenantAdminForm(forms.ModelForm):
    """Custom form for Tenant admin with editable schema_name widget"""

    class Meta:
        model = Tenant
        fields = '__all__'
        widgets = {
            'schema_name': EditableSchemaNameWidget(),
        }


@admin.register(Tenant)
class TenantAdmin(ModelAdmin):
    """Admin interface for Tenant model with Unfold best practices"""

    # Use custom form
    form = TenantAdminForm

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'name', 'business_name', 'email', 'show_subscription',
        'show_active', 'created_on'
    ]
    list_filter = ['is_active', 'subscription_plan', 'created_on']
    search_fields = ['name', 'business_name', 'email', 'tax_id']
    readonly_fields = ['created_on', 'updated_on']  # Removed schema_name
    list_per_page = 25
    save_on_top = True

    @display(description="Subscription", label=True)
    def show_subscription(self, obj):
        """Display subscription plan with color badge"""
        colors = {
            'free': 'info',
            'basic': 'success',
            'premium': 'warning',
            'enterprise': 'danger',
        }
        return colors.get(obj.subscription_plan, 'info'), obj.get_subscription_plan_display()

    @display(description="Status", label=True)
    def show_active(self, obj):
        """Display active status with color badge"""
        if obj.is_active:
            return 'success', 'Active'
        return 'danger', 'Inactive'

    fieldsets = (
        ('Tenant Information', {
            'fields': ('name', 'schema_name', 'is_active')
        }),
        ('Business Information', {
            'fields': ('business_name', 'tax_id', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'max_users')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_on', 'updated_on'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Domain)
class DomainAdmin(ModelAdmin):
    """Admin interface for Domain model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = ['domain', 'tenant', 'show_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']
    list_per_page = 50

    @display(description="Primary", label=True)
    def show_primary(self, obj):
        """Display primary status with color badge"""
        if obj.is_primary:
            return 'success', 'Primary'
        return 'info', 'Secondary'
