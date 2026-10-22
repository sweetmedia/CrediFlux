"""Bug 2 (Fase 0): cálculo de mora.

Antes el comando comparaba `late_fee_frequency` contra 'per_day'/'per_week'
(el Tenant usa 'daily'/'monthly'/'one_time'), así que la mora diaria caía en
"único" y devolvía `Money(0, 'USD')` en vez de la moneda del préstamo.
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from constance.test import override_config
from django.core.management import call_command
from moneyed import Money

from apps.loans.management.commands.calculate_late_fees import Command
from apps.tenants.models import Tenant


def _tenant(**overrides):
    data = {
        "late_fee_type": "percentage",
        "late_fee_percentage": Decimal("5.00"),
        "late_fee_fixed_amount": Money(Decimal("0.00"), "DOP"),
        "late_fee_frequency": "monthly",
        "grace_period_days": 0,
    }
    data.update(overrides)
    return Tenant(schema_name="sin_guardar", name="x", **data)


BALANCE = Money(Decimal("1000.00"), "DOP")


def fee(tenant, days):
    return Command()._calculate_late_fee(BALANCE, days, tenant)


def test_porcentaje_diario_cobra_por_dia_en_dop():
    tenant = _tenant(late_fee_frequency="daily", late_fee_percentage=Decimal("1.00"), grace_period_days=5)
    assert fee(tenant, 12) == Money(Decimal("70.00"), "DOP")  # 7 días efectivos × 1 % × 1,000


def test_fijo_diario():
    tenant = _tenant(
        late_fee_type="fixed", late_fee_frequency="daily", late_fee_fixed_amount=Money(Decimal("25"), "DOP")
    )
    assert fee(tenant, 4) == Money(Decimal("100.00"), "DOP")


def test_mensual_cobra_por_mes_iniciado_desde_que_vence_la_gracia():
    tenant = _tenant(late_fee_frequency="monthly", grace_period_days=5)
    assert fee(tenant, 6) == Money(Decimal("50.00"), "DOP")  # 1er mes
    assert fee(tenant, 35) == Money(Decimal("50.00"), "DOP")  # 30 días efectivos: sigue el 1er mes
    assert fee(tenant, 36) == Money(Decimal("100.00"), "DOP")  # 2º mes


def test_unico_al_vencer():
    tenant = _tenant(late_fee_frequency="one_time")
    assert fee(tenant, 1) == fee(tenant, 90) == Money(Decimal("50.00"), "DOP")


@pytest.mark.parametrize("days", [0, 3, 5])
def test_dentro_de_la_gracia_no_hay_mora_y_la_moneda_es_la_del_prestamo(days):
    tenant = _tenant(grace_period_days=5)
    result = fee(tenant, days)
    assert result == Money(Decimal("0.00"), "DOP")
    assert result.currency.code == "DOP"


def test_sin_mora():
    assert fee(_tenant(late_fee_type="none"), 40) == Money(Decimal("0.00"), "DOP")


def test_moneda_del_prestamo_en_usd():
    tenant = _tenant(late_fee_type="fixed", late_fee_fixed_amount=Money(Decimal("10"), "DOP"),
                     late_fee_frequency="one_time")
    result = Command()._calculate_late_fee(Money(Decimal("100"), "USD"), 3, tenant)
    assert result == Money(Decimal("10.00"), "USD")


@pytest.mark.django_db
@override_config(LATE_PAYMENT_FEE=500.0, LATE_PAYMENT_GRACE_DAYS=5)
def test_fijo_sin_monto_usa_la_constance_como_respaldo():
    tenant = _tenant(late_fee_type="fixed", late_fee_frequency="one_time", grace_period_days=5)
    assert fee(tenant, 6) == Money(Decimal("500.00"), "DOP")


@pytest.mark.django_db
@override_config(LATE_PAYMENT_FEE=500.0, LATE_PAYMENT_GRACE_DAYS=5)
def test_sin_tenant_usa_la_constance():
    """RD$ 500 únicos tras 5 días de gracia (lo que asumen los prototipos)."""
    assert fee(None, 5) == Money(Decimal("0.00"), "DOP")
    assert fee(None, 6) == Money(Decimal("500.00"), "DOP")


def test_comando_actualiza_cuotas_vencidas_y_parciales(tenant, active_loan):
    from apps.loans.models import LoanSchedule

    tenant = Tenant.objects.get(pk=tenant.pk)  # copia: no tocar el tenant de sesión
    tenant.late_fee_type = "percentage"
    tenant.late_fee_percentage = Decimal("1.00")
    tenant.late_fee_frequency = "daily"
    tenant.grace_period_days = 0
    tenant.save()

    today = date.today()
    first, second = active_loan.payment_schedules.order_by("installment_number")[:2]
    LoanSchedule.objects.filter(pk=first.pk).update(due_date=today - timedelta(days=10))
    LoanSchedule.objects.filter(pk=second.pk).update(
        due_date=today - timedelta(days=3), status="partial", paid_amount=Money(Decimal("100"), "DOP")
    )

    call_command("calculate_late_fees", tenant=tenant.schema_name, stdout=StringIO())

    first.refresh_from_db()
    second.refresh_from_db()
    expected_first = (first.total_amount.amount * Decimal("0.10")).quantize(Decimal("0.01"))
    assert first.late_fee_amount == Money(expected_first, "DOP")
    assert first.status == "overdue"
    assert first.days_overdue == 10
    expected_second = ((second.total_amount.amount - Decimal("100")) * Decimal("0.03")).quantize(Decimal("0.01"))
    assert second.late_fee_amount == Money(expected_second, "DOP")
    assert second.status == "overdue"  # igual que reconcile_loan_from_payments
