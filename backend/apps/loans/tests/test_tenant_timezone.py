"""Zona horaria por tenant (por defecto America/New_York).

"Hoy" (fecha de pago por defecto, días de atraso, recordatorios) se calcula en
la zona del tenant, y las tareas diarias corren cuando en SU zona es la hora.

Momento de referencia: 2026-03-10 20:00 UTC
  - America/New_York  → 2026-03-10 16:00
  - Asia/Tokyo        → 2026-03-11 05:00
  - Pacific/Kiritimati (UTC+14) → 2026-03-11 10:00
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time
from moneyed import Money

MOMENT = "2026-03-10 20:00:00+00:00"


def _set_tz(tenant, tz):
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant.pk).update(timezone=tz)


def test_por_defecto_es_nueva_york():
    from apps.tenants.models import Tenant

    assert Tenant._meta.get_field("timezone").default == "America/New_York"


def test_zona_invalida_no_valida():
    from django.core.exceptions import ValidationError

    from apps.tenants.models import validate_timezone

    validate_timezone("America/Santo_Domingo")
    with pytest.raises(ValidationError):
        validate_timezone("Marte/Olympus")


def test_ajustes_del_tenant_exponen_y_validan_la_zona(auth_client, tenant):
    response = auth_client.get("/api/tenants/settings/")
    assert response.status_code == 200, response.content
    assert response.json()["timezone"] == "America/New_York"

    bad = auth_client.patch("/api/tenants/settings/", {"timezone": "Marte/Olympus"}, format="json")
    assert bad.status_code == 400

    ok = auth_client.patch("/api/tenants/settings/", {"timezone": "America/Santo_Domingo"}, format="json")
    assert ok.status_code == 200, ok.content
    assert auth_client.get("/api/tenants/settings/").json()["timezone"] == "America/Santo_Domingo"


@freeze_time(MOMENT)
@pytest.mark.parametrize("tz, expected", [("America/New_York", date(2026, 3, 10)), ("Asia/Tokyo", date(2026, 3, 11))])
def test_pago_sin_fecha_usa_el_hoy_del_tenant(auth_client, tenant, active_loan, tz, expected):
    from apps.loans.models import LoanPayment

    _set_tz(tenant, tz)
    response = auth_client.post(
        "/api/loans/payments/",
        {"loan": str(active_loan.id), "amount": "100.00", "amount_currency": "DOP",
         "payment_method": "bank_transfer"},
        format="json",
    )

    assert response.status_code == 201, response.content
    assert LoanPayment.objects.get().payment_date == expected


@freeze_time(MOMENT)
@pytest.mark.parametrize("tz, expected_days", [("America/New_York", 0), ("Asia/Tokyo", 1)])
def test_dias_de_atraso_se_cuentan_en_la_zona_del_tenant(tenant, active_loan, tz, expected_days):
    from apps.loans.models import LoanSchedule
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant.pk).update(
        timezone=tz, late_fee_type="fixed", late_fee_frequency="daily",
        late_fee_fixed_amount=Decimal("10"), grace_period_days=0,
    )
    first = active_loan.payment_schedules.get(installment_number=1)
    LoanSchedule.objects.filter(pk=first.pk).update(
        due_date=date(2026, 3, 10), status="pending", days_overdue=0
    )

    call_command("calculate_late_fees", tenant=tenant.schema_name, stdout=StringIO())

    first.refresh_from_db()
    assert first.days_overdue == expected_days
    assert first.late_fee_amount == Money(Decimal(10 * expected_days), "DOP")


# ---------------------------------------------------------------------------
# Tareas horarias: cada tenant se procesa cuando en su zona es la hora
# (febrero: Nueva York en horario estándar, UTC−5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "moment, tz, should_run",
    [
        ("2026-02-10 05:30:00+00:00", "America/New_York", True),    # 00:30 NY (EST)
        ("2026-02-10 06:30:00+00:00", "America/New_York", False),   # 01:30 NY
        ("2026-02-10 15:30:00+00:00", "Asia/Tokyo", True),          # 00:30 Tokio
        ("2026-02-10 05:30:00+00:00", "Asia/Tokyo", False),         # 14:30 Tokio
    ],
)
def test_mora_corre_a_medianoche_local(public_schema, tenant, moment, tz, should_run):
    from apps.loans.tasks import calculate_late_fees

    _set_tz(tenant, tz)
    with freeze_time(moment), mock.patch("apps.loans.tasks.call_command") as command:
        result = calculate_late_fees.delay().get()

    ran = any(c.kwargs.get("tenant") == tenant.schema_name for c in command.call_args_list)
    assert ran is should_run
    assert (tenant.schema_name in result["processed"]) is should_run


def test_mora_force_ignora_la_hora(public_schema, tenant):
    from apps.loans.tasks import calculate_late_fees

    with freeze_time("2026-03-10 18:00:00+00:00"), mock.patch("apps.loans.tasks.call_command") as command:
        calculate_late_fees.delay(force=True).get()

    assert any(c.kwargs.get("tenant") == tenant.schema_name for c in command.call_args_list)


@pytest.mark.parametrize(
    "task_name, moment, should_run",
    [
        ("send_payment_reminders", "2026-02-10 14:00:00+00:00", True),   # 09:00 NY
        ("send_payment_reminders", "2026-02-10 13:00:00+00:00", False),  # 08:00 NY
        ("send_overdue_notice", "2026-02-10 14:30:00+00:00", True),      # 09:30 NY
        ("send_overdue_notice", "2026-02-10 20:30:00+00:00", False),     # 15:30 NY
    ],
)
def test_whatsapp_corre_a_las_9_locales(tenant_schema, task_name, moment, should_run):
    from apps.loans import tasks
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_schema.pk).update(is_active=True, enable_whatsapp_reminders=True)
    service = mock.MagicMock()
    service.is_configured.return_value = True
    with freeze_time(moment), mock.patch("apps.loans.tasks.get_whatsapp_service", return_value=service) as factory:
        getattr(tasks, task_name).delay().get()

    called_for = [c.args[0].schema_name for c in factory.call_args_list]
    assert (tenant_schema.schema_name in called_for) is should_run


def test_whatsapp_usa_el_hoy_del_tenant(tenant_schema, active_loan):
    """A las 09:00 de Tokio (00:00 UTC del día anterior) la cuota vence 'hoy' en Tokio."""
    from apps.loans import tasks
    from apps.loans.models import LoanSchedule
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_schema.pk).update(
        is_active=True, enable_whatsapp_reminders=True, timezone="Asia/Tokyo", reminder_days_before=3
    )
    first = active_loan.payment_schedules.get(installment_number=1)
    LoanSchedule.objects.filter(pk=first.pk).update(due_date=date(2026, 3, 11), status="pending")
    service = mock.MagicMock()
    service.is_configured.return_value = True
    service.send_payment_reminder.return_value = True

    # 2026-03-11 00:00 UTC = 2026-03-11 09:00 Tokio
    with freeze_time("2026-03-11 00:00:00+00:00"), mock.patch(
        "apps.loans.tasks.get_whatsapp_service", return_value=service
    ):
        tasks.send_payment_reminders.delay().get()

    assert service.send_payment_reminder.call_args.kwargs["days_until_due"] == 0


def test_setup_periodic_tasks_programa_por_hora(public_schema):
    from django_celery_beat.models import PeriodicTask

    call_command("setup_periodic_tasks", stdout=mock.MagicMock())

    expected = {
        "loans.calculate_late_fees": "30",
        "loans.send_payment_reminders": "0",
        "loans.send_overdue_notice": "30",
    }
    for task_name, minute in expected.items():
        crontab = PeriodicTask.objects.get(task=task_name).crontab
        assert (crontab.minute, crontab.hour, crontab.day_of_week) == (minute, "*", "*"), task_name


@pytest.mark.parametrize(
    "moment, should_run",
    [
        ("2026-07-10 04:30:00+00:00", True),   # 00:30 NY (EDT, UTC−4)
        ("2026-07-10 05:30:00+00:00", False),  # 01:30 NY
    ],
)
def test_mora_sigue_el_horario_de_verano(public_schema, tenant, moment, should_run):
    from apps.loans.tasks import calculate_late_fees

    _set_tz(tenant, "America/New_York")
    with freeze_time(moment), mock.patch("apps.loans.tasks.call_command"):
        result = calculate_late_fees.delay().get()

    assert (tenant.schema_name in result["processed"]) is should_run
