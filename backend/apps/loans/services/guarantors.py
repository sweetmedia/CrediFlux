"""Consultas sobre garantes."""
from apps.loans.models_guarantors import Guarantor
from apps.loans.utils_ids import normalize_id_number


def guarantor_of(id_number, exclude_customer_id=None):
    """Préstamos de otros clientes donde esta cédula figura como garante activo.

    Compara por `id_number_digits` (indexado), sólo dígitos. Excluye los préstamos
    del propio cliente.
    """
    digits = normalize_id_number(id_number)[:20]
    if not digits:
        return []
    qs = Guarantor.objects.filter(id_number_digits=digits, status='active').select_related('loan__customer')
    if exclude_customer_id:
        qs = qs.exclude(loan__customer_id=exclude_customer_id)
    return [
        {
            'loan_id': str(g.loan_id),
            'loan_number': g.loan.loan_number,
            'customer_id': str(g.loan.customer_id),
            'customer_name': g.loan.customer.get_full_name(),
            'status': g.loan.status,
        }
        for g in qs.order_by('loan__loan_number')
    ]
