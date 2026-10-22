"""
Cálculo de amortización compartido por la calculadora, el wizard y el cronograma.

Semántica de la tasa (única en todo CrediFlux):
    `Loan.interest_rate` es la tasa MENSUAL en porcentaje (5 = 5 % mensual).
    La tasa por período es proporcional a la duración del período:
        diario    → mensual / 30
        semanal   → mensual / 4
        quincenal → mensual / 2
        mensual   → mensual
        trimestral→ mensual × 3

Este módulo sólo calcula montos; las fechas de vencimiento las pone quien lo use.
Cualquier cambio aquí cambia a la vez la cotización y el contrato, que es justo
lo que se busca: nunca deben dar cuotas distintas.
"""
from decimal import Decimal

CENT = Decimal('0.01')

# Cuotas por mes para cada frecuencia (= divisor de la tasa mensual).
PAYMENTS_PER_MONTH = {
    'daily': Decimal('30'),
    'weekly': Decimal('4'),
    'biweekly': Decimal('2'),
    'monthly': Decimal('1'),
}

# Métodos antiguos guardados en préstamos existentes → método equivalente.
LEGACY_METHODS = {
    'fixed': 'flat',
    'variable': 'saldo_insoluto',
}


def normalize_method(method):
    return LEGACY_METHODS.get(method, method)


def period_rate(monthly_rate_pct, frequency):
    """Tasa por período (fracción, no porcentaje) a partir de la tasa mensual en %."""
    monthly_rate = Decimal(str(monthly_rate_pct)) / Decimal('100')
    if frequency == 'quarterly':
        return monthly_rate * 3
    return monthly_rate / PAYMENTS_PER_MONTH.get(frequency, Decimal('1'))


def number_of_payments(term_months, frequency):
    """Número de cuotas de un préstamo a `term_months` meses."""
    if frequency == 'quarterly':
        return max(1, term_months // 3)
    return int(term_months * PAYMENTS_PER_MONTH.get(frequency, Decimal('1')))


def build_installments(principal, monthly_rate_pct, num_payments, frequency, method):
    """
    Devuelve (cuotas, cuota_representativa, interés_total).

    Cada cuota es un dict con `payment`, `principal`, `interest` y `balance`
    (Decimal a 2 decimales). La última cuota absorbe el redondeo para que el
    capital sume exactamente `principal`.
    """
    principal = Decimal(str(principal))
    method = normalize_method(method)
    if num_payments < 1:
        return [], Decimal('0.00'), Decimal('0.00')

    if method == 'variable_rd':
        # Tasa directa por período (método RD heredado): NO se divide entre la frecuencia.
        rate = Decimal(str(monthly_rate_pct)) / Decimal('100')
        return _declining_balance(principal, rate, num_payments)

    rate = period_rate(monthly_rate_pct, frequency)
    if method == 'french':
        return _french(principal, rate, num_payments)
    if method == 'flat':
        return _flat(principal, rate, num_payments)
    if method in ('saldo_insoluto', 'german'):
        return _declining_balance(principal, rate, num_payments)
    raise ValueError(f'Método de amortización desconocido: {method}')


def _row(payment, principal_portion, interest, balance):
    return {
        'payment': payment.quantize(CENT),
        'principal': principal_portion.quantize(CENT),
        'interest': interest.quantize(CENT),
        'balance': max(balance, Decimal('0')).quantize(CENT),
    }


def _declining_balance(principal, rate, num_payments):
    """Saldo insoluto / alemán: capital fijo, interés sobre el saldo pendiente."""
    principal_per_payment = (principal / num_payments).quantize(CENT)
    balance = principal
    total_interest = Decimal('0')
    rows = []
    for i in range(1, num_payments + 1):
        interest = (balance * rate).quantize(CENT)
        principal_portion = balance if i == num_payments else principal_per_payment
        balance -= principal_portion
        total_interest += interest
        rows.append(_row(principal_portion + interest, principal_portion, interest, balance))
    return rows, rows[0]['payment'], total_interest


def _french(principal, rate, num_payments):
    """Francés: cuota fija (anualidad)."""
    if rate == 0:
        payment = (principal / num_payments).quantize(CENT)
    else:
        factor = (1 + rate) ** num_payments
        payment = (principal * rate * factor / (factor - 1)).quantize(CENT)

    balance = principal
    total_interest = Decimal('0')
    rows = []
    for i in range(1, num_payments + 1):
        interest = (balance * rate).quantize(CENT)
        if i == num_payments:
            principal_portion = balance
            payment_actual = principal_portion + interest
        else:
            principal_portion = payment - interest
            payment_actual = payment
        balance -= principal_portion
        total_interest += interest
        rows.append(_row(payment_actual, principal_portion, interest, balance))
    return rows, payment, total_interest


def _flat(principal, rate, num_payments):
    """
    Plano: interés total = capital × tasa por período × cuotas
    (= capital × tasa mensual × meses), repartido en cuotas iguales.
    """
    total_interest = (principal * rate * num_payments).quantize(CENT)
    payment = ((principal + total_interest) / num_payments).quantize(CENT)
    principal_per_payment = (principal / num_payments).quantize(CENT)

    balance = principal
    interest_assigned = Decimal('0')
    rows = []
    for i in range(1, num_payments + 1):
        if i == num_payments:
            principal_portion = balance
            interest = total_interest - interest_assigned
            payment_actual = principal_portion + interest
        else:
            principal_portion = principal_per_payment
            interest = payment - principal_portion
            payment_actual = payment
        balance -= principal_portion
        interest_assigned += interest
        rows.append(_row(payment_actual, principal_portion, interest, balance))
    return rows, payment, total_interest
