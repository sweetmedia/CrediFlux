"""
Conexión de préstamos con la caja.

Los pagos y desembolsos EN EFECTIVO generan su `CashMovement` en la sesión de
caja abierta. Las funciones de este módulo no abren transacciones propias: se
llaman desde dentro del `transaction.atomic()` del pago/desembolso para que,
si algo falla, no quede un pago sin su movimiento (ni al revés).

Qué sesión se usa (`find_open_session`):
1. la sesión abierta del propio usuario (el cajero responde por su caja);
2. si no tiene, la única sesión abierta del tenant (financiera de una caja);
3. si no hay ninguna o hay varias ajenas, ninguna (None).
"""
from decimal import Decimal

from moneyed import Money

from .models import CashMovement, CashSession

CASH = 'cash'


def find_open_session(user):
    open_sessions = CashSession.objects.select_for_update().filter(status='open')
    own = open_sessions.filter(cashier=user).order_by('-opened_at').first()
    if own:
        return own
    others = list(open_sessions[:2])
    return others[0] if len(others) == 1 else None


def _customer_name(loan):
    customer = getattr(loan, 'customer', None)
    return customer.get_full_name() if customer else ''


def record_payment_inflow(payment, user):
    """
    Entrada de caja por un pago completado en efectivo. Idempotente: si el pago
    ya tiene movimientos, no crea otros. Devuelve la lista de movimientos creados.
    """
    if payment.payment_method != CASH or payment.status != 'completed':
        return []
    if payment.cash_movements.exists():
        return []
    session = find_open_session(user)
    if session is None:
        return []

    currency = payment.amount.currency
    late_fee = payment.late_fee_paid.amount if payment.late_fee_paid else Decimal('0')
    parts = [
        ('late_fee', late_fee, f'Mora cobrada — {payment.loan.loan_number}'),
        ('loan_payment', payment.amount.amount - late_fee, f'Pago de préstamo {payment.loan.loan_number}'),
    ]
    return [
        CashMovement.objects.create(
            session=session,
            movement_type='inflow',
            category=category,
            amount=Money(amount, currency),
            description=description,
            reference=payment.payment_number,
            loan_payment=payment,
            loan=payment.loan,
            customer_name=_customer_name(payment.loan),
            recorded_by=user,
        )
        for category, amount, description in parts
        if amount > 0
    ]


def record_payment_reversal(payment, user):
    """
    Salida de caja al reversar un pago en efectivo, sólo si la sesión donde
    entró el dinero sigue abierta (corrección el mismo turno). Si la caja ya
    cerró, el reverso no inventa una salida en la caja de hoy.
    """
    created = []
    inflows = payment.cash_movements.filter(movement_type='inflow', session__status='open')
    for inflow in inflows.select_related('session'):
        created.append(CashMovement.objects.create(
            session=inflow.session,
            movement_type='outflow',
            category='refund',
            amount=inflow.amount,
            description=f'Reverso de {inflow.get_category_display().lower()} {payment.payment_number}',
            reference=payment.payment_number,
            loan_payment=payment,
            loan=payment.loan,
            customer_name=inflow.customer_name,
            recorded_by=user,
        ))
    return created


def record_disbursement_outflow(loan, user, session):
    """Salida de caja por el desembolso en efectivo del préstamo."""
    return CashMovement.objects.create(
        session=session,
        movement_type='outflow',
        category='loan_disbursement',
        amount=loan.principal_amount,
        description=f'Desembolso de préstamo {loan.loan_number}',
        reference=loan.loan_number,
        loan=loan,
        customer_name=_customer_name(loan),
        recorded_by=user,
    )
