"""Variables de plantillas de contrato y montos en letras."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.loans.utils_contracts import (
    amount_to_words_es,
    number_to_words_es,
    replace_contract_variables,
)


@pytest.mark.parametrize(
    "number, expected",
    [
        (0, "CERO"),
        (1, "UNO"),
        (15, "QUINCE"),
        (21, "VEINTIUNO"),
        (24, "VEINTICUATRO"),
        (100, "CIEN"),
        (101, "CIENTO UNO"),
        (500, "QUINIENTOS"),
        (1000, "MIL"),
        (1001, "MIL UNO"),
        (21000, "VEINTIÚN MIL"),
        (82800, "OCHENTA Y DOS MIL OCHOCIENTOS"),
        (1000000, "UN MILLÓN"),
        (2500000, "DOS MILLONES QUINIENTOS MIL"),
    ],
)
def test_number_to_words_es(number, expected):
    assert number_to_words_es(number) == expected


def test_amount_to_words_es():
    assert amount_to_words_es(Decimal("82800.00")) == "OCHENTA Y DOS MIL OCHOCIENTOS PESOS CON 00/100"
    assert amount_to_words_es(Decimal("3450.5")) == "TRES MIL CUATROCIENTOS CINCUENTA PESOS CON 50/100"
    assert amount_to_words_es(Decimal("1")) == "UN PESO CON 00/100"


@pytest.fixture
def loan(tenant_schema):
    from apps.loans.models import Customer, Loan, LoanSchedule
    from apps.loans.models_guarantors import Guarantor

    customer = Customer.objects.create(
        first_name="Juan", last_name="Pérez Arocha", date_of_birth=date(1990, 1, 1),
        email="juan@crediflux.test", phone="+18095550101",
        address_line1="Calle 4 #26", city="Santiago", state="Santiago",
        postal_code="51000", id_type="cedula", id_number="035-0038658-7",
    )
    loan = Loan.objects.create(
        customer=customer, loan_type="personal", principal_amount=Decimal("60000"),
        interest_rate=Decimal("4.69"), term_months=12, payment_frequency="biweekly",
        payment_amount=Decimal("3450"), first_payment_date=date(2026, 5, 1),
        maturity_date=date(2027, 4, 1),
    )
    for n in range(1, 25):
        LoanSchedule.objects.create(
            loan=loan, installment_number=n, due_date=date(2026, 5, 1) if n == 1 else date(2027, 4, 15),
            total_amount=Decimal("3450"), principal_amount=Decimal("2500"), interest_amount=Decimal("950"),
        )
    Guarantor.objects.create(
        loan=loan, first_name="Pedro", last_name="Pérez Arocha", id_type="cedula",
        id_number="031-0000000-1", phone="+18095550102", address="Calle 8, Gurabo",
        relationship="sibling",
    )
    return loan


def test_variables_de_pagare(loan, tenant):
    tenant.late_fee_percentage = Decimal("2.50")
    tenant.late_fee_frequency = "daily"
    tenant.tax_id = "031-1111111-1"
    content = (
        "{{total_con_interes_letras}} ({{total_con_interes}})|{{cantidad_cuotas_letras}} ({{cantidad_cuotas}})"
        "|{{frecuencia_pago_plural}}|{{monto_cuota_letras}}|{{mora_porcentaje}} {{mora_frecuencia}}"
        "|{{payment_frequency}}|{{guarantor_name}}|{{final_payment_date}}|{{company_tax_id}}"
    )
    rendered = replace_contract_variables(content, loan, tenant).split("|")
    assert rendered[0] == "OCHENTA Y DOS MIL OCHOCIENTOS PESOS CON 00/100 (RD$ 82,800.00)"
    assert rendered[1] == "VEINTICUATRO (24)"
    assert rendered[2] == "quincenales"
    assert rendered[3] == "TRES MIL CUATROCIENTOS CINCUENTA PESOS CON 00/100"
    assert rendered[4] == "2.50% por cada día de retraso"
    assert rendered[5] == "Quincenal"
    assert rendered[6] == "Pedro Pérez Arocha"
    # La última cuota del calendario manda sobre maturity_date
    assert rendered[7] == "15 de abril de 2027"
    assert rendered[8] == "031-1111111-1"


def test_seed_pagare_notarial_es_idempotente(tenant_schema, tenant):
    from apps.loans.models_contracts import ContractTemplate

    call_command("seed_contract_templates", schema=tenant.schema_name)
    call_command("seed_contract_templates", schema=tenant.schema_name)
    templates = ContractTemplate.objects.filter(name="Pagaré notarial con co-deudor")
    assert templates.count() == 1
    template = templates.get()
    assert template.includes_signatures is True
    assert "{{guarantor_name}}" in template.content
    assert "{{total_con_interes_letras}}" in template.content
