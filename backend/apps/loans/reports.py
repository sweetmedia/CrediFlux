"""
PDF Report Generation for Loans
"""
from decimal import Decimal
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from django.db import connection
from django.conf import settings
from constance import config
import os

from .models import Loan


class LoanBalanceReport:
    """
    Generates a Balance de Cuotas (Payment Schedule Balance) PDF report
    """

    def __init__(self, loan: Loan):
        self.loan = loan
        self.buffer = BytesIO()

    def _format_cedula(self, cedula: str) -> str:
        """Format cedula with dashes (XXX-XXXXXXX-X)"""
        if not cedula:
            return ''

        # Remove any existing dashes or spaces
        clean = cedula.replace('-', '').replace(' ', '')

        # Format as XXX-XXXXXXX-X (Dominican cedula format)
        if len(clean) == 11:
            return f"{clean[:3]}-{clean[3:10]}-{clean[10]}"

        # If not 11 digits, return as-is
        return cedula

    def _get_period_letter(self) -> str:
        """Get period letter based on payment frequency"""
        frequency_map = {
            'daily': 'D',       # Diario
            'weekly': 'S',      # Semanal
            'biweekly': 'Q',    # Quincenal
            'monthly': 'M',     # Mensual
            'quarterly': 'T',   # Trimestral
        }
        return frequency_map.get(self.loan.payment_frequency, 'M')

    def _draw_footer(self, pdf, width):
        """Draw footer on current page"""
        # Save current state
        pdf.saveState()

        # Footer - Discrete attribution
        pdf.setFont("Helvetica", 7)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)  # Gray color for discreteness
        company_name = getattr(config, 'COMPANY_NAME', 'CrediFlux')
        footer_text = f"Reporte generado por {company_name}"
        pdf.drawCentredString(width / 2, 20, footer_text)

        # Restore state
        pdf.restoreState()

    def generate(self):
        """Generate the PDF report"""
        # Create the PDF object using ReportLab in Landscape orientation
        pdf = canvas.Canvas(self.buffer, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Set up fonts
        pdf.setFont("Helvetica", 9)

        # Current page number
        page_num = 1
        y_position = height - 40  # Start position from top

        # Logo del Tenant (if available)
        tenant = connection.tenant
        logo_height = 0
        if tenant and hasattr(tenant, 'logo') and tenant.logo:
            try:
                # Build full path to logo
                logo_path = os.path.join(settings.MEDIA_ROOT, str(tenant.logo))
                if os.path.exists(logo_path):
                    # Draw logo in top left corner
                    logo_width = 80
                    logo_height = 50
                    pdf.drawImage(logo_path, 40, y_position - logo_height,
                                width=logo_width, height=logo_height,
                                preserveAspectRatio=True, mask='auto')
            except Exception as e:
                # If logo fails to load, continue without it
                print(f"Warning: Could not load tenant logo: {e}")
                logo_height = 0

        # Header - Date in top right
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - 40, y_position, datetime.now().strftime('%d/%m/%Y'))

        # Adjust position based on logo height
        if logo_height > 0:
            y_position -= max(logo_height + 10, 30)
        else:
            y_position -= 30

        # Title
        pdf.setFont("Helvetica-Bold", 12)
        title = "REPORTE DE BALANCES DE CUOTAS"
        title_width = pdf.stringWidth(title, "Helvetica-Bold", 12)
        pdf.drawString((width - title_width) / 2, y_position, title)
        y_position -= 25

        # Loan Information Section
        pdf.setFont("Helvetica", 9)

        # Left column
        left_x = 40
        right_x = width - 250

        # Préstamo No.
        pdf.drawString(left_x, y_position, f"Préstamo No.")
        pdf.drawString(left_x + 80, y_position, f": {self.loan.loan_number}")
        y_position -= 12

        # Deudor
        customer = self.loan.customer
        pdf.drawString(left_x, y_position, f"Deudor")
        pdf.drawString(left_x + 80, y_position, f": {customer.get_full_name().upper()}")
        # Cedula on the right
        formatted_cedula = self._format_cedula(customer.id_number)
        pdf.drawRightString(width - 40, y_position, f"Cedula: {formatted_cedula}")
        y_position -= 12

        # Dirección
        pdf.drawString(left_x, y_position, f"Dirección")
        address = customer.address_line1 or ""
        pdf.drawString(left_x + 80, y_position, f": {address}")
        y_position -= 12

        # Teléfono
        pdf.drawString(left_x, y_position, f"Teléfono")
        pdf.drawString(left_x + 80, y_position, f": {customer.phone}")
        y_position -= 12

        # Acreedor (tenant name)
        pdf.drawString(left_x, y_position, f"Acreedor")
        # Get tenant from current connection
        tenant = connection.tenant
        acreedor = getattr(tenant, 'business_name', '') if tenant else ''
        pdf.drawString(left_x + 80, y_position, f": {acreedor}")
        y_position -= 12

        # Financial Information - Two columns
        # Get period letter
        period_letter = self._get_period_letter()

        # Left side
        pdf.drawString(left_x, y_position, f"Monto Préstamo :")
        pdf.drawString(left_x + 90, y_position, f"{float(self.loan.principal_amount.amount):,.2f}")

        # Right side - Interest rate per period
        interest_per_period = self._get_interest_per_period()
        pdf.drawRightString(width - 150, y_position, f"Int/Acr.: {interest_per_period}%{period_letter}")
        y_position -= 12

        # Fecha Préstamo
        pdf.drawString(left_x, y_position, f"Fecha Préstamo :")
        fecha_prestamo = self.loan.disbursement_date.strftime('%d/%m/%Y') if self.loan.disbursement_date else 'N/A'
        pdf.drawString(left_x + 90, y_position, fecha_prestamo)

        # Comisión (assuming 0 for now)
        pdf.drawRightString(width - 150, y_position, f"Comisión: 0.00%{period_letter}")
        y_position -= 12

        # Balance/Capital
        outstanding = float(self.loan.outstanding_balance.amount)
        pdf.drawString(left_x, y_position, f"Balance/Capital:")
        pdf.drawString(left_x + 90, y_position, f"{outstanding:,.2f}")

        # Mora rate (assuming 0 for now)
        pdf.drawRightString(width - 150, y_position, f"Mora    : 0.00%{period_letter}")
        y_position -= 12

        # Balance Real
        pdf.drawString(left_x, y_position, f"Balance Real   :")
        pdf.drawString(left_x + 90, y_position, f"{outstanding:,.2f}")

        # Tiempo (period description)
        tiempo = self._get_period_description()
        pdf.drawRightString(width - 150, y_position, f"Tiempo  : {tiempo}")
        y_position -= 12

        # Balance/Cuotas
        total_balance = self._calculate_total_balance()
        pdf.drawString(left_x, y_position, f"Balance/Cuotas :")
        pdf.drawString(left_x + 90, y_position, f"{total_balance:,.2f}")

        # Int.Tot. (total interest rate)
        pdf.drawRightString(width - 150, y_position, f"Int.Tot.: {self.loan.interest_rate}%{period_letter}")
        y_position -= 15

        # Separator line
        pdf.line(left_x, y_position, width - 40, y_position)
        y_position -= 15

        # Table Header
        headers = ["CUOTA#", "FECHA", "MONTO-CUOTA", "CAPITAL", "INTERES", "MORA", "OTROS", "SALDO/CUOTA"]

        # Draw header
        col_widths = [50, 70, 80, 70, 70, 60, 60, 80]
        x_pos = left_x
        pdf.setFont("Helvetica-Bold", 8)
        for i, header in enumerate(headers):
            if i == 0:
                pdf.drawString(x_pos, y_position, header)
            elif i == 1:
                pdf.drawString(x_pos, y_position, header)
            else:
                # Right align numeric headers
                pdf.drawRightString(x_pos + col_widths[i], y_position, header)
            x_pos += col_widths[i]

        y_position -= 12
        pdf.line(left_x, y_position, width - 40, y_position)
        y_position -= 12

        # Get payment schedules
        schedules = self.loan.payment_schedules.all().order_by('installment_number')

        # Data rows
        pdf.setFont("Helvetica", 8)
        total_capital = Decimal('0.00')
        total_interest = Decimal('0.00')
        total_mora = Decimal('0.00')
        total_otros = Decimal('0.00')
        total_saldo = Decimal('0.00')

        for schedule in schedules:
            # Check if we need a new page
            if y_position < 80:
                # Draw footer before starting new page
                self._draw_footer(pdf, width)
                pdf.showPage()
                page_num += 1
                y_position = height - 40
                pdf.setFont("Helvetica", 8)

            # Prepare row data
            cuota_num = f"{schedule.installment_number}/{schedules.count()}"
            fecha = schedule.due_date.strftime('%d/%m/%Y')
            monto_cuota = float(schedule.total_amount.amount)
            capital = float(schedule.principal_amount.amount)
            interes = float(schedule.interest_amount.amount)
            mora = float(schedule.late_fee_amount.amount) if schedule.late_fee_amount else 0.00
            otros = 0.00  # Not in current model
            saldo_cuota = float(schedule.balance.amount) if schedule.balance else monto_cuota

            # Update totals
            total_capital += Decimal(str(capital))
            total_interest += Decimal(str(interes))
            total_mora += Decimal(str(mora))
            total_otros += Decimal(str(otros))
            total_saldo += Decimal(str(saldo_cuota))

            # Draw row
            x_pos = left_x

            # CUOTA#
            pdf.drawString(x_pos, y_position, cuota_num)
            x_pos += col_widths[0]

            # FECHA
            pdf.drawString(x_pos, y_position, fecha)
            x_pos += col_widths[1]

            # MONTO-CUOTA
            pdf.drawRightString(x_pos + col_widths[2], y_position, f"{monto_cuota:,.2f}")
            x_pos += col_widths[2]

            # CAPITAL
            pdf.drawRightString(x_pos + col_widths[3], y_position, f"{capital:,.2f}")
            x_pos += col_widths[3]

            # INTERES
            pdf.drawRightString(x_pos + col_widths[4], y_position, f"{interes:,.2f}")
            x_pos += col_widths[4]

            # MORA
            pdf.drawRightString(x_pos + col_widths[5], y_position, f"{mora:,.2f}")
            x_pos += col_widths[5]

            # OTROS
            pdf.drawRightString(x_pos + col_widths[6], y_position, f"{otros:,.2f}")
            x_pos += col_widths[6]

            # SALDO/CUOTA
            pdf.drawRightString(x_pos + col_widths[7], y_position, f"{saldo_cuota:,.2f}")

            y_position -= 12

        # Totals separator
        y_position -= 5
        pdf.line(left_x + col_widths[0] + col_widths[1], y_position, width - 40, y_position)
        y_position -= 12

        # Draw totals
        pdf.setFont("Helvetica-Bold", 8)
        x_pos = left_x + col_widths[0] + col_widths[1]

        # Skip MONTO-CUOTA column
        x_pos += col_widths[2]

        # CAPITAL total
        pdf.drawRightString(x_pos + col_widths[3], y_position, f"{float(total_capital):,.2f}")
        x_pos += col_widths[3]

        # INTERES total
        pdf.drawRightString(x_pos + col_widths[4], y_position, f"{float(total_interest):,.2f}")
        x_pos += col_widths[4]

        # MORA total
        pdf.drawRightString(x_pos + col_widths[5], y_position, f"{float(total_mora):,.2f}")
        x_pos += col_widths[5]

        # OTROS total
        pdf.drawRightString(x_pos + col_widths[6], y_position, f"{float(total_otros):,.2f}")
        x_pos += col_widths[6]

        # SALDO/CUOTA total
        total_balance_cuotas = float(total_capital) + float(total_interest)
        pdf.drawRightString(x_pos + col_widths[7], y_position, f"{total_balance_cuotas:,.2f}")

        # Draw footer on last page
        self._draw_footer(pdf, width)

        # Save PDF
        pdf.save()

        # Get the value of the BytesIO buffer and return it
        pdf_data = self.buffer.getvalue()
        self.buffer.close()
        return pdf_data

    def _get_interest_per_period(self):
        """Calculate interest rate per period"""
        if self.loan.interest_type == 'fixed':
            # For fixed, total interest divided by periods
            return f"{self.loan.interest_rate:.2f}"
        elif self.loan.interest_type == 'variable':
            # For variable, rate divided by periods per year
            if self.loan.payment_frequency == 'monthly':
                return f"{self.loan.interest_rate / 12:.2f}"
            elif self.loan.payment_frequency == 'weekly':
                return f"{self.loan.interest_rate / 52:.2f}"
            elif self.loan.payment_frequency == 'biweekly':
                return f"{self.loan.interest_rate / 26:.2f}"
            elif self.loan.payment_frequency == 'daily':
                return f"{self.loan.interest_rate / 365:.2f}"
            elif self.loan.payment_frequency == 'quarterly':
                return f"{self.loan.interest_rate / 4:.2f}"
        elif self.loan.interest_type == 'variable_rd':
            # For Variable RD, it's the direct rate per period
            return f"{self.loan.interest_rate:.2f}"

        return f"{self.loan.interest_rate:.2f}"

    def _get_period_description(self):
        """Get human-readable period description"""
        num_payments = self.loan.term_months
        frequency = self.loan.payment_frequency

        if frequency == 'monthly':
            return f"{num_payments} Meses"
        elif frequency == 'biweekly':
            return f"{num_payments} Quincenas"
        elif frequency == 'weekly':
            return f"{num_payments} Semanas"
        elif frequency == 'daily':
            return f"{num_payments} Días"
        elif frequency == 'quarterly':
            return f"{num_payments} Trimestres"

        return f"{num_payments} Períodos"

    def _calculate_total_balance(self):
        """Calculate total balance (sum of all payment amounts including outstanding)"""
        schedules = self.loan.payment_schedules.all()
        total = sum(float(s.balance.amount) if s.balance else float(s.total_amount.amount) for s in schedules)
        return total
