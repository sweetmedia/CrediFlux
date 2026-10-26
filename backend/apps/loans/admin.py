"""
Loan admin configuration with Unfold best practices
"""
from django import forms
from django.contrib import admin
from django.contrib.admin.actions import delete_selected
from django.contrib.admin.utils import flatten_fieldsets
from django.utils.html import format_html
from django.db import connection, router, transaction
from django.db.models.constants import LOOKUP_SEP
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from apps.core.admin_mixins import TenantHistoryMixin, TenantUserFKMixin
from .models import Customer, CustomerDocument, Loan, LoanSchedule, LoanPayment, Collateral
from .models_contacts import CustomerPhone, CustomerEmail
from .models_guarantors import Guarantor
from .models_collections import CollectionReminder, CollectionContact
from .models_contracts import ContractTemplate, Contract, ContractSignatureToken
from rest_framework.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.http import Http404
from .policy import (
    CONTRACT_EDITABLE_FIELDS, LOAN_LIFECYCLE_FIELDS, LOAN_LOCKED_FIELDS, LOAN_TERM_FIELDS,
    OPEN_CONTRACT_MESSAGE, TERMINAL_CONTRACT_STATUSES, contract_deletable, loan_has_open_contract,
    loan_terms_locked, validate_approval, validate_origination,
)
from .permissions import can_manage_loans
from .disbursement import apply_disbursement, calculate_payment_amount, check_disbursable
from .locks import LoanNotPending, lock_contract, lock_pending_loans, lock_row_loans


# Roles que pueden aprobar, rechazar y desembolsar: mismo criterio que CanApproveLoan en
# permissions.py (superusuario, dueño del tenant o uno de estos roles). Allí la regla está
# dentro de has_permission y lanza la excepción de DRF, así que se replica aquí.
APPROVER_ROLES = ('admin', 'manager', 'loan_officer')


def is_tenant_schema():
    """Check if we're in a tenant schema (not public)"""
    try:
        return connection.schema_name != 'public'
    except:
        return False


def _regenerate_loan_contracts(request, loan_ids):
    """Rehace el contrato por firmar de cada préstamo afectado (ids distintos, sin None).

    No captura excepciones: un error al renderizar debe deshacer también el cambio de la fila.
    Cada llamador debe estar dentro de una transacción: changeform_view/delete_view ya la abren;
    la acción masiva «Eliminar» (changelist_view/delete_selected) no, así que los
    delete_queryset que llaman a este helper abren la suya.
    """
    from .utils_contracts import regenerate_latest_loan_contract

    tenant = getattr(request, 'tenant', None)
    for loan in Loan.objects.filter(pk__in={pk for pk in loan_ids if pk is not None}):
        regenerate_latest_loan_contract(loan, tenant)


def _lock_pending_loans(loan_ids, message):
    """Adaptador del admin sobre locks.lock_pending_loans: LoanNotPending → PermissionDenied(message).

    Debe llamarse dentro de una transacción (changeform_view/delete_view ya la abren; los
    delete_queryset abren la suya). Bloquea los préstamos ordenados por pk y exige que sigan
    pendientes; ver apps/loans/locks.py (orden préstamo → contrato → token).
    """
    try:
        return lock_pending_loans(loan_ids)
    except LoanNotPending:
        raise PermissionDenied(message)


def _lock_row_loans(model, obj, loan_ids, message):
    """Adaptador del admin sobre locks.lock_row_loans para save_model/delete_model.

    Bloquea los préstamos de la fila y vuelve a leer su loan_id tras el bloqueo: si otra petición
    la movió a un préstamo no bloqueado, rechaza con PermissionDenied(message).
    """
    try:
        return lock_row_loans(model, obj, loan_ids)
    except LoanNotPending:
        raise PermissionDenied(message)


def _lock_related_loans(queryset, message):
    """Para los delete_queryset de garantías/garantes: bloquea los préstamos de la selección.

    Debe llamarse dentro de la transacción del borrado. Tras bloquear se vuelven a leer los
    préstamos de la selección: si una fila se movió a otro préstamo antes del bloqueo, se
    rechaza el borrado (el usuario reintenta). No se toma un segundo bloqueo: iría fuera del
    orden por pk y podría provocar un interbloqueo con un movimiento concurrente. Devuelve los
    ids para rehacer sus contratos.
    """
    loan_ids = set(queryset.order_by().values_list('loan_id', flat=True).distinct())
    locked = _lock_pending_loans(loan_ids, message)
    current = set(queryset.order_by().values_list('loan_id', flat=True).distinct())
    if current - locked:
        raise PermissionDenied(message)
    return list(locked)


def atomic_delete_selected(modeladmin, request, queryset):
    """La acción «Eliminar» de Django dentro de una transacción.

    delete_selected escribe los LogEntry de borrado antes de llamar a delete_queryset: si éste
    rehúsa sobre las filas bloqueadas (PermissionDenied), el historial no debe decir que se borró.
    Mismo patrón que delete_selected_tenants (apps/tenants/admin.py).
    """
    with transaction.atomic(using=router.db_for_write(modeladmin.model)):
        return delete_selected(modeladmin, request, queryset)


atomic_delete_selected.allowed_permissions = delete_selected.allowed_permissions
atomic_delete_selected.short_description = delete_selected.short_description


class AtomicDeleteSelectedMixin:
    """Sustituye la acción «Eliminar» por atomic_delete_selected (mismo nombre y permisos)."""

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            _, name, description = actions['delete_selected']
            actions['delete_selected'] = (atomic_delete_selected, name, description)
        return actions


class _ReadOnlyLoanInline(TenantUserFKMixin, TabularInline):
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


class CustomerDocumentInline(TenantUserFKMixin, TabularInline):
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
class CustomerAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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


class CollateralInline(TenantUserFKMixin, TabularInline):
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
class LoanAdmin(TenantHistoryMixin, AtomicDeleteSelectedMixin, TenantUserFKMixin, ModelAdmin):
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
    # Saldos: sólo los mueven el desembolso y los pagos, nunca el formulario.
    BALANCE_FIELDS = ('outstanding_balance', 'total_paid', 'total_interest_paid')

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    # Escribir exige, como LoanViewSet (CanManageLoans), el rol gestor además del permiso de
    # modelo: un cajero o viewer con permisos de préstamo sólo consulta.
    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_add_permission(request)
        )

    def has_change_permission(self, request, obj=None):
        """Only allow change in tenant schemas"""
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_change_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        """Sólo en tenants y, como LoanViewSet.perform_destroy, sólo pendientes o rechazados."""
        if obj is not None and obj.status not in ('pending', 'rejected'):
            return False
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_delete_permission(request, obj)
        )

    # Filas que caen con el préstamo, como en LoanViewSet.perform_destroy, aunque sus admins no
    # dejen borrarlas sueltas o el usuario no tenga su permiso de modelo.
    CASCADE_EXEMPT_MODELS = (Contract, ContractSignatureToken, Collateral, Guarantor)

    def get_deleted_objects(self, objs, request):
        """Contratos, enlaces de firma, garantías y garantes caen con el préstamo, como en la API.

        Sus admins no dejan borrarlos sueltos (ContractAdmin aplica contract_deletable,
        ContractSignatureTokenAdmin no borra nunca y garantías/garantes sólo con el préstamo
        pendiente), pero eso no debe impedir la cascada de un préstamo que sí se puede borrar. La
        exención sólo cubre la cascada de los préstamos seleccionados (objs), y el préstamo mismo
        sigue en perms_needed si no es pendiente o rechazado; delete_model/delete_queryset
        revalidan esa regla sobre la fila bloqueada.
        """
        deleted, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        for model in self.CASCADE_EXEMPT_MODELS:
            perms_needed.discard(model._meta.verbose_name)
        return deleted, model_count, perms_needed, protected

    def has_approve_permission(self, request, obj=None):
        """Aprobar, rechazar y desembolsar: paridad con la API (CanApproveLoan).

        Además de poder editar préstamos, el usuario debe ser superusuario, dueño del tenant o
        tener un rol aprobador. Las acciones declaran permissions=['approve']: Django las quita de
        get_actions para los demás y un POST manipulado al changelist no las ejecuta.
        """
        if not self.has_change_permission(request, obj):
            return False
        user = request.user
        return bool(
            user.is_superuser
            or getattr(user, 'is_tenant_owner', False)
            or getattr(user, 'role', None) in APPROVER_ROLES
        )

    @staticmethod
    def _lock_loan(pk):
        """Bloquea el préstamo (SELECT ... FOR UPDATE, sólo su fila) dentro de la transacción de la vista.

        Si otra petición lo borró entre get_object y el bloqueo, responde 404 en vez de un 500.
        """
        try:
            return Loan.objects.select_for_update(of=('self',)).get(pk=pk)
        except Loan.DoesNotExist:
            raise Http404('El préstamo ya no existe; pudo haber sido eliminado por otra operación.')

    def delete_model(self, request, obj):
        """Borrado individual: la regla de has_delete_permission se decide sobre la fila bloqueada.

        has_delete_permission se evaluó sobre la instancia leída sin bloqueo; un préstamo aprobado
        o desembolsado entretanto por la API no debe borrarse con su calendario. delete_view ya
        abre la transacción.
        """
        locked = self._lock_loan(obj.pk)
        if locked.status not in ('pending', 'rejected'):
            raise PermissionDenied('Solo se pueden eliminar préstamos pendientes o rechazados.')
        super().delete_model(request, locked)

    def delete_queryset(self, request, queryset):
        """La acción masiva «Eliminar» aplica la misma regla que has_delete_permission.

        delete_selected no abre transacción: se abre aquí y se bloquean los préstamos antes de
        evaluar la regla, para que guarda y borrado sean una sola unidad y un préstamo aprobado
        o desembolsado entretanto por la API no se borre con su calendario.
        """
        with transaction.atomic(using=router.db_for_write(self.model)):
            # of=('self',): una búsqueda del changelist une customers; sólo se bloquean los préstamos.
            statuses = list(
                queryset.select_for_update(of=('self',)).order_by().values_list('status', flat=True)
            )
            if any(status not in ('pending', 'rejected') for status in statuses):
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
        """Defensa en profundidad: un POST manipulado no cambia estado ni términos bloqueados.

        En la edición se bloquea el préstamo (SELECT ... FOR UPDATE, dentro de la transacción de
        changeform_view) antes de decidir, y las guardas se evalúan sobre la fila bloqueada. Sólo
        se escriben los campos que cambió el formulario (más la cuota si cambiaron los términos):
        estado, fechas del ciclo y saldos conservan los valores de la fila bloqueada, para que un
        cambio de notas no deshaga una aprobación o un desembolso hecho entretanto por la API.
        """
        changed = set(getattr(form, 'changed_data', ()))
        current = None
        if change:
            current = self._lock_loan(obj.pk)
        if change and 'status' in changed:
            raise PermissionDenied(
                'El estado del préstamo sólo cambia con las acciones aprobar, rechazar o desembolsar.'
            )
        if change and changed & set(self.TERM_FIELDS) and loan_terms_locked(current):
            raise PermissionDenied(
                'No se puede modificar el deudor ni los términos después de aprobado el préstamo '
                'o firmado el contrato.'
            )
        if change and 'late_fees' in changed and current.status != 'pending':
            raise PermissionDenied('La mora de un préstamo aprobado sólo cambia por sus flujos.')

        terms_changed = bool(changed & set(LOAN_TERM_FIELDS))
        if not change or terms_changed:
            self._validate_origination(request, obj, change, changed)
            # La cuota sale del mismo cálculo que la API, nunca del formulario.
            obj.payment_amount = calculate_payment_amount(obj)
        if not change:
            obj.outstanding_balance = obj.principal_amount
            super().save_model(request, obj, form, change)
            return
        obj.save(update_fields=self._changed_update_fields(changed, terms_changed))

    def _changed_update_fields(self, changed, terms_changed):
        """Columnas a escribir en la edición: las del formulario que cambiaron (con la moneda de
        los campos Money), la cuota si cambiaron los términos, y updated_at. Nunca las del ciclo
        de vida ni los saldos, que no son editables en el formulario."""
        names = set(changed)
        if terms_changed:
            names.add('payment_amount')
        # Defensa en profundidad: no depende de readonly_fields.
        forbidden = (set(self.LIFECYCLE_FIELDS) - {'payment_amount'}) | set(self.BALANCE_FIELDS)
        concrete = {f.name: f for f in Loan._meta.concrete_fields if not f.primary_key}
        fields = set()
        for name in names:
            if name in concrete and name not in forbidden:
                fields.add(name)
                if f'{name}_currency' in concrete:
                    fields.add(f'{name}_currency')
        fields.add('updated_at')
        return sorted(fields)

    def save_formset(self, request, form, formset, change):
        """Las garantías del inline se escriben con el préstamo bloqueado y aún pendiente.

        has_*_permission de CollateralInline se evaluó sobre la instancia leída sin bloqueo; aquí
        se bloquea el préstamo y se exige que siga pendiente antes de guardar las filas. El orden
        préstamo → fila → contrato se respeta: save_related rehace el contrato después.
        """
        if change and formset.model is Collateral and formset.has_changed():
            _lock_pending_loans(
                [form.instance.pk], 'Las garantías sólo se modifican mientras el préstamo está pendiente.'
            )
        super().save_formset(request, form, formset, change)

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
            _regenerate_loan_contracts(request, [obj.pk])

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

    def _for_each_locked_loan(self, request, queryset, expected_status, handler):
        """Aplica handler a cada préstamo seleccionado que siga en expected_status.

        El changelist no abre transacción: cada préstamo va en la suya y se bloquea
        (SELECT ... FOR UPDATE) antes de comprobar su estado, para que un préstamo aprobado,
        rechazado o editado por la API entre la selección y el guardado no se pise con la
        instancia vieja. Una transacción por préstamo: el error de uno no deshace los demás.
        Un ValidationError de handler deshace ese préstamo y se informa.
        Devuelve (elegibles tras bloquear, procesados).
        """
        eligible = done = 0
        pks = list(dict.fromkeys(queryset.order_by().values_list('pk', flat=True)))
        for pk in pks:
            locked = None
            try:
                with transaction.atomic(using=router.db_for_write(Loan)):
                    try:
                        # of=('self',): sólo se bloquea la fila del préstamo, como en delete_queryset.
                        locked = Loan.objects.select_for_update(of=('self',)).get(pk=pk)
                    except Loan.DoesNotExist:
                        continue  # borrado entretanto: no elegible
                    if locked.status != expected_status:
                        continue  # cambió de estado entretanto: no elegible
                    eligible += 1
                    handler(locked)
            except ValidationError as exc:
                self._report_policy_violation(request, locked, exc)
                continue
            done += 1
        return eligible, done

    @admin.action(description='Aprobar préstamos seleccionados', permissions=['approve'])
    def approve_loans(self, request, queryset):
        """Aprueba los pendientes que cumplen la política; informa los que no."""
        from django.utils import timezone
        from django.contrib import messages

        def approve(loan):
            validate_approval(loan, request)
            loan.status = 'approved'
            loan.approval_date = timezone.localdate()
            loan.approved_by = request.user
            loan.save()

        eligible, approved = self._for_each_locked_loan(request, queryset, 'pending', approve)

        if eligible == 0:
            self.message_user(request, 'No hay préstamos pendientes para aprobar', messages.WARNING)
            return
        if approved:
            self.message_user(
                request,
                f'{approved} préstamo(s) aprobado(s) exitosamente',
                messages.SUCCESS
            )

    @admin.action(description='Rechazar préstamos seleccionados', permissions=['approve'])
    def reject_loans(self, request, queryset):
        """Rechaza los pendientes (estado comprobado sobre la fila bloqueada)."""
        from django.utils import timezone
        from django.contrib import messages

        def reject(loan):
            loan.status = 'rejected'
            loan.rejection_date = timezone.localdate()
            loan.rejected_by = request.user
            loan.save()

        eligible, rejected = self._for_each_locked_loan(request, queryset, 'pending', reject)

        if eligible == 0:
            self.message_user(request, 'No hay préstamos pendientes para rechazar', messages.WARNING)
            return
        if rejected:
            self.message_user(
                request,
                f'{rejected} préstamo(s) rechazado(s) exitosamente',
                messages.SUCCESS
            )

    @admin.action(description='Desembolsar préstamos aprobados', permissions=['approve'])
    def disburse_loans(self, request, queryset):
        """Desembolsa los aprobados que cumplen las precondiciones; informa los que no."""
        from django.contrib import messages

        def disburse(loan):
            # Mismas precondiciones y efectos que la API (apps.loans.disbursement); sin caja:
            # el admin no tiene sesión de caja, así que no registra egreso.
            contract = check_disbursable(loan, request.user, request)
            apply_disbursement(loan, contract)

        eligible, disbursed = self._for_each_locked_loan(request, queryset, 'approved', disburse)

        if eligible == 0:
            self.message_user(request, 'No hay préstamos aprobados para desembolsar', messages.WARNING)
            return
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
class LoanScheduleAdmin(TenantHistoryMixin, ModelAdmin):
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
class LoanPaymentAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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
class CollateralAdmin(TenantHistoryMixin, AtomicDeleteSelectedMixin, TenantUserFKMixin, ModelAdmin):
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
    # Escribir exige, como CollateralViewSet (CanManageLoans), el rol gestor además del permiso
    # de modelo: un cajero o viewer con permisos de garantías sólo consulta.
    def has_add_permission(self, request):
        """Only allow add in tenant schemas"""
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_add_permission(request)
        )

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_change_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_delete_permission(request, obj)
        )

    def delete_queryset(self, request, queryset):
        """La acción masiva «Eliminar» aplica la misma regla que has_delete_permission.

        delete_selected no abre transacción: se abre aquí para que un error al rehacer el
        contrato deshaga también el borrado.
        """
        with transaction.atomic(using=router.db_for_write(self.model)):
            loan_ids = _lock_related_loans(
                queryset, 'Las garantías sólo se eliminan mientras el préstamo está pendiente.'
            )
            super().delete_queryset(request, queryset)
            # El contrato por firmar deja de nombrar las garantías borradas.
            _regenerate_loan_contracts(request, loan_ids)

    def delete_model(self, request, obj):
        # delete_view ya es atómica: el préstamo queda bloqueado hasta el borrado.
        loan_id = obj.loan_id
        _lock_row_loans(
            Collateral, obj, [loan_id],
            'Las garantías sólo se eliminan mientras el préstamo está pendiente.',
        )
        super().delete_model(request, obj)
        _regenerate_loan_contracts(request, [loan_id])

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'loan':
            kwargs['queryset'] = Loan.objects.filter(status='pending')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        loans = [obj.loan_id]
        if change:
            loans.append(Collateral.objects.filter(pk=obj.pk).values_list('loan_id', flat=True).first())
        # changeform_view ya es atómica: los préstamos (nuevo y anterior) quedan bloqueados
        # hasta el guardado y la regeneración del contrato.
        _lock_row_loans(
            Collateral, obj, loans,
            'Las garantías sólo se modifican mientras el préstamo está pendiente.',
        )
        super().save_model(request, obj, form, change)
        # Igual que CollateralSerializer: el contrato por firmar refleja la garantía; si cambió de
        # préstamo, el anterior también se rehace porque la pierde.
        _regenerate_loan_contracts(request, loans)

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
class CustomerDocumentAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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
class CollectionReminderAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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
class CollectionContactAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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
class ContractTemplateAdmin(TenantHistoryMixin, TenantUserFKMixin, ModelAdmin):
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

def _lock_contract(obj):
    """locks.lock_contract con 404 si otra petición borró el contrato antes del bloqueo."""
    try:
        return lock_contract(obj)
    except Contract.DoesNotExist:
        raise Http404('El contrato ya no existe; pudo haber sido eliminado por otra operación.')


class ContractAdminForm(forms.ModelForm):
    """Alta: misma regla que ContractCreateSerializer.validate_loan (loan_has_open_contract).

    En edición el préstamo es de sólo lectura y no llega al formulario.
    """

    def clean_loan(self):
        loan = self.cleaned_data.get('loan')
        if loan is not None and self.instance._state.adding and loan_has_open_contract(loan):
            raise forms.ValidationError(OPEN_CONTRACT_MESSAGE)
        return loan


@admin.register(Contract)
class ContractAdmin(TenantHistoryMixin, AtomicDeleteSelectedMixin, TenantUserFKMixin, ModelAdmin):
    """Admin interface for Contract model"""

    list_fullwidth = True
    warn_unsaved_form = True
    form = ContractAdminForm

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

    # Mismas reglas que ContractViewSet: en el alta se eligen préstamo, plantilla y campos libres
    # (el texto sale de la plantilla); estado, PDF y firmas sólo cambian por las acciones del
    # contrato. En edición sólo quedan los campos libres (CONTRACT_EDITABLE_FIELDS).
    ADD_LOCKED_FIELDS = (
        'status', 'content', 'pdf_file', 'generated_by',
        'customer_signed_at', 'customer_signature', 'officer_signed_at', 'officer_signature',
        'witness_signed_at', 'witness_signature',
    )
    TERMINAL_MESSAGE = 'Este contrato está cancelado o completado; genere uno nuevo.'
    DELETE_MESSAGE = 'Solo se eliminan contratos sin firmas de préstamos no desembolsados; use cancelar.'

    def has_module_permission(self, request):
        """Only show in tenant schemas"""
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        """Only allow view in tenant schemas"""
        return is_tenant_schema() and super().has_view_permission(request, obj)

    # Escribir exige, además del permiso de modelo, el rol de CanManageLoans (superusuario, dueño
    # del tenant o rol gestor): un viewer o cajero con permisos de contrato sólo puede mirar.
    def has_add_permission(self, request):
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_add_permission(request)
        )

    def has_change_permission(self, request, obj=None):
        """Un contrato cancelado o completado no se edita; la decisión final, en save_model."""
        if obj is not None and obj.status in TERMINAL_CONTRACT_STATUSES:
            return False
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_change_permission(request, obj)
        )

    def has_delete_permission(self, request, obj=None):
        """Como ContractViewSet.perform_destroy (contract_deletable); se revalida bloqueando."""
        if obj is not None and not contract_deletable(obj):
            return False
        return (
            is_tenant_schema() and can_manage_loans(request.user)
            and super().has_delete_permission(request, obj)
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
        """Alta: todo menos préstamo, plantilla y campos libres. Edición: todo menos los campos libres."""
        if obj is None:
            return list(self.readonly_fields) + list(self.ADD_LOCKED_FIELDS)
        return [
            field for field in flatten_fieldsets(self.fieldsets)
            if field not in CONTRACT_EDITABLE_FIELDS
        ]

    def save_model(self, request, obj, form, change):
        """Alta: generated_by y texto desde la plantilla. Edición: sólo campos libres, bloqueando."""
        if change:
            # Como ContractViewSet.perform_update: se decide y se escribe sobre la fila bloqueada
            # (un cancel confirmado entretanto queda a la vista y no se pisa con la copia leída
            # antes) y sólo se guardan los campos libres cambiados.
            with transaction.atomic():
                contract = _lock_contract(obj)
                if contract.status in TERMINAL_CONTRACT_STATUSES:
                    raise PermissionDenied(self.TERMINAL_MESSAGE)
                changed = [field for field in form.changed_data if field in CONTRACT_EDITABLE_FIELDS]
                for field in changed:
                    setattr(contract, field, getattr(obj, field))
                contract.save(update_fields=changed + ['updated_at'])
            return

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

    def delete_model(self, request, obj):
        """Como ContractViewSet.perform_destroy: se decide sobre el contrato bloqueado."""
        with transaction.atomic():
            contract = _lock_contract(obj)
            if not contract_deletable(contract):
                raise PermissionDenied(self.DELETE_MESSAGE)
            super().delete_model(request, contract)

    def delete_queryset(self, request, queryset):
        """Acción masiva «Eliminar»: todo o nada, con el mismo predicado que la API.

        La acción no abre transacción, así que se abre aquí. Se bloquean los contratos en orden de
        pk (orden determinista frente a otro borrado masivo) y se decide sobre las filas bloqueadas:
        si alguno ya no se puede borrar (p. ej. se firmó entretanto), no se borra ninguno.
        """
        with transaction.atomic():
            pks = list(queryset.order_by().values_list('pk', flat=True))
            locked = list(
                Contract.objects.select_for_update(of=('self',)).filter(pk__in=pks).order_by('pk')
            )
            if any(not contract_deletable(contract) for contract in locked):
                raise PermissionDenied(self.DELETE_MESSAGE)
            super().delete_queryset(request, Contract.objects.filter(pk__in=[c.pk for c in locked]))

    def get_deleted_objects(self, objs, request):
        """Los enlaces de firma caen con su contrato, como en la API.

        ContractSignatureTokenAdmin no deja borrar enlaces sueltos (revocar es cancelar el contrato),
        así que no se exige ese permiso para la cascada de un contrato que sí se puede borrar.
        """
        deleted, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        perms_needed.discard(ContractSignatureToken._meta.verbose_name)
        return deleted, model_count, perms_needed, protected

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('loan', 'loan__customer', 'template', 'generated_by')


@admin.register(ContractSignatureToken)
class ContractSignatureTokenAdmin(TenantHistoryMixin, ModelAdmin):
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
    # El token es una credencial al portador (firma por public_contract_sign): no se muestra ni
    # se busca. Sólo se ve si el enlace sigue valiendo.
    search_fields = ['email', 'contract__contract_number']
    readonly_fields = [
        'id', 'contract', 'email', 'can_sign_as_customer', 'can_sign_as_officer',
        'expires_at', 'is_valid_status', 'sent_at', 'used_at', 'created_at',
    ]

    fieldsets = [
        ('Contract Information', {
            'fields': ['contract', 'email']
        }),
        ('Permissions', {
            'fields': ['can_sign_as_customer', 'can_sign_as_officer']
        }),
        ('Token Details', {
            'fields': ['expires_at', 'is_valid_status']
        }),
        ('Tracking', {
            'fields': ['sent_at', 'used_at', 'created_at']
        }),
    ]

    # Sólo lectura para todos, superusuario incluido: los enlaces sólo nacen de
    # ContractViewSet.send_for_signature (alcance y vencimiento los fija el servidor) y se revocan
    # cancelando el contrato. Borrar uno suelto tampoco se permite; caen con su contrato
    # (ContractAdmin.get_deleted_objects).
    def has_module_permission(self, request):
        return is_tenant_schema()

    def has_view_permission(self, request, obj=None):
        return is_tenant_schema() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def lookup_allowed(self, lookup, value, request=None):
        """Ningún filtro de la URL sobre el token (?token__startswith=, __gt, __regex...).

        Django permite siempre los lookups sobre campos propios; con el número de filas un staff
        con sólo view reconstruiría el token carácter a carácter y firmaría por el enlace público.
        Los caminos desde otros modelos (signature_tokens__token) ya los rechaza Django por no
        estar en list_filter.
        """
        if lookup.split(LOOKUP_SEP, 1)[0] == 'token':
            return False
        return super().lookup_allowed(lookup, value, request)

    def is_valid_status(self, obj):
        """Display whether token is valid"""
        if obj.is_valid:
            color, label = 'green', '✓ Valid'
        elif obj.is_used:
            color, label = 'gray', 'Used'
        else:
            color, label = 'red', 'Expired'
        return format_html('<span style="color: {};">{}</span>', color, label)
    is_valid_status.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('contract', 'contract__loan')


# ============================================================
# Customer Contacts
# ============================================================

@admin.register(CustomerPhone)
class CustomerPhoneAdmin(TenantHistoryMixin, ModelAdmin):
    list_display = ['phone', 'customer', 'phone_type', 'is_primary', 'is_whatsapp']
    list_filter = ['phone_type', 'is_primary', 'is_whatsapp']
    search_fields = ['phone', 'customer__first_name', 'customer__last_name']
    raw_id_fields = ['customer']


@admin.register(CustomerEmail)
class CustomerEmailAdmin(TenantHistoryMixin, ModelAdmin):
    list_display = ['email', 'customer', 'email_type', 'is_primary']
    list_filter = ['email_type', 'is_primary']
    search_fields = ['email', 'customer__first_name', 'customer__last_name']
    raw_id_fields = ['customer']


# ============================================================
# Guarantors
# ============================================================

@admin.register(Guarantor)
class GuarantorAdmin(TenantHistoryMixin, AtomicDeleteSelectedMixin, TenantUserFKMixin, ModelAdmin):
    list_display = ['get_full_name', 'id_number', 'loan', 'relationship', 'status', 'phone']
    list_filter = ['status', 'relationship', 'id_type']
    search_fields = ['first_name', 'last_name', 'id_number', 'phone', 'email']
    raw_id_fields = ['loan']
    readonly_fields = ['created_at', 'updated_at']

    # Igual que las garantías: los garantes sólo se agregan, editan, mueven o borran mientras el
    # préstamo está pendiente (lo que el aprobador revisó). has_*_permission es el filtro de la
    # interfaz; la decisión al escribir se toma sobre el préstamo bloqueado (_lock_pending_loans).
    # Escribir exige además, como GuarantorViewSet (CanManageLoans), el rol gestor.
    def has_add_permission(self, request):
        return can_manage_loans(request.user) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return can_manage_loans(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.loan.status != 'pending':
            return False
        return can_manage_loans(request.user) and super().has_delete_permission(request, obj)

    # Igual que GuarantorSerializer: el contrato por firmar nombra al primer garante, así que se
    # rehace al agregar, editar, mover o borrar garantes (uno firmado no se reescribe).
    def save_model(self, request, obj, form, change):
        loans = [obj.loan_id]
        if change:
            loans.append(Guarantor.objects.filter(pk=obj.pk).values_list('loan_id', flat=True).first())
        # changeform_view ya es atómica: los préstamos (nuevo y anterior) quedan bloqueados
        # hasta el guardado y la regeneración del contrato.
        _lock_row_loans(
            Guarantor, obj, loans,
            'Los garantes sólo se modifican mientras el préstamo está pendiente.',
        )
        super().save_model(request, obj, form, change)
        _regenerate_loan_contracts(request, loans)

    def delete_model(self, request, obj):
        # delete_view ya es atómica: el préstamo queda bloqueado hasta el borrado.
        loan_id = obj.loan_id
        _lock_row_loans(
            Guarantor, obj, [loan_id],
            'Los garantes sólo se eliminan mientras el préstamo está pendiente.',
        )
        super().delete_model(request, obj)
        _regenerate_loan_contracts(request, [loan_id])

    def delete_queryset(self, request, queryset):
        # delete_selected no abre transacción: un error al rehacer el contrato deshace el borrado,
        # y los préstamos quedan bloqueados hasta el final.
        with transaction.atomic(using=router.db_for_write(self.model)):
            loan_ids = _lock_related_loans(
                queryset, 'Los garantes sólo se eliminan mientras el préstamo está pendiente.'
            )
            super().delete_queryset(request, queryset)
            _regenerate_loan_contracts(request, loan_ids)

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
