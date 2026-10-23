"""Reportes DGII 606/607 sin inyección de fórmulas en el CSV.

Cubre: `csv_safe` neutraliza celdas que empiezan por `=`, `+`, `-`, `@`, tab, CR o LF;
`normalize_tax_id` deja sólo alfanuméricos en RNC/cédula; ambos writers pasan cada
celda por `csv_safe`.
"""

import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

import pytest
from moneyed import Money

from apps.billing import reports_dgii
from apps.billing.reports_dgii import DGIIReport606, DGIIReport607, csv_safe, normalize_tax_id

ROW_KEYS = (
    "rnc_cedula", "tipo_identificacion", "ncf", "ncf_modificado", "tipo_ingreso",
    "fecha_comprobante", "fecha_retencion", "monto_facturado", "itbis_facturado",
    "itbis_retenido_terceros", "itbis_percibido", "retencion_isr", "isr_percibido",
    "impuesto_selectivo", "otros_impuestos", "propina_legal", "efectivo",
    "cheque_transferencia", "tarjeta", "credito", "bonos", "permuta", "otras_ventas",
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("=HYPERLINK(1)", "'=HYPERLINK(1)"),
        ("+1", "'+1"),
        ("-100.00", "'-100.00"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tx", "'\tx"),
        ("\rx", "'\rx"),
        ("\nx", "'\nx"),
        ("00112345671", "00112345671"),
        ("", ""),
        (Decimal("12.50"), "12.50"),
        (None, ""),
    ],
)
def test_csv_safe(value, expected):
    assert csv_safe(value) == expected


def test_normalize_tax_id():
    assert normalize_tax_id("=HYPERLINK(1)") == "HYPERLINK1"
    assert normalize_tax_id("001-0000001-1 ") == "00100000011"
    assert normalize_tax_id(None) == ""


def _rows(text):
    return [r for r in csv.reader(StringIO(text)) if r]


def test_607_writer_prefixes_formula_cells():
    row = {key: "0.00" for key in ROW_KEYS}
    row["rnc_cedula"] = "=HYPERLINK(1)"
    row["ncf"] = "@cmd"
    row["monto_facturado"] = "-100.00"

    report = DGIIReport607.__new__(DGIIReport607)
    with mock.patch.object(DGIIReport607, "generate_data", return_value=[row]):
        rows = _rows(report.generate_csv())

    assert rows[1][0] == "'=HYPERLINK(1)"
    assert rows[1][2] == "'@cmd"
    assert rows[1][7] == "'-100.00"


def test_607_customer_id_number_with_formula_is_neutralized(tenant_schema):
    from apps.loans.models import Customer, Loan, LoanPayment

    # Creado por ORM (sin serializer): simula datos previos a la validación de id_number.
    customer = Customer.objects.create(
        first_name="Juana", last_name="Pérez", date_of_birth=date(1990, 1, 1), gender="F",
        email="cliente.csv@crediflux.test", phone="+18095550000",
        address_line1="Calle 1", city="Santo Domingo", state="DN", postal_code="10101",
        id_type="passport", id_number="=HYPERLINK(1)", employment_status="employed",
    )
    loan = Loan.objects.create(
        customer=customer, loan_type="personal",
        principal_amount=Money(Decimal("10000.00"), "DOP"), interest_rate=Decimal("5.00"),
        interest_type="french", term_months=6, payment_frequency="monthly",
        payment_amount=Money(Decimal("1.00"), "DOP"), status="active",
        disbursement_date=date(2031, 6, 1), first_payment_date=date(2031, 7, 1),
    )
    LoanPayment.objects.create(
        loan=loan,
        payment_date=date(2031, 7, 5),
        amount=Money(Decimal("500.00"), "DOP"),
        payment_method="cash",
        status="completed",
    )

    report = DGIIReport607(2031, 7)
    assert report.generate_data()[0]["rnc_cedula"] == "HYPERLINK1"

    rows = _rows(report.generate_csv())
    assert len(rows) == 2
    assert rows[1][0] == "HYPERLINK1"
    for r in rows:
        for cell in r:
            assert not cell or cell[0] not in "=+-@\t\r\n", cell


def test_606_writer_goes_through_csv_safe(tenant_schema):
    with mock.patch.object(reports_dgii, "csv_safe", wraps=reports_dgii.csv_safe) as safe:
        text = DGIIReport606(2031, 7).generate_csv()

    header = _rows(text)[0]
    assert len(header) == 23
    assert safe.call_count == 23
