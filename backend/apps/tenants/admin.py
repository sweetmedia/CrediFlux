"""
Tenant admin configuration with Unfold best practices
"""
from django.contrib import admin
from django import forms
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.db import connection
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
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
        'show_active', 'created_on', 'demo_data_actions'
    ]
    list_filter = ['is_active', 'subscription_plan', 'created_on']
    search_fields = ['name', 'business_name', 'email', 'tax_id']
    readonly_fields = ['created_on', 'updated_on']  # Removed schema_name
    list_per_page = 25
    save_on_top = True
    actions = ['generate_demo_data_action']

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

    @display(description="Demo Data", ordering="id")
    def demo_data_actions(self, obj):
        """Display button to generate demo data"""
        return format_html(
            '<a class="button" style="padding: 6px 12px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); '
            'color: white; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 500; '
            'display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.1);" '
            'href="{}?tenant_id={}" onmouseover="this.style.transform=\'translateY(-1px)\'; this.style.boxShadow=\'0 4px 6px rgba(0,0,0,0.15)\'" '
            'onmouseout="this.style.transform=\'translateY(0)\'; this.style.boxShadow=\'0 1px 3px rgba(0,0,0,0.1)\'">'
            '<span style="font-size: 14px;">🎲</span> Generate Demo Data</a>',
            reverse('admin:generate_demo_data'),
            obj.id
        )

    @action(description="Generate demo data for selected tenants")
    def generate_demo_data_action(self, request, queryset):
        """Action to generate demo data for selected tenants"""
        from django.core.management import call_command
        from apps.loans.models import Loan

        success_count = 0
        error_count = 0

        for tenant in queryset:
            try:
                # Switch to tenant schema
                connection.set_tenant(tenant)

                # Check if tenant already has loans
                loan_count = Loan.objects.count()

                if loan_count > 0:
                    self.message_user(
                        request,
                        f'⚠️ Tenant "{tenant.business_name}" already has {loan_count} loans. Skipped.',
                        level=messages.WARNING
                    )
                    continue

                # Run the create_demo_data command
                call_command('create_demo_data', tenant.schema_name)
                success_count += 1

            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f'❌ Error creating demo data for "{tenant.business_name}": {str(e)}',
                    level=messages.ERROR
                )

        if success_count > 0:
            self.message_user(
                request,
                f'✅ Successfully created demo data for {success_count} tenant(s)',
                level=messages.SUCCESS
            )

        if error_count > 0:
            self.message_user(
                request,
                f'⚠️ Failed to create demo data for {error_count} tenant(s)',
                level=messages.WARNING
            )

    def get_urls(self):
        """Add custom URL for demo data generation"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'generate-demo-data/',
                self.admin_site.admin_view(self.generate_demo_data_view),
                name='generate_demo_data',
            ),
        ]
        return custom_urls + urls

    def generate_demo_data_view(self, request):
        """View to generate demo data with tenant selection"""
        from django.core.management import call_command
        from apps.loans.models import Loan

        tenant_id = request.GET.get('tenant_id')

        if request.method == 'POST':
            selected_tenant_id = request.POST.get('tenant')

            if not selected_tenant_id:
                messages.error(request, 'Please select a tenant')
                return redirect('admin:tenants_tenant_changelist')

            try:
                tenant = Tenant.objects.get(id=selected_tenant_id)

                # Switch to tenant schema
                connection.set_tenant(tenant)

                # Check if tenant already has data
                loan_count = Loan.objects.count()

                if loan_count > 0 and not request.POST.get('force'):
                    context = {
                        **self.admin_site.each_context(request),
                        'title': 'Generate Demo Data',
                        'tenant': tenant,
                        'loan_count': loan_count,
                        'needs_confirmation': True,
                        'tenants': Tenant.objects.filter(is_active=True).order_by('business_name'),
                        'selected_tenant_id': selected_tenant_id,
                    }
                    return render(request, 'admin/generate_demo_data.html', context)

                # Run the create_demo_data command
                call_command('create_demo_data', tenant.schema_name)

                messages.success(
                    request,
                    f'✅ Successfully created demo data for tenant "{tenant.business_name}"'
                )
                return redirect('admin:tenants_tenant_changelist')

            except Tenant.DoesNotExist:
                messages.error(request, f'Tenant not found')
                return redirect('admin:tenants_tenant_changelist')
            except Exception as e:
                messages.error(request, f'Error creating demo data: {str(e)}')
                return redirect('admin:tenants_tenant_changelist')

        # GET request - show form
        context = {
            **self.admin_site.each_context(request),
            'title': 'Generate Demo Data',
            'tenants': Tenant.objects.filter(is_active=True).order_by('business_name'),
            'selected_tenant_id': tenant_id,
        }
        return render(request, 'admin/generate_demo_data.html', context)

    fieldsets = (
        ('Tenant Information', {
            'fields': ('name', 'schema_name', 'is_active')
        }),
        ('Business Information', {
            'fields': ('business_name', 'tax_id', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'max_users')
        }),
        ('Branding', {
            'fields': ('logo', 'primary_color'),
            'classes': ('collapse',)
        }),

        # ============================================================
        # LOAN CONFIGURATION SECTIONS
        # ============================================================

        ('Loan Interest Rates', {
            'fields': (
                'default_interest_rate',
                'min_interest_rate',
                'max_interest_rate',
            ),
            'classes': ('collapse',),
            'description': 'Configure the allowed interest rates for loans'
        }),

        ('Loan Amounts & Terms', {
            'fields': (
                'min_loan_amount',
                'max_loan_amount',
                'default_loan_term_months',
                'min_loan_term_months',
                'max_loan_term_months',
            ),
            'classes': ('collapse',),
            'description': 'Set minimum and maximum loan amounts and term limits'
        }),

        ('Loan Defaults', {
            'fields': (
                'default_payment_frequency',
                'default_loan_type',
                'default_grace_period_days',
                'enabled_loan_types',
            ),
            'classes': ('collapse',),
            'description': 'Default values for new loans'
        }),

        ('Auto-Approval Settings', {
            'fields': (
                'enable_auto_approval',
                'auto_approval_max_amount',
            ),
            'classes': ('collapse',),
            'description': 'Configure automatic loan approval'
        }),

        ('Collateral & Guarantor Requirements', {
            'fields': (
                'require_collateral_default',
                'collateral_required_above',
                'require_guarantor',
                'guarantor_required_above',
            ),
            'classes': ('collapse',),
            'description': 'Security and guarantor requirements'
        }),

        ('Disbursement Configuration', {
            'fields': (
                'require_disbursement_approval',
                'allow_partial_disbursement',
            ),
            'classes': ('collapse',),
            'description': 'Fund disbursement settings'
        }),

        ('Payment Methods', {
            'fields': (
                'accepted_payment_methods',
                'enable_cash_payments',
                'enable_check_payments',
                'enable_bank_transfer_payments',
                'enable_card_payments',
                'enable_mobile_payments',
            ),
            'classes': ('collapse',),
            'description': 'Accepted payment methods for loan repayments'
        }),

        ('Credit Score Requirements', {
            'fields': (
                'require_credit_score',
                'minimum_credit_score',
                'credit_score_for_auto_approval',
            ),
            'classes': ('collapse',),
            'description': 'Credit score validation settings'
        }),

        ('Currency Settings', {
            'fields': (
                'default_currency',
                'allow_multiple_currencies',
                'supported_currencies',
            ),
            'classes': ('collapse',),
            'description': 'Currency configuration for loans'
        }),

        ('Document Requirements', {
            'fields': (
                'require_id_document',
                'require_proof_of_income',
                'require_proof_of_address',
                'require_bank_statement',
                'require_employment_letter',
                'enhanced_verification_amount',
                'enhanced_verification_documents',
            ),
            'classes': ('collapse',),
            'description': 'Required documents for loan applications'
        }),

        ('Additional Loan Settings', {
            'fields': (
                'allow_early_repayment',
                'early_repayment_penalty',
                'max_active_loans_per_customer',
            ),
            'classes': ('collapse',),
            'description': 'Other loan configuration options'
        }),

        ('Late Fee Configuration', {
            'fields': (
                'late_fee_type',
                'late_fee_percentage',
                'late_fee_fixed_amount',
                'late_fee_frequency',
                'grace_period_days',
            ),
            'classes': ('collapse',),
            'description': 'Late payment fee settings'
        }),

        ('Notification Settings', {
            'fields': (
                'enable_email_reminders',
                'enable_sms_reminders',
                'enable_whatsapp_reminders',
                'reminder_days_before',
                'notification_email_from',
            ),
            'classes': ('collapse',),
            'description': 'Payment reminder notification settings'
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
