"""
Tenant admin configuration with Unfold best practices
"""
import logging

from django.contrib import admin
from django import forms
from django.contrib.admin.actions import delete_selected
from django.contrib.admin.utils import unquote
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from apps.audit.models import AuditLog
from .models import Tenant, Domain

logger = logging.getLogger(__name__)

PROVISIONED_DELETE_MESSAGE = (
    'Este tenant tiene schema aprovisionado; no se borra desde el admin. Sus filas guardan '
    'referencias a usuarios de la plataforma que el borrado no alcanza: es una operación de '
    'plataforma aparte. Desde aquí sólo se borran registros pendientes.'
)


def _is_platform_admin(user):
    return user.is_superuser and user.tenant_id is None


def delete_selected_tenants(modeladmin, request, queryset):
    """`delete_selected` de Django, salvo que la selección incluya un tenant aprovisionado:
    entonces no borra ninguno (ni muestra la confirmación) y lo dice."""
    provisioned = list(queryset.filter(provisioning_pending=False).values_list('name', flat=True))
    if provisioned:
        modeladmin.message_user(
            request,
            f'No se borró ningún tenant. {PROVISIONED_DELETE_MESSAGE} Aprovisionados: {", ".join(provisioned)}.',
            level=messages.ERROR,
        )
        return None
    return delete_selected(modeladmin, request, queryset)


delete_selected_tenants.allowed_permissions = delete_selected.allowed_permissions
delete_selected_tenants.short_description = delete_selected.short_description


class TenantAdminForm(forms.ModelForm):
    """Tenant admin form. `schema_name` is read-only: renaming it orphans the Postgres schema."""

    class Meta:
        model = Tenant
        fields = '__all__'


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
    list_filter = ['is_active', 'provisioning_pending', 'subscription_plan', 'created_on']
    search_fields = ['name', 'business_name', 'email', 'tax_id']
    # El estado pendiente sólo lo cambia el aprovisionamiento (crea el schema): marcarlo a mano
    # dejaría un tenant activo sin schema.
    readonly_fields = ['created_on', 'updated_on', 'provisioning_pending', 'pending_since']
    list_per_page = 25
    save_on_top = True
    actions = ['generate_demo_data_action', 'provision_pending_action']

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

        if not _is_platform_admin(request.user):
            self.message_user(
                request,
                'Solo un superusuario de plataforma puede generar datos demo.',
                level=messages.ERROR
            )
            return

        success_count = 0
        error_count = 0

        # Un registro pendiente no tiene schema: set_tenant caería en el schema público.
        for tenant in queryset.filter(provisioning_pending=False):
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

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not _is_platform_admin(request.user):
            actions.pop('provision_pending_action', None)
        if 'delete_selected' in actions:
            _, name, description = actions['delete_selected']
            actions['delete_selected'] = (delete_selected_tenants, name, description)
        return actions

    # ------------------------------------------------------------------
    # Borrado: sólo el superusuario de plataforma y sólo registros pendientes
    # ------------------------------------------------------------------

    def has_delete_permission(self, request, obj=None):
        """Sólo el superusuario de plataforma (no basta el permiso de modelo `delete_tenant`).

        Un tenant aprovisionado no se borra desde aquí: la cascada corre en public y no ve las
        filas de su schema que referencian a sus usuarios (`created_by`...); el COMMIT fallaría.
        """
        if not _is_platform_admin(request.user):
            return False
        return obj is None or obj.provisioning_pending

    def delete_view(self, request, object_id, extra_context=None):
        # Rehusar con un mensaje antes de que has_delete_permission(obj) responda 403
        if _is_platform_admin(request.user):
            obj = self.get_object(request, unquote(object_id))
            if obj is not None and not obj.provisioning_pending:
                self.message_user(request, PROVISIONED_DELETE_MESSAGE, level=messages.ERROR)
                return redirect(reverse('admin:tenants_tenant_change', args=[obj.pk]))
        return super().delete_view(request, object_id, extra_context)

    def get_deleted_objects(self, objs, request):
        """La historia de auditoría del tenant se va con él (CASCADE) sin pedir permiso de
        borrado en `AuditLogAdmin`, que no lo da a nadie: borrarla por la cascada del tenant no
        es borrar filas de auditoría a mano, y el borrado deja su fila de plataforma. Sigue
        listada en la confirmación. Cualquier otro modelo sin permiso sigue bloqueando."""
        deleted, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        if _is_platform_admin(request.user):
            perms_needed.discard(AuditLog._meta.verbose_name)
        return deleted, model_count, perms_needed, protected

    def _assert_still_pending(self, pks):
        # Decide sobre las filas bloqueadas: el aprovisionamiento (que también bloquea) pudo
        # adelantarse entre la confirmación y el borrado. 403, nunca un 500 en el COMMIT.
        pks = set(pks)
        locked = set(
            Tenant.objects.select_for_update(of=('self',))
            .filter(pk__in=pks, provisioning_pending=True)
            .values_list('pk', flat=True)
        )
        if locked != pks:
            raise PermissionDenied(PROVISIONED_DELETE_MESSAGE)

    def delete_model(self, request, obj):
        with transaction.atomic():
            self._assert_still_pending([obj.pk])
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        # queryset.delete() es TenantQuerySet.delete(): ámbito tenant_deletion de la auditoría
        with transaction.atomic():
            self._assert_still_pending(queryset.values_list('pk', flat=True))
            super().delete_queryset(request, queryset)

    @action(description="Aprovisionar registros pendientes")
    def provision_pending_action(self, request, queryset):
        """Crea el schema y activa los tenants pendientes seleccionados (los demás se saltan).

        Equivale al comando `provision_pending_tenants [--limit N]`. Los pendientes que nadie
        aprovisiona se borran con `expire_pending_registrations [--days 7]` (a mano o desde
        cron; aún no hay tarea Celery que lo envuelva).
        """
        from .provisioning import provision_pending_tenant

        if not _is_platform_admin(request.user):
            self.message_user(
                request,
                'Solo un superusuario de plataforma puede aprovisionar registros pendientes.',
                level=messages.ERROR
            )
            return

        provisioned = skipped = failed = 0
        for pk in queryset.order_by('pk').values_list('pk', flat=True):
            try:
                if provision_pending_tenant(pk):
                    provisioned += 1
                else:
                    skipped += 1
            except Exception:
                failed += 1
                logger.exception('No se pudo aprovisionar el tenant pendiente id=%s', pk)

        logger.info('Aprovisionamiento desde el admin por %s: %s aprovisionados, %s saltados, %s con error',
                    request.user.pk, provisioned, skipped, failed)
        self.message_user(
            request,
            f'Tenants aprovisionados: {provisioned}. Saltados (no pendientes): {skipped}. Con error: {failed}.',
            level=messages.ERROR if failed else messages.SUCCESS
        )

    def save_model(self, request, obj, form, change):
        # Guardar un pendiente desde el formulario no debe crearle el schema por la puerta de
        # atrás (TenantMixin.save crea el schema de un tenant existente que no lo tiene): eso
        # sólo lo hace el aprovisionamiento, que además lo activa y migra.
        if obj.provisioning_pending:
            obj.auto_create_schema = False
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        # schema_name se fija al crear el tenant; renombrarlo deja el schema de Postgres huérfano.
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            readonly.append('schema_name')
        return readonly

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

        if not _is_platform_admin(request.user):
            raise PermissionDenied

        tenant_id = request.GET.get('tenant_id')

        if request.method == 'POST':
            selected_tenant_id = request.POST.get('tenant')

            if not selected_tenant_id:
                messages.error(request, 'Please select a tenant')
                return redirect('admin:tenants_tenant_changelist')

            try:
                tenant = Tenant.objects.get(id=selected_tenant_id, provisioning_pending=False)

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
