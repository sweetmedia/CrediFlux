"""
DRF Serializers for the Billing app.
"""
from rest_framework import serializers
from .models import (
    DigitalCertificate, FiscalSequence, Invoice, InvoiceItem, ECFSubmission
)


class DigitalCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalCertificate
        fields = [
            'id', 'name', 'issuer', 'serial_number',
            'valid_from', 'valid_until', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DigitalCertificateUploadSerializer(serializers.ModelSerializer):
    """Serializer para subir certificado con password."""
    class Meta:
        model = DigitalCertificate
        fields = [
            'id', 'name', 'certificate_file', 'certificate_password',
            'is_active',
        ]
        extra_kwargs = {
            'certificate_password': {'write_only': True},
        }


class FiscalSequenceSerializer(serializers.ModelSerializer):
    available_count = serializers.ReadOnlyField()
    is_exhausted = serializers.ReadOnlyField()
    ecf_type_display = serializers.CharField(source='get_ecf_type_display', read_only=True)

    class Meta:
        model = FiscalSequence
        fields = [
            'id', 'ecf_type', 'ecf_type_display', 'prefix',
            'range_from', 'range_to', 'current_number',
            'expiration_date', 'is_active', 'authorization_number',
            'available_count', 'is_exhausted',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'available_count', 'is_exhausted', 'created_at', 'updated_at']


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'line_number', 'description', 'quantity',
            'unit_price', 'unit_price_currency',
            'discount_amount', 'discount_amount_currency',
            'itbis_rate', 'itbis_amount', 'itbis_amount_currency',
            'total', 'total_currency',
        ]
        read_only_fields = ['id', 'itbis_amount', 'total']


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listados."""
    ecf_type_display = serializers.CharField(source='get_ecf_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'encf_number', 'ecf_type', 'ecf_type_display',
            'comprador_razon_social', 'comprador_rnc',
            'total', 'total_currency',
            'status', 'status_display',
            'issue_date', 'due_date',
            'dgii_status', 'dgii_submitted_at',
            'created_at',
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle."""
    items = InvoiceItemSerializer(many=True, read_only=True)
    ecf_type_display = serializers.CharField(source='get_ecf_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'encf_number', 'ecf_type', 'ecf_type_display',
            'fiscal_sequence', 'security_code',
            'status', 'status_display',
            # Emisor
            'emisor_rnc', 'emisor_razon_social',
            # Comprador
            'comprador_rnc', 'comprador_razon_social',
            # Vinculación
            'loan', 'payment', 'customer', 'reference_invoice',
            # Fechas
            'issue_date', 'due_date',
            'payment_method', 'payment_method_display',
            # Totales
            'subtotal', 'subtotal_currency',
            'total_itbis', 'total_itbis_currency',
            'total_discount', 'total_discount_currency',
            'total', 'total_currency',
            # DGII
            'dgii_trackid', 'dgii_status', 'dgii_response', 'dgii_submitted_at',
            # XML
            'xml_content', 'signed_xml',
            'certificate',
            # Items
            'items',
            # Meta
            'notes', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'id', 'encf_number', 'xml_content', 'signed_xml',
            'dgii_trackid', 'dgii_status', 'dgii_response', 'dgii_submitted_at',
            'created_at', 'updated_at', 'created_by',
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear factura con items."""
    items = InvoiceItemSerializer(many=True)

    class Meta:
        model = Invoice
        fields = [
            'ecf_type', 'customer', 'loan', 'payment',
            'issue_date', 'due_date', 'payment_method',
            'reference_invoice', 'notes', 'items',
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        return invoice


class ECFSubmissionSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    environment_display = serializers.CharField(source='get_environment_display', read_only=True)

    class Meta:
        model = ECFSubmission
        fields = [
            'id', 'invoice', 'action', 'action_display',
            'environment', 'environment_display',
            'trackid', 'response_status', 'response_body',
            'http_status_code', 'error_message', 'submitted_at',
        ]
        read_only_fields = ['id', 'submitted_at']
