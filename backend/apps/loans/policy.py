"""
Política de originación del tenant aplicada a los préstamos.

La configuración vive en `tenants.Tenant` (schema public). Estas funciones la
leen del tenant activo (`connection.tenant`, con `request.user.tenant` como
respaldo) y lanzan `serializers.ValidationError` con las reglas incumplidas.
"""
from decimal import Decimal

from django.db import connection
from django.db.models import Q
from django_tenants.utils import get_public_schema_name
from rest_framework import serializers

from .amortization import PAYMENTS_PER_MONTH, normalize_method

# Estados que cuentan como préstamo "vivo" para max_active_loans_per_customer.
OPEN_LOAN_STATUSES = ('pending', 'approved', 'active')
ID_DOCUMENT_TYPES = ('id_card', 'passport', 'drivers_license')

# Estado y aprobación: sólo cambian por las acciones approve/reject/disburse (API y admin).
LOAN_LIFECYCLE_FIELDS = (
    'status', 'approval_date', 'rejection_date', 'disbursement_date',
    'maturity_date', 'approved_by', 'rejected_by', 'approval_notes',
)

# Deudor y términos económicos: fijos tras aprobar o firmar (API y admin, ver loan_terms_locked).
LOAN_TERM_FIELDS = (
    'customer', 'loan_type', 'principal_amount', 'interest_rate', 'interest_type',
    'term_months', 'payment_frequency', 'first_payment_date',
)

# Términos + documento del contrato: congelados con loan_terms_locked (API y admin); sólo
# LOAN_TERM_FIELDS rehacen la cuota y el contrato por firmar.
LOAN_LOCKED_FIELDS = LOAN_TERM_FIELDS + ('contract_document',)


def loan_terms_locked(loan):
    """¿Quedan fijos deudor y términos? Sí si el préstamo ya no está pendiente o tiene firma.

    Un contrato firmado bloquea mientras no esté cancelado, archivado o no: archivar no
    desbloquea. Uno cancelado ya no bloquea, y tampoco sirve para desembolsar ni puede
    desarchivarse (LoanViewSet.disburse, ContractViewSet.unarchive): cambiar términos
    tras una firma exige cancelar y firmar un contrato nuevo. Única regla para el
    serializer (LoanSerializer._ensure_terms_editable) y el admin (LoanAdmin).
    """
    if loan.status != 'pending':
        return True
    if loan._state.adding:
        return False
    return loan.contracts.exclude(status='cancelled').filter(
        Q(customer_signed_at__isnull=False) | Q(officer_signed_at__isnull=False)
    ).exists()


# Estados finales del contrato: ninguna acción vuelve a reescribir su estado ni sus campos libres.
TERMINAL_CONTRACT_STATUSES = ('cancelled', 'completed')

# Estados del préstamo anteriores al desembolso: sólo con éstos se puede cancelar o borrar su
# contrato. (`disbursement_date` también marca el desembolso, pero el estado es la condición principal.)
LOAN_STATUSES_BEFORE_DISBURSEMENT = ('pending', 'approved', 'rejected')

# Campos libres del contrato: lo único que se edita a mano (API: ContractSerializer; admin:
# ContractAdmin). Préstamo, plantilla, texto, PDF, estado y firmas sólo cambian por las acciones.
CONTRACT_EDITABLE_FIELDS = ('special_terms', 'notes', 'witness_name', 'witness_id')


# Contratos vigentes o en curso de firma: mientras el préstamo tenga uno no se genera otro.
OPEN_CONTRACT_STATUSES = ('active', 'signed', 'pending_signature')
OPEN_CONTRACT_MESSAGE = 'Este préstamo ya tiene un contrato activo'


def loan_has_open_contract(loan):
    """¿Tiene el préstamo un contrato vigente o por firmar?

    Invariante: como mucho un contrato abierto por préstamo. Única regla para el alta (API y admin)
    y para las acciones que pasan un contrato de no abierto a abierto (send_for_signature,
    sign_customer, sign_officer de un borrador). Esas acciones sólo la consultan mientras el
    contrato aún no está abierto, así que el propio contrato nunca se cuenta y no hace falta
    excluirlo. La decisión vale sólo sobre el préstamo bloqueado (locks.lock_loan);
    ContractCreateSerializer.validate_loan y ContractAdminForm.clean_loan la usan sin bloqueo sólo
    para dar el error en el formulario.
    """
    return loan.contracts.filter(status__in=OPEN_CONTRACT_STATUSES).exists()


def contract_deletable(contract):
    """¿Se puede borrar el contrato? Borrar no sustituye a cancelar.

    Sólo un contrato sin firmas, en borrador o por firmar, de un préstamo no desembolsado.
    Única regla para ContractViewSet.perform_destroy y ContractAdmin (delete_model y
    delete_queryset); evaluarla sobre la fila bloqueada (locks.lock_contract).
    """
    return (
        not contract.customer_signed_at
        and not contract.officer_signed_at
        and contract.status in ('draft', 'pending_signature')
        and contract.loan.status in LOAN_STATUSES_BEFORE_DISBURSEMENT
    )


def _amount(value):
    """Money / Decimal / número / None → Decimal | None."""
    if value is None:
        return None
    return Decimal(str(getattr(value, 'amount', value)))


def annual_nominal_rate(rate, interest_type=None, frequency=None):
    """Tasa anual nominal (%) de `Loan.interest_rate` según el método de amortización.

    Para casi todos los métodos la tasa es MENSUAL (anual = mensual × 12). Con
    `variable_rd` es una tasa directa POR CUOTA (ver `amortization.build_installments`):
    anual = tasa × cuotas al año, con las mismas cuotas por mes que el calendario.
    """
    rate = Decimal(str(rate))
    if normalize_method(interest_type) == 'variable_rd':
        if frequency == 'quarterly':
            return (rate * 4).quantize(Decimal('0.01'))
        return (rate * PAYMENTS_PER_MONTH.get(frequency, Decimal('1')) * 12).quantize(Decimal('0.01'))
    return (rate * 12).quantize(Decimal('0.01'))


def get_policy_tenant(request=None):
    tenant = getattr(connection, 'tenant', None)
    if tenant is not None and getattr(tenant, 'schema_name', None) not in (None, get_public_schema_name()) \
            and getattr(tenant, 'pk', None) is not None:
        return tenant
    user = getattr(request, 'user', None)
    return getattr(user, 'tenant', None) if user is not None else None


def _required_by_threshold(flag, threshold, principal):
    """Obligatorio si la bandera está activa y el monto alcanza el umbral (sin umbral: siempre)."""
    if not flag:
        return False
    limit = _amount(threshold)
    return limit is None or principal is None or principal >= limit


def validate_origination(attrs, customer, request=None, instance=None):
    """Monto, tasa y plazo dentro del rango del tenant y tope de préstamos vivos por cliente."""
    tenant = get_policy_tenant(request)
    if tenant is None:
        return

    errors = {}
    principal = _amount(attrs.get('principal_amount'))
    if principal is not None:
        low, high = _amount(tenant.min_loan_amount), _amount(tenant.max_loan_amount)
        if (low is not None and principal < low) or (high is not None and principal > high):
            errors['principal_amount'] = (
                f'El monto debe estar entre {low} y {high} según la política de la organización.'
            )

    rate = attrs.get('interest_rate')
    if rate is not None:
        # Los límites del tenant son ANUALES; la tasa del préstamo es mensual o, con
        # variable_rd, por cuota: se anualiza según el método y la frecuencia.
        interest_type, frequency = attrs.get('interest_type'), attrs.get('payment_frequency')
        annual = annual_nominal_rate(rate, interest_type, frequency)
        per = 'por cuota' if normalize_method(interest_type) == 'variable_rd' else 'mensual'
        low, high = tenant.min_interest_rate, tenant.max_interest_rate
        if high is not None and annual > high:
            errors['interest_rate'] = (
                f'La tasa {rate:.2f}% {per} ({annual:.2f}% anual) excede el máximo anual de {high:.2f}%.'
            )
        elif low is not None and annual < low:
            errors['interest_rate'] = (
                f'La tasa {rate:.2f}% {per} ({annual:.2f}% anual) es menor al mínimo anual de {low:.2f}%.'
            )

    term = attrs.get('term_months')
    if term is not None:
        low, high = tenant.min_loan_term_months, tenant.max_loan_term_months
        if (low is not None and term < low) or (high is not None and term > high):
            errors['term_months'] = (
                f'El plazo debe estar entre {low} y {high} meses según la política de la organización.'
            )

    limit = tenant.max_active_loans_per_customer
    if customer is not None and limit is not None:
        open_loans = customer.loans.filter(status__in=OPEN_LOAN_STATUSES)
        if instance is not None and instance.pk:
            open_loans = open_loans.exclude(pk=instance.pk)
        if open_loans.count() >= limit:
            errors['customer'] = (
                f'El cliente ya tiene {limit} préstamo(s) vigente(s), el máximo permitido por la organización.'
            )

    if errors:
        raise serializers.ValidationError(errors)


def validate_approval(loan, request=None):
    """Documento de identidad, garante, colateral y score crediticio exigidos por el tenant."""
    tenant = get_policy_tenant(request)
    if tenant is None:
        return

    errors = {}
    customer = loan.customer
    principal = _amount(loan.principal_amount)

    if tenant.require_id_document:
        has_id = bool(customer.id_document) or customer.documents.filter(
            document_type__in=ID_DOCUMENT_TYPES
        ).exclude(verification_status__in=('rejected', 'expired')).exists()
        if not has_id:
            errors['id_document'] = 'El cliente debe tener un documento de identidad cargado.'

    if _required_by_threshold(tenant.require_guarantor, tenant.guarantor_required_above, principal):
        if not loan.guarantors.filter(status='active').exists():
            errors['guarantor'] = 'La política de la organización exige un garante para este préstamo.'

    if _required_by_threshold(
        tenant.require_collateral_default, tenant.collateral_required_above, principal
    ):
        if not loan.collaterals.filter(status='active').exists():
            errors['collateral'] = 'La política de la organización exige una garantía (colateral) para este préstamo.'

    if tenant.require_credit_score:
        score = customer.credit_score
        if score is None:
            errors['credit_score'] = 'La política de la organización exige el score crediticio del cliente.'
        elif tenant.minimum_credit_score is not None and score < tenant.minimum_credit_score:
            errors['credit_score'] = (
                f'El score crediticio del cliente ({score}) es menor al mínimo requerido '
                f'({tenant.minimum_credit_score}).'
            )

    if errors:
        raise serializers.ValidationError(errors)


def validate_disbursement(loan, user, request=None):
    """Con require_disbursement_approval, quien aprobó no desembolsa (salvo admin/dueño)."""
    tenant = get_policy_tenant(request)
    if tenant is None or not tenant.require_disbursement_approval:
        return

    privileged = (
        getattr(user, 'is_superuser', False)
        or getattr(user, 'is_tenant_owner', False)
        or getattr(user, 'role', None) == 'admin'
    )
    if not privileged and loan.approved_by_id is not None and loan.approved_by_id == user.pk:
        raise serializers.ValidationError({
            'approved_by': 'Quien aprobó el préstamo no puede desembolsarlo; '
                           'se requiere otro usuario autorizado.'
        })
