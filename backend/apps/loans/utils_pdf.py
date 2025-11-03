"""
Utility functions for generating contract PDFs
"""
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def generate_contract_pdf(contract):
    """
    Generate a PDF file for a contract.

    Args:
        contract: Contract model instance

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
        topMargin=72,
        bottomMargin=18,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

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

    # Add contract header
    title = Paragraph(
        f"<b>{contract.contract_number}</b>",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Add metadata
    if contract.loan:
        metadata_items = [
            f"<b>Préstamo:</b> {contract.loan.loan_number}",
            f"<b>Cliente:</b> {contract.loan.customer.get_full_name()}",
            f"<b>Monto:</b> ${contract.loan.principal_amount.amount:,.2f}",
            f"<b>Fecha de generación:</b> {contract.generated_at.strftime('%d de %B de %Y')}",
        ]

        for item in metadata_items:
            elements.append(Paragraph(item, metadata_style))

        elements.append(Spacer(1, 20))

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
