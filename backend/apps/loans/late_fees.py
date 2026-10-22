"""
Cálculo de mora (cargo por atraso) de una cuota.

Fuente de la configuración — una sola, con respaldo explícito:

1. **El Tenant manda** (`late_fee_type`, `late_fee_percentage`,
   `late_fee_fixed_amount`, `late_fee_frequency`, `grace_period_days`).
   Es lo que cada financiera edita en su configuración.
2. **Constance es el respaldo** (`LATE_PAYMENT_FEE`, `LATE_PAYMENT_GRACE_DAYS`),
   y sólo se usa cuando:
   - no hay tenant (p. ej. el schema público), con un cargo fijo único de
     `LATE_PAYMENT_FEE` tras `LATE_PAYMENT_GRACE_DAYS` días; o
   - el tenant eligió mora fija pero dejó el monto en 0: se toma el monto de
     `LATE_PAYMENT_FEE` y se respetan la frecuencia y la gracia del tenant.

Frecuencias ('daily' / 'monthly' / 'one_time', las choices del Tenant), contadas
desde que vence la gracia:
- daily    → un cargo por cada día de atraso efectivo;
- monthly  → un cargo por cada mes (30 días) iniciado;
- one_time → un único cargo.

El resultado va siempre en la moneda del saldo de la cuota.
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from moneyed import Money

CENT = Decimal('0.01')


@dataclass(frozen=True)
class LateFeePolicy:
    fee_type: str  # 'percentage' | 'fixed' | 'none'
    percentage: Decimal
    fixed_amount: Decimal
    frequency: str  # 'daily' | 'monthly' | 'one_time'
    grace_days: int
    source: str  # 'tenant' | 'constance' | 'tenant+constance'


def _constance():
    from constance import config

    return Decimal(str(config.LATE_PAYMENT_FEE)), int(config.LATE_PAYMENT_GRACE_DAYS)


def policy_for(tenant):
    """Política de mora vigente para `tenant` (None → Constance)."""
    if tenant is None:
        amount, grace = _constance()
        return LateFeePolicy('fixed', Decimal('0'), amount, 'one_time', grace, 'constance')

    fixed = tenant.late_fee_fixed_amount
    fixed_amount = Decimal(str(getattr(fixed, 'amount', fixed) or 0))
    source = 'tenant'
    if tenant.late_fee_type == 'fixed' and fixed_amount <= 0:
        fixed_amount, _ = _constance()
        source = 'tenant+constance'

    return LateFeePolicy(
        fee_type=tenant.late_fee_type,
        percentage=Decimal(str(tenant.late_fee_percentage or 0)),
        fixed_amount=fixed_amount,
        frequency=tenant.late_fee_frequency,
        grace_days=tenant.grace_period_days or 0,
        source=source,
    )


def _periods(effective_days, frequency):
    if effective_days <= 0:
        return 0
    if frequency == 'daily':
        return effective_days
    if frequency == 'monthly':
        return (effective_days + 29) // 30
    return 1  # one_time


def calculate_late_fee(balance, days_overdue, policy):
    """Mora de una cuota con saldo `balance` (Money) y `days_overdue` días de atraso."""
    currency = balance.currency
    periods = _periods(days_overdue - policy.grace_days, policy.frequency)

    if policy.fee_type == 'percentage':
        amount = balance.amount * policy.percentage / Decimal('100') * periods
    elif policy.fee_type == 'fixed':
        amount = policy.fixed_amount * periods
    else:  # 'none'
        amount = Decimal('0')

    return Money(max(amount, Decimal('0')).quantize(CENT, rounding=ROUND_HALF_UP), currency)
