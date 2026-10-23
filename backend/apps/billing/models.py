"""
Models for the Billing (Facturación Electrónica) app.
Handles e-CF generation, digital signing, and DGII submission.
"""
from decimal import Decimal
from django.db import models, transaction
from django.core.validators import MinValueValidator
from djmoney.models.fields import MoneyField
from apps.core.models import UUIDModel, AuditModel, TimeStampedModel
from .constants import (
    ECF_TYPE_CHOICES, DGII_ENV_CHOICES, INVOICE_STATUS_CHOICES,
    ITBIS_RATE_CHOICES, PAYMENT_METHOD_CHOICES,
)


class DigitalCertificate(UUIDModel, TimeStampedModel):
    """
    Certificado digital para firma de e-CF.
    Cada tenant puede tener múltiples certificados (rotación).
    """
    name = models.CharField(
        max_length=255,
        help_text='Nombre descriptivo del certificado'
    )
    certificate_file = models.FileField(
        upload_to='billing/certificates/',
        help_text='Archivo del certificado digital (.p12 / .pfx)'
    )
    # Password encriptado — en producción usar django-encrypted-model-fields
    certificate_password = models.CharField(
        max_length=255,
        help_text='Contraseña del certificado (almacenada encriptada)'
    )
    issuer = models.CharField(
        max_length=255,
        blank=True,
        help_text='Entidad emisora del certificado'
    )
    serial_number = models.CharField(
        max_length=255,
        blank=True,
        help_text='Número de serie del certificado'
    )
    valid_from = models.DateTimeField(
        null=True, blank=True,
        help_text='Fecha de inicio de validez'
    )
    valid_until = models.DateTimeField(
        null=True, blank=True,
        help_text='Fecha de expiración del certificado'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Certificado activo para firmar e-CF'
    )

    class Meta:
        verbose_name = 'Certificado Digital'
        verbose_name_plural = 'Certificados Digitales'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        status = '✅' if self.is_active else '❌'
        return f'{status} {self.name} ({self.issuer})'


class FiscalSequence(UUIDModel, TimeStampedModel):
    """
    Secuencias de Números de Comprobantes Fiscales Electrónicos (e-NCF).
    Autorizadas por la DGII para cada tipo de e-CF.
    """
    ecf_type = models.CharField(
        max_length=2,
        choices=ECF_TYPE_CHOICES,
        help_text='Tipo de comprobante fiscal electrónico'
    )
    prefix = models.CharField(
        max_length=3,
        help_text='Prefijo de la secuencia (ej: E31, E32)'
    )
    range_from = models.BigIntegerField(
        help_text='Inicio del rango autorizado'
    )
    range_to = models.BigIntegerField(
        help_text='Fin del rango autorizado'
    )
    current_number = models.BigIntegerField(
        help_text='Próximo número a utilizar'
    )
    expiration_date = models.DateField(
        null=True, blank=True,
        help_text='Fecha de vencimiento de la secuencia'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Secuencia activa para emisión'
    )
    authorization_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Número de autorización DGII'
    )

    class Meta:
        verbose_name = 'Secuencia Fiscal'
        verbose_name_plural = 'Secuencias Fiscales'
        ordering = ['ecf_type', '-is_active']
        unique_together = ['ecf_type', 'prefix', 'range_from']

    def __str__(self):
        used = self.current_number - self.range_from
        total = self.range_to - self.range_from + 1
        return f'{self.get_ecf_type_display()} [{self.prefix}{self.range_from}-{self.range_to}] ({used}/{total} usados)'

    @property
    def available_count(self):
        """Cantidad de secuencias disponibles."""
        return max(0, self.range_to - self.current_number + 1)

    @property
    def is_exhausted(self):
        """True si la secuencia está agotada."""
        return self.current_number > self.range_to

    def get_next_encf(self):
        """
        Obtiene el próximo e-NCF disponible y avanza el contador.
        Returns: str (ej: 'E310000000001') or None si agotada.
        """
        with transaction.atomic():
            # Relee la fila bajo bloqueo: dos emisiones concurrentes (o una
            # instancia desactualizada) nunca reciben el mismo número.
            locked = type(self).objects.select_for_update().get(pk=self.pk)
            self.current_number = locked.current_number
            self.is_active = locked.is_active
            if locked.is_exhausted or not locked.is_active:
                return None
            encf = f'{locked.prefix}{str(locked.current_number).zfill(10)}'
            locked.current_number += 1
            locked.save(update_fields=['current_number'])
        self.current_number = locked.current_number
        return encf


class Invoice(UUIDModel, AuditModel):
    """
    Factura electrónica (e-CF).
    Puede estar vinculada a un préstamo y/o pago específico.
    """
    # Vinculación con préstamos
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
        help_text='Préstamo asociado'
    )
    payment = models.ForeignKey(
        'loans.LoanPayment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
        help_text='Pago de préstamo asociado'
    )
    customer = models.ForeignKey(
        'loans.Customer',
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text='Cliente/comprador'
    )

    # Identificación fiscal
    ecf_type = models.CharField(
        max_length=2,
        choices=ECF_TYPE_CHOICES,
        default='31',
        help_text='Tipo de comprobante fiscal electrónico'
    )
    encf_number = models.CharField(
        max_length=13,
        unique=True,
        null=True, blank=True,
        help_text='Número de Comprobante Fiscal Electrónico (e-NCF)'
    )
    fiscal_sequence = models.ForeignKey(
        FiscalSequence,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='invoices',
        help_text='Secuencia fiscal utilizada'
    )
    security_code = models.CharField(
        max_length=6,
        blank=True,
        help_text='Código de seguridad para QR'
    )

    # Status
    status = models.CharField(
        max_length=30,
        choices=INVOICE_STATUS_CHOICES,
        default='draft',
        help_text='Estado actual de la factura'
    )

    # Datos del emisor (snapshot al momento de emisión)
    emisor_rnc = models.CharField(
        max_length=11,
        blank=True,
        help_text='RNC/Cédula del emisor'
    )
    emisor_razon_social = models.CharField(
        max_length=255,
        blank=True,
        help_text='Razón social del emisor'
    )

    # Datos del comprador (snapshot)
    comprador_rnc = models.CharField(
        max_length=11,
        blank=True,
        help_text='RNC/Cédula del comprador'
    )
    comprador_razon_social = models.CharField(
        max_length=255,
        blank=True,
        help_text='Nombre/Razón social del comprador'
    )

    # Fechas
    issue_date = models.DateField(
        help_text='Fecha de emisión'
    )
    due_date = models.DateField(
        null=True, blank=True,
        help_text='Fecha de vencimiento del pago'
    )

    # Forma de pago
    payment_method = models.CharField(
        max_length=2,
        choices=PAYMENT_METHOD_CHOICES,
        default='04',
        help_text='Forma de pago'
    )

    # Totales
    subtotal = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Subtotal antes de impuestos'
    )
    total_itbis = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Total ITBIS (impuesto)'
    )
    total_discount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Total descuentos'
    )
    total = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Monto total de la factura'
    )

    # XML y firma
    xml_content = models.TextField(
        blank=True,
        help_text='XML del e-CF generado (sin firmar)'
    )
    signed_xml = models.TextField(
        blank=True,
        help_text='XML del e-CF firmado digitalmente'
    )
    certificate = models.ForeignKey(
        DigitalCertificate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
        help_text='Certificado utilizado para firmar'
    )

    # Respuesta DGII
    dgii_trackid = models.CharField(
        max_length=100,
        blank=True,
        help_text='TrackId recibido de la DGII'
    )
    dgii_status = models.CharField(
        max_length=50,
        blank=True,
        help_text='Estado en la DGII'
    )
    dgii_response = models.JSONField(
        null=True, blank=True,
        help_text='Respuesta completa de la DGII (JSON)'
    )
    dgii_submitted_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Fecha/hora de envío a DGII'
    )

    # Notas
    notes = models.TextField(
        blank=True,
        help_text='Notas internas'
    )

    # Referencia (para notas de crédito/débito)
    reference_invoice = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='credit_debit_notes',
        help_text='Factura original (para NC/ND)'
    )

    class Meta:
        verbose_name = 'Factura Electrónica'
        verbose_name_plural = 'Facturas Electrónicas'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['encf_number']),
            models.Index(fields=['status']),
            models.Index(fields=['ecf_type']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['dgii_trackid']),
        ]

    def __str__(self):
        encf = self.encf_number or 'SIN-NCF'
        return f'{encf} - {self.comprador_razon_social} ({self.total})'

    def recalculate_totals(self):
        """
        Recalcula subtotal, ITBIS, descuento y total sumando las líneas
        (cada línea se recalcula con ``InvoiceItem.calculate_totals``).
        """
        subtotal = total_itbis = total_discount = Decimal('0.00')
        for item in self.items.all():
            item.calculate_totals()
            item.save(update_fields=['itbis_amount', 'itbis_amount_currency',
                                     'total', 'total_currency'])
            total_discount += item.discount_amount.amount
            total_itbis += item.itbis_amount.amount
            subtotal += item.total.amount - item.itbis_amount.amount
        self.subtotal = subtotal
        self.total_itbis = total_itbis
        self.total_discount = total_discount
        self.total = subtotal + total_itbis
        self.save(update_fields=[
            'subtotal', 'subtotal_currency', 'total_itbis', 'total_itbis_currency',
            'total_discount', 'total_discount_currency', 'total', 'total_currency',
        ])


class InvoiceItem(UUIDModel):
    """
    Línea de detalle de una factura electrónica.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Factura a la que pertenece'
    )
    line_number = models.PositiveIntegerField(
        help_text='Número de línea'
    )
    description = models.CharField(
        max_length=500,
        help_text='Descripción del bien o servicio'
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text='Cantidad'
    )
    unit_price = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        help_text='Precio unitario'
    )
    discount_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Monto de descuento'
    )
    itbis_rate = models.CharField(
        max_length=2,
        choices=ITBIS_RATE_CHOICES,
        default='18',
        help_text='Tasa de ITBIS aplicable'
    )
    itbis_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Monto de ITBIS calculado'
    )
    total = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        default=Decimal('0.00'),
        help_text='Total de la línea (cantidad × precio - descuento + ITBIS)'
    )

    class Meta:
        verbose_name = 'Línea de Factura'
        verbose_name_plural = 'Líneas de Factura'
        ordering = ['invoice', 'line_number']
        unique_together = ['invoice', 'line_number']

    def __str__(self):
        return f'#{self.line_number} - {self.description[:50]} ({self.total})'

    def calculate_totals(self):
        """Calcula ITBIS y total de la línea."""
        cents = Decimal('0.01')
        subtotal = (self.quantity * self.unit_price.amount - self.discount_amount.amount).quantize(cents)
        itbis_rate = Decimal(self.itbis_rate) / Decimal('100')
        # Local en Decimal: tras asignarlo, self.itbis_amount es Money y no suma con Decimal.
        itbis_amount = (subtotal * itbis_rate).quantize(cents)
        self.itbis_amount = itbis_amount
        self.total = subtotal + itbis_amount


class ECFSubmission(UUIDModel, TimeStampedModel):
    """
    Registro de cada envío/consulta a la DGII.
    Permite tracking del historial de comunicación con la DGII.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='submissions',
        help_text='Factura enviada'
    )
    action = models.CharField(
        max_length=30,
        choices=[
            ('submit', 'Envío de e-CF'),
            ('query_status', 'Consulta de Estado'),
            ('query_result', 'Consulta de Resultado'),
            ('cancel', 'Anulación'),
            ('webhook', 'Webhook del proveedor'),
        ],
        help_text='Tipo de acción realizada'
    )
    environment = models.CharField(
        max_length=10,
        choices=DGII_ENV_CHOICES,
        help_text='Ambiente DGII utilizado'
    )
    trackid = models.CharField(
        max_length=100,
        blank=True,
        help_text='TrackId de la DGII'
    )
    request_xml = models.TextField(
        blank=True,
        help_text='XML enviado a la DGII'
    )
    response_status = models.CharField(
        max_length=50,
        blank=True,
        help_text='Estado de la respuesta'
    )
    response_body = models.JSONField(
        null=True, blank=True,
        help_text='Cuerpo completo de la respuesta'
    )
    http_status_code = models.IntegerField(
        null=True, blank=True,
        help_text='Código HTTP de la respuesta'
    )
    error_message = models.TextField(
        blank=True,
        help_text='Mensaje de error (si aplica)'
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha/hora del envío'
    )

    class Meta:
        verbose_name = 'Envío a DGII'
        verbose_name_plural = 'Envíos a DGII'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.get_action_display()} - {self.invoice.encf_number} ({self.response_status})'


class NexConnectWebhookEvent(UUIDModel, TimeStampedModel):
    """
    Evento de webhook de NexConnect ya recibido.

    ``event_id`` único: es la llave de idempotencia. NexConnect entrega
    at-least-once (reintentos, replays), así que un evento repetido se responde
    200 sin volver a aplicarse.
    """
    OUTCOME_CHOICES = [
        ('applied', 'Aplicado'),
        ('stale', 'Ignorado (más viejo que el estado actual)'),
        ('unmatched', 'Sin factura asociada'),
        ('mismatch', 'Factura con otro id de NexConnect'),
        ('ignored', 'Tipo de evento no manejado'),
    ]

    event_id = models.CharField(max_length=100, unique=True,
                                help_text='Id del evento (evt_…)')
    event_type = models.CharField(max_length=60, help_text='Tipo de evento (invoice.accepted, …)')
    event_created_at = models.DateTimeField(null=True, blank=True,
                                            help_text='Fecha del evento según NexConnect')
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='nexconnect_events', help_text='Factura afectada',
    )
    nexconnect_invoice_id = models.CharField(max_length=64, blank=True,
                                             help_text='Id de la factura en NexConnect')
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    payload = models.JSONField(null=True, blank=True,
                               help_text='Evento recibido (sin XML ni líneas)')

    class Meta:
        verbose_name = 'Evento de webhook NexConnect'
        verbose_name_plural = 'Eventos de webhook NexConnect'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} {self.event_id} ({self.outcome})'
