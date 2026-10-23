"""Recordatorios y avisos de mora por WhatsApp programados en Celery Beat.

Nunca sale nada a la red: `get_whatsapp_service` se reemplaza por un doble.
Las tareas recorren tenants con `schema_context`; los datos se crean en el
schema `test` dentro de la transacción del test.
"""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from moneyed import Money


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def wa(tenant_schema):
    """Doble del servicio de WhatsApp; habilita los recordatorios del tenant de pruebas."""
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_schema.pk).update(
        is_active=True, enable_whatsapp_reminders=True, reminder_days_before=3
    )
    service = mock.MagicMock()
    service.is_configured.return_value = True
    service.send_payment_reminder.return_value = True
    service.send_overdue_notice.return_value = True
    service._format_phone.side_effect = lambda phone: str(phone)
    with mock.patch("apps.loans.tasks.get_whatsapp_service", return_value=service):
        yield service


def _due_in(loan, installment, days, status="pending"):
    from apps.loans.models import LoanSchedule

    schedule = loan.payment_schedules.get(installment_number=installment)
    LoanSchedule.objects.filter(pk=schedule.pk).update(
        due_date=timezone.localdate() + timedelta(days=days), status=status
    )
    return schedule


def _run(task_name):
    from apps.loans import tasks

    return getattr(tasks, task_name).delay(force=True).get()


def test_recordatorio_antes_del_vencimiento_usa_los_dias_del_tenant(wa, active_loan):
    _due_in(active_loan, 1, 3)  # tenant.reminder_days_before = 3
    _due_in(active_loan, 2, 5)  # fuera de ventana

    result = _run("send_payment_reminders")

    assert result["total_sent"] == 1
    kwargs = wa.send_payment_reminder.call_args.kwargs
    assert kwargs["days_until_due"] == 3


def test_recordatorio_despues_del_vencimiento_incluye_cuotas_ya_marcadas_en_mora(wa, active_loan):
    _due_in(active_loan, 1, -1, status="overdue")  # la tarea de mora la marcó a las 00:30

    assert _run("send_payment_reminders")["total_sent"] == 1


def test_no_repite_el_recordatorio_el_mismo_dia(wa, active_loan):
    _due_in(active_loan, 1, 3)

    assert _run("send_payment_reminders")["total_sent"] == 1
    assert _run("send_payment_reminders")["total_sent"] == 0  # reintento del mismo día
    assert wa.send_payment_reminder.call_count == 1


def test_aviso_de_mora_a_los_15_dias_una_sola_vez_por_dia(wa, active_loan):
    _due_in(active_loan, 1, -15, status="overdue")

    assert _run("send_overdue_notice")["total_sent"] == 1
    assert _run("send_overdue_notice")["total_sent"] == 0
    # Plantilla `cuota_vencida`, nunca texto libre (Meta lo rechaza fuera de las 24 h)
    assert wa.send_overdue_notice.call_count == 1
    assert wa.send_overdue_notice.call_args.kwargs["days_overdue"] == 15
    wa.wa_client.send_message.assert_not_called()


def test_tenant_sin_whatsapp_habilitado_no_envia(tenant, active_loan):
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant.pk).update(enable_whatsapp_reminders=False)
    _due_in(active_loan, 1, 3)

    with mock.patch("apps.loans.tasks.get_whatsapp_service") as factory:
        assert _run("send_payment_reminders")["total_sent"] == 0
    factory.assert_not_called()
