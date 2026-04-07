"""
Generador de XML para Comprobantes Fiscales Electrónicos (e-CF).
Genera XML según el formato oficial de la DGII.
"""
import logging
from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger(__name__)


class ECFGenerator:
    """
    Genera XML de e-CF a partir de un Invoice model.
    Soporta todos los tipos de e-CF definidos por la DGII.
    """

    def __init__(self, invoice):
        """
        Args:
            invoice: Instance de apps.billing.models.Invoice
        """
        self.invoice = invoice
        self.items = invoice.items.all().order_by('line_number')

    def generate(self):
        """
        Genera el XML completo del e-CF.
        
        Returns:
            str: XML string del e-CF
        """
        root = ET.Element('ECF')

        # A. Encabezado
        self._build_encabezado(root)

        # B. Detalle de bienes o servicios
        self._build_detalle(root)

        # C. Subtotales informativos (opcional)
        self._build_subtotales(root)

        # D. Descuentos o recargos (condicional)
        if self.invoice.total_discount and self.invoice.total_discount.amount > 0:
            self._build_descuentos(root)

        # E. Paginación
        self._build_paginacion(root)

        # F. Información de referencia (para NC/ND)
        if self.invoice.reference_invoice:
            self._build_referencia(root)

        # G. Fecha/hora de firma (se agrega al firmar)
        # H. Firma digital (se agrega al firmar)

        xml_str = self._prettify(root)
        logger.info(f'XML generado para e-CF {self.invoice.encf_number}')
        return xml_str

    def _build_encabezado(self, root):
        """Construye la sección Encabezado del e-CF."""
        encabezado = ET.SubElement(root, 'Encabezado')

        # Identificación del documento
        id_doc = ET.SubElement(encabezado, 'IdDoc')
        ET.SubElement(id_doc, 'TipoeCF').text = self.invoice.ecf_type
        ET.SubElement(id_doc, 'eNCF').text = self.invoice.encf_number

        if self.invoice.fiscal_sequence and self.invoice.fiscal_sequence.expiration_date:
            ET.SubElement(id_doc, 'FechaVencimientoSecuencia').text = (
                self.invoice.fiscal_sequence.expiration_date.strftime('%d-%m-%Y')
            )

        # Indicador de monto gravado
        ET.SubElement(id_doc, 'IndicadorMontoGravado').text = '0'  # 0=Incluye ITBIS
        ET.SubElement(id_doc, 'TipoIngresos').text = '01'  # 01=Ingresos por operaciones
        ET.SubElement(id_doc, 'TipoPago').text = self.invoice.payment_method
        ET.SubElement(id_doc, 'FechaLimitePago').text = (
            self.invoice.due_date.strftime('%d-%m-%Y') if self.invoice.due_date else ''
        )

        # Emisor
        emisor = ET.SubElement(encabezado, 'Emisor')
        ET.SubElement(emisor, 'RNCEmisor').text = self.invoice.emisor_rnc
        ET.SubElement(emisor, 'RazonSocialEmisor').text = self.invoice.emisor_razon_social
        ET.SubElement(emisor, 'FechaEmision').text = (
            self.invoice.issue_date.strftime('%d-%m-%Y')
        )

        # Comprador
        comprador = ET.SubElement(encabezado, 'Comprador')
        ET.SubElement(comprador, 'RNCComprador').text = self.invoice.comprador_rnc
        ET.SubElement(comprador, 'RazonSocialComprador').text = self.invoice.comprador_razon_social

        # Totales
        totales = ET.SubElement(encabezado, 'Totales')
        ET.SubElement(totales, 'MontoGravadoTotal').text = str(self.invoice.subtotal.amount)
        ET.SubElement(totales, 'MontoGravadoI1').text = str(self.invoice.subtotal.amount)  # ITBIS 18%
        ET.SubElement(totales, 'TotalITBIS').text = str(self.invoice.total_itbis.amount)
        ET.SubElement(totales, 'TotalITBIS1').text = str(self.invoice.total_itbis.amount)  # ITBIS 18%
        ET.SubElement(totales, 'MontoTotal').text = str(self.invoice.total.amount)

        if self.invoice.total_discount and self.invoice.total_discount.amount > 0:
            ET.SubElement(totales, 'TotalDescuento').text = str(self.invoice.total_discount.amount)

    def _build_detalle(self, root):
        """Construye la sección Detalle de Bienes o Servicios."""
        detalle = ET.SubElement(root, 'DetallesItems')

        for item in self.items:
            linea = ET.SubElement(detalle, 'Item')
            ET.SubElement(linea, 'NumeroLinea').text = str(item.line_number)
            ET.SubElement(linea, 'IndicadorFacturacion').text = '1'  # 1=Bien o servicio
            ET.SubElement(linea, 'NombreItem').text = item.description
            ET.SubElement(linea, 'CantidadItem').text = str(item.quantity)
            ET.SubElement(linea, 'UnidadMedida').text = '43'  # 43=Unidad
            ET.SubElement(linea, 'PrecioUnitarioItem').text = str(item.unit_price.amount)
            ET.SubElement(linea, 'MontoItem').text = str(
                item.quantity * item.unit_price.amount
            )

            if item.discount_amount and item.discount_amount.amount > 0:
                ET.SubElement(linea, 'DescuentoMonto').text = str(item.discount_amount.amount)

            # Sub-detalle de ITBIS
            if item.itbis_rate != '0':
                sub = ET.SubElement(linea, 'SubDescuento')
                ET.SubElement(sub, 'TipoSubDescuento').text = 'ITBIS'
                ET.SubElement(sub, 'SubDescuentoPorcentaje').text = item.itbis_rate

    def _build_subtotales(self, root):
        """Construye subtotales informativos."""
        # Opcional — se puede expandir según necesidad
        pass

    def _build_descuentos(self, root):
        """Construye la sección de descuentos o recargos globales."""
        descuentos = ET.SubElement(root, 'DescuentosORecargos')
        desc = ET.SubElement(descuentos, 'DescuentoORecargo')
        ET.SubElement(desc, 'TipoAjuste').text = 'D'  # D=Descuento
        ET.SubElement(desc, 'DescripcionDescuentooRecargo').text = 'Descuento general'
        ET.SubElement(desc, 'MontoDescuentooRecargo').text = str(
            self.invoice.total_discount.amount
        )

    def _build_paginacion(self, root):
        """Construye la sección de paginación para representación impresa."""
        paginacion = ET.SubElement(root, 'Paginacion')
        pagina = ET.SubElement(paginacion, 'Pagina')
        ET.SubElement(pagina, 'PaginaNo').text = '1'
        ET.SubElement(pagina, 'NoLineaDesde').text = '1'
        ET.SubElement(pagina, 'NoLineaHasta').text = str(self.items.count())
        ET.SubElement(pagina, 'TotalPaginas').text = '1'

    def _build_referencia(self, root):
        """Construye información de referencia (para NC/ND)."""
        ref_section = ET.SubElement(root, 'InformacionReferencia')
        ref = ET.SubElement(ref_section, 'Referencia')
        ref_invoice = self.invoice.reference_invoice
        ET.SubElement(ref, 'NCFModificado').text = ref_invoice.encf_number
        ET.SubElement(ref, 'FechaNCFModificado').text = (
            ref_invoice.issue_date.strftime('%d-%m-%Y')
        )
        ET.SubElement(ref, 'CodigoModificacion').text = '1'  # 1=Descuento

    def _prettify(self, elem):
        """Retorna XML formateado con indentación."""
        rough_string = ET.tostring(elem, encoding='unicode', xml_declaration=True)
        dom = minidom.parseString(rough_string)
        return dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
