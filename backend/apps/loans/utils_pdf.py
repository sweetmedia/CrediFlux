"""
Utility functions for generating contract PDFs.
"""
from io import BytesIO
import os
from decimal import Decimal

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND_GREEN = colors.HexColor("#163300")
BRAND_SAGE = colors.HexColor("#738566")
BRAND_GOLD = colors.HexColor("#FFE026")
TEXT_DARK = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#6B7280")
BORDER = colors.HexColor("#D1D5DB")
PAPER = colors.HexColor("#FCFBF8")


def _money_str(value, symbol="RD$"):
    if value is None:
        return "N/A"
    if hasattr(value, "amount"):
        value = value.amount
    return f"{symbol} {Decimal(str(value)):,.2f}"


def _format_long_date(dt):
    if not dt:
        return "N/A"
    return dt.strftime("%d/%m/%Y")


def generate_contract_pdf(contract, tenant=None):
    """Generate a contract PDF with a more formal legal-document layout."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=56,
        leftMargin=56,
        topMargin=42,
        bottomMargin=36,
        title=contract.contract_number,
        author=(tenant.business_name if tenant and tenant.business_name else "CrediFlux"),
        subject="Contrato legal",
    )

    elements = []
    styles = getSampleStyleSheet()

    company_style = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=BRAND_GREEN,
        alignment=TA_CENTER,
        spaceAfter=4,
    )

    legal_kicker_style = ParagraphStyle(
        "LegalKicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
        spaceAfter=3,
    )

    header_info_style = ParagraphStyle(
        "HeaderInfo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=11,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
        spaceAfter=2,
    )

    contract_title_style = ParagraphStyle(
        "ContractTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=TEXT_DARK,
        alignment=TA_CENTER,
        spaceAfter=5,
    )

    contract_subtitle_style = ParagraphStyle(
        "ContractSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
        spaceAfter=10,
    )

    metadata_label_style = ParagraphStyle(
        "MetadataLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=TEXT_MUTED,
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    metadata_value_style = ParagraphStyle(
        "MetadataValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
    )

    body_style = ParagraphStyle(
        "ContractBody",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=11,
        leading=18,
        alignment=TA_JUSTIFY,
        textColor=TEXT_DARK,
        firstLineIndent=16,
        spaceAfter=11,
    )

    signature_title_style = ParagraphStyle(
        "SignatureTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
        spaceAfter=10,
    )

    signature_meta_style = ParagraphStyle(
        "SignatureMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=TEXT_MUTED,
        alignment=TA_LEFT,
    )

    company_name = tenant.business_name if tenant and tenant.business_name else (tenant.name if tenant else "CrediFlux")
    currency_symbol = getattr(tenant, "currency_symbol", "RD$") if tenant else "RD$"

    # Header / letterhead
    if tenant and getattr(tenant, "logo", None):
        try:
            logo_path = os.path.join(settings.MEDIA_ROOT, str(tenant.logo))
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=1.0 * inch, height=1.0 * inch, kind="proportional")
                logo.hAlign = "CENTER"
                elements.append(logo)
                elements.append(Spacer(1, 6))
        except Exception as e:
            print(f"Error loading logo: {e}")

    elements.append(Paragraph(company_name, company_style))
    elements.append(Paragraph("DOCUMENTO LEGAL CONTRACTUAL", legal_kicker_style))

    if tenant:
        if getattr(tenant, "tax_id", None):
            elements.append(Paragraph(f"RNC: {tenant.tax_id}", header_info_style))

        address_parts = [
            part for part in [
                getattr(tenant, "address", None),
                getattr(tenant, "city", None),
                getattr(tenant, "state", None),
                getattr(tenant, "country", None),
            ] if part
        ]
        if address_parts:
            elements.append(Paragraph(", ".join(address_parts), header_info_style))

        contact_parts = []
        if getattr(tenant, "phone", None):
            contact_parts.append(f"Tel: {tenant.phone}")
        if getattr(tenant, "email", None):
            contact_parts.append(f"Email: {tenant.email}")
        if contact_parts:
            elements.append(Paragraph(" | ".join(contact_parts), header_info_style))

    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.3, color=BRAND_GREEN, lineCap="round", spaceAfter=14))

    # Title block
    elements.append(Paragraph(contract.contract_number, contract_title_style))
    elements.append(Paragraph("Contrato vinculado al expediente de préstamo", contract_subtitle_style))

    if contract.loan:
        metadata_rows = [
            [
                Paragraph("EXPEDIENTE", metadata_label_style),
                Paragraph(contract.loan.loan_number, metadata_value_style),
                Paragraph("MONTO", metadata_label_style),
                Paragraph(_money_str(contract.loan.principal_amount, currency_symbol), metadata_value_style),
            ],
            [
                Paragraph("CLIENTE", metadata_label_style),
                Paragraph(contract.loan.customer.get_full_name(), metadata_value_style),
                Paragraph("FECHA", metadata_label_style),
                Paragraph(_format_long_date(contract.generated_at), metadata_value_style),
            ],
        ]

        metadata_table = Table(metadata_rows, colWidths=[1.1 * inch, 2.2 * inch, 1.0 * inch, 2.0 * inch])
        metadata_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAPER),
            ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(metadata_table)
        elements.append(Spacer(1, 18))

    elements.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceAfter=18))

    # Body
    if contract.content:
        paragraphs = contract.content.split("\n\n")
        for para in paragraphs:
            if para.strip():
                formatted_para = para.strip().replace("\n", "<br/>")
                elements.append(Paragraph(formatted_para, body_style))
    else:
        elements.append(Paragraph("<i>Este contrato no tiene contenido generado.</i>", body_style))

    elements.append(Spacer(1, 22))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceAfter=14))

    # Signatures block
    elements.append(Paragraph("FIRMAS Y VALIDACIÓN", signature_title_style))

    signature_rows = [
        [
            Paragraph("Cliente / Deudor", metadata_label_style),
            Paragraph("Oficial de crédito", metadata_label_style),
        ],
        [
            Paragraph("<br/><br/>_______________________________", metadata_value_style),
            Paragraph("<br/><br/>_______________________________", metadata_value_style),
        ],
        [
            Paragraph(contract.loan.customer.get_full_name() if contract.loan else "Pendiente", signature_meta_style),
            Paragraph(contract.loan.loan_officer.get_full_name() if contract.loan and contract.loan.loan_officer else "Pendiente", signature_meta_style),
        ],
        [
            Paragraph(
                f"Firmado: {_format_long_date(contract.customer_signed_at)}" if contract.customer_signed_at else "Firma pendiente",
                signature_meta_style,
            ),
            Paragraph(
                f"Firmado: {_format_long_date(contract.officer_signed_at)}" if contract.officer_signed_at else "Firma pendiente",
                signature_meta_style,
            ),
        ],
    ]

    signature_table = Table(signature_rows, colWidths=[3.15 * inch, 3.15 * inch])
    signature_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(signature_table)

    elements.append(Spacer(1, 14))
    elements.append(Paragraph(
        "Este documento forma parte del expediente legal del préstamo y debe conservarse conforme a las políticas internas y regulatorias aplicables.",
        ParagraphStyle(
            "FooterNote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=TEXT_MUTED,
            alignment=TA_CENTER,
        ),
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
