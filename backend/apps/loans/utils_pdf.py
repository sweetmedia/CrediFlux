"""
Utility functions for generating contract PDFs
"""
from io import BytesIO
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings


def generate_contract_pdf(contract, tenant=None):
    """
    Generate a PDF file for a contract with company letterhead.

    Args:
        contract: Contract model instance
        tenant: Tenant model instance (optional, for letterhead)

    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()

    # Create the PDF object using the BytesIO object as its "file"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=40,  # Reduced for letterhead at top
        bottomMargin=18,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom style for letterhead company name
    letterhead_company_style = ParagraphStyle(
        'LetterheadCompany',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#1e40af',
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )

    # Custom style for letterhead info
    letterhead_info_style = ParagraphStyle(
        'LetterheadInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor='#475569',
        spaceAfter=2,
        alignment=TA_CENTER,
    )

    # Custom style for contract title
    title_style = ParagraphStyle(
        'ContractTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#1e40af',
        spaceAfter=30,
        alignment=TA_CENTER,
    )

    # Custom style for contract body
    body_style = ParagraphStyle(
        'ContractBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )

    # Custom style for metadata
    metadata_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#64748b',
        spaceAfter=6,
    )

    # Add company letterhead
    if tenant:
        # Try to add logo if exists
        if tenant.logo:
            try:
                # Get the logo path
                logo_path = os.path.join(settings.MEDIA_ROOT, str(tenant.logo))
                if os.path.exists(logo_path):
                    # Add logo centered with smaller size
                    logo = Image(logo_path, width=1.2*inch, height=1.2*inch, kind='proportional')
                    logo.hAlign = 'CENTER'
                    elements.append(logo)
                    elements.append(Spacer(1, 6))
            except Exception as e:
                # If logo fails to load, continue without it
                print(f"Error loading logo: {e}")

        # Company name
        if tenant.business_name:
            elements.append(Paragraph(
                f"<b>{tenant.business_name}</b>",
                letterhead_company_style
            ))

        # Tax ID
        if tenant.tax_id:
            elements.append(Paragraph(
                f"RNC: {tenant.tax_id}",
                letterhead_info_style
            ))

        # Address
        address_parts = []
        if tenant.address:
            address_parts.append(tenant.address)
        if tenant.city:
            address_parts.append(tenant.city)
        if tenant.state:
            address_parts.append(tenant.state)
        if tenant.country:
            address_parts.append(tenant.country)

        if address_parts:
            elements.append(Paragraph(
                ", ".join(address_parts),
                letterhead_info_style
            ))

        # Contact info
        contact_parts = []
        if tenant.phone:
            contact_parts.append(f"Tel: {tenant.phone}")
        if tenant.email:
            contact_parts.append(f"Email: {tenant.email}")

        if contact_parts:
            elements.append(Paragraph(
                " | ".join(contact_parts),
                letterhead_info_style
            ))

        elements.append(Spacer(1, 12))

        # Separator line
        from reportlab.platypus import HRFlowable
        elements.append(HRFlowable(width="100%", thickness=2, color='#1e40af', spaceAfter=15))

    # Add contract header
    title = Paragraph(
        f"<b>{contract.contract_number}</b>",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Add metadata in 2 columns using a table
    if contract.loan:
        # Prepare metadata data for table
        metadata_data = [
            [
                Paragraph(f"<b>Préstamo:</b> {contract.loan.loan_number}", metadata_style),
                Paragraph(f"<b>Monto:</b> ${contract.loan.principal_amount.amount:,.2f}", metadata_style),
            ],
            [
                Paragraph(f"<b>Cliente:</b> {contract.loan.customer.get_full_name()}", metadata_style),
                Paragraph(f"<b>Fecha:</b> {contract.generated_at.strftime('%d de %B de %Y')}", metadata_style),
            ],
        ]

        # Create table with 2 columns
        metadata_table = Table(metadata_data, colWidths=[3.25*inch, 3.25*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(metadata_table)
        elements.append(Spacer(1, 15))

    # Add horizontal line
    from reportlab.platypus import HRFlowable
    elements.append(HRFlowable(width="100%", thickness=1, color='#cbd5e1', spaceAfter=20))

    # Add contract content
    if contract.content:
        # Split content by paragraphs (double newlines)
        paragraphs = contract.content.split('\n\n')

        for para in paragraphs:
            if para.strip():
                # Replace single newlines with <br/> for proper formatting
                formatted_para = para.strip().replace('\n', '<br/>')
                p = Paragraph(formatted_para, body_style)
                elements.append(p)
    else:
        elements.append(Paragraph(
            "<i>Este contrato no tiene contenido generado.</i>",
            body_style
        ))

    # Add footer spacer
    elements.append(Spacer(1, 40))

    # Add signatures section if signed
    if contract.customer_signed_at or contract.officer_signed_at:
        elements.append(HRFlowable(width="100%", thickness=1, color='#cbd5e1', spaceAfter=20))
        elements.append(Paragraph("<b>Firmas</b>", title_style))
        elements.append(Spacer(1, 12))

        if contract.customer_signed_at:
            elements.append(Paragraph(
                f"<b>Cliente:</b> Firmado el {contract.customer_signed_at.strftime('%d de %B de %Y a las %H:%M')}",
                metadata_style
            ))

        if contract.officer_signed_at:
            elements.append(Paragraph(
                f"<b>Oficial de crédito:</b> Firmado el {contract.officer_signed_at.strftime('%d de %B de %Y a las %H:%M')}",
                metadata_style
            ))

    # Build PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer and return it
    buffer.seek(0)
    return buffer
