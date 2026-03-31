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
    ECFSubmissionSerializer,
)
from .services.ecf_generator import ECFGenerator
from .services.ecf_signer import ECFSigner, ECFSignerError
from .services.dgii_client import DGIIClient, DGIIClientError

logger = logging.getLogger(__name__)


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
    - Generar XML (e-CF)
    - Firmar digitalmente
    - Enviar a DGII
    - Consultar estado en DGII
    """
    queryset = Invoice.objects.all()
    permission_classes = [IsAuthenticated]

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

    @action(detail=False, methods=['get'], url_path='status')
    def provider_status(self, request):
        """Test connection to the configured e-CF provider."""
        from .services.ecf_provider import get_ecf_provider, ECFProviderError

        try:
            provider = get_ecf_provider()
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
