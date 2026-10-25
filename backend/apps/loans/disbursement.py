"""
Desembolso de préstamos: precondiciones y efectos compartidos por la API y el admin.

`check_disbursable` es la única puerta: préstamo aprobado, política de aprobación y de
desembolso vigentes y un contrato vigente (el último no archivado) en un estado
desembolsable y firmado por el cliente. `apply_disbursement` hace el cambio de estado
y genera el cronograma; quien llama lo envuelve en una transacción.
"""
from django.utils import timezone
from rest_framework import serializers

from .policy import validate_approval, validate_disbursement

# Estados de contrato con los que se puede desembolsar (lista positiva).
DISBURSABLE_CONTRACT_STATUSES = ('pending_signature', 'signed', 'active')


def check_disbursable(loan, user, request=None):
    """Devuelve el contrato vigente si el préstamo se puede desembolsar; si no, ValidationError."""
    if loan.status != 'approved':
        raise serializers.ValidationError({'error': 'Only approved loans can be disbursed'})

    # La política de aprobación se vuelve a aplicar: el préstamo que sale es el de hoy.
    validate_approval(loan, request)
    validate_disbursement(loan, user, request)

    contract = loan.contracts.filter(is_archived=False).order_by('-generated_at').first()
    if not contract:
        raise serializers.ValidationError(
            {'error': 'No se puede desembolsar este préstamo porque no tiene contrato generado.'}
        )

    if contract.status not in DISBURSABLE_CONTRACT_STATUSES:
        # Lista positiva: un contrato cancelado, cumplido o en borrador no es el vigente
        # de un desembolso, aunque alguien haya conseguido revivirlo.
        raise serializers.ValidationError({
            'error': 'El contrato vigente no está en un estado válido para desembolsar '
                     '(cancelado, completado o borrador); genere y firme uno nuevo.',
            'contract_id': str(contract.id),
            'contract_status': contract.status,
        })

    if not contract.customer_signed_at:
        raise serializers.ValidationError({
            'error': 'No se puede desembolsar hasta que el contrato esté firmado por el cliente.',
            'contract_id': str(contract.id),
            'contract_status': contract.status,
        })

    return contract


def apply_disbursement(loan, contract):
    """Activa el préstamo y su contrato y genera el cronograma (llamar dentro de una transacción)."""
    loan.status = 'active'
    loan.disbursement_date = timezone.localdate()
    loan.outstanding_balance = loan.principal_amount
    loan.save()

    if contract.status != 'active':
        contract.status = 'active'
        contract.save(update_fields=['status', 'updated_at'])

    generate_payment_schedule(loan)


def generate_payment_schedule(loan):
    """
    Genera el cronograma con el mismo cálculo que la calculadora
    (`apps.loans.amortization`): tasa MENSUAL, período = mes / divisor.
    """
    from dateutil.relativedelta import relativedelta
    from moneyed import Money

    from .amortization import build_installments, number_of_payments
    from .models import LoanSchedule

    frequency_map = {
        'daily': {'days': 1},
        'weekly': {'weeks': 1},
        'biweekly': {'weeks': 2},
        'monthly': {'months': 1},
        'quarterly': {'months': 3},
    }
    period_delta = frequency_map.get(loan.payment_frequency, {'months': 1})
    currency = loan.principal_amount.currency

    num_payments = number_of_payments(loan.term_months, loan.payment_frequency)
    rows, _, _ = build_installments(
        loan.principal_amount.amount,
        loan.interest_rate,
        num_payments,
        loan.payment_frequency,
        getattr(loan, 'interest_type', 'fixed'),
    )

    current_date = loan.first_payment_date or loan.disbursement_date
    schedules = []
    for i, row in enumerate(rows, start=1):
        schedules.append(LoanSchedule.objects.create(
            loan=loan,
            installment_number=i,
            due_date=current_date,
            total_amount=Money(row['payment'], currency),
            principal_amount=Money(row['principal'], currency),
            interest_amount=Money(row['interest'], currency),
        ))
        current_date = current_date + relativedelta(**period_delta)

    # Vencimiento = fecha de la última cuota (antes quedaba un período después)
    if schedules:
        loan.maturity_date = schedules[-1].due_date
        # outstanding_balance = total del cronograma (capital + interés)
        loan.outstanding_balance = Money(sum(row['payment'] for row in rows), currency)
        loan.payment_amount = Money(rows[0]['payment'], currency)

    loan.save()
