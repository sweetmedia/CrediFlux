"""
Servicio de autenticación con la DGII.
Maneja el flujo: obtener semilla → firmar → obtener token JWT.
"""
import logging
import requests
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from ..constants import DGII_BASE_URLS, DGII_SERVICES

logger = logging.getLogger(__name__)


class DGIIAuthService:
    """
    Servicio para autenticarse con la DGII y obtener token JWT.
    
    Flujo:
    1. GET /api/autenticacion/semilla → XML con valor semilla
    2. Firmar semilla con certificado digital del tenant
    3. POST /api/autenticacion/validarsemilla → Token JWT (1 hora)
    """

    def __init__(self, environment='testecf'):
        self.environment = environment
        self.base_url = DGII_BASE_URLS.get(environment)
        if not self.base_url:
            raise ValueError(f'Ambiente DGII no válido: {environment}')
        self._token = None
        self._token_expiry = None

    @property
    def is_token_valid(self):
        """Verifica si el token actual sigue vigente."""
        if not self._token or not self._token_expiry:
            return False
        return datetime.now(timezone.utc) < self._token_expiry

    def get_semilla(self):
        """
        Obtiene la semilla XML de la DGII.
        
        Returns:
            str: XML de la semilla
        Raises:
            DGIIAuthError: Si falla la petición
        """
        url = f'{self.base_url}{DGII_SERVICES["autenticacion"]["semilla"]}'
        logger.info(f'Obteniendo semilla de {url}')

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.info('Semilla obtenida exitosamente')
            return response.text
        except requests.RequestException as e:
            logger.error(f'Error obteniendo semilla: {e}')
            raise DGIIAuthError(f'Error obteniendo semilla de DGII: {e}')

    def sign_semilla(self, semilla_xml, certificate_path, certificate_password):
        """
        Firma la semilla XML con el certificado digital.
        
        Args:
            semilla_xml: XML de la semilla a firmar
            certificate_path: Ruta al archivo del certificado (.p12/.pfx)
            certificate_password: Contraseña del certificado
            
        Returns:
            str: XML de la semilla firmada
        """
        # TODO: Implementar firma XMLDSig con signxml o xmlsec
        # Por ahora retorna la semilla sin firmar (para testing)
        from .ecf_signer import ECFSigner
        signer = ECFSigner(certificate_path, certificate_password)
        return signer.sign_xml(semilla_xml)

    def validate_semilla(self, signed_semilla_xml):
        """
        Envía la semilla firmada a la DGII para obtener el token.
        
        Args:
            signed_semilla_xml: XML de la semilla firmada
            
        Returns:
            dict: {'token': str, 'expira': datetime, 'expedido': datetime}
        """
        url = f'{self.base_url}{DGII_SERVICES["autenticacion"]["validar_semilla"]}'
        logger.info(f'Validando semilla en {url}')

        try:
            files = {
                'xml': ('semilla.xml', signed_semilla_xml.encode('utf-8'), 'text/xml')
            }
            response = requests.post(url, files=files, timeout=30)
            response.raise_for_status()

            data = response.json()
            self._token = data.get('token')
            self._token_expiry = datetime.fromisoformat(
                data.get('expira', '').replace('Z', '+00:00')
            )
            
            logger.info(f'Token obtenido, expira: {self._token_expiry}')
            return data
        except requests.RequestException as e:
            logger.error(f'Error validando semilla: {e}')
            raise DGIIAuthError(f'Error validando semilla con DGII: {e}')

    def get_token(self, certificate_path, certificate_password):
        """
        Obtiene un token JWT válido. Si el actual es válido, lo reutiliza.
        
        Args:
            certificate_path: Ruta al certificado digital
            certificate_password: Contraseña del certificado
            
        Returns:
            str: Token JWT
        """
        if self.is_token_valid:
            return self._token

        # Flujo completo de autenticación
        semilla_xml = self.get_semilla()
        signed_xml = self.sign_semilla(semilla_xml, certificate_path, certificate_password)
        result = self.validate_semilla(signed_xml)
        return result['token']

    def get_auth_header(self, certificate_path, certificate_password):
        """Retorna el header de autorización para usar en otros servicios."""
        token = self.get_token(certificate_path, certificate_password)
        return {'Authorization': f'Bearer {token}'}


class DGIIAuthError(Exception):
    """Error de autenticación con la DGII."""
    pass
