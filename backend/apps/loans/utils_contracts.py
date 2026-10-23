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


_UNIDADES = [
    '', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE',
    'DIEZ', 'ONCE', 'DOCE', 'TRECE', 'CATORCE', 'QUINCE', 'DIECISÉIS', 'DIECISIETE',
    'DIECIOCHO', 'DIECINUEVE', 'VEINTE', 'VEINTIUNO', 'VEINTIDÓS', 'VEINTITRÉS',
    'VEINTICUATRO', 'VEINTICINCO', 'VEINTISÉIS', 'VEINTISIETE', 'VEINTIOCHO', 'VEINTINUEVE',
]
_DECENAS = ['', '', '', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
_CENTENAS = [
    '', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS',
    'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS',
]


def _hasta_999(n):
    if n == 100:
        return 'CIEN'
    centenas, resto = divmod(n, 100)
    if resto < 30:
        resto_str = _UNIDADES[resto]
    else:
        decenas, unidades = divmod(resto, 10)
        resto_str = _DECENAS[decenas] + (f' Y {_UNIDADES[unidades]}' if unidades else '')
    return ' '.join(p for p in (_CENTENAS[centenas], resto_str) if p)


def _apocopar(words):
    """'UNO' delante de un sustantivo (MIL, MILLONES, PESOS) se apocopa: VEINTIÚN MIL, UN MILLÓN."""
    if words.endswith('VEINTIUNO'):
        return words[:-len('VEINTIUNO')] + 'VEINTIÚN'
    if words.endswith('UNO'):
        return words[:-1]
    return words


def number_to_words_es(number):
    """Convierte un entero no negativo a letras en español (mayúsculas): 82800 -> 'OCHENTA Y DOS MIL OCHOCIENTOS'."""
    n = int(number)
    if n == 0:
        return 'CERO'

    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    parts = []
    if millones:
        parts.append('UN MILLÓN' if millones == 1 else f'{_apocopar(number_to_words_es(millones))} MILLONES')
    if miles:
        parts.append('MIL' if miles == 1 else f'{_apocopar(_hasta_999(miles))} MIL')
    if unidades:
        parts.append(_hasta_999(unidades))
    return ' '.join(parts)


def amount_to_words_es(amount, currency_name='PESOS'):
    """Monto en letras con centavos en formato de cheque: 'OCHENTA Y DOS MIL OCHOCIENTOS PESOS CON 00/100'."""
    if hasattr(amount, 'amount'):
        amount = amount.amount
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    integer_part = int(amount)
    cents = int((amount - integer_part) * 100)
    if integer_part == 1:
        return f"UN {currency_name[:-1] if currency_name.endswith('S') else currency_name} CON {cents:02d}/100"
    words = number_to_words_es(integer_part)
    if words.endswith('MILLÓN') or words.endswith('MILLONES'):
        words += ' DE'
    return f"{_apocopar(words)} {currency_name} CON {cents:02d}/100"


PAYMENT_FREQUENCY_ES = {
    'daily': ('Diaria', 'diarias'),
    'weekly': ('Semanal', 'semanales'),
    'biweekly': ('Quincenal', 'quincenales'),
    'monthly': ('Mensual', 'mensuales'),
    'quarterly': ('Trimestral', 'trimestrales'),
}

LATE_FEE_FREQUENCY_ES = {
    'daily': 'por cada día de retraso',
    'monthly': 'por cada mes de retraso',
    'one_time': 'por única vez al vencer la cuota',
}


# Línea para completar a mano cuando falta un dato del tenant (documentos legales)
BLANK = '________________'


def _long_date(value):
    if not value:
        return 'N/A'
    return f"{value.day} de {get_spanish_month_name(value.month)} de {value.year}"


def _money_str(value, currency_symbol='RD$'):
    if value is None:
        return 'N/A'
    if hasattr(value, 'amount'):
        value = value.amount
    return f"{currency_symbol} {Decimal(str(value)):,.2f}"


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
    - {{interest_rate}}: Monthly interest rate (the app stores rates as % per month)
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

    company_name = (tenant.business_name or tenant.name) if tenant else 'N/A'
    currency_symbol = getattr(tenant, 'currency_symbol', 'RD$') if tenant else 'RD$'
    customer_name = customer.get_full_name()
    customer_address = f"{customer.address_line1 or ''}{', ' + customer.address_line2 if customer.address_line2 else ''}, {customer.city or ''}, {customer.state or ''}".strip(', ')
    customer_id_number = customer.id_number or 'N/A'

    # Calendario: total con interés, número de cuotas y fecha de la última cuota
    schedules = list(loan.payment_schedules.order_by('installment_number'))
    if schedules:
        installments = len(schedules)
        total_with_interest = sum((s.total_amount.amount for s in schedules), Decimal('0'))
        final_payment_date = schedules[-1].due_date
    else:
        installments = 0
        total_with_interest = loan.total_amount.amount
        final_payment_date = loan.maturity_date
    frequency_singular, frequency_plural = PAYMENT_FREQUENCY_ES.get(
        loan.payment_frequency, (loan.get_payment_frequency_display(), loan.get_payment_frequency_display())
    )

    # Customer + loan variables
    replacements = {
        '{{customer_name}}': customer_name,
        '{{customer}}': customer_name,
        '{{customer_full_name}}': customer_name,
        '{{cliente}}': customer_name,
        '{{cliente_nombre}}': customer_name,
        '{{nombre_cliente}}': customer_name,

        '{{customer_id}}': customer.customer_id,
        '{{customer_code}}': customer.customer_id,
        '{{customer_id_number}}': customer_id_number,
        '{{cedula_cliente}}': customer_id_number,
        '{{customer_document}}': customer_id_number,
        '{{customer_address}}': customer_address or 'N/A',
        '{{customer_phone}}': str(customer.phone) if customer.phone else 'N/A',
        '{{customer_email}}': customer.email or 'N/A',

        # Loan variables
        '{{loan_number}}': loan.loan_number,
        '{{numero_prestamo}}': loan.loan_number,
        '{{loan_amount}}': _money_str(loan.principal_amount, currency_symbol),
        '{{loan_amount_words}}': amount_to_words_es(loan.principal_amount),
        '{{interest_rate}}': f"{loan.interest_rate}%",
        '{{loan_term}}': str(loan.term_months),
        '{{plazo_prestamo}}': str(loan.term_months),
        '{{payment_frequency}}': frequency_singular,
        '{{frecuencia_pago}}': frequency_singular,
        '{{frecuencia_pago_plural}}': frequency_plural,
        '{{monthly_payment}}': _money_str(loan.payment_amount, currency_symbol) if loan.payment_amount else 'N/A',
        '{{total_amount}}': _money_str(loan.outstanding_balance, currency_symbol) if loan.outstanding_balance else 'N/A',
        '{{monto_cuota}}': _money_str(loan.payment_amount, currency_symbol) if loan.payment_amount else 'N/A',
        '{{monto_cuota_letras}}': amount_to_words_es(loan.payment_amount) if loan.payment_amount else 'N/A',
        '{{total_con_interes}}': _money_str(total_with_interest, currency_symbol),
        '{{total_con_interes_letras}}': amount_to_words_es(total_with_interest),
        '{{cantidad_cuotas}}': str(installments) if installments else 'N/A',
        '{{cantidad_cuotas_letras}}': number_to_words_es(installments) if installments else 'N/A',

        # Dates
        '{{disbursement_date}}': f"{loan.disbursement_date.day} de {get_spanish_month_name(loan.disbursement_date.month)} de {loan.disbursement_date.year}" if loan.disbursement_date else 'Pendiente',
        '{{first_payment_date}}': f"{loan.first_payment_date.day} de {get_spanish_month_name(loan.first_payment_date.month)} de {loan.first_payment_date.year}" if loan.first_payment_date else 'N/A',
        '{{final_payment_date}}': _long_date(final_payment_date),
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
            '{{company_name}}': company_name,
            '{{empresa}}': company_name,
            '{{nombre_empresa}}': company_name,
            '{{company_address}}': ', '.join(p for p in (tenant.address, tenant.city, tenant.state) if p) or BLANK,
            '{{company_phone}}': str(tenant.phone) if tenant.phone else 'N/A',
            '{{company_email}}': tenant.email or 'N/A',
            '{{company_tax_id}}': tenant.tax_id or BLANK,
            '{{mora_porcentaje}}': f"{tenant.late_fee_percentage}%",
            '{{mora_frecuencia}}': LATE_FEE_FREQUENCY_ES.get(tenant.late_fee_frequency, ''),
            '{{ciudad}}': tenant.city or BLANK,
            '{{municipio}}': tenant.city or BLANK,  # Using city as municipality
            '{{provincia}}': tenant.state or BLANK,
            '{{pais}}': tenant.country or 'República Dominicana',
        })
    else:
        replacements.update({
            '{{company_name}}': 'N/A',
            '{{company_address}}': 'N/A',
            '{{company_phone}}': 'N/A',
            '{{company_email}}': 'N/A',
            '{{company_tax_id}}': BLANK,
            '{{mora_porcentaje}}': 'N/A',
            '{{mora_frecuencia}}': '',
            '{{ciudad}}': 'N/A',
            '{{municipio}}': 'N/A',
            '{{provincia}}': 'N/A',
            '{{pais}}': 'N/A',
        })

    # Guarantor variables
    guarantor = loan.guarantors.order_by('created_at').first()
    if guarantor:
        replacements.update({
            '{{guarantor_name}}': guarantor.get_full_name(),
            '{{guarantor}}': guarantor.get_full_name(),
            '{{guarantor_id}}': guarantor.id_number or 'N/A',
            '{{cedula_garante}}': guarantor.id_number or 'N/A',
            '{{guarantor_phone}}': str(guarantor.phone) if guarantor.phone else 'N/A',
            '{{guarantor_address}}': guarantor.address or 'N/A',
            '{{guarantor_relationship}}': guarantor.get_relationship_display(),
        })
    else:
        replacements.update({
            '{{guarantor_name}}': 'N/A',
            '{{guarantor}}': 'N/A',
            '{{guarantor_id}}': 'N/A',
            '{{cedula_garante}}': 'N/A',
            '{{guarantor_phone}}': 'N/A',
            '{{guarantor_address}}': 'N/A',
            '{{guarantor_relationship}}': 'N/A',
        })

    # Collateral variables
    collaterals = loan.collaterals.all()
    if collaterals.exists():
        collateral_desc = ', '.join([
            f"{c.get_collateral_type_display()}: {c.description} ({_money_str(c.estimated_value, currency_symbol)})"
            for c in collaterals
        ])
        replacements['{{collateral_description}}'] = collateral_desc
    else:
        replacements['{{collateral_description}}'] = 'Sin garantías'

    # Replace all variables in content (supports {{ variable }} spacing variants)
    for variable, value in replacements.items():
        key = variable.strip('{} ').strip()
        content = re.sub(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', str(value), content)

    return content


def regenerate_latest_loan_contract(loan, tenant=None):
    """Regenerate the latest active/pending contract for a loan after related data changes."""
    contract = loan.contracts.filter(is_archived=False).order_by('-generated_at').first()
    if not contract or not contract.template:
        return None
    # Un contrato firmado no se reescribe: el texto firmado es el que vale.
    if contract.customer_signed_at or contract.officer_signed_at:
        return None

    contract.content = replace_contract_variables(contract.template.content, loan, tenant)
    contract.save(update_fields=['content', 'updated_at'])
    return contract


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
        {'variable': '{{interest_rate}}', 'description': 'Tasa de interés mensual'},
        {'variable': '{{loan_term}}', 'description': 'Plazo del préstamo en meses'},
        {'variable': '{{payment_frequency}}', 'description': 'Frecuencia de pago (Quincenal, Mensual…)'},
        {'variable': '{{frecuencia_pago_plural}}', 'description': 'Frecuencia en plural (quincenales, mensuales…)'},
        {'variable': '{{monthly_payment}}', 'description': 'Monto de la cuota'},
        {'variable': '{{monto_cuota_letras}}', 'description': 'Monto de la cuota en letras'},
        {'variable': '{{cantidad_cuotas}}', 'description': 'Cantidad de cuotas del calendario'},
        {'variable': '{{cantidad_cuotas_letras}}', 'description': 'Cantidad de cuotas en letras'},
        {'variable': '{{total_con_interes}}', 'description': 'Total a pagar (capital + interés, suma del calendario)'},
        {'variable': '{{total_con_interes_letras}}', 'description': 'Total a pagar en letras'},
        {'variable': '{{total_amount}}', 'description': 'Balance pendiente actual'},
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
        {'variable': '{{company_tax_id}}', 'description': 'RNC/Cédula de la empresa'},
        {'variable': '{{mora_porcentaje}}', 'description': 'Porcentaje de mora configurado'},
        {'variable': '{{mora_frecuencia}}', 'description': "Frecuencia de la mora ('por cada día de retraso'…)"},
        {'variable': '{{ciudad}}', 'description': 'Ciudad de la empresa'},
        {'variable': '{{municipio}}', 'description': 'Municipio de la empresa'},
        {'variable': '{{provincia}}', 'description': 'Provincia/Estado de la empresa'},
        {'variable': '{{pais}}', 'description': 'País de la empresa'},
        {'variable': '{{guarantor_name}}', 'description': 'Nombre del garante (si aplica)'},
        {'variable': '{{guarantor_id}}', 'description': 'Cédula del garante (si aplica)'},
        {'variable': '{{guarantor_address}}', 'description': 'Dirección del garante (si aplica)'},
        {'variable': '{{collateral_description}}', 'description': 'Descripción de garantías'},
    ]
