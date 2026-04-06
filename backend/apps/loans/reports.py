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

from .models import Loan, LoanPayment, Customer


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


class PaymentReceiptReport:
    """
    Generates a professional payment receipt (Recibo de Pago) PDF in portrait format.
    """

    PAYMENT_METHOD_LABELS = {
        'cash': 'Efectivo',
        'check': 'Cheque',
        'bank_transfer': 'Transferencia',
        'card': 'Tarjeta',
        'mobile_payment': 'Pago Móvil',
    }

    def __init__(self, payment: LoanPayment):
        self.payment = payment
        self.buffer = BytesIO()

    def _format_cedula(self, cedula: str) -> str:
        """Format cedula with dashes (XXX-XXXXXXX-X)"""
        if not cedula:
            return ''
        clean = cedula.replace('-', '').replace(' ', '')
        if len(clean) == 11:
            return f"{clean[:3]}-{clean[3:10]}-{clean[10]}"
        return cedula

    def _fmt_money(self, value) -> str:
        """Format a Decimal/Money value as RD$ X,XXX.XX"""
        try:
            amount = float(value.amount) if hasattr(value, 'amount') else float(value)
        except (AttributeError, TypeError, ValueError):
            amount = 0.0
        return f"RD$ {amount:,.2f}"

    def _draw_footer(self, pdf, width):
        """Draw footer on current page"""
        pdf.saveState()
        pdf.setFont("Helvetica", 7)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_text = f"Generado por CrediFlux — {now_str}"
        pdf.drawCentredString(width / 2, 20, footer_text)
        pdf.restoreState()

    def generate(self):
        """Generate a Stripe-inspired financial receipt PDF and return bytes."""
        pdf = canvas.Canvas(self.buffer, pagesize=letter)
        width, height = letter

        payment = self.payment
        loan = payment.loan
        customer = loan.customer
        schedule = payment.schedule
        tenant = connection.tenant

        primary = colors.HexColor('#163300')
        accent = colors.HexColor('#FFE026')
        border = colors.HexColor('#E5E7EB')
        soft_bg = colors.HexColor('#F8FAFC')
        panel_bg = colors.HexColor('#F8FAF8')
        text_dark = colors.HexColor('#0F172A')
        text_muted = colors.HexColor('#64748B')
        success = colors.HexColor('#166534')

        left = 40
        right = width - 40
        usable_width = right - left
        top = height - 44

        tenant_name = getattr(tenant, 'business_name', None) or 'CrediFlux'
        tenant_address = getattr(tenant, 'address', None) or ''
        tenant_tax_id = getattr(tenant, 'tax_id', None) or ''
        tenant_phone = getattr(tenant, 'phone', None) or ''
        tenant_email = getattr(tenant, 'email', None) or ''

        def draw_kv(x, y_pos, label, value, width_limit=None):
            pdf.setFillColor(text_muted)
            pdf.setFont('Helvetica', 7.5)
            pdf.drawString(x, y_pos, str(label).upper())
            pdf.setFillColor(text_dark)
            pdf.setFont('Helvetica-Bold', 10)
            text = str(value or '—')
            if width_limit and pdf.stringWidth(text, 'Helvetica-Bold', 10) > width_limit:
                while text and pdf.stringWidth(text + '…', 'Helvetica-Bold', 10) > width_limit:
                    text = text[:-1]
                text = text + '…'
            pdf.drawString(x, y_pos - 12, text)

        def draw_money_line(x, y_pos, label, value, strong=False, color=text_dark):
            pdf.setFillColor(text_muted if not strong else text_dark)
            pdf.setFont('Helvetica', 9)
            pdf.drawString(x, y_pos, label)
            pdf.setFillColor(color)
            pdf.setFont('Helvetica-Bold', 10 if not strong else 12)
            pdf.drawRightString(x + 210, y_pos, self._fmt_money(value))

        # Background card
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(border)
        pdf.roundRect(left, 54, usable_width, height - 100, 18, stroke=1, fill=1)

        # Header
        header_y = top
        brand_x = left + 18
        logo_drawn = False

        if tenant and hasattr(tenant, 'logo') and tenant.logo:
            try:
                logo_path = os.path.join(settings.MEDIA_ROOT, str(tenant.logo))
                if os.path.exists(logo_path):
                    pdf.drawImage(logo_path, brand_x, header_y - 42, width=70, height=42,
                                  preserveAspectRatio=True, mask='auto')
                    logo_drawn = True
            except Exception:
                logo_drawn = False

        if not logo_drawn:
            pdf.setFillColor(primary)
            pdf.roundRect(brand_x, header_y - 38, 42, 28, 8, stroke=0, fill=1)
            pdf.setFillColor(colors.white)
            pdf.setFont('Helvetica-Bold', 12)
            initials = ''.join([word[0] for word in tenant_name.split()[:2]]).upper() or 'CF'
            pdf.drawCentredString(brand_x + 21, header_y - 28, initials)

        text_x = brand_x + (86 if logo_drawn else 56)
        pdf.setFillColor(text_dark)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(text_x, header_y - 18, tenant_name)
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 9)
        meta_line = ' • '.join([item for item in [tenant_tax_id and f'RNC {tenant_tax_id}', tenant_phone, tenant_email] if item])
        if meta_line:
            pdf.drawString(text_x, header_y - 33, meta_line)
        if tenant_address:
            pdf.drawString(text_x, header_y - 46, tenant_address[:82])

        pdf.setFillColor(text_dark)
        pdf.setFont('Helvetica-Bold', 22)
        pdf.drawRightString(right - 18, header_y - 18, 'Recibo de pago')
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 9)
        pdf.drawRightString(right - 18, header_y - 33, f'Recibo {payment.payment_number}')
        pdf.drawRightString(right - 18, header_y - 46, f'Emitido {payment.payment_date.strftime("%d/%m/%Y") if payment.payment_date else "N/A"}')

        pdf.setFillColor(accent)
        pdf.rect(left + 18, header_y - 62, usable_width - 36, 3, stroke=0, fill=1)

        # Amount hero
        hero_y = header_y - 104
        pdf.setFillColor(soft_bg)
        pdf.setStrokeColor(border)
        pdf.roundRect(left + 18, hero_y - 82, usable_width - 36, 82, 14, stroke=1, fill=1)
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 9)
        pdf.drawString(left + 34, hero_y - 22, 'MONTO RECIBIDO')
        pdf.setFillColor(primary)
        pdf.setFont('Helvetica-Bold', 28)
        pdf.drawString(left + 34, hero_y - 50, self._fmt_money(payment.amount))
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 9)
        pdf.drawRightString(right - 34, hero_y - 22, f'Préstamo {loan.loan_number}')
        pdf.drawRightString(right - 34, hero_y - 36, f'Estado {loan.get_status_display()}')
        pdf.drawRightString(right - 34, hero_y - 50, f'Cliente {customer.get_full_name()}')

        # Info panels
        section_top = hero_y - 112
        gutter = 14
        col_w = (usable_width - 36 - gutter) / 2
        left_x = left + 18
        right_x = left_x + col_w + gutter

        # Left panel - who/what
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(border)
        pdf.roundRect(left_x, section_top - 160, col_w, 160, 14, stroke=1, fill=1)
        pdf.setFillColor(text_dark)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(left_x + 16, section_top - 20, 'Datos de la operación')
        pdf.setStrokeColor(border)
        pdf.line(left_x + 16, section_top - 28, left_x + col_w - 16, section_top - 28)

        row_y = section_top - 46
        draw_kv(left_x + 16, row_y, 'Cliente', customer.get_full_name().upper(), width_limit=160)
        draw_kv(left_x + 210, row_y, 'Cédula', self._format_cedula(customer.id_number or ''), width_limit=120)
        row_y -= 34
        draw_kv(left_x + 16, row_y, 'Método de pago', self.PAYMENT_METHOD_LABELS.get(payment.payment_method, payment.payment_method or ''), width_limit=140)
        draw_kv(left_x + 210, row_y, 'Fecha', payment.payment_date.strftime('%d/%m/%Y') if payment.payment_date else 'N/A', width_limit=120)
        row_y -= 34
        draw_kv(left_x + 16, row_y, 'Referencia', payment.reference_number or 'N/A', width_limit=160)
        cuota_val = f'{schedule.installment_number} de {loan.payment_schedules.count()}' if schedule else 'Aplicación general'
        draw_kv(left_x + 210, row_y, 'Cuota', cuota_val, width_limit=120)
        row_y -= 34
        draw_kv(left_x + 16, row_y, 'Notas', payment.notes or 'Sin notas registradas', width_limit=col_w - 32)

        # Right panel - payment breakdown
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(border)
        pdf.roundRect(right_x, section_top - 160, col_w, 160, 14, stroke=1, fill=1)
        pdf.setFillColor(text_dark)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(right_x + 16, section_top - 20, 'Desglose del pago')
        pdf.setStrokeColor(border)
        pdf.line(right_x + 16, section_top - 28, right_x + col_w - 16, section_top - 28)

        pay_y = section_top - 54
        draw_money_line(right_x + 16, pay_y, 'Capital pagado', payment.principal_paid)
        pay_y -= 22
        draw_money_line(right_x + 16, pay_y, 'Interés pagado', payment.interest_paid)
        pay_y -= 22
        draw_money_line(right_x + 16, pay_y, 'Mora pagada', payment.late_fee_paid)
        pay_y -= 14
        pdf.setStrokeColor(border)
        pdf.line(right_x + 16, pay_y, right_x + col_w - 16, pay_y)
        pay_y -= 18
        draw_money_line(right_x + 16, pay_y, 'Total recibido', payment.amount, strong=True, color=primary)

        # Balance/result panel
        result_y = section_top - 188
        pdf.setFillColor(panel_bg)
        pdf.setStrokeColor(border)
        pdf.roundRect(left + 18, result_y - 92, usable_width - 36, 92, 14, stroke=1, fill=1)
        pdf.setFillColor(text_dark)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(left + 34, result_y - 20, 'Resultado del pago')
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 9)
        pdf.drawString(left + 34, result_y - 38, 'Solo la porción aplicada a capital reduce el balance del préstamo. Interés y mora se registran aparte.')

        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 8)
        pdf.drawString(left + 34, result_y - 62, 'BALANCE PENDIENTE DESPUÉS DE ESTE PAGO')
        pdf.setFillColor(success if float(getattr(loan.outstanding_balance, 'amount', loan.outstanding_balance)) <= 0 else text_dark)
        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(left + 34, result_y - 80, self._fmt_money(loan.outstanding_balance))

        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 8)
        pdf.drawRightString(right - 34, result_y - 62, f'Total abonado acumulado: {self._fmt_money(loan.total_paid)}')
        pdf.drawRightString(right - 34, result_y - 76, f'Interés acumulado pagado: {self._fmt_money(loan.total_interest_paid)}')

        # Footer signatures
        sig_y = 108
        line_len = 145
        pdf.setStrokeColor(colors.HexColor('#CBD5E1'))
        pdf.line(left + 26, sig_y, left + 26 + line_len, sig_y)
        pdf.line(right - 26 - line_len, sig_y, right - 26, sig_y)
        pdf.setFillColor(text_muted)
        pdf.setFont('Helvetica', 8)
        pdf.drawCentredString(left + 26 + line_len / 2, sig_y - 12, 'Firma del cliente')
        pdf.drawCentredString(right - 26 - line_len / 2, sig_y - 12, 'Caja / oficial')

        self._draw_footer(pdf, width)
        pdf.save()
        pdf_data = self.buffer.getvalue()
        self.buffer.close()
        return pdf_data


class CustomerStatementReport:
    """
    Generates an Estado de Cuenta (Customer Statement) PDF in portrait letter format.
    Shows all active loans and their payment schedules for a customer.
    """

    # Column widths for the schedule table (portrait, usable width ~532pt)
    COL_WIDTHS = [42, 62, 62, 62, 62, 52, 62, 64]  # sum = 468 (leaves room for margins)
    COL_HEADERS = ["CUOTA#", "FECHA", "MONTO", "CAPITAL", "INTERÉS", "MORA", "PAGADO", "BALANCE"]

    def __init__(self, customer: Customer):
        self.customer = customer
        self.buffer = BytesIO()

    def _fmt_money(self, value) -> str:
        """Format a Decimal/Money value as RD$ X,XXX.XX"""
        try:
            amount = float(value.amount) if hasattr(value, 'amount') else float(value)
        except (AttributeError, TypeError, ValueError):
            amount = 0.0
        return f"RD$ {amount:,.2f}"

    def _fmt_num(self, value) -> str:
        """Format a number as X,XXX.XX (no currency prefix)"""
        try:
            amount = float(value.amount) if hasattr(value, 'amount') else float(value)
        except (AttributeError, TypeError, ValueError):
            amount = 0.0
        return f"{amount:,.2f}"

    def _format_cedula(self, cedula: str) -> str:
        if not cedula:
            return ''
        clean = cedula.replace('-', '').replace(' ', '')
        if len(clean) == 11:
            return f"{clean[:3]}-{clean[3:10]}-{clean[10]}"
        return cedula

    def _draw_footer(self, pdf, width):
        pdf.saveState()
        pdf.setFont("Helvetica", 7)
        pdf.setFillColorRGB(0.5, 0.5, 0.5)
        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        footer_text = f"Generado por CrediFlux — {now_str}"
        pdf.drawCentredString(width / 2, 20, footer_text)
        pdf.restoreState()

    def _check_page(self, pdf, y, width, height, min_y=80):
        """Start a new page if y is below min_y. Returns new y."""
        if y < min_y:
            self._draw_footer(pdf, width)
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            return height - 40
        return y

    def generate(self):
        """Generate the customer statement PDF and return bytes."""
        pdf = canvas.Canvas(self.buffer, pagesize=letter)
        width, height = letter  # 612 x 792

        left = 40
        right = width - 40
        y = height - 40

        tenant = connection.tenant
        customer = self.customer

        # --- Logo ---
        logo_height = 0
        if tenant and hasattr(tenant, 'logo') and tenant.logo:
            try:
                logo_path = os.path.join(settings.MEDIA_ROOT, str(tenant.logo))
                if os.path.exists(logo_path):
                    logo_width = 70
                    logo_height = 45
                    pdf.drawImage(logo_path, left, y - logo_height,
                                  width=logo_width, height=logo_height,
                                  preserveAspectRatio=True, mask='auto')
            except Exception as e:
                print(f"Warning: Could not load tenant logo: {e}")
                logo_height = 0

        # --- Tenant header ---
        header_x = left + (80 if logo_height > 0 else 0)
        business_name = getattr(tenant, 'business_name', '') if tenant else ''
        tenant_address = getattr(tenant, 'address', '') if tenant else ''
        tax_id = getattr(tenant, 'tax_id', '') if tenant else ''

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(header_x, y - 10, business_name.upper())
        pdf.setFont("Helvetica", 8)
        if tenant_address:
            pdf.drawString(header_x, y - 22, tenant_address)
        if tax_id:
            pdf.drawString(header_x, y - 33, f"RNC: {tax_id}")

        # Date top-right
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(right, y - 10, datetime.now().strftime('%d/%m/%Y'))

        y -= max(logo_height + 10, 50)

        # --- Title ---
        pdf.setFont("Helvetica-Bold", 15)
        title = "ESTADO DE CUENTA"
        pdf.drawCentredString(width / 2, y, title)
        y -= 6

        # Underline title
        pdf.setLineWidth(1.5)
        title_w = pdf.stringWidth(title, "Helvetica-Bold", 15)
        pdf.line((width - title_w) / 2, y, (width + title_w) / 2, y)
        y -= 16

        # --- Customer section ---
        pdf.setLineWidth(0.5)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left, y, "DATOS DEL CLIENTE")
        y -= 12

        label_w = 85
        pdf.setFont("Helvetica", 9)

        def draw_kv(label, value):
            nonlocal y
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(left, y, label)
            pdf.setFont("Helvetica", 9)
            pdf.drawString(left + label_w, y, f": {value}")
            y -= 12

        draw_kv("Cliente", customer.get_full_name().upper())
        draw_kv("Cédula", self._format_cedula(customer.id_number))
        draw_kv("Teléfono", str(customer.phone or ''))
        cust_address = customer.address_line1 or ''
        if customer.city:
            cust_address += f", {customer.city}"
        draw_kv("Dirección", cust_address)
        if customer.email:
            draw_kv("Email", customer.email)

        y -= 5
        pdf.line(left, y, right, y)
        y -= 14

        # --- Loans ---
        active_loans = customer.loans.filter(
            status__in=['active', 'approved', 'disbursed']
        ).order_by('created_at')

        # Summary accumulators
        total_cartera = Decimal('0.00')
        total_pagado = Decimal('0.00')
        total_pendiente = Decimal('0.00')
        total_mora = Decimal('0.00')

        for loan in active_loans:
            y = self._check_page(pdf, y, width, height, min_y=120)

            # --- Loan header ---
            pdf.setFont("Helvetica-Bold", 9)
            loan_type = loan.get_loan_type_display() if hasattr(loan, 'get_loan_type_display') else loan.loan_type
            disbursed = loan.disbursement_date.strftime('%d/%m/%Y') if loan.disbursement_date else 'N/D'
            pdf.drawString(left, y,
                f"Préstamo: {loan.loan_number}  |  Tipo: {loan_type}  |  Estado: {loan.get_status_display()}  |  Desembolso: {disbursed}")
            y -= 11
            pdf.setFont("Helvetica", 9)
            pdf.drawString(left, y,
                f"Principal: {self._fmt_money(loan.principal_amount)}  |  "
                f"Tasa: {loan.interest_rate}%  |  "
                f"Balance pendiente: {self._fmt_money(loan.outstanding_balance)}")
            y -= 8
            pdf.setLineWidth(0.3)
            pdf.line(left, y, right, y)
            y -= 11

            # --- Column headers ---
            pdf.setFont("Helvetica-Bold", 7.5)
            x = left
            for i, header in enumerate(self.COL_HEADERS):
                if i == 0:
                    pdf.drawString(x, y, header)
                elif i == 1:
                    pdf.drawString(x, y, header)
                else:
                    pdf.drawRightString(x + self.COL_WIDTHS[i], y, header)
                x += self.COL_WIDTHS[i]

            y -= 10
            pdf.setLineWidth(0.5)
            pdf.line(left, y, right, y)
            y -= 10

            # --- Schedule rows ---
            schedules = loan.payment_schedules.all().order_by('installment_number')
            total_count = schedules.count()

            sub_capital = Decimal('0.00')
            sub_interest = Decimal('0.00')
            sub_mora = Decimal('0.00')
            sub_pagado = Decimal('0.00')

            today = datetime.now().date()

            for sched in schedules:
                y = self._check_page(pdf, y, width, height)

                is_overdue = (
                    sched.status in ('pending', 'overdue', 'partial') and
                    sched.due_date < today
                )

                if is_overdue:
                    pdf.setFillColorRGB(0.75, 0.1, 0.1)  # Red for overdue
                else:
                    pdf.setFillColorRGB(0, 0, 0)

                pdf.setFont("Helvetica", 7.5)

                capital = sched.principal_amount.amount
                interest = sched.interest_amount.amount
                mora = sched.late_fee_amount.amount if sched.late_fee_amount else Decimal('0.00')
                pagado = sched.paid_amount.amount if sched.paid_amount else Decimal('0.00')
                balance = sched.balance.amount if sched.balance else sched.total_amount.amount

                sub_capital += capital
                sub_interest += interest
                sub_mora += mora
                sub_pagado += pagado

                x = left
                cuota_label = f"{sched.installment_number}/{total_count}"
                fecha_label = sched.due_date.strftime('%d/%m/%Y')

                pdf.drawString(x, y, cuota_label)
                x += self.COL_WIDTHS[0]
                pdf.drawString(x, y, fecha_label)
                x += self.COL_WIDTHS[1]
                pdf.drawRightString(x + self.COL_WIDTHS[2], y, self._fmt_num(sched.total_amount))
                x += self.COL_WIDTHS[2]
                pdf.drawRightString(x + self.COL_WIDTHS[3], y, self._fmt_num(capital))
                x += self.COL_WIDTHS[3]
                pdf.drawRightString(x + self.COL_WIDTHS[4], y, self._fmt_num(interest))
                x += self.COL_WIDTHS[4]
                pdf.drawRightString(x + self.COL_WIDTHS[5], y, self._fmt_num(mora))
                x += self.COL_WIDTHS[5]
                pdf.drawRightString(x + self.COL_WIDTHS[6], y, self._fmt_num(pagado))
                x += self.COL_WIDTHS[6]
                pdf.drawRightString(x + self.COL_WIDTHS[7], y, self._fmt_num(balance))

                y -= 10

            # Reset color
            pdf.setFillColorRGB(0, 0, 0)

            # --- Loan sub-totals ---
            y = self._check_page(pdf, y, width, height)
            pdf.setLineWidth(0.3)
            pdf.line(left + self.COL_WIDTHS[0] + self.COL_WIDTHS[1], y, right, y)
            y -= 10

            pdf.setFont("Helvetica-Bold", 7.5)
            x = left + self.COL_WIDTHS[0] + self.COL_WIDTHS[1]
            pdf.drawRightString(x + self.COL_WIDTHS[2], y, "Sub-totales:")
            x += self.COL_WIDTHS[2]
            pdf.drawRightString(x + self.COL_WIDTHS[3], y, self._fmt_num(sub_capital))
            x += self.COL_WIDTHS[3]
            pdf.drawRightString(x + self.COL_WIDTHS[4], y, self._fmt_num(sub_interest))
            x += self.COL_WIDTHS[4]
            pdf.drawRightString(x + self.COL_WIDTHS[5], y, self._fmt_num(sub_mora))
            x += self.COL_WIDTHS[5]
            pdf.drawRightString(x + self.COL_WIDTHS[6], y, self._fmt_num(sub_pagado))

            y -= 16

            # Accumulate global totals
            total_cartera += loan.principal_amount.amount
            total_pagado += sub_pagado
            total_pendiente += loan.outstanding_balance.amount
            total_mora += sub_mora

        # --- Summary block ---
        y = self._check_page(pdf, y, width, height, min_y=120)
        pdf.setLineWidth(1)
        pdf.line(left, y, right, y)
        y -= 14

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(left, y, "RESUMEN GENERAL")
        y -= 12

        sum_label_w = 150
        pdf.setFont("Helvetica", 9)

        def draw_summary(label, value_str):
            nonlocal y
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(left, y, label)
            pdf.setFont("Helvetica", 9)
            pdf.drawRightString(left + sum_label_w + 120, y, value_str)
            y -= 12

        draw_summary("Total cartera activa:", f"RD$ {float(total_cartera):,.2f}")
        draw_summary("Total pagado:", f"RD$ {float(total_pagado):,.2f}")
        draw_summary("Total pendiente:", f"RD$ {float(total_pendiente):,.2f}")
        draw_summary("Total mora:", f"RD$ {float(total_mora):,.2f}")

        # --- Footer ---
        self._draw_footer(pdf, width)
        pdf.save()

        pdf_data = self.buffer.getvalue()
        self.buffer.close()
        return pdf_data
