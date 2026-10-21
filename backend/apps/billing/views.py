"""
API ViewSets for the Billing app.
"""
import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    DigitalCertificate, FiscalSequence, Invoice, InvoiceItem, ECFSubmission
)
from .serializers import (
    DigitalCertificateSerializer, DigitalCertificateUploadSerializer,
    FiscalSequenceSerializer,
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceCreateSerializer,
    ECFSubmissionSerializer, ECFProviderConfigSerializer,
)
from .services.ecf_generator import ECFGenerator
from .services.ecf_signer import ECFSigner, ECFSignerError
from .services.dgii_client import DGIIClient, DGIIClientError
from .services.ecf_provider import (
    ECFProviderError, current_tenant, get_ecf_provider, tenant_provider_key,
)
from .services.nexconnect.provider import PROVIDER_KEY as NEXCONNECT, nexconnect_invoice_id

logger = logging.getLogger(__name__)


def provider_error_status(error: ECFProviderError) -> int:
    """502 si NexConnect no respondió o falló (5xx); 400 para lo demás."""
    from .services.nexconnect.client import NexConnectError
    cause = error.__cause__
    if isinstance(cause, NexConnectError) and (cause.status_code is None or cause.status_code >= 500):
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_400_BAD_REQUEST


NEXCONNECT_DIRECT_FLOW_ERROR = (
    'Este tenant emite sus e-CF vía NexConnect: use "Emitir vía NexConnect" '
    '(POST /api/billing/invoices/{id}/emit/). NexConnect asigna el e-NCF, firma y envía a la DGII.'
)


class DigitalCertificateViewSet(viewsets.ModelViewSet):
    """CRUD para certificados digitales."""
    queryset = DigitalCertificate.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return DigitalCertificateUploadSerializer
        return DigitalCertificateSerializer


class FiscalSequenceViewSet(viewsets.ModelViewSet):
    """CRUD para secuencias fiscales e-NCF."""
    queryset = FiscalSequence.objects.all()
    serializer_class = FiscalSequenceSerializer
    permission_classes = [IsAuthenticated]


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    CRUD de facturas electrónicas con acciones para:
    - Flujo directo (certificado propio): generar XML, firmar, enviar a DGII,
      consultar estado en DGII.
    - Flujo NexConnect (``tenant.ecf_provider == 'nexconnect'``): emitir y
      actualizar estado. El flujo directo queda bloqueado para esos tenants.
    """
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]

    def _refuse_direct_flow(self):
        """Respuesta 400 si el tenant emite vía NexConnect; None si puede usar el flujo directo."""
        if tenant_provider_key(current_tenant()) == NEXCONNECT:
            return Response(
                {'error': NEXCONNECT_DIRECT_FLOW_ERROR, 'code': 'provider_nexconnect'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='generate-ecf')
    def generate_ecf(self, request, pk=None):
        """
        Genera el XML del e-CF para una factura.
        Asigna e-NCF de la secuencia activa.
        """
        refused = self._refuse_direct_flow()
        if refused:
            return refused

        invoice = self.get_object()

        if invoice.status not in ('draft',):
            return Response(
                {'error': 'Solo se puede generar XML para facturas en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener secuencia fiscal activa para el tipo
        try:
            sequence = FiscalSequence.objects.filter(
                ecf_type=invoice.ecf_type,
                is_active=True,
            ).first()

            if not sequence:
                return Response(
                    {'error': f'No hay secuencia fiscal activa para tipo {invoice.ecf_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            encf = sequence.get_next_encf()
            if not encf:
                return Response(
                    {'error': 'Secuencia fiscal agotada'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Asignar datos del tenant como emisor
            from django.db import connection
            from apps.tenants.models import Tenant
            tenant = Tenant.objects.get(schema_name=connection.schema_name)

            invoice.encf_number = encf
            invoice.fiscal_sequence = sequence
            invoice.emisor_rnc = tenant.tax_id or ''
            invoice.emisor_razon_social = tenant.business_name or tenant.name

            # Generar XML
            generator = ECFGenerator(invoice)
            invoice.xml_content = generator.generate()
            invoice.status = 'generated'
            invoice.save()

            return Response(
                InvoiceDetailSerializer(invoice).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f'Error generando e-CF: {e}')
            return Response(
                {'error': f'Error generando e-CF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='sign')
    def sign_ecf(self, request, pk=None):
        """Firma digitalmente el XML del e-CF."""
        refused = self._refuse_direct_flow()
        if refused:
            return refused

        invoice = self.get_object()

        if invoice.status != 'generated':
            return Response(
                {'error': 'Solo se puede firmar una factura con XML generado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        certificate_id = request.data.get('certificate_id')
        if not certificate_id:
            # Usar certificado activo por defecto
            cert = DigitalCertificate.objects.filter(is_active=True).first()
        else:
            cert = DigitalCertificate.objects.filter(id=certificate_id).first()

        if not cert:
            return Response(
                {'error': 'No hay certificado digital disponible'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            signer = ECFSigner(
                certificate_path=cert.certificate_file.path if cert.certificate_file else None,
                certificate_password=cert.certificate_password
            )
            invoice.signed_xml = signer.sign_xml(invoice.xml_content)
            invoice.certificate = cert
            invoice.status = 'signed'
            invoice.save()

            return Response(
                InvoiceDetailSerializer(invoice).data,
                status=status.HTTP_200_OK
            )
        except ECFSignerError as e:
            return Response(
                {'error': f'Error firmando e-CF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='submit-dgii')
    def submit_to_dgii(self, request, pk=None):
        """Envía el e-CF firmado a la DGII."""
        refused = self._refuse_direct_flow()
        if refused:
            return refused

        invoice = self.get_object()

        if invoice.status != 'signed':
            return Response(
                {'error': 'Solo se puede enviar una factura firmada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cert = invoice.certificate
        if not cert:
            return Response(
                {'error': 'No hay certificado asociado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        environment = request.data.get('environment', 'testecf')

        try:
            client = DGIIClient(
                environment=environment,
                certificate_path=cert.certificate_file.path if cert.certificate_file else None,
                certificate_password=cert.certificate_password
            )
            result = client.submit_ecf(invoice)

            return Response(
                {
                    'message': 'e-CF enviado a DGII exitosamente',
                    'trackid': invoice.dgii_trackid,
                    'invoice': InvoiceDetailSerializer(invoice).data,
                },
                status=status.HTTP_200_OK
            )
        except DGIIClientError as e:
            return Response(
                {'error': f'Error enviando a DGII: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

    @action(detail=True, methods=['get'], url_path='dgii-status')
    def check_dgii_status(self, request, pk=None):
        """Consulta el estado de un e-CF en la DGII."""
        invoice = self.get_object()

        if nexconnect_invoice_id(invoice):
            return Response(
                {'error': 'Esta factura se emitió vía NexConnect: use "Actualizar estado" '
                          '(POST /api/billing/invoices/{id}/refresh-status/).',
                 'code': 'provider_nexconnect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not invoice.dgii_trackid:
            return Response(
                {'error': 'Esta factura no ha sido enviada a la DGII'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cert = invoice.certificate
        environment = request.query_params.get('environment', 'testecf')

        try:
            client = DGIIClient(
                environment=environment,
                certificate_path=cert.certificate_file.path if cert and cert.certificate_file else None,
                certificate_password=cert.certificate_password if cert else None,
            )
            result = client.query_result(invoice)
            invoice.refresh_from_db()

            return Response(
                {
                    'dgii_status': invoice.dgii_status,
                    'dgii_response': invoice.dgii_response,
                    'invoice': InvoiceDetailSerializer(invoice).data,
                },
                status=status.HTTP_200_OK
            )
        except DGIIClientError as e:
            return Response(
                {'error': f'Error consultando DGII: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

    @action(detail=True, methods=['post'])
    def emit(self, request, pk=None):
        """
        Emite la factura vía NexConnect (un solo paso): NexConnect asigna el
        e-NCF, firma y envía a la DGII en segundo plano. El estado final llega
        por webhook o con ``refresh-status``.
        """
        invoice = self.get_object()
        tenant = current_tenant()
        if tenant_provider_key(tenant) != NEXCONNECT:
            return Response(
                {'error': 'La emisión en un paso es solo para tenants con NexConnect; '
                          'use el flujo Generar XML → Firmar → Enviar a DGII.',
                 'code': 'provider_not_nexconnect'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = get_ecf_provider(tenant).submit_invoice(invoice)
        except ECFProviderError as e:
            return Response({'error': str(e)}, status=provider_error_status(e))

        return Response({
            'message': result.get('message'),
            'status': result.get('status'),
            'ncf': result.get('ncf'),
            'invoice': InvoiceDetailSerializer(invoice, context={'tenant': tenant}).data,
        })

    @action(detail=True, methods=['post'], url_path='refresh-status')
    def refresh_status(self, request, pk=None):
        """Consulta a NexConnect el estado de una factura emitida por NexConnect."""
        invoice = self.get_object()
        tenant = current_tenant()
        if not nexconnect_invoice_id(invoice):
            return Response(
                {'error': 'La factura no ha sido emitida vía NexConnect'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = get_ecf_provider(tenant).query_status(invoice)
        except ECFProviderError as e:
            return Response({'error': str(e)}, status=provider_error_status(e))

        return Response({
            'status': result.get('status'),
            'is_final': result.get('is_final'),
            'invoice': InvoiceDetailSerializer(invoice, context={'tenant': tenant}).data,
        })

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Lista el historial de envíos a DGII de una factura."""
        invoice = self.get_object()
        submissions = invoice.submissions.all()
        serializer = ECFSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)


class ECFSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Historial de envíos a DGII (solo lectura)."""
    queryset = ECFSubmission.objects.all()
    serializer_class = ECFSubmissionSerializer
    permission_classes = [IsAuthenticated]


class ECFProviderViewSet(viewsets.ViewSet):
    """
    Endpoints para gestión del proveedor e-CF configurado.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'patch'], url_path='config')
    def config(self, request):
        """
        GET: proveedor, ambiente y si hay API key (la key nunca se devuelve).
        PATCH: ``ecf_provider``, ``dgii_environment``, ``api_key`` (solo escritura,
        se guarda cifrada) o ``clear_api_key``. Solo dueño/admin del tenant.
        """
        tenant = current_tenant()
        if tenant is None:
            return Response({'error': 'No se pudo determinar el tenant'},
                            status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            return Response(ECFProviderConfigSerializer(tenant).data)

        user = request.user
        if not (getattr(user, 'is_tenant_owner', False) or getattr(user, 'role', None) == 'admin'
                or user.is_superuser):
            return Response(
                {'error': 'Solo el dueño o un administrador puede cambiar la facturación electrónica.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ECFProviderConfigSerializer(tenant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='status')
    def provider_status(self, request):
        """Prueba la conexión con el proveedor e-CF del tenant."""
        try:
            provider = get_ecf_provider(current_tenant())
            result = provider.test_connection()
            return Response(result)
        except ECFProviderError as e:
            return Response({
                'status': 'not_configured',
                'error': str(e),
            }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit_invoice(self, request):
        """Submit an invoice via the configured provider."""
        from .services.ecf_provider import get_ecf_provider, ECFProviderError
        from .models import Invoice

        invoice_id = request.data.get('invoice_id')
        if not invoice_id:
            return Response({'error': 'invoice_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        try:
            provider = get_ecf_provider()
            result = provider.submit_invoice(invoice)
            return Response(result)
        except ECFProviderError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=False, methods=['post'], url_path='query')
    def query_invoice(self, request):
        """Query status of a submitted invoice."""
        from .services.ecf_provider import get_ecf_provider, ECFProviderError
        from .models import Invoice

        invoice_id = request.data.get('invoice_id')
        if not invoice_id:
            return Response({'error': 'invoice_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        try:
            provider = get_ecf_provider()
            result = provider.query_status(invoice)
            return Response(result)
        except ECFProviderError as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel_invoice(self, request):
        """Anula un e-CF vía el proveedor (NexConnect: emite una Nota de Crédito E34)."""
        from .services.ecf_provider import get_ecf_provider, ECFProviderError
        from .models import Invoice

        invoice_id = request.data.get('invoice_id')
        reason = (request.data.get('reason') or '').strip()
        if not invoice_id:
            return Response({'error': 'invoice_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': 'reason requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        try:
            provider = get_ecf_provider()
            result = provider.cancel_invoice(invoice, reason)
            return Response(result)
        except ECFProviderError as e:
            # 400 para reglas de negocio (no aceptada, ya anulada…); 502 si NexConnect no respondió.
            return Response({'error': str(e)}, status=provider_error_status(e))


class DGIIReportViewSet(viewsets.ViewSet):
    """
    Endpoints para generar reportes DGII 606 y 607.
    
    Usage:
        GET /api/billing/dgii-reports/607/?year=2026&month=3  → summary JSON
        GET /api/billing/dgii-reports/607/csv/?year=2026&month=3  → CSV download
        GET /api/billing/dgii-reports/606/?year=2026&month=3  → summary JSON
        GET /api/billing/dgii-reports/606/csv/?year=2026&month=3  → CSV download
    """
    permission_classes = [IsAuthenticated]

    def _parse_period(self, request):
        """Extract year and month from query params"""
        now = timezone.now()
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
        except (ValueError, TypeError):
            return None, None, Response(
                {'error': 'Parámetros year/month inválidos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if month < 1 or month > 12:
            return None, None, Response(
                {'error': 'Mes debe estar entre 1 y 12'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return year, month, None

    @action(detail=False, methods=['get'], url_path='607')
    def report_607_summary(self, request):
        """Resumen del reporte 607 (ventas/ingresos) para el período"""
        from .reports_dgii import DGIIReport607

        year, month, err = self._parse_period(request)
        if err:
            return err

        report = DGIIReport607(year, month)
        summary = report.get_summary()
        data = report.generate_data()

        # Add row details (without internal _ fields)
        detail_rows = []
        for row in data:
            detail_rows.append({
                'cliente': row['_customer_name'],
                'rnc_cedula': row['rnc_cedula'],
                'prestamo': row['_loan_number'],
                'pago': row['_payment_number'],
                'fecha': row['fecha_comprobante'],
                'monto': row['monto_facturado'],
                'interes': row['_interest_paid'],
                'capital': row['_principal_paid'],
                'mora': row['_late_fee_paid'],
                'metodo_efectivo': row['efectivo'],
                'metodo_cheque': row['cheque_transferencia'],
                'metodo_tarjeta': row['tarjeta'],
            })

        return Response({
            'tipo': '607',
            'descripcion': 'Ventas de Bienes y Servicios',
            'resumen': summary,
            'detalle': detail_rows,
        })

    @action(detail=False, methods=['get'], url_path='607/csv')
    def report_607_csv(self, request):
        """Descargar reporte 607 en formato CSV (compatible DGII)"""
        from .reports_dgii import DGIIReport607
        from django.http import HttpResponse

        year, month, err = self._parse_period(request)
        if err:
            return err

        report = DGIIReport607(year, month)
        csv_content = report.generate_csv()

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="607-{year}{month:02d}.csv"'
        return response

    @action(detail=False, methods=['get'], url_path='606')
    def report_606_summary(self, request):
        """Resumen del reporte 606 (compras/gastos) para el período"""
        from .reports_dgii import DGIIReport606

        year, month, err = self._parse_period(request)
        if err:
            return err

        report = DGIIReport606(year, month)
        summary = report.get_summary()

        return Response({
            'tipo': '606',
            'descripcion': 'Compras de Bienes y Servicios',
            'resumen': summary,
        })

    @action(detail=False, methods=['get'], url_path='606/csv')
    def report_606_csv(self, request):
        """Descargar reporte 606 en formato CSV (template — gastos no implementados)"""
        from .reports_dgii import DGIIReport606
        from django.http import HttpResponse

        year, month, err = self._parse_period(request)
        if err:
            return err

        report = DGIIReport606(year, month)
        csv_content = report.generate_csv()

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="606-{year}{month:02d}.csv"'
        return response
