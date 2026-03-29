"""
Servicio de firma digital para e-CF.
Firma XML usando certificados digitales (.p12/.pfx).
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ECFSigner:
    """
    Firma XML de e-CF usando XMLDSig con certificados digitales.
    
    Requiere: signxml o xmlsec1 para firma real.
    En desarrollo, simula la firma para testing con DGII pre-certificación.
    """

    def __init__(self, certificate_path=None, certificate_password=None):
        self.certificate_path = certificate_path
        self.certificate_password = certificate_password
        self._private_key = None
        self._certificate = None

    def load_certificate(self):
        """
        Carga el certificado digital desde archivo .p12/.pfx.
        
        Requiere: cryptography o pyOpenSSL
        """
        if not self.certificate_path:
            raise ECFSignerError('No se especificó ruta del certificado')

        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography import x509

            with open(self.certificate_path, 'rb') as f:
                pfx_data = f.read()

            private_key, certificate, chain = pkcs12.load_key_and_certificates(
                pfx_data,
                self.certificate_password.encode('utf-8') if self.certificate_password else None,
            )

            self._private_key = private_key
            self._certificate = certificate

            logger.info(
                f'Certificado cargado: {certificate.subject}, '
                f'válido hasta {certificate.not_valid_after_utc}'
            )
            return {
                'subject': str(certificate.subject),
                'issuer': str(certificate.issuer),
                'serial': certificate.serial_number,
                'valid_from': certificate.not_valid_before_utc,
                'valid_until': certificate.not_valid_after_utc,
            }
        except ImportError:
            logger.warning('cryptography no instalado — firma simulada')
            return None
        except Exception as e:
            raise ECFSignerError(f'Error cargando certificado: {e}')

    def sign_xml(self, xml_string):
        """
        Firma un XML con XMLDSig.
        
        Args:
            xml_string: XML a firmar (str)
            
        Returns:
            str: XML firmado
        """
        try:
            from signxml import XMLSigner, methods
            from lxml import etree

            # Cargar certificado si no está cargado
            if not self._private_key:
                self.load_certificate()

            # Parsear XML
            root = etree.fromstring(xml_string.encode('utf-8'))

            # Agregar fecha/hora de firma
            firma_dt = ET.SubElement(root, 'FechaHoraFirma')
            firma_dt.text = datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M:%S')

            # Firmar con XMLDSig enveloped
            signer = XMLSigner(
                method=methods.enveloped,
                signature_algorithm='rsa-sha256',
                digest_algorithm='sha256',
            )

            signed_root = signer.sign(
                root,
                key=self._private_key,
                cert=[self._certificate],
            )

            signed_xml = etree.tostring(signed_root, pretty_print=True, encoding='unicode')
            logger.info('XML firmado exitosamente')
            return signed_xml

        except ImportError:
            logger.warning(
                'signxml/lxml no instalados — retornando XML sin firma real. '
                'Instalar: pip install signxml lxml'
            )
            # En modo desarrollo, agregar un placeholder de firma
            return self._add_placeholder_signature(xml_string)
        except Exception as e:
            raise ECFSignerError(f'Error firmando XML: {e}')

    def _add_placeholder_signature(self, xml_string):
        """
        Agrega una firma placeholder para testing.
        NO usar en producción.
        """
        from xml.etree import ElementTree as ET

        # Insertar antes del cierre del root
        timestamp = datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M:%S')

        # Parse y agregar FechaHoraFirma
        root = ET.fromstring(xml_string)
        fecha = ET.SubElement(root, 'FechaHoraFirma')
        fecha.text = timestamp

        # Placeholder de firma
        sig = ET.SubElement(root, 'Signature')
        sig.set('xmlns', 'http://www.w3.org/2000/09/xmldsig#')
        signed_info = ET.SubElement(sig, 'SignedInfo')
        ET.SubElement(signed_info, 'CanonicalizationMethod').set(
            'Algorithm', 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
        )
        ET.SubElement(signed_info, 'SignatureMethod').set(
            'Algorithm', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256'
        )
        sig_value = ET.SubElement(sig, 'SignatureValue')
        sig_value.text = 'PLACEHOLDER_SIGNATURE_FOR_TESTING'

        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    def verify_signature(self, signed_xml):
        """
        Verifica la firma digital de un XML.
        
        Args:
            signed_xml: XML firmado
            
        Returns:
            bool: True si la firma es válida
        """
        try:
            from signxml import XMLVerifier
            from lxml import etree

            root = etree.fromstring(signed_xml.encode('utf-8'))
            XMLVerifier().verify(root)
            return True
        except ImportError:
            logger.warning('signxml no instalado — no se puede verificar firma')
            return None
        except Exception as e:
            logger.error(f'Firma inválida: {e}')
            return False


class ECFSignerError(Exception):
    """Error en la firma digital del e-CF."""
    pass
