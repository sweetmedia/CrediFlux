"""
e-CF Provider Strategy Pattern.

Allows tenants to choose between different e-CF providers:
1. DirectDGII — Direct submission to DGII (requires own certificate)
2. DGMax — Via DGMax.do API (PSFE provider)
3. EF2 — Via EF2.do API (PSFE provider)

Usage:
    provider = get_ecf_provider(tenant)
    result = provider.submit_invoice(invoice)
    status = provider.query_status(invoice)
"""
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from django.db import connection
from django.conf import settings

from ..models import ECFSubmission

logger = logging.getLogger(__name__)


class ECFProviderError(Exception):
    """Base exception for e-CF provider errors."""
    pass


class ECFProvider(ABC):
    """Abstract base class for e-CF providers."""

    @abstractmethod
    def submit_invoice(self, invoice) -> dict:
        """
        Submit an invoice to the e-CF provider.
        
        Returns:
            dict with keys: trackid, status, ncf, message
        """
        pass

    @abstractmethod
    def query_status(self, invoice) -> dict:
        """
        Query the status of a submitted e-CF.
        
        Returns:
            dict with keys: status, ncf, dgii_response
        """
        pass

    @abstractmethod
    def cancel_invoice(self, invoice, reason: str) -> dict:
        """Cancel/anull a submitted e-CF."""
        pass

    @abstractmethod
    def test_connection(self) -> dict:
        """Test connectivity to the provider."""
        pass

    def _log_submission(self, invoice, action, status, response_data, error=None):
        """Log submission to ECFSubmission model."""
        return ECFSubmission.objects.create(
            invoice=invoice,
            action=action,
            environment=getattr(self, 'environment', 'production'),
            response_status=status,
            response_body=response_data,
            error_message=error or '',
        )


class DirectDGIIProvider(ECFProvider):
    """
    Direct submission to DGII services.
    Requires tenant to have own digital certificate.
    Uses existing DGIIClient under the hood.
    """

    def __init__(self, tenant):
        self.tenant = tenant
        self.environment = getattr(tenant, 'dgii_environment', 'testecf')

    def submit_invoice(self, invoice) -> dict:
        from .dgii_client import DGIIClient, DGIIClientError
        from ..models import DigitalCertificate

        # Get active certificate for this tenant
        cert = DigitalCertificate.objects.filter(
            is_active=True,
        ).first()

        if not cert:
            raise ECFProviderError('No hay certificado digital activo configurado')

        try:
            client = DGIIClient(
                environment=self.environment,
                certificate_path=cert.certificate_file.path if cert.certificate_file else None,
                certificate_password=cert.password,
            )
            result = client.submit_ecf(invoice)
            return {
                'trackid': result.get('trackId', ''),
                'status': 'enviado',
                'ncf': invoice.encf_number,
                'message': 'Enviado directamente a DGII',
                'raw_response': result,
            }
        except DGIIClientError as e:
            raise ECFProviderError(f'Error DGII directo: {str(e)}')

    def query_status(self, invoice) -> dict:
        from .dgii_client import DGIIClient, DGIIClientError
        from ..models import DigitalCertificate

        cert = DigitalCertificate.objects.filter(is_active=True).first()
        if not cert:
            raise ECFProviderError('No hay certificado digital activo')

        try:
            client = DGIIClient(
                environment=self.environment,
                certificate_path=cert.certificate_file.path if cert.certificate_file else None,
                certificate_password=cert.password,
            )
            result = client.query_result(invoice)
            return {
                'status': result.get('estado', 'desconocido'),
                'ncf': invoice.encf_number,
                'dgii_response': result,
            }
        except DGIIClientError as e:
            raise ECFProviderError(f'Error consultando DGII: {str(e)}')

    def cancel_invoice(self, invoice, reason: str) -> dict:
        raise ECFProviderError('Anulación directa a DGII no implementada. Use Nota de Crédito.')

    def test_connection(self) -> dict:
        from .dgii_client import DGIIClient
        client = DGIIClient(environment=self.environment)
        result = client.check_service_status()
        return {
            'provider': 'DGII Directo',
            'environment': self.environment,
            'status': result.get('status', 'unknown'),
        }


class DGMaxProvider(ECFProvider):
    """
    DGMax.do — PSFE (Proveedor de Servicios de Facturación Electrónica).
    
    API docs: https://dgmax.do/api-docs
    Handles XML generation, digital signature, and DGII submission.
    Tenant only needs to provide invoice data in JSON format.
    """

    BASE_URL = 'https://api.dgmax.do/v1'
    SANDBOX_URL = 'https://sandbox.dgmax.do/v1'

    def __init__(self, tenant):
        self.tenant = tenant
        self.api_key = getattr(tenant, 'ecf_provider_api_key', '') or ''
        self.api_secret = getattr(tenant, 'ecf_provider_api_secret', '') or ''
        self.environment = getattr(tenant, 'dgii_environment', 'testecf')
        self.base_url = self.SANDBOX_URL if self.environment == 'testecf' else self.BASE_URL

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Api-Secret': self.api_secret,
        }

    def _build_invoice_payload(self, invoice) -> dict:
        """Convert CrediFlux invoice to DGMax API payload."""
        items = []
        for item in invoice.items.all().order_by('line_number'):
            items.append({
                'descripcion': item.description,
                'cantidad': float(item.quantity),
                'precio_unitario': float(item.unit_price.amount),
                'itbis_tasa': int(item.itbis_rate) if item.itbis_rate != '0' else 0,
            })

        return {
            'tipo_ecf': invoice.ecf_type,
            'emisor': {
                'rnc': invoice.emisor_rnc,
                'razon_social': invoice.emisor_razon_social,
            },
            'comprador': {
                'rnc_cedula': invoice.comprador_rnc,
                'razon_social': invoice.comprador_razon_social,
            },
            'fecha_emision': invoice.issue_date.strftime('%Y-%m-%d'),
            'fecha_vencimiento': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None,
            'forma_pago': invoice.payment_method,
            'items': items,
            'moneda': 'DOP',
            'ncf_modificado': invoice.reference_invoice.encf_number if invoice.reference_invoice else None,
        }

    def submit_invoice(self, invoice) -> dict:
        if not self.api_key:
            raise ECFProviderError('API key de DGMax no configurada')

        payload = self._build_invoice_payload(invoice)
        
        try:
            response = requests.post(
                f'{self.base_url}/ecf/submit',
                json=payload,
                headers=self._headers(),
                timeout=60,
            )

            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

            self._log_submission(invoice, 'submit', 
                'enviado' if response.ok else 'error', data,
                error=data.get('error', '') if not response.ok else None)

            if response.ok:
                ncf = data.get('ncf', data.get('encf', ''))
                invoice.encf_number = ncf or invoice.encf_number
                invoice.dgii_trackid = data.get('trackid', data.get('track_id', ''))
                invoice.dgii_status = 'enviado'
                invoice.dgii_response = data
                invoice.status = 'submitted'
                invoice.save()

                return {
                    'trackid': invoice.dgii_trackid,
                    'status': 'enviado',
                    'ncf': ncf,
                    'message': f'Enviado via DGMax.do',
                    'raw_response': data,
                }
            else:
                error_msg = data.get('error', data.get('message', f'HTTP {response.status_code}'))
                raise ECFProviderError(f'Error DGMax: {error_msg}')

        except requests.RequestException as e:
            raise ECFProviderError(f'Error de conexión con DGMax: {e}')

    def query_status(self, invoice) -> dict:
        if not invoice.dgii_trackid:
            raise ECFProviderError('Factura sin TrackId')

        try:
            response = requests.get(
                f'{self.base_url}/ecf/status/{invoice.dgii_trackid}',
                headers=self._headers(),
                timeout=30,
            )
            data = response.json() if response.ok else {}

            if response.ok:
                dgii_status = data.get('status', data.get('estado', 'desconocido'))
                invoice.dgii_status = dgii_status
                invoice.dgii_response = data
                invoice.save()

                return {
                    'status': dgii_status,
                    'ncf': data.get('ncf', invoice.encf_number),
                    'dgii_response': data,
                }
            else:
                raise ECFProviderError(f'Error consultando DGMax: {response.status_code}')
        except requests.RequestException as e:
            raise ECFProviderError(f'Error conexión DGMax: {e}')

    def cancel_invoice(self, invoice, reason: str) -> dict:
        try:
            response = requests.post(
                f'{self.base_url}/ecf/cancel',
                json={
                    'ncf': invoice.encf_number,
                    'trackid': invoice.dgii_trackid,
                    'motivo': reason,
                },
                headers=self._headers(),
                timeout=30,
            )
            data = response.json() if response.ok else {}

            if response.ok:
                invoice.status = 'cancelled'
                invoice.dgii_status = 'anulado'
                invoice.save()
                return {'status': 'anulado', 'message': 'Comprobante anulado via DGMax'}
            else:
                raise ECFProviderError(f'Error anulando en DGMax: {data.get("error", response.status_code)}')
        except requests.RequestException as e:
            raise ECFProviderError(f'Error conexión DGMax: {e}')

    def test_connection(self) -> dict:
        try:
            response = requests.get(
                f'{self.base_url}/health',
                headers=self._headers(),
                timeout=10,
            )
            return {
                'provider': 'DGMax.do',
                'environment': self.environment,
                'status': 'online' if response.ok else 'error',
                'http_code': response.status_code,
            }
        except requests.RequestException as e:
            return {
                'provider': 'DGMax.do',
                'status': 'offline',
                'error': str(e),
            }


class EF2Provider(ECFProvider):
    """
    EF2.do — PSFE (Proveedor de Servicios de Facturación Electrónica).
    
    EF2 (Emisión Fiscal 2) is another popular Dominican e-CF provider.
    Similar pattern to DGMax but with different API structure.
    """

    BASE_URL = 'https://api.ef2.do/api/v2'
    SANDBOX_URL = 'https://sandbox-api.ef2.do/api/v2'

    def __init__(self, tenant):
        self.tenant = tenant
        self.api_key = getattr(tenant, 'ecf_provider_api_key', '') or ''
        self.api_secret = getattr(tenant, 'ecf_provider_api_secret', '') or ''
        self.environment = getattr(tenant, 'dgii_environment', 'testecf')
        self.base_url = self.SANDBOX_URL if self.environment == 'testecf' else self.BASE_URL

    def _headers(self):
        return {
            'X-API-Key': self.api_key,
            'X-API-Secret': self.api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _build_payload(self, invoice) -> dict:
        """Convert invoice to EF2 API format."""
        lineas = []
        for item in invoice.items.all().order_by('line_number'):
            lineas.append({
                'NumeroLinea': item.line_number,
                'Descripcion': item.description,
                'Cantidad': float(item.quantity),
                'PrecioUnitario': float(item.unit_price.amount),
                'Monto': float(item.quantity * item.unit_price.amount),
                'TasaITBIS': int(item.itbis_rate) if item.itbis_rate != '0' else 0,
            })

        return {
            'TipoECF': invoice.ecf_type,
            'RNCEmisor': invoice.emisor_rnc,
            'RazonSocialEmisor': invoice.emisor_razon_social,
            'RNCComprador': invoice.comprador_rnc,
            'RazonSocialComprador': invoice.comprador_razon_social,
            'FechaEmision': invoice.issue_date.strftime('%Y-%m-%d'),
            'FechaVencimiento': invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else None,
            'FormaPago': invoice.payment_method,
            'Moneda': 'DOP',
            'Lineas': lineas,
            'NCFModificado': invoice.reference_invoice.encf_number if invoice.reference_invoice else None,
        }

    def submit_invoice(self, invoice) -> dict:
        if not self.api_key:
            raise ECFProviderError('API key de EF2 no configurada')

        payload = self._build_payload(invoice)

        try:
            response = requests.post(
                f'{self.base_url}/comprobantes',
                json=payload,
                headers=self._headers(),
                timeout=60,
            )
            data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

            self._log_submission(invoice, 'submit',
                'enviado' if response.ok else 'error', data,
                error=data.get('mensaje', '') if not response.ok else None)

            if response.ok:
                ncf = data.get('eNCF', data.get('NCF', ''))
                trackid = data.get('TrackId', data.get('trackId', ''))

                invoice.encf_number = ncf or invoice.encf_number
                invoice.dgii_trackid = trackid
                invoice.dgii_status = 'enviado'
                invoice.dgii_response = data
                invoice.status = 'submitted'
                invoice.save()

                return {
                    'trackid': trackid,
                    'status': 'enviado',
                    'ncf': ncf,
                    'message': 'Enviado via EF2.do',
                    'raw_response': data,
                }
            else:
                error_msg = data.get('mensaje', data.get('error', f'HTTP {response.status_code}'))
                raise ECFProviderError(f'Error EF2: {error_msg}')

        except requests.RequestException as e:
            raise ECFProviderError(f'Error de conexión con EF2: {e}')

    def query_status(self, invoice) -> dict:
        if not invoice.dgii_trackid:
            raise ECFProviderError('Factura sin TrackId')

        try:
            response = requests.get(
                f'{self.base_url}/comprobantes/{invoice.dgii_trackid}/estado',
                headers=self._headers(),
                timeout=30,
            )
            data = response.json() if response.ok else {}

            if response.ok:
                dgii_status = data.get('Estado', data.get('estado', 'desconocido'))
                invoice.dgii_status = dgii_status
                invoice.dgii_response = data
                invoice.save()
                return {
                    'status': dgii_status,
                    'ncf': data.get('eNCF', invoice.encf_number),
                    'dgii_response': data,
                }
            else:
                raise ECFProviderError(f'Error consultando EF2: {response.status_code}')
        except requests.RequestException as e:
            raise ECFProviderError(f'Error conexión EF2: {e}')

    def cancel_invoice(self, invoice, reason: str) -> dict:
        try:
            response = requests.post(
                f'{self.base_url}/comprobantes/{invoice.dgii_trackid}/anular',
                json={'motivo': reason},
                headers=self._headers(),
                timeout=30,
            )
            data = response.json() if response.ok else {}

            if response.ok:
                invoice.status = 'cancelled'
                invoice.dgii_status = 'anulado'
                invoice.save()
                return {'status': 'anulado', 'message': 'Comprobante anulado via EF2'}
            else:
                raise ECFProviderError(f'Error anulando en EF2: {data.get("mensaje", response.status_code)}')
        except requests.RequestException as e:
            raise ECFProviderError(f'Error conexión EF2: {e}')

    def test_connection(self) -> dict:
        try:
            response = requests.get(
                f'{self.base_url}/status',
                headers=self._headers(),
                timeout=10,
            )
            return {
                'provider': 'EF2.do',
                'environment': self.environment,
                'status': 'online' if response.ok else 'error',
                'http_code': response.status_code,
            }
        except requests.RequestException as e:
            return {
                'provider': 'EF2.do',
                'status': 'offline',
                'error': str(e),
            }


# ============================================================
# Provider Factory
# ============================================================

PROVIDER_MAP = {
    'direct': DirectDGIIProvider,
    'dgmax': DGMaxProvider,
    'ef2': EF2Provider,
}

ECF_PROVIDER_CHOICES = [
    ('direct', 'DGII Directo (certificado propio)'),
    ('dgmax', 'DGMax.do (PSFE)'),
    ('ef2', 'EF2.do (PSFE)'),
    ('none', 'Sin facturación electrónica'),
]


def get_ecf_provider(tenant=None) -> ECFProvider:
    """
    Factory function — returns the configured e-CF provider for the tenant.
    
    Reads tenant.ecf_provider field to determine which provider to use.
    Falls back to DirectDGII if not configured.
    """
    if tenant is None:
        tenant = connection.tenant

    provider_key = getattr(tenant, 'ecf_provider', 'direct') or 'direct'

    if provider_key == 'none':
        raise ECFProviderError('Facturación electrónica no está habilitada para este tenant')

    provider_class = PROVIDER_MAP.get(provider_key)
    if not provider_class:
        raise ECFProviderError(f'Proveedor e-CF no válido: {provider_key}')

    return provider_class(tenant)
