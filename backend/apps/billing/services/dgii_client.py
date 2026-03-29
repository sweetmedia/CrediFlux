"""
Cliente HTTP para los servicios web de la DGII.
Maneja envío de e-CF, consulta de estado y directorio.
"""
import logging
import requests
from datetime import datetime, timezone
from django.utils import timezone as dj_timezone

from ..constants import DGII_BASE_URLS, DGII_FC_BASE_URLS, DGII_SERVICES, FC_RESUMEN_MAX_AMOUNT
from ..models import ECFSubmission
from .dgii_auth import DGIIAuthService, DGIIAuthError

logger = logging.getLogger(__name__)


class DGIIClient:
    """
    Cliente para interactuar con los servicios REST de la DGII.
    Maneja autenticación automática y retry de tokens expirados.
    """

    def __init__(self, environment='testecf', certificate_path=None, certificate_password=None):
        self.environment = environment
        self.base_url = DGII_BASE_URLS.get(environment)
        self.fc_base_url = DGII_FC_BASE_URLS.get(environment)
        self.certificate_path = certificate_path
        self.certificate_password = certificate_password
        self.auth_service = DGIIAuthService(environment)

        if not self.base_url:
            raise ValueError(f'Ambiente DGII no válido: {environment}')

    def _get_headers(self):
        """Obtiene headers con token de autenticación."""
        return self.auth_service.get_auth_header(
            self.certificate_path, self.certificate_password
        )

    def submit_ecf(self, invoice):
        """
        Envía un e-CF firmado a la DGII.
        
        Args:
            invoice: Instance de Invoice con signed_xml
            
        Returns:
            dict: {'trackid': str, 'status': str, ...}
        """
        if not invoice.signed_xml:
            raise DGIIClientError('La factura no tiene XML firmado')

        url = f'{self.base_url}{DGII_SERVICES["recepcion"]["enviar"]}'
        logger.info(f'Enviando e-CF {invoice.encf_number} a {url}')

        try:
            headers = self._get_headers()
            filename = f'{invoice.emisor_rnc}{invoice.ecf_type}{invoice.encf_number}.xml'
            files = {
                'xml': (filename, invoice.signed_xml.encode('utf-8'), 'text/xml')
            }

            response = requests.post(url, headers=headers, files=files, timeout=60)

            # Registrar el envío
            submission = ECFSubmission.objects.create(
                invoice=invoice,
                action='submit',
                environment=self.environment,
                request_xml=invoice.signed_xml[:5000],  # Truncar para storage
                http_status_code=response.status_code,
            )

            if response.status_code in (200, 201):
                data = response.json()
                trackid = data.get('trackId', '')

                submission.trackid = trackid
                submission.response_status = 'enviado'
                submission.response_body = data
                submission.save()

                # Actualizar invoice
                invoice.dgii_trackid = trackid
                invoice.dgii_status = 'enviado'
                invoice.dgii_submitted_at = dj_timezone.now()
                invoice.status = 'submitted'
                invoice.dgii_response = data
                invoice.save()

                logger.info(f'e-CF enviado exitosamente. TrackId: {trackid}')
                return data
            else:
                error_msg = response.text[:500]
                submission.response_status = 'error'
                submission.error_message = error_msg
                submission.response_body = {'error': error_msg}
                submission.save()

                logger.error(f'Error enviando e-CF: {response.status_code} - {error_msg}')
                raise DGIIClientError(f'Error DGII ({response.status_code}): {error_msg}')

        except requests.RequestException as e:
            logger.error(f'Error de conexión con DGII: {e}')
            raise DGIIClientError(f'Error de conexión con DGII: {e}')

    def query_result(self, invoice):
        """
        Consulta el resultado de un e-CF enviado.
        
        Args:
            invoice: Instance de Invoice con dgii_trackid
            
        Returns:
            dict: Estado y detalles del e-CF en DGII
        """
        if not invoice.dgii_trackid:
            raise DGIIClientError('La factura no tiene TrackId')

        url = f'{self.base_url}{DGII_SERVICES["consulta_resultado"]["consultar"]}'
        logger.info(f'Consultando resultado de {invoice.encf_number} (TrackId: {invoice.dgii_trackid})')

        try:
            headers = self._get_headers()
            params = {'TrackId': invoice.dgii_trackid}
            response = requests.get(url, headers=headers, params=params, timeout=30)

            submission = ECFSubmission.objects.create(
                invoice=invoice,
                action='query_result',
                environment=self.environment,
                trackid=invoice.dgii_trackid,
                http_status_code=response.status_code,
            )

            if response.status_code == 200:
                data = response.json()
                dgii_status = data.get('estado', '').lower()

                submission.response_status = dgii_status
                submission.response_body = data
                submission.save()

                # Mapear estado DGII a status de invoice
                status_map = {
                    'aceptado': 'accepted',
                    'aceptado condicional': 'conditionally_accepted',
                    'rechazado': 'rejected',
                    'en proceso': 'submitted',
                }
                invoice.dgii_status = dgii_status
                invoice.dgii_response = data
                invoice.status = status_map.get(dgii_status, invoice.status)
                invoice.save()

                logger.info(f'Estado de {invoice.encf_number}: {dgii_status}')
                return data
            else:
                submission.response_status = 'error'
                submission.error_message = response.text[:500]
                submission.save()
                raise DGIIClientError(f'Error consultando resultado: {response.status_code}')

        except requests.RequestException as e:
            logger.error(f'Error de conexión consultando resultado: {e}')
            raise DGIIClientError(f'Error de conexión: {e}')

    def query_directory(self, rnc):
        """
        Consulta si un RNC es emisor electrónico certificado.
        
        Args:
            rnc: RNC a consultar
            
        Returns:
            dict: Información del emisor electrónico
        """
        url = f'{self.base_url}{DGII_SERVICES["consulta_directorio"]["consultar"]}'
        logger.info(f'Consultando directorio para RNC: {rnc}')

        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params={'rnc': rnc}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Error consultando directorio: {e}')
            raise DGIIClientError(f'Error consultando directorio DGII: {e}')

    def check_service_status(self):
        """
        Verifica el estado de los servicios DGII.
        
        Returns:
            dict: Estado de los servicios
        """
        url = f'{self.base_url}{DGII_SERVICES["consulta_estado"]["status"]}'
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Error verificando estado DGII: {e}')
            return {'status': 'unavailable', 'error': str(e)}


class DGIIClientError(Exception):
    """Error del cliente DGII."""
    pass
