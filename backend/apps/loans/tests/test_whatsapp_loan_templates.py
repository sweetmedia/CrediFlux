"""Los avisos de préstamos salen como plantillas Utility (no texto libre).

`send_template` se reemplaza por un doble: aquí se prueba QUÉ plantilla y QUÉ
valores manda cada aviso. El envío en sí está en
apps/communications/tests/test_whatsapp_templates.py.
"""

from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from moneyed import Money


@pytest.fixture
def service(tenant_schema):
    from apps.loans.utils_whatsapp import WhatsAppService
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_schema.pk).update(
        whatsapp_phone_id='111', whatsapp_token='tok', whatsapp_business_account_id='222',
        enable_whatsapp_reminders=True, business_name='Financiera de Prueba SRL', currency_symbol='RD$',
    )
    tenant = Tenant.objects.get(pk=tenant_schema.pk)
    svc = WhatsAppService(tenant)
    svc.wa_client = mock.MagicMock()  # nunca se usa para estos avisos
    with mock.patch("apps.loans.utils_whatsapp.send_template", return_value=mock.MagicMock()) as send:
        svc.send = send
        yield svc


def _call(svc):
    args, kwargs = svc.send.call_args
    return args[1], args[3], kwargs  # key, values, kwargs


def test_recordatorio_antes_del_vencimiento(service, active_loan):
    customer = active_loan.customer

    assert service.send_payment_reminder(
        active_loan, "8095550000", days_until_due=3, amount_due=Decimal("4500"), due_date=date(2026, 4, 15),
    )

    key, values, kwargs = _call(service)
    assert key == "recordatorio_cuota"
    assert values == [customer.first_name, "Financiera de Prueba SRL", active_loan.loan_number,
                      "15 de abril de 2026", "RD$4,500.00"]
    assert kwargs["customer"] == customer
    service.wa_client.send_message.assert_not_called()


def test_recordatorio_de_cuota_vencida_incluye_la_mora(service, active_loan):
    service.send_payment_reminder(
        active_loan, "8095550000", days_until_due=-7, amount_due=Decimal("4500"),
        due_date=date(2026, 4, 15), late_fee=Decimal("500"),
    )

    key, values, _ = _call(service)
    assert key == "cuota_vencida"
    assert values[3:] == ["15 de abril de 2026", "7", "RD$5,000.00"]


def test_recibo_usa_el_numero_del_pago(service, active_loan, admin_user):
    from apps.loans.models import LoanPayment

    payment = LoanPayment.objects.create(
        loan=active_loan, amount=Money(Decimal("1250.50"), "DOP"), payment_method="cash",
        payment_date=date(2026, 5, 2), created_by=admin_user,
    )

    service.send_payment_receipt(payment, "8095550000")

    key, values, _ = _call(service)
    assert key == "recibo_pago"
    assert values[2:] == ["RD$1,250.50", "2 de mayo de 2026", active_loan.loan_number, payment.payment_number]


def test_firma_manda_solo_el_token_en_el_boton(service, active_loan, admin_user):
    from apps.loans.models_contracts import Contract

    contract = Contract.objects.create(loan=active_loan, content="x", generated_by=admin_user)

    service.send_contract_signature_link(contract, "8095550000", "https://demo.crediflux.com.do/sign/abc123")

    key, values, kwargs = _call(service)
    assert key == "firma_contrato"
    assert values == [active_loan.customer.first_name, contract.contract_number, "Financiera de Prueba SRL"]
    assert kwargs["button_value"] == "abc123"


def test_prestamo_aprobado_ya_no_falla_por_start_date(service, active_loan):
    """Antes usaba loan.start_date, que no existe: el aviso fallaba siempre."""
    assert service.send_loan_approved(active_loan, "8095550000")

    key, values, _ = _call(service)
    assert key == "prestamo_aprobado"
    assert values[2:] == [active_loan.loan_number, "RD$10,000.00"]


def test_sin_whatsapp_configurado_no_envia(tenant_schema, active_loan):
    from apps.loans.utils_whatsapp import WhatsAppService

    with mock.patch("apps.loans.utils_whatsapp.send_template") as send:
        assert not WhatsAppService(tenant_schema).send_loan_approved(active_loan, "8095550000")
    send.assert_not_called()
