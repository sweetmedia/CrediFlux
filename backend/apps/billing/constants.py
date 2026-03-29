"""
Constants for DGII e-CF (Comprobantes Fiscales Electrónicos).
"""

# ============================================================
# Tipos de e-CF
# ============================================================
ECF_TYPE_CHOICES = [
    ('31', 'Factura de Crédito Fiscal Electrónica'),
    ('32', 'Factura de Consumo Electrónica'),
    ('33', 'Nota de Débito Electrónica'),
    ('34', 'Nota de Crédito Electrónica'),
    ('41', 'Compras Electrónico'),
    ('43', 'Gastos Menores Electrónico'),
    ('44', 'Regímenes Especiales Electrónico'),
    ('45', 'Gubernamental Electrónico'),
    ('46', 'Comprobante de Exportaciones Electrónico'),
    ('47', 'Comprobante para Pagos al Exterior Electrónico'),
]

ECF_TYPE_MAP = dict(ECF_TYPE_CHOICES)

# ============================================================
# Ambientes DGII
# ============================================================
DGII_ENV_CHOICES = [
    ('testecf', 'Pre-Certificación (Pruebas)'),
    ('certecf', 'Certificación'),
    ('ecf', 'Producción'),
]

# URLs base por ambiente
DGII_BASE_URLS = {
    'testecf': 'https://ecf.dgii.gov.do/testecf',
    'certecf': 'https://ecf.dgii.gov.do/certecf',
    'ecf': 'https://ecf.dgii.gov.do/ecf',
}

# URLs base para Facturas de Consumo
DGII_FC_BASE_URLS = {
    'testecf': 'https://fc.dgii.gov.do/testecf',
    'certecf': 'https://fc.dgii.gov.do/certecf',
    'ecf': 'https://fc.dgii.gov.do/ecf',
}

# ============================================================
# Servicios DGII (endpoints relativos)
# ============================================================
DGII_SERVICES = {
    'autenticacion': {
        'semilla': '/autenticacion/api/autenticacion/semilla',
        'validar_semilla': '/autenticacion/api/autenticacion/validarsemilla',
    },
    'recepcion': {
        'enviar': '/recepcion/api/facturaselectronicas',
    },
    'consulta_resultado': {
        'consultar': '/consultaresultado/api/consultaresultado',
    },
    'consulta_estado': {
        'status': '/consultaestado/api/consultaestado',
    },
    'consulta_directorio': {
        'consultar': '/consultadirectorio/api/consultadirectorio',
    },
    'anulacion_rangos': {
        'anular': '/anulacionrangos/api/anulacionrangos',
    },
    'resumen_fc': {
        'enviar': '/recepcionfc/api/recepcionfc',
    },
}

# ============================================================
# Estados de factura
# ============================================================
INVOICE_STATUS_CHOICES = [
    ('draft', 'Borrador'),
    ('generated', 'XML Generado'),
    ('signed', 'Firmado'),
    ('submitted', 'Enviado a DGII'),
    ('accepted', 'Aceptado por DGII'),
    ('conditionally_accepted', 'Aceptado Condicional'),
    ('rejected', 'Rechazado por DGII'),
    ('cancelled', 'Anulado'),
]

# ============================================================
# Estados de respuesta DGII
# ============================================================
DGII_RESPONSE_STATUS = {
    'aceptado': 'Aceptado',
    'aceptado_condicional': 'Aceptado Condicional',
    'rechazado': 'Rechazado',
    'en_proceso': 'En Proceso',
}

# ============================================================
# Tipos de impuesto (ITBIS)
# ============================================================
ITBIS_RATE_CHOICES = [
    ('18', '18% (Tasa General)'),
    ('16', '16% (Tasa Reducida)'),
    ('0', '0% (Exento)'),
]

# ============================================================
# Formas de pago
# ============================================================
PAYMENT_METHOD_CHOICES = [
    ('01', 'Efectivo'),
    ('02', 'Cheque / Transferencia / Depósito'),
    ('03', 'Tarjeta de Crédito / Débito'),
    ('04', 'Venta a Crédito'),
    ('05', 'Permuta'),
    ('06', 'Nota de Crédito'),
    ('07', 'Mixto'),
]

# ============================================================
# Formato de nombre de archivo XML
# ============================================================
# Formato: RNCEmisor + TipoeCF + eNCF + ".xml"
# Ejemplo: 101000001310E310000000001.xml

# ============================================================
# Tags XML principales
# ============================================================
ECF_ROOT_TAG = 'ECF'
ACUSE_RECIBO_ROOT_TAG = 'ARECF'
APROBACION_COMERCIAL_ROOT_TAG = 'ACECF'
ANULACION_ROOT_TAG = 'ANECF'
RESUMEN_FC_ROOT_TAG = 'RFCE'

# Monto máximo para Factura de Consumo vía resumen
FC_RESUMEN_MAX_AMOUNT = 250000.00  # RD$250,000.00
