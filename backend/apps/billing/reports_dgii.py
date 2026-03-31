"""
DGII Report Generation — Formatos 606 and 607

Format 606: Compras y Gastos (purchases/expenses)
Format 607: Ventas de Bienes y Servicios (sales/income)

For a financiera/prestamista:
- 607 is the key report: tracks loan interest, commissions, late fees as income
- 606 tracks operational expenses

Reference: DGII Norma General 07-2014, updated Norma General 05-2023
"""
import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO, BytesIO
from typing import List, Optional

from django.db import connection
from django.utils import timezone

from apps.loans.models import Loan, LoanPayment, LoanSchedule


class DGIIReport607:
    """
    Genera el Formato 607 — Envío de Datos de Ventas de Bienes y Servicios.
    
    For a financiera, "ventas" = interest income, commissions, late fees, insurance.
    Each payment received is a reportable line item.
    
    Columns (per DGII spec):
    1. RNC/Cédula del Comprador
    2. Tipo de Identificación (1=RNC, 2=Cédula, 3=Pasaporte)
    3. Número de Comprobante Fiscal (NCF)
    4. Número de Comprobante Fiscal Modificado (if credit/debit note)
    5. Tipo de Ingreso (01=Ingresos por operaciones, 02=Ingresos financieros, 03=Ingresos extraordinarios, etc.)
    6. Fecha del Comprobante (YYYYMMDD)
    7. Fecha de Retención (YYYYMMDD) — if applies
    8. Monto Facturado (total billed)
    9. ITBIS Facturado (18% tax — usually 0 for loan interest which is exempt)
    10. ITBIS Retenido por Terceros
    11. ITBIS Percibido
    12. Retención ISR
    13. ISR Percibido
    14. Impuesto Selectivo al Consumo
    15. Otros Impuestos/Tasas
    16. Monto Propina Legal
    17. Efectivo
    18. Cheque/Transferencia
    19. Tarjeta Débito/Crédito
    20. Venta a Crédito
    21. Bonos/Certificados
    22. Permuta
    23. Otras Formas de Venta
    """

    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.tenant = connection.tenant

    def _get_id_type(self, id_type: str) -> str:
        """Map customer id_type to DGII type code"""
        mapping = {
            'rnc': '1',
            'cedula': '2',
            'passport': '3',
        }
        return mapping.get(id_type, '2')

    def _get_payment_method_columns(self, payment: LoanPayment) -> dict:
        """Map payment method to DGII payment columns"""
        amount = float(payment.amount.amount)
        method = payment.payment_method

        # Default all to 0
        cols = {
            'efectivo': Decimal('0.00'),
            'cheque_transferencia': Decimal('0.00'),
            'tarjeta': Decimal('0.00'),
            'credito': Decimal('0.00'),
            'bonos': Decimal('0.00'),
            'permuta': Decimal('0.00'),
            'otras': Decimal('0.00'),
        }

        if method == 'cash':
            cols['efectivo'] = payment.amount.amount
        elif method in ('transfer', 'check'):
            cols['cheque_transferencia'] = payment.amount.amount
        elif method in ('card', 'debit_card', 'credit_card'):
            cols['tarjeta'] = payment.amount.amount
        elif method == 'mobile':
            cols['otras'] = payment.amount.amount
        else:
            cols['efectivo'] = payment.amount.amount  # default to cash

        return cols

    def _format_date(self, d: date) -> str:
        """Format date as YYYYMMDD per DGII spec"""
        if not d:
            return ''
        return d.strftime('%Y%m%d')

    def _format_amount(self, amount: Decimal) -> str:
        """Format amount with 2 decimals, no thousands separator"""
        if not amount:
            return '0.00'
        return f"{float(amount):.2f}"

    def generate_data(self) -> List[dict]:
        """Generate 607 report data from payments in the period"""
        # Get all completed payments in the period
        payments = LoanPayment.objects.filter(
            payment_date__year=self.year,
            payment_date__month=self.month,
            status='completed',
        ).select_related(
            'loan', 'loan__customer', 'schedule'
        ).order_by('payment_date')

        rows = []
        for payment in payments:
            customer = payment.loan.customer
            pay_cols = self._get_payment_method_columns(payment)

            # Interest income is EXEMPT from ITBIS in RD
            # Commissions DO pay 18% ITBIS
            # For simplicity, we report interest as Tipo Ingreso 02 (Ingresos financieros)
            # with ITBIS = 0
            itbis = Decimal('0.00')

            row = {
                'rnc_cedula': (customer.id_number or '').replace('-', '').replace(' ', ''),
                'tipo_identificacion': self._get_id_type(customer.id_type),
                'ncf': '',  # Would come from e-CF system when integrated
                'ncf_modificado': '',
                'tipo_ingreso': '02',  # Ingresos financieros
                'fecha_comprobante': self._format_date(payment.payment_date),
                'fecha_retencion': '',
                'monto_facturado': self._format_amount(payment.amount.amount),
                'itbis_facturado': self._format_amount(itbis),
                'itbis_retenido_terceros': '0.00',
                'itbis_percibido': '0.00',
                'retencion_isr': '0.00',
                'isr_percibido': '0.00',
                'impuesto_selectivo': '0.00',
                'otros_impuestos': '0.00',
                'propina_legal': '0.00',
                'efectivo': self._format_amount(pay_cols['efectivo']),
                'cheque_transferencia': self._format_amount(pay_cols['cheque_transferencia']),
                'tarjeta': self._format_amount(pay_cols['tarjeta']),
                'credito': self._format_amount(pay_cols['credito']),
                'bonos': self._format_amount(pay_cols['bonos']),
                'permuta': self._format_amount(pay_cols['permuta']),
                'otras_ventas': self._format_amount(pay_cols['otras']),
                # Extra fields for internal use / display
                '_customer_name': customer.get_full_name(),
                '_loan_number': payment.loan.loan_number,
                '_payment_number': payment.payment_number,
                '_interest_paid': self._format_amount(payment.interest_paid.amount if payment.interest_paid else Decimal('0')),
                '_principal_paid': self._format_amount(payment.principal_paid.amount if payment.principal_paid else Decimal('0')),
                '_late_fee_paid': self._format_amount(payment.late_fee_paid.amount if payment.late_fee_paid else Decimal('0')),
            }
            rows.append(row)

        return rows

    def generate_csv(self) -> str:
        """Generate CSV file content in DGII 607 format"""
        rows = self.generate_data()

        output = StringIO()
        
        # Header row (DGII standard column names)
        headers = [
            'RNC/Cédula', 'Tipo Id', 'NCF', 'NCF Modificado',
            'Tipo Ingreso', 'Fecha Comprobante', 'Fecha Retención',
            'Monto Facturado', 'ITBIS Facturado', 'ITBIS Ret. Terceros',
            'ITBIS Percibido', 'Retención ISR', 'ISR Percibido',
            'Imp. Selectivo', 'Otros Impuestos', 'Propina Legal',
            'Efectivo', 'Cheque/Transferencia', 'Tarjeta',
            'Crédito', 'Bonos', 'Permuta', 'Otras Ventas'
        ]

        writer = csv.writer(output)
        writer.writerow(headers)

        for row in rows:
            writer.writerow([
                row['rnc_cedula'], row['tipo_identificacion'], row['ncf'],
                row['ncf_modificado'], row['tipo_ingreso'], row['fecha_comprobante'],
                row['fecha_retencion'], row['monto_facturado'], row['itbis_facturado'],
                row['itbis_retenido_terceros'], row['itbis_percibido'],
                row['retencion_isr'], row['isr_percibido'],
                row['impuesto_selectivo'], row['otros_impuestos'], row['propina_legal'],
                row['efectivo'], row['cheque_transferencia'], row['tarjeta'],
                row['credito'], row['bonos'], row['permuta'], row['otras_ventas']
            ])

        return output.getvalue()

    def get_summary(self) -> dict:
        """Get summary statistics for the period"""
        rows = self.generate_data()
        
        total_facturado = sum(Decimal(r['monto_facturado']) for r in rows)
        total_efectivo = sum(Decimal(r['efectivo']) for r in rows)
        total_cheque = sum(Decimal(r['cheque_transferencia']) for r in rows)
        total_tarjeta = sum(Decimal(r['tarjeta']) for r in rows)
        total_interest = sum(Decimal(r['_interest_paid']) for r in rows)
        total_principal = sum(Decimal(r['_principal_paid']) for r in rows)
        total_late_fees = sum(Decimal(r['_late_fee_paid']) for r in rows)

        return {
            'periodo': f"{self.year}-{self.month:02d}",
            'total_registros': len(rows),
            'total_facturado': float(total_facturado),
            'total_efectivo': float(total_efectivo),
            'total_cheque_transferencia': float(total_cheque),
            'total_tarjeta': float(total_tarjeta),
            'total_interes_cobrado': float(total_interest),
            'total_capital_cobrado': float(total_principal),
            'total_mora_cobrada': float(total_late_fees),
            'total_itbis': 0.0,  # Loan interest exempt
        }


class DGIIReport606:
    """
    Genera el Formato 606 — Envío de Datos de Compras de Bienes y Servicios.
    
    For a financiera, this tracks operational expenses:
    - Office rent, utilities, supplies
    - Professional services (legal, accounting)
    - Technology/software expenses
    - Insurance premiums paid
    
    Note: Since CrediFlux currently doesn't track expenses directly,
    this generates a template/placeholder. In a full implementation,
    this would pull from an expense/accounts-payable module.
    
    Columns (per DGII spec):
    1. RNC/Cédula del Proveedor
    2. Tipo de Identificación
    3. Tipo de Bienes/Servicios Comprados
    4. NCF
    5. NCF Modificado
    6. Fecha del Comprobante
    7. Fecha de Pago
    8. Monto Facturado Servicios
    9. Monto Facturado Bienes
    10. Total Monto Facturado
    11. ITBIS Facturado
    12. ITBIS Retenido
    13. ITBIS sujeto a Proporcionalidad
    14. ITBIS llevado al Costo
    15. ITBIS por Adelantar
    16. ITBIS Percibido en compras
    17. Tipo de Retención ISR
    18. Monto Retención Renta
    19. ISR Percibido en compras
    20. Impuesto Selectivo al Consumo
    21. Otros Impuestos/Tasas
    22. Monto Propina Legal
    23. Forma de Pago
    """

    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self.tenant = connection.tenant

    def generate_csv(self) -> str:
        """Generate empty 606 CSV template with proper headers"""
        output = StringIO()
        
        headers = [
            'RNC/Cédula', 'Tipo Id', 'Tipo Bien/Servicio', 'NCF',
            'NCF Modificado', 'Fecha Comprobante', 'Fecha Pago',
            'Monto Serv.', 'Monto Bienes', 'Total Facturado',
            'ITBIS Facturado', 'ITBIS Retenido',
            'ITBIS Proporcionalidad', 'ITBIS al Costo',
            'ITBIS por Adelantar', 'ITBIS Percibido',
            'Tipo Ret. ISR', 'Monto Ret. Renta',
            'ISR Percibido', 'Imp. Selectivo',
            'Otros Impuestos', 'Propina Legal', 'Forma Pago'
        ]

        writer = csv.writer(output)
        writer.writerow(headers)
        # No data rows — expense module not yet implemented

        return output.getvalue()

    def get_summary(self) -> dict:
        """Get summary (placeholder — no expense module yet)"""
        return {
            'periodo': f"{self.year}-{self.month:02d}",
            'total_registros': 0,
            'total_facturado': 0.0,
            'total_itbis': 0.0,
            'nota': 'Módulo de gastos no implementado. Los datos del 606 deben ingresarse manualmente o desde un sistema contable externo.',
        }
