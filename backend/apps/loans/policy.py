"""
Política de originación del tenant aplicada a los préstamos.

La configuración vive en `tenants.Tenant` (schema public). Estas funciones la
leen del tenant activo (`connection.tenant`, con `request.user.tenant` como
respaldo) y lanzan `serializers.ValidationError` con las reglas incumplidas.
"""
from decimal import Decimal

from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework import serializers

# Estados que cuentan como préstamo "vivo" para max_active_loans_per_customer.
OPEN_LOAN_STATUSES = ('pending', 'approved', 'active')
ID_DOCUMENT_TYPES = ('id_card', 'passport', 'drivers_license')


def _amount(value):
    """Money / Decimal / número / None → Decimal | None."""
    if value is None:
        return None
    return Decimal(str(getattr(value, 'amount', value)))


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
        low, high = tenant.min_interest_rate, tenant.max_interest_rate
        if (low is not None and rate < low) or (high is not None and rate > high):
            errors['interest_rate'] = (
                f'La tasa de interés debe estar entre {low} y {high} según la política de la organización.'
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
