"""
Utility functions for contract template processing
"""
from decimal import Decimal
from django.utils import timezone
import re


def get_spanish_month_name(month_number):
    """
    Get Spanish month name from month number (1-12).
    """
    spanish_months = {
        1: 'enero',
        2: 'febrero',
        3: 'marzo',
        4: 'abril',
        5: 'mayo',
        6: 'junio',
        7: 'julio',
        8: 'agosto',
        9: 'septiembre',
        10: 'octubre',
        11: 'noviembre',
        12: 'diciembre'
    }
    return spanish_months.get(month_number, str(month_number))


def number_to_words_es(number):
    """
    Convert a number to words in Spanish (Dominican Republic format).
    For now, returns a simple format. Can be expanded for full word conversion.
    """
    # Simplified version - in production, you might want to use num2words library
    # Example: 50000.00 -> "CINCUENTA MIL PESOS CON 00/100"

    try:
        number = Decimal(str(number))
        integer_part = int(number)
        decimal_part = int((number - integer_part) * 100)

        # For now, return a formatted string
        # TODO: Implement full Spanish word conversion
        return f"{integer_part:,} PESOS CON {decimal_part:02d}/100".replace(',', ' ')
    except:
        return str(number)


def replace_contract_variables(template_content, loan, tenant=None):
    """
    Replace template variables with actual loan/customer data.

    Available variables:
    - {{customer_name}}: Full name of customer
    - {{customer_id}}: Customer ID number
    - {{customer_id_number}}: Customer cedula/ID
    - {{customer_address}}: Full customer address
    - {{customer_phone}}: Customer phone number
    - {{customer_email}}: Customer email
    - {{loan_number}}: Loan number
    - {{loan_amount}}: Principal loan amount
    - {{loan_amount_words}}: Loan amount in words
    - {{interest_rate}}: Annual interest rate
    - {{loan_term}}: Loan term in months
    - {{payment_frequency}}: Payment frequency
    - {{monthly_payment}}: Monthly payment amount
    - {{total_amount}}: Total amount to be repaid
    - {{disbursement_date}}: Date loan was disbursed
    - {{first_payment_date}}: Date of first payment
    - {{final_payment_date}}: Date of final payment
    - {{loan_officer}}: Name of loan officer
    - {{company_name}}: Tenant company name
    - {{company_address}}: Tenant address
    - {{company_phone}}: Tenant phone
    - {{company_email}}: Tenant email
    - {{contract_date}}: Date contract was generated
    - {{año}}: Current year
    - {{mes}}: Current month (name)
    - {{dia}}: Current day
    - {{ciudad}}: Tenant city
    - {{municipio}}: Tenant municipality
    - {{provincia}}: Tenant province/state
    - {{pais}}: Tenant country
    - {{guarantor_name}}: Guarantor name (if applicable)
    - {{guarantor_id}}: Guarantor ID (if applicable)
    - {{collateral_description}}: Description of collaterals
    """

    customer = loan.customer
    content = template_content

    # Get current date
    now = timezone.now()

    # Customer variables
    replacements = {
        '{{customer_name}}': customer.get_full_name(),
        '{{customer_id}}': customer.customer_id,
        '{{customer_id_number}}': customer.id_number or 'N/A',
        '{{customer_address}}': f"{customer.address_line1 or ''}{', ' + customer.address_line2 if customer.address_line2 else ''}, {customer.city or ''}, {customer.state or ''}".strip(', '),
        '{{customer_phone}}': str(customer.phone) if customer.phone else 'N/A',
        '{{customer_email}}': customer.email or 'N/A',

        # Loan variables
        '{{loan_number}}': loan.loan_number,
        '{{loan_amount}}': f"${loan.principal_amount.amount:,.2f}",
        '{{loan_amount_words}}': number_to_words_es(loan.principal_amount.amount),
        '{{interest_rate}}': f"{loan.interest_rate}%",
        '{{loan_term}}': str(loan.term_months),
        '{{payment_frequency}}': loan.get_payment_frequency_display(),
        '{{monthly_payment}}': f"${loan.payment_amount.amount:,.2f}" if loan.payment_amount else 'N/A',
        '{{total_amount}}': f"${loan.outstanding_balance.amount:,.2f}" if loan.outstanding_balance else 'N/A',

        # Dates
        '{{disbursement_date}}': f"{loan.disbursement_date.day} de {get_spanish_month_name(loan.disbursement_date.month)} de {loan.disbursement_date.year}" if loan.disbursement_date else 'Pendiente',
        '{{first_payment_date}}': f"{loan.first_payment_date.day} de {get_spanish_month_name(loan.first_payment_date.month)} de {loan.first_payment_date.year}" if loan.first_payment_date else 'N/A',
        '{{final_payment_date}}': f"{loan.maturity_date.day} de {get_spanish_month_name(loan.maturity_date.month)} de {loan.maturity_date.year}" if loan.maturity_date else 'N/A',
        '{{contract_date}}': f"{now.day} de {get_spanish_month_name(now.month)} de {now.year}",

        # Date components
        '{{año}}': str(now.year),
        '{{mes}}': get_spanish_month_name(now.month),
        '{{dia}}': str(now.day),

        # Loan officer
        '{{loan_officer}}': loan.loan_officer.get_full_name() if loan.loan_officer else 'N/A',
    }

    # Tenant/Company variables
    if tenant:
        replacements.update({
            '{{company_name}}': tenant.business_name or tenant.name,
            '{{company_address}}': f"{tenant.address or ''}, {tenant.city or ''}, {tenant.state or ''}".strip(', '),
            '{{company_phone}}': str(tenant.phone) if tenant.phone else 'N/A',
            '{{company_email}}': tenant.email or 'N/A',
            '{{ciudad}}': tenant.city or 'N/A',
            '{{municipio}}': tenant.city or 'N/A',  # Using city as municipality
            '{{provincia}}': tenant.state or 'N/A',
            '{{pais}}': tenant.country or 'República Dominicana',
        })
    else:
        replacements.update({
            '{{company_name}}': 'N/A',
            '{{company_address}}': 'N/A',
            '{{company_phone}}': 'N/A',
            '{{company_email}}': 'N/A',
            '{{ciudad}}': 'N/A',
            '{{municipio}}': 'N/A',
            '{{provincia}}': 'N/A',
            '{{pais}}': 'N/A',
        })

    # Guarantor variables (if available)
    # TODO: Add guarantor model relationship
    replacements.update({
        '{{guarantor_name}}': 'N/A',
        '{{guarantor_id}}': 'N/A',
    })

    # Collateral variables
    collaterals = loan.collaterals.all()
    if collaterals.exists():
        collateral_desc = ', '.join([
            f"{c.get_collateral_type_display()}: {c.description} (${c.estimated_value.amount:,.2f})"
            for c in collaterals
        ])
        replacements['{{collateral_description}}'] = collateral_desc
    else:
        replacements['{{collateral_description}}'] = 'Sin garantías'

    # Replace all variables in content
    for variable, value in replacements.items():
        content = content.replace(variable, str(value))

    return content


def get_available_variables():
    """
    Return a list of all available variables with their descriptions.
    Useful for displaying help to users.
    """
    return [
        {'variable': '{{customer_name}}', 'description': 'Nombre completo del cliente'},
        {'variable': '{{customer_id}}', 'description': 'ID del cliente en el sistema'},
        {'variable': '{{customer_id_number}}', 'description': 'Cédula/ID del cliente'},
        {'variable': '{{customer_address}}', 'description': 'Dirección completa del cliente'},
        {'variable': '{{customer_phone}}', 'description': 'Teléfono del cliente'},
        {'variable': '{{customer_email}}', 'description': 'Correo electrónico del cliente'},
        {'variable': '{{loan_number}}', 'description': 'Número del préstamo'},
        {'variable': '{{loan_amount}}', 'description': 'Monto del préstamo'},
        {'variable': '{{loan_amount_words}}', 'description': 'Monto del préstamo en palabras'},
        {'variable': '{{interest_rate}}', 'description': 'Tasa de interés anual'},
        {'variable': '{{loan_term}}', 'description': 'Plazo del préstamo en meses'},
        {'variable': '{{payment_frequency}}', 'description': 'Frecuencia de pago'},
        {'variable': '{{monthly_payment}}', 'description': 'Pago mensual'},
        {'variable': '{{total_amount}}', 'description': 'Monto total a pagar'},
        {'variable': '{{disbursement_date}}', 'description': 'Fecha de desembolso'},
        {'variable': '{{first_payment_date}}', 'description': 'Fecha del primer pago'},
        {'variable': '{{final_payment_date}}', 'description': 'Fecha del último pago'},
        {'variable': '{{contract_date}}', 'description': 'Fecha de generación del contrato'},
        {'variable': '{{año}}', 'description': 'Año actual'},
        {'variable': '{{mes}}', 'description': 'Mes actual (nombre completo)'},
        {'variable': '{{dia}}', 'description': 'Día actual'},
        {'variable': '{{loan_officer}}', 'description': 'Nombre del oficial de crédito'},
        {'variable': '{{company_name}}', 'description': 'Nombre de la empresa'},
        {'variable': '{{company_address}}', 'description': 'Dirección de la empresa'},
        {'variable': '{{company_phone}}', 'description': 'Teléfono de la empresa'},
        {'variable': '{{company_email}}', 'description': 'Correo de la empresa'},
        {'variable': '{{ciudad}}', 'description': 'Ciudad de la empresa'},
        {'variable': '{{municipio}}', 'description': 'Municipio de la empresa'},
        {'variable': '{{provincia}}', 'description': 'Provincia/Estado de la empresa'},
        {'variable': '{{pais}}', 'description': 'País de la empresa'},
        {'variable': '{{guarantor_name}}', 'description': 'Nombre del garante (si aplica)'},
        {'variable': '{{guarantor_id}}', 'description': 'Cédula del garante (si aplica)'},
        {'variable': '{{collateral_description}}', 'description': 'Descripción de garantías'},
    ]
