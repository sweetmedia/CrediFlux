"""Cabos sueltos de la Fase 0.

- Quién puede registrar pagos (antes: cualquier usuario autenticado).
- Fechas por defecto: `DateField(default=timezone.now)` metía un datetime y
  crear un préstamo sin `application_date` respondía 500.
- La mora se calcula a diario vía Celery Beat (antes nada corría el comando).
"""

from decimal import Decimal
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone


def _pay(client, loan, **extra):
    return client.post(
        "/api/loans/payments/",
        {
            "loan": str(loan.id),
            "amount": "100.00",
            "amount_currency": "DOP",
            "payment_method": "bank_transfer",
            **extra,
        },
        format="json",
    )


@pytest.mark.parametrize("role", ["viewer", "accountant"])
def test_roles_sin_cobro_no_registran_pagos(api_client, user_factory, active_loan, role):
    from apps.loans.models import LoanPayment

    api_client.force_authenticate(user=user_factory(role=role))

    assert _pay(api_client, active_loan).status_code == 403
    assert not LoanPayment.objects.exists()
    assert api_client.get("/api/loans/payments/").status_code == 200  # leer sí


@pytest.mark.parametrize(
    "role", ["admin", "manager", "loan_officer", "collector", "collection_supervisor", "cashier"]
)
def test_roles_de_cobro_registran_pagos(api_client, user_factory, active_loan, role):
    api_client.force_authenticate(user=user_factory(role=role))
    assert _pay(api_client, active_loan).status_code == 201


def test_dueno_registra_pagos_aunque_su_rol_sea_viewer(api_client, user_factory, active_loan):
    api_client.force_authenticate(user=user_factory(role="viewer", is_tenant_owner=True))
    assert _pay(api_client, active_loan).status_code == 201


def test_pago_sin_fecha_usa_hoy(auth_client, active_loan):
    response = _pay(auth_client, active_loan)

    assert response.status_code == 201, response.content
    from apps.loans.models import LoanPayment

    assert LoanPayment.objects.get().payment_date == timezone.localdate()


def test_crear_prestamo_sin_fecha_de_solicitud_usa_hoy(auth_client, customer_factory):
    from apps.loans.models import Loan
    from apps.loans.models_contracts import ContractTemplate

    ContractTemplate.objects.create(name="Base", content="x", is_active=True, is_default=True)
    response = auth_client.post(
        "/api/loans/",
        {
            "customer": str(customer_factory().id),
            "loan_type": "personal",
            "principal_amount": "5000.00",
            "principal_amount_currency": "DOP",
            "interest_rate": "5.00",
            "interest_type": "flat",
            "term_months": 2,
            "payment_frequency": "monthly",
            "payment_amount": "0.01",
            "payment_amount_currency": "DOP",
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    assert Loan.objects.get(id=response.json()["id"]).application_date == timezone.localdate()


def test_la_tarea_de_mora_corre_el_comando_por_tenant(public_schema, tenant):
    from apps.loans.tasks import calculate_late_fees

    with mock.patch("apps.loans.tasks.call_command") as command:
        calculate_late_fees.delay()

    tenants = [call.kwargs["tenant"] for call in command.call_args_list]
    assert tenant.schema_name in tenants
    assert "public" not in tenants
    assert all(call.args == ("calculate_late_fees",) for call in command.call_args_list)


def test_un_tenant_que_falla_no_frena_a_los_demas(public_schema, tenant):
    from apps.loans.tasks import calculate_late_fees

    with mock.patch("apps.loans.tasks.call_command", side_effect=RuntimeError("boom")):
        result = calculate_late_fees.delay().get()

    assert tenant.schema_name in result["failed"]


def test_setup_periodic_tasks_programa_la_mora_a_diario(public_schema):
    from django_celery_beat.models import PeriodicTask

    call_command("setup_periodic_tasks", stdout=mock.MagicMock())
    call_command("setup_periodic_tasks", stdout=mock.MagicMock())  # idempotente

    task = PeriodicTask.objects.get(task="loans.calculate_late_fees")
    assert task.enabled
    assert (task.crontab.minute, task.crontab.hour, task.crontab.day_of_week) == ("30", "0", "*")
    assert str(task.crontab.timezone) == "America/Santo_Domingo"
