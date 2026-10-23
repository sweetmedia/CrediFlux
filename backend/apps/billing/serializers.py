"""
DRF Serializers for the Billing app.
"""
from rest_framework import serializers

from apps.core.media import SignedFilesModelSerializer
from .models import (
    DigitalCertificate, FiscalSequence, Invoice, InvoiceItem, ECFSubmission
)

# Estados locales en los que la DGII ya no va a cambiar nada.
FINAL_INVOICE_STATUSES = {'accepted', 'conditionally_accepted', 'rejected', 'cancelled'}


class DigitalCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalCertificate
        fields = [
            'id', 'name', 'issuer', 'serial_number',
            'valid_from', 'valid_until', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DigitalCertificateUploadSerializer(SignedFilesModelSerializer):
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
        read_only_fields = [
            'id', 'current_number', 'available_count', 'is_exhausted', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        # El contador sólo lo avanza get_next_encf; una secuencia nueva arranca al inicio del rango.
        validated_data['current_number'] = validated_data['range_from']
        return super().create(validated_data)


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
    ecf_provider = serializers.SerializerMethodField(
        help_text='Flujo de emisión de esta factura: "nexconnect" (Emitir en un paso) o el '
                  'proveedor del tenant ("direct" = Generar XML → Firmar → Enviar)'
    )
    is_final = serializers.SerializerMethodField(
        help_text='La DGII ya resolvió la factura (aceptada, condicional, rechazada o anulada)'
    )
    dgii_error_message = serializers.SerializerMethodField()
    credit_notes = serializers.SerializerMethodField(
        help_text='Notas de crédito/débito que referencian esta factura (p. ej. la E34 de anulación)'
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'encf_number', 'ecf_type', 'ecf_type_display',
            'fiscal_sequence', 'security_code',
            'status', 'status_display',
            'ecf_provider', 'is_final', 'dgii_error_message', 'credit_notes',
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
            # Estado e identidad fiscal: sólo los fija el flujo (generate/sign/submit).
            'status', 'fiscal_sequence', 'certificate', 'security_code',
            'emisor_rnc', 'emisor_razon_social', 'comprador_rnc', 'comprador_razon_social',
            # Totales: salen de las líneas (Invoice.recalculate_totals).
            'subtotal', 'total_itbis', 'total_discount', 'total',
            'subtotal_currency', 'total_itbis_currency', 'total_discount_currency', 'total_currency',
        ]

    def get_ecf_provider(self, obj):
        from .services.nexconnect.provider import PROVIDER_KEY, nexconnect_invoice_id
        from .services.ecf_provider import current_tenant, tenant_provider_key

        # Una factura ya emitida por NexConnect sigue en ese flujo aunque el tenant cambie.
        if nexconnect_invoice_id(obj):
            return PROVIDER_KEY
        tenant = self.context.get('tenant') or current_tenant()
        return tenant_provider_key(tenant)

    def get_is_final(self, obj):
        return obj.status in FINAL_INVOICE_STATUSES

    def get_dgii_error_message(self, obj):
        data = obj.dgii_response if isinstance(obj.dgii_response, dict) else {}
        return data.get('dgii_error_message') or ''

    def get_credit_notes(self, obj):
        notes = obj.credit_debit_notes.all().order_by('created_at')
        return [
            {
                'id': str(note.id),
                'ecf_type': note.ecf_type,
                'encf_number': note.encf_number or '',
                'status': note.status,
                'status_display': note.get_status_display(),
                'created_at': note.created_at,
            }
            for note in notes
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


class ECFProviderConfigSerializer(serializers.Serializer):
    """
    Configuración e-CF del tenant. La API key es de solo escritura: se guarda
    cifrada y nunca se devuelve (solo ``has_api_key``).
    """
    ecf_provider = serializers.ChoiceField(choices=[], required=False)
    dgii_environment = serializers.ChoiceField(choices=[], required=False)
    api_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=True,
        style={'input_type': 'password'},
    )
    clear_api_key = serializers.BooleanField(write_only=True, required=False, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.tenants.models import Tenant
        self.fields['ecf_provider'].choices = Tenant._meta.get_field('ecf_provider').choices
        self.fields['dgii_environment'].choices = Tenant._meta.get_field('dgii_environment').choices

    def validate(self, attrs):
        if attrs.get('api_key') and attrs.get('clear_api_key'):
            raise serializers.ValidationError('Envíe api_key o clear_api_key, no ambos.')
        return attrs

    def validate_api_key(self, value):
        if value and not value.startswith('nxc_'):
            raise serializers.ValidationError('La API key de NexConnect empieza por nxc_')
        return value

    def update(self, tenant, validated_data):
        from .services.nexconnect.credentials import set_tenant_api_key

        update_fields = []
        for field in ('ecf_provider', 'dgii_environment'):
            if field in validated_data:
                setattr(tenant, field, validated_data[field])
                update_fields.append(field)
        if validated_data.get('api_key'):
            set_tenant_api_key(tenant, validated_data['api_key'], save=False)
            update_fields.append('ecf_provider_api_key')
        elif validated_data.get('clear_api_key'):
            tenant.ecf_provider_api_key = None
            update_fields.append('ecf_provider_api_key')
        if update_fields:
            tenant.save(update_fields=update_fields)
        return tenant

    def to_representation(self, tenant):
        from apps.tenants.models import Tenant
        from apps.core.crypto import SecretDecryptionError
        from .services.ecf_provider import tenant_provider_key
        from .services.nexconnect.credentials import (
            NexConnectCredentialsError, credentials_for_tenant,
        )

        try:
            is_test_key = credentials_for_tenant(tenant).is_test_key
        except (NexConnectCredentialsError, SecretDecryptionError):
            is_test_key = None  # sin key, formato no nxc_ o no descifrable

        def choices(field):
            return [{'value': v, 'label': l} for v, l in Tenant._meta.get_field(field).choices]

        return {
            'ecf_provider': tenant_provider_key(tenant),
            'dgii_environment': tenant.dgii_environment or 'testecf',
            'has_api_key': bool(tenant.ecf_provider_api_key),
            'is_test_key': is_test_key,
            'webhook_registered': bool(getattr(tenant, 'nexconnect_webhook_id', '')),
            'ecf_provider_choices': choices('ecf_provider'),
            'dgii_environment_choices': choices('dgii_environment'),
        }
