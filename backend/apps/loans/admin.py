"""
Loan admin configuration with Unfold best practices
"""
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from .models import Customer, CustomerDocument, Loan, LoanSchedule, LoanPayment, Collateral
from .models_contacts import CustomerPhone, CustomerEmail
from .models_guarantors import Guarantor
from .models_collections import CollectionReminder, CollectionContact
from .models_contracts import ContractTemplate, Contract, ContractSignatureToken
from rest_framework.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from .policy import (
    LOAN_LIFECYCLE_FIELDS, LOAN_LOCKED_FIELDS, LOAN_TERM_FIELDS, loan_terms_locked,
    validate_approval, validate_origination,
)
from .disbursement import apply_disbursement, calculate_payment_amount, check_disbursable


def is_tenant_schema():
    """Check if we're in a tenant schema (not public)"""
    try:
        return connection.schema_name != 'public'
    except:
        return False


class _ReadOnlyLoanInline(TabularInline):
    """Filas que sólo cambian por sus flujos (desembolso, pagos, reversos), nunca por el formulario."""
    extra = 0
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        return list(self.fields)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CustomerDocumentInline(TabularInline):
    """Inline admin for customer documents"""
    model = CustomerDocument
    extra = 0
    fields = ['document_type', 'title', 'verification_status', 'expiry_date', 'is_primary']
    readonly_fields = []
    can_delete = True
    show_change_link = True


class LoanInline(_ReadOnlyLoanInline):
    """Préstamos del cliente (solo lectura: estado y términos cambian en LoanAdmin y sus acciones)"""
    model = Loan
    fields = ['loan_number', 'loan_type', 'principal_amount', 'status', 'created_at']
    show_change_link = True


class CustomerPhoneInline(TabularInline):
    model = CustomerPhone
    extra = 0
    fields = ['phone', 'phone_type', 'is_primary', 'is_whatsapp', 'label']


class CustomerEmailInline(TabularInline):
    model = CustomerEmail
    extra = 0
    fields = ['email', 'email_type', 'is_primary', 'label']


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    """Admin interface for Customer model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'customer_id', 'get_full_name', 'email', 'phone',
        'id_type', 'id_number', 'show_status', 'created_at'
    ]
    list_filter = ['status', 'employment_status', 'id_type', 'created_at', 'gender']
    search_fields = [
        'customer_id', 'first_name', 'last_name', 'email',
        'phone', 'id_number'
    ]
    list_per_page = 25
    list_select_related = True

    # Form configuration
    readonly_fields = ['customer_id', 'created_at', 'updated_at']
    inlines = [CustomerPhoneInline, CustomerEmailInline, CustomerDocumentInline, LoanInline]
    save_on_top = True

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Only allow delete in tenant schemas"""
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'active': 'success',
            'inactive': 'danger',
            'suspended': 'warning',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    # Tabs configuration
    tab_personal = [
        (None, {
            'fields': ('customer_id', 'status')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'photo'
            )
        }),
        ('Identification', {
            'fields': (
                'id_type', 'id_number', 'id_expiry_date', 'id_document'
            )
        }),
    ]

    tab_contact = [
        ('Contact Information', {
            'fields': ('email', 'phone', 'alternate_phone')
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state', 'country', 'postal_code'
            )
        }),
    ]

    tab_financial = [
        ('Employment', {
            'fields': (
                'employment_status', 'employer_name',
                'occupation', 'monthly_income'
            )
        }),
        ('Financial Information', {
            'fields': ('credit_score',)
        }),
    ]

    tab_loans = [
        (None, {
            'fields': ()
        }),
    ]

    # Default fieldsets (fallback when tabs are not used)
    fieldsets = (
        (None, {
            'fields': ('customer_id', 'status')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'photo'
            )
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'alternate_phone')
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city',
                'state', 'country', 'postal_code'
            )
        }),
        ('Identification', {
            'fields': (
                'id_type', 'id_number', 'id_expiry_date', 'id_document'
            )
        }),
        ('Employment', {
            'fields': (
                'employment_status', 'employer_name',
                'occupation', 'monthly_income'
            )
        }),
        ('Financial Information', {
            'fields': ('credit_score',)
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class LoanScheduleInline(_ReadOnlyLoanInline):
    """Inline admin for loan schedules (solo lectura: el cronograma sale del desembolso)"""
    model = LoanSchedule
    fields = [
        'installment_number', 'due_date', 'total_amount',
        'principal_amount', 'interest_amount', 'paid_amount', 'status'
    ]


class LoanPaymentInline(_ReadOnlyLoanInline):
    """Inline admin for loan payments (solo lectura: los pagos tienen su propio flujo)"""
    model = LoanPayment
    fields = [
        'payment_number', 'payment_date', 'amount',
        'payment_method', 'status'
    ]


class CollateralInline(TabularInline):
    """Inline admin for collaterals (editables sólo mientras el préstamo está pendiente)"""
    model = Collateral
    extra = 0
    fields = [
        'collateral_type', 'description', 'estimated_value', 'status'
    ]

    @staticmethod
    def _editable(obj):
        return obj is None or obj.status == 'pending'

    def has_add_permission(self, request, obj=None):
        return self._editable(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._editable(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._editable(obj) and super().has_delete_permission(request, obj)


class LoanAdminForm(forms.ModelForm):
    """Formulario de LoanAdmin: la política de originación del tenant se informa como errores
    del formulario (igual que el 400 de la API), no como una página 403.

    `request` lo fija LoanAdmin.get_form en la clase que construye para cada petición.
    """

    request = None
    POLICY_ATTRS = ('principal_amount', 'interest_rate', 'term_months', 'interest_type', 'payment_frequency')

    def clean(self):
        cleaned = super().clean()
        adding = self.instance.pk is None
        if not adding and not set(self.changed_data) & set(LOAN_TERM_FIELDS):
            return cleaned
        attrs = {
            f: cleaned[f] if f in cleaned else getattr(self.instance, f, None)
            for f in self.POLICY_ATTRS
        }
        # El tope por cliente sólo se revisa al crear o si el préstamo cambia de cliente.
        customer = cleaned.get('customer') if (adding or 'customer' in self.changed_data) else None
        try:
            validate_origination(attrs, customer, self.request,
                                 instance=None if adding else self.instance)
        except ValidationError as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {None: exc.detail}
            for field, msgs in detail.items():
                target = field if field in self.fields else None
                for msg in (msgs if isinstance(msgs, list) else [msgs]):
                    self.add_error(target, str(msg))
        return cleaned


@admin.register(Loan)
class LoanAdmin(ModelAdmin):
    """Admin interface for Loan model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'loan_number', 'customer', 'loan_type', 'principal_amount',
        'interest_rate', 'show_status', 'disbursement_date', 'created_at'
    ]
    list_filter = ['status', 'loan_type', 'payment_frequency', 'created_at']
    search_fields = [
        'loan_number', 'customer__customer_id',
        'customer__first_name', 'customer__last_name'
    ]
    list_per_page = 25
    actions = ['approve_loans', 'reject_loans', 'disburse_loans']

    # Form configuration
    readonly_fields = [
        'loan_number', 'created_at', 'updated_at',
        'total_paid', 'total_interest_paid', 'outstanding_balance'
    ]
    inlines = [CollateralInline, LoanScheduleInline, LoanPaymentInline]
    save_on_top = True
    form = LoanAdminForm

    # Estado y fechas del ciclo sólo cambian por las acciones approve/reject/disburse
    # (que aplican la política); la cuota sale del cálculo de amortización.
    LIFECYCLE_FIELDS = LOAN_LIFECYCLE_FIELDS + ('payment_amount',)
    # Deudor, términos y documento: los mismos que fija la API (loan_terms_locked).
    TERM_FIELDS = LOAN_LOCKED_FIELDS

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Sólo en tenants y, como LoanViewSet.perform_destroy, sólo pendientes o rechazados."""
        if obj is not None and obj.status not in ('pending', 'rejected'):
            return False
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        """La acción masiva «Eliminar» aplica la misma regla que has_delete_permission."""
        if queryset.exclude(status__in=('pending', 'rejected')).exists():
            raise PermissionDenied('Solo se pueden eliminar préstamos pendientes o rechazados.')
        super().delete_queryset(request, queryset)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        readonly += [f for f in self.LIFECYCLE_FIELDS if f not in readonly]
        if obj is not None and obj.status != 'pending' and 'late_fees' not in readonly:
            readonly.append('late_fees')  # mora de un préstamo vivo: sólo por sus flujos
        if obj is not None and loan_terms_locked(obj):
            readonly += [f for f in self.TERM_FIELDS if f not in readonly]
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        # modelform_factory crea una clase nueva por llamada: el atributo no se comparte.
        form_class = super().get_form(request, obj, **kwargs)
        form_class.request = request
        return form_class

    def save_model(self, request, obj, form, change):
        """Defensa en profundidad: un POST manipulado no cambia estado ni términos bloqueados."""
        changed = set(getattr(form, 'changed_data', ()))
        if change and 'status' in changed:
            raise PermissionDenied(
                'El estado del préstamo sólo cambia con las acciones aprobar, rechazar o desembolsar.'
            )
        if change and changed & set(self.TERM_FIELDS) and loan_terms_locked(Loan.objects.get(pk=obj.pk)):
            raise PermissionDenied(
                'No se puede modificar el deudor ni los términos después de aprobado el préstamo '
                'o firmado el contrato.'
            )
        if change and 'late_fees' in changed and Loan.objects.get(pk=obj.pk).status != 'pending':
            raise PermissionDenied('La mora de un préstamo aprobado sólo cambia por sus flujos.')

        terms_changed = bool(changed & set(LOAN_TERM_FIELDS))
        if not change or terms_changed:
            self._validate_origination(request, obj, change, changed)
            # La cuota sale del mismo cálculo que la API, nunca del formulario.
            obj.payment_amount = calculate_payment_amount(obj)
        if not change:
            obj.outstanding_balance = obj.principal_amount
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        """El contrato se genera o rehace después de guardar los inlines (garantías incluidas).

        En save_model las garantías del mismo formulario aún no existen y el contrato saldría con
        "Sin garantías". Todo sigue dentro de la transacción de changeform_view.
        """
        super().save_related(request, form, formsets, change)
        obj = form.instance

        if not change:
            self._generate_initial_contract(request, obj)
            return

        terms_changed = bool(set(getattr(form, 'changed_data', ())) & set(LOAN_TERM_FIELDS))
        collateral_changed = any(
            formset.model is Collateral and formset.has_changed() for formset in formsets
        )
        if terms_changed or collateral_changed:
            # Igual que la API (perform_update y altas/cambios de garantías): el contrato por
            # firmar refleja los términos y las garantías; uno firmado no se reescribe.
            from .utils_contracts import regenerate_latest_loan_contract
            regenerate_latest_loan_contract(obj, getattr(request, 'tenant', None))

    def _generate_initial_contract(self, request, obj):
        """Mismo contrato inicial que LoanViewSet.perform_create.

        Asimetría deliberada: la API falla si no hay plantilla activa; aquí el préstamo se guarda
        igual y se avisa, porque queda `pending` y no se puede desembolsar sin un contrato firmado.
        Cualquier otro error se propaga y deshace también el préstamo (changeform_view es atómica).
        """
        from django.contrib import messages
        from .utils_contracts import NoActiveContractTemplate, generate_initial_contract

        try:
            generate_initial_contract(obj, request.user, getattr(request, 'tenant', None))
        except NoActiveContractTemplate:
            self.message_user(
                request,
                'El préstamo se creó sin contrato porque no hay una plantilla de contrato activa para '
                'este tipo de préstamo. Genere el contrato cuando exista una plantilla; sin contrato '
                'firmado no se puede desembolsar.',
                level=messages.WARNING,
            )

    @staticmethod
    def _validate_origination(request, obj, change, changed):
        """Política de originación del tenant, igual que la API al crear o editar términos.

        LoanAdminForm.clean ya la aplica y devuelve el formulario con errores; esto queda como
        defensa en profundidad (403) por si se llega a save_model con un formulario que no la pasó.
        """
        attrs = {f: getattr(obj, f) for f in (
            'principal_amount', 'interest_rate', 'term_months', 'interest_type', 'payment_frequency',
        )}
        # El tope por cliente sólo se revisa al crear o si el préstamo cambia de cliente.
        customer = obj.customer if (not change or 'customer' in changed) else None
        try:
            validate_origination(attrs, customer, request, instance=obj if change else None)
        except ValidationError as exc:
            detail = exc.detail
            messages_ = detail.values() if isinstance(detail, dict) else [detail]
            text = ' '.join(
                str(m) for msgs in messages_ for m in (msgs if isinstance(msgs, list) else [msgs])
            )
            raise PermissionDenied(f'El préstamo no cumple la política de la organización: {text}')

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'warning',
            'approved': 'info',
            'active': 'success',
            'completed': 'success',
            'defaulted': 'danger',
            'cancelled': 'danger',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    # Tabs configuration
    tab_general = [
        ('Loan Information', {
            'fields': (
                'loan_number', 'customer', 'loan_type', 'status', 'loan_officer'
            )
        }),
        ('Loan Amount', {
            'fields': (
                'principal_amount', 'interest_rate', 'term_months',
                'payment_frequency', 'payment_amount'
            )
        }),
        ('Dates', {
            'fields': (
                'application_date', 'approval_date', 'disbursement_date',
                'first_payment_date', 'maturity_date'
            )
        }),
        ('Balances', {
            'fields': (
                'outstanding_balance', 'total_paid',
                'total_interest_paid', 'late_fees'
            ),
            'classes': ('tab-fs-8',)
        }),
        ('Additional Information', {
            'fields': (
                'purpose', 'notes', 'terms_accepted', 'contract_document'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]

    tab_schedule = [
        (None, {
            'fields': ()
        }),
    ]

    tab_payments = [
        (None, {
            'fields': ()
        }),
    ]

    tab_collateral = [
        (None, {
            'fields': ()
        }),
    ]

    # Default fieldsets (fallback when tabs are not used)
    fieldsets = (
        ('Loan Information', {
            'fields': (
                'loan_number', 'customer', 'loan_type', 'status', 'loan_officer'
            )
        }),
        ('Loan Amount', {
            'fields': (
                'principal_amount', 'interest_rate', 'term_months',
                'payment_frequency', 'payment_amount'
            )
        }),
        ('Dates', {
            'fields': (
                'application_date', 'approval_date', 'disbursement_date',
                'first_payment_date', 'maturity_date'
            )
        }),
        ('Balances', {
            'fields': (
                'outstanding_balance', 'total_paid',
                'total_interest_paid', 'late_fees'
            )
        }),
        ('Additional Information', {
            'fields': (
                'purpose', 'notes', 'terms_accepted', 'contract_document'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'loan_officer')

    @admin.action(description='Aprobar préstamos seleccionados')
    def approve_loans(self, request, queryset):
        """Approve selected loans"""
        from django.utils import timezone
        from django.contrib import messages

        pending_loans = queryset.filter(status='pending')
        count = pending_loans.count()

        if count == 0:
            self.message_user(request, 'No hay préstamos pendientes para aprobar', messages.WARNING)
            return

        approved = 0
        for loan in pending_loans:
            try:
                validate_approval(loan, request)
            except ValidationError as exc:
                self._report_policy_violation(request, loan, exc)
                continue
            loan.status = 'approved'
            loan.approval_date = timezone.localdate()
            loan.approved_by = request.user
            loan.save()
            approved += 1

        if approved:
            self.message_user(
                request,
                f'{approved} préstamo(s) aprobado(s) exitosamente',
                messages.SUCCESS
            )

    @admin.action(description='Rechazar préstamos seleccionados')
    def reject_loans(self, request, queryset):
        """Reject selected loans"""
        from django.utils import timezone
        from django.contrib import messages

        pending_loans = queryset.filter(status='pending')
        count = pending_loans.count()

        if count == 0:
            self.message_user(request, 'No hay préstamos pendientes para rechazar', messages.WARNING)
            return

        # Update all pending loans
        for loan in pending_loans:
            loan.status = 'rejected'
            loan.rejection_date = timezone.localdate()
            loan.rejected_by = request.user
            loan.save()

        self.message_user(
            request,
            f'{count} préstamo(s) rechazado(s) exitosamente',
            messages.SUCCESS
        )

    @admin.action(description='Desembolsar préstamos aprobados')
    def disburse_loans(self, request, queryset):
        """Desembolsa los aprobados que cumplen las precondiciones; informa los que no."""
        from django.contrib import messages
        from django.db import transaction

        approved_loans = queryset.filter(status='approved')
        count = approved_loans.count()

        if count == 0:
            self.message_user(request, 'No hay préstamos aprobados para desembolsar', messages.WARNING)
            return

        disbursed = 0
        for loan in approved_loans:
            # Mismas precondiciones y efectos que la API (apps.loans.disbursement); sin caja:
            # el admin no tiene sesión de caja, así que no registra egreso.
            try:
                with transaction.atomic():
                    locked = Loan.objects.select_for_update().get(pk=loan.pk)
                    contract = check_disbursable(locked, request.user, request)
                    apply_disbursement(locked, contract)
            except ValidationError as exc:
                self._report_policy_violation(request, loan, exc)
                continue
            disbursed += 1

        if disbursed:
            self.message_user(
                request,
                f'{disbursed} préstamo(s) desembolsado(s) exitosamente',
                messages.SUCCESS
            )

    def _report_policy_violation(self, request, loan, exc):
        from django.contrib import messages

        detail = exc.detail
        if isinstance(detail, dict):
            # contract_id/contract_status son datos para la API, no texto para el mensaje.
            detail = {k: v for k, v in detail.items() if k not in ('contract_id', 'contract_status')}
            parts = [str(msg) for msgs in detail.values() for msg in (msgs if isinstance(msgs, list) else [msgs])]
        else:
            parts = [str(msg) for msg in detail]
        self.message_user(
            request,
            f'{loan.loan_number}: ' + ' '.join(parts),
            messages.ERROR
        )


@admin.register(LoanSchedule)
class LoanScheduleAdmin(ModelAdmin):
    """Admin interface for LoanSchedule model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'loan', 'installment_number', 'due_date',
        'total_amount', 'paid_amount', 'show_status'
    ]
    list_filter = ['status', 'due_date']
    search_fields = ['loan__loan_number']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    # Solo lectura para todos: cuotas y pagos cambian únicamente por sus flujos
    # (desembolso, registro y reverso de pagos), nunca editando la fila.
    def get_readonly_fields(self, request, obj=None):
        return [f for _, opts in self.get_fieldsets(request, obj) for f in opts['fields']]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'warning',
            'paid': 'success',
            'overdue': 'danger',
            'partial': 'info',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    fieldsets = (
        ('Schedule Information', {
            'fields': ('loan', 'installment_number', 'due_date', 'status')
        }),
        ('Amount Breakdown', {
            'fields': (
                'total_amount', 'principal_amount',
                'interest_amount', 'paid_amount', 'paid_date'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoanPayment)
class LoanPaymentAdmin(ModelAdmin):
    """Admin interface for LoanPayment model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'payment_number', 'loan', 'payment_date', 'amount',
        'payment_method', 'show_status'
    ]
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = [
        'payment_number', 'loan__loan_number',
        'reference_number'
    ]
    readonly_fields = ['payment_number', 'created_at', 'updated_at']
    list_per_page = 50
    save_on_top = True

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    # Solo lectura para todos: cuotas y pagos cambian únicamente por sus flujos
    # (desembolso, registro y reverso de pagos), nunca editando la fila.
    def get_readonly_fields(self, request, obj=None):
        return [f for _, opts in self.get_fieldsets(request, obj) for f in opts['fields']]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'reversed': 'danger',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_number', 'loan', 'schedule',
                'payment_date', 'status'
            )
        }),
        ('Amount Details', {
            'fields': (
                'amount', 'principal_paid', 'interest_paid', 'late_fee_paid'
            )
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'reference_number')
        }),
        ('Additional Information', {
            'fields': ('notes', 'receipt')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Collateral)
class CollateralAdmin(ModelAdmin):
    """Admin interface for Collateral model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'loan', 'collateral_type', 'estimated_value',
        'appraisal_value', 'show_status'
    ]
    list_filter = ['collateral_type', 'status']
    search_fields = ['loan__loan_number', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    # Las garantías sólo se dan de alta, editan o borran mientras el préstamo está pendiente
    # (lo que el aprobador revisó); después cambian por sus flujos.
    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        """La acción masiva «Eliminar» aplica la misma regla que has_delete_permission."""
        if queryset.exclude(loan__status='pending').exists():
            raise PermissionDenied('Las garantías sólo se eliminan mientras el préstamo está pendiente.')
        super().delete_queryset(request, queryset)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'loan':
            kwargs['queryset'] = Loan.objects.filter(status='pending')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        loans = [obj.loan_id]
        if change:
            loans.append(Collateral.objects.filter(pk=obj.pk).values_list('loan_id', flat=True).first())
        if Loan.objects.filter(pk__in=loans).exclude(status='pending').exists():
            raise PermissionDenied('Las garantías sólo se modifican mientras el préstamo está pendiente.')
        super().save_model(request, obj, form, change)

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'warning',
            'verified': 'success',
            'released': 'info',
            'seized': 'danger',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    fieldsets = (
        ('Collateral Information', {
            'fields': (
                'loan', 'collateral_type', 'description', 'status'
            )
        }),
        ('Valuation', {
            'fields': (
                'estimated_value', 'appraisal_value', 'appraisal_date'
            )
        }),
        ('Documentation', {
            'fields': ('documents', 'photos')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomerDocument)
class CustomerDocumentAdmin(ModelAdmin):
    """Admin interface for CustomerDocument model with Unfold best practices"""

    # Unfold specific settings
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'customer', 'document_type', 'title', 'show_verification_status',
        'show_expiry_status', 'is_primary', 'created_at'
    ]
    list_filter = ['document_type', 'verification_status', 'is_primary', 'created_at']
    search_fields = [
        'title', 'description', 'customer__customer_id',
        'customer__first_name', 'customer__last_name'
    ]
    list_per_page = 50
    save_on_top = True

    # Form configuration
    readonly_fields = [
        'file_size', 'file_type', 'file_size_mb', 'is_expired',
        'verified_by', 'verified_at', 'created_at', 'updated_at'
    ]

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Only allow delete in tenant schemas"""
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    @display(description="Verification Status", label=True)
    def show_verification_status(self, obj):
        """Display verification status with color badge"""
        colors = {
            'pending': 'warning',
            'verified': 'success',
            'rejected': 'danger',
            'expired': 'danger',
        }
        return colors.get(obj.verification_status, 'info'), obj.get_verification_status_display()

    @display(description="Expiry", label=True)
    def show_expiry_status(self, obj):
        """Display expiry status with color badge"""
        if not obj.expiry_date:
            return 'info', 'No Expiry'

        if obj.is_expired:
            return 'danger', f'Expired ({obj.expiry_date})'

        from django.utils import timezone
        days_until_expiry = (obj.expiry_date - timezone.localdate()).days

        if days_until_expiry <= 30:
            return 'warning', f'Expires Soon ({obj.expiry_date})'

        return 'success', f'Valid ({obj.expiry_date})'

    fieldsets = (
        ('Document Information', {
            'fields': (
                'customer', 'document_type', 'title', 'description', 'is_primary'
            )
        }),
        ('File Upload', {
            'fields': (
                'document_file', 'file_size', 'file_type', 'file_size_mb'
            )
        }),
        ('Verification', {
            'fields': (
                'verification_status', 'verified_by', 'verified_at', 'rejection_reason'
            )
        }),
        ('Document Dates', {
            'fields': (
                'issue_date', 'expiry_date', 'is_expired'
            )
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'verified_by')


@admin.register(CollectionReminder)
class CollectionReminderAdmin(ModelAdmin):
    """Admin interface for CollectionReminder model"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'customer', 'loan', 'reminder_type', 'channel',
        'scheduled_for', 'show_status', 'sent_at'
    ]
    list_filter = ['status', 'reminder_type', 'channel', 'scheduled_for']
    search_fields = [
        'loan__loan_number', 'customer__first_name',
        'customer__last_name', 'message_content'
    ]
    readonly_fields = ['sent_at', 'sent_by', 'created_at', 'updated_at']
    list_per_page = 50

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Only allow delete in tenant schemas"""
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    @display(description="Status", label=True)
    def show_status(self, obj):
        """Display status with color badge"""
        colors = {
            'pending': 'warning',
            'sent': 'success',
            'failed': 'danger',
            'cancelled': 'info',
        }
        return colors.get(obj.status, 'info'), obj.get_status_display()

    fieldsets = (
        ('Reminder Information', {
            'fields': (
                'loan', 'loan_schedule', 'customer',
                'reminder_type', 'channel', 'status'
            )
        }),
        ('Scheduling', {
            'fields': ('scheduled_for', 'sent_at', 'sent_by')
        }),
        ('Content', {
            'fields': ('message_content', 'error_message')
        }),
        ('Customer Response', {
            'fields': ('customer_response', 'response_received_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'customer', 'loan_schedule', 'sent_by')


@admin.register(CollectionContact)
class CollectionContactAdmin(ModelAdmin):
    """Admin interface for CollectionContact model"""

    # Unfold specific settings
    list_fullwidth = True
    compressed_fields = True

    # List view configuration
    list_display = [
        'customer', 'loan', 'contact_date', 'contact_type',
        'outcome', 'show_escalation', 'contacted_by'
    ]
    list_filter = [
        'contact_type', 'outcome', 'requires_escalation',
        'promise_kept', 'contact_date'
    ]
    search_fields = [
        'loan__loan_number', 'customer__first_name',
        'customer__last_name', 'notes'
    ]
    readonly_fields = ['contacted_by', 'created_at', 'updated_at']
    list_per_page = 50

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return is_tenant_schema() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return is_tenant_schema() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Only allow delete in tenant schemas"""
        return is_tenant_schema() and super().has_delete_permission(request, obj)

    @display(description="Escalation", label=True)
    def show_escalation(self, obj):
        """Display escalation status with color badge"""
        if obj.requires_escalation:
            return 'danger', 'Requires Escalation'
        return 'success', 'Normal'

    fieldsets = (
        ('Contact Information', {
            'fields': (
                'loan', 'customer', 'contact_date',
                'contact_type', 'contacted_by'
            )
        }),
        ('Outcome', {
            'fields': ('outcome', 'notes')
        }),
        ('Promise to Pay', {
            'fields': (
                'promise_date', 'promise_amount', 'promise_kept'
            )
        }),
        ('Follow-up', {
            'fields': (
                'next_contact_date', 'requires_escalation'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'customer', 'contacted_by')


# ============================================================================
# CONTRACT TEMPLATE ADMIN
# ============================================================================

@admin.register(ContractTemplate)
class ContractTemplateAdmin(ModelAdmin):
    """Admin interface for ContractTemplate model"""

    list_fullwidth = True
    warn_unsaved_form = True

    list_display = [
        'name', 'is_active', 'is_default', 
        'created_by', 'created_at'
    ]

    list_filter = ['is_active', 'is_default', 'created_at']

    search_fields = ['name', 'description']

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'is_active', 'is_default')
        }),
        ('Content', {
            'fields': ('content', 'header_image', 'footer_text')
        }),
        ('Settings', {
            'fields': ('loan_types',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make created_by readonly after creation"""
        readonly = super().get_readonly_fields(request, obj)
        if obj:  # Editing existing object
            return readonly + ['created_by']
        return readonly

    def save_model(self, request, obj, form, change):
        """Auto-assign created_by on creation"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# CONTRACT ADMIN
# ============================================================================

@admin.register(Contract)
class ContractAdmin(ModelAdmin):
    """Admin interface for Contract model"""

    list_fullwidth = True
    warn_unsaved_form = True

    list_display = [
        'contract_number', 'get_loan_number', 'get_customer_name',
        'status', 'is_fully_signed', 'generated_at'
    ]

    list_filter = ['status', 'generated_at']

    search_fields = [
        'contract_number', 'loan__loan_number', 
        'loan__customer__first_name', 'loan__customer__last_name'
    ]

    readonly_fields = [
        'contract_number', 'generated_at', 'updated_at', 
        'is_fully_signed'
    ]

    fieldsets = (
        ('Contract Information', {
            'fields': ('contract_number', 'loan', 'template', 'status')
        }),
        ('Content', {
            'fields': ('content', 'pdf_file', 'special_terms')
        }),
        ('Signatures - Customer', {
            'fields': (
                'customer_signed_at', 'customer_signature'
            )
        }),
        ('Signatures - Officer', {
            'fields': (
                'officer_signed_at', 'officer_signature'
            )
        }),
        ('Signatures - Witness', {
            'fields': (
                'witness_name', 'witness_id', 
                'witness_signed_at', 'witness_signature'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'generated_by', 'generated_at', 'updated_at',
                'is_fully_signed'
            ),
            'classes': ('collapse',)
        }),
    )

    @display(description='Loan Number', ordering='loan__loan_number')
    def get_loan_number(self, obj):
        """Display loan number"""
        return obj.loan.loan_number if obj.loan else '-'

    @display(description='Customer', ordering='loan__customer__last_name')
    def get_customer_name(self, obj):
        """Display customer name"""
        return obj.loan.customer.get_full_name() if obj.loan else '-'

    def get_readonly_fields(self, request, obj=None):
        """Make generated_by readonly after creation"""
        readonly = super().get_readonly_fields(request, obj)
        if obj:
            return readonly + ['generated_by']
        return readonly

    def save_model(self, request, obj, form, change):
        """Auto-assign generated_by and generate content on creation"""
        if not change:
            obj.generated_by = request.user

            # Generate content from template if template is set
            if obj.template:
                from .utils_contracts import replace_contract_variables
                from apps.tenants.models import Tenant

                # Try to get tenant from request
                try:
                    tenant_schema = connection.schema_name
                    if tenant_schema and tenant_schema != 'public':
                        tenant = Tenant.objects.get(schema_name=tenant_schema)
                    else:
                        tenant = None
                except:
                    tenant = None

                obj.content = replace_contract_variables(
                    obj.template.content,
                    obj.loan,
                    tenant
                )

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'loan__customer', 'template', 'generated_by')


@admin.register(ContractSignatureToken)
class ContractSignatureTokenAdmin(ModelAdmin):
    """Admin interface for ContractSignatureToken model"""

    list_fullwidth = True
    list_display = [
        'contract',
        'email',
        'can_sign_as_customer',
        'can_sign_as_officer',
        'sent_at',
        'expires_at',
        'used_at',
        'is_valid_status',
    ]
    list_filter = [
        'can_sign_as_customer',
        'can_sign_as_officer',
        'sent_at',
        'expires_at',
    ]
    search_fields = ['email', 'contract__contract_number', 'token']
    readonly_fields = ['id', 'token', 'sent_at', 'used_at', 'created_at']

    fieldsets = [
        ('Contract Information', {
            'fields': ['contract', 'email']
        }),
        ('Permissions', {
            'fields': ['can_sign_as_customer', 'can_sign_as_officer']
        }),
        ('Token Details', {
            'fields': ['token', 'expires_at']
        }),
        ('Tracking', {
            'fields': ['sent_at', 'used_at', 'created_at']
        }),
    ]

    def is_valid_status(self, obj):
        """Display whether token is valid"""
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        elif obj.is_used:
            return format_html('<span style="color: gray;">Used</span>')
        else:
            return format_html('<span style="color: red;">Expired</span>')
    is_valid_status.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('contract', 'contract__loan')


# ============================================================
# Customer Contacts
# ============================================================

@admin.register(CustomerPhone)
class CustomerPhoneAdmin(ModelAdmin):
    list_display = ['phone', 'customer', 'phone_type', 'is_primary', 'is_whatsapp']
    list_filter = ['phone_type', 'is_primary', 'is_whatsapp']
    search_fields = ['phone', 'customer__first_name', 'customer__last_name']
    raw_id_fields = ['customer']


@admin.register(CustomerEmail)
class CustomerEmailAdmin(ModelAdmin):
    list_display = ['email', 'customer', 'email_type', 'is_primary']
    list_filter = ['email_type', 'is_primary']
    search_fields = ['email', 'customer__first_name', 'customer__last_name']
    raw_id_fields = ['customer']


# ============================================================
# Guarantors
# ============================================================

@admin.register(Guarantor)
class GuarantorAdmin(ModelAdmin):
    list_display = ['get_full_name', 'id_number', 'loan', 'relationship', 'status', 'phone']
    list_filter = ['status', 'relationship', 'id_type']
    search_fields = ['first_name', 'last_name', 'id_number', 'phone', 'email']
    raw_id_fields = ['loan']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'id_type', 'id_number',
                       'date_of_birth', 'gender')
        }),
        ('Contacto', {
            'fields': ('phone', 'alternate_phone', 'email', 'address', 'city', 'province')
        }),
        ('Empleo', {
            'fields': ('employer_name', 'occupation', 'monthly_income')
        }),
        ('Relación con Préstamo', {
            'fields': ('loan', 'relationship', 'status', 'notes')
        }),
        ('Documentos', {
            'fields': ('id_document', 'proof_of_income')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
