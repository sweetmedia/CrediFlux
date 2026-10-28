"""Consultas sobre garantes."""
from apps.loans.models_guarantors import Guarantor
from apps.loans.utils_ids import normalize_id_number

# El garante sigue respondiendo mientras su garantía está vigente o en mora (no «liberado»).
ESTADOS_GARANTE_VIGENTE = ('active', 'defaulted')
# Préstamos cerrados: pagado o rechazado. Uno castigado (`written_off`) sigue contando: la
# deuda existe y el garante puede responder por ella.
ESTADOS_PRESTAMO_CERRADO = ('paid', 'rejected')


def guarantor_of(id_number, exclude_customer_id=None, con_prestamo=True):
    """Préstamos de otros clientes donde esta cédula figura como garante vigente.

    Compara por `id_number_digits` (indexado), sólo dígitos. Cuenta las garantías activas o en
    mora de préstamos no cerrados y excluye los préstamos del propio cliente. Con
    `con_prestamo=False` (quien no tiene loans.view) cada entrada sólo trae el cliente
    garantizado, sin id, número ni estado del préstamo.
    """
    digits = normalize_id_number(id_number)[:20]
    if not digits:
        return []
    qs = (
        Guarantor.objects
        .filter(id_number_digits=digits, status__in=ESTADOS_GARANTE_VIGENTE)
        .exclude(loan__status__in=ESTADOS_PRESTAMO_CERRADO)
        .select_related('loan__customer')
    )
    if exclude_customer_id:
        qs = qs.exclude(loan__customer_id=exclude_customer_id)
    resultado = []
    for g in qs.order_by('loan__loan_number'):
        entrada = {
            'customer_id': str(g.loan.customer_id),
            'customer_name': g.loan.customer.get_full_name(),
        }
        if con_prestamo:
            entrada.update({
                'loan_id': str(g.loan_id),
                'loan_number': g.loan.loan_number,
                'status': g.loan.status,
            })
        resultado.append(entrada)
    return resultado
