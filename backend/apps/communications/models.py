"""
Communications models for Email and WhatsApp messaging
"""
import uuid
from django.db import models
from django.conf import settings
from apps.loans.models import Customer


class Email(models.Model):
    """
    Model to store sent and received emails
    Multi-tenant aware via customer relationship
    """

    DIRECTION_CHOICES = [
        ('inbound', 'Recibido'),
        ('outbound', 'Enviado'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
        ('received', 'Recibido'),
    ]

    # Message metadata
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default='outbound',
        help_text='Dirección del correo (enviado o recibido)'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text='Estado del correo'
    )

    # Email addresses
    from_email = models.EmailField(
        max_length=255,
        help_text='Dirección de correo del remitente'
    )

    to_email = models.EmailField(
        max_length=255,
        help_text='Dirección de correo del destinatario'
    )

    cc = models.TextField(
        blank=True,
        null=True,
        help_text='Direcciones en copia (CC), separadas por comas'
    )

    bcc = models.TextField(
        blank=True,
        null=True,
        help_text='Direcciones en copia oculta (BCC), separadas por comas'
    )

    # Content
    subject = models.CharField(
        max_length=255,
        help_text='Asunto del correo'
    )

    body_text = models.TextField(
        help_text='Contenido del correo en texto plano'
    )

    body_html = models.TextField(
        blank=True,
        null=True,
        help_text='Contenido del correo en HTML'
    )

    # Metadata
    message_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text='ID único del mensaje de email'
    )

    in_reply_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID del mensaje al que responde'
    )

    references = models.TextField(
        blank=True,
        null=True,
        help_text='Referencias a otros mensajes'
    )

    # Attachments
    has_attachments = models.BooleanField(
        default=False,
        help_text='Indica si el correo tiene archivos adjuntos'
    )

    attachments_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata de archivos adjuntos (nombre, tamaño, tipo)'
    )

    # Relationships
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails',
        help_text='Cliente relacionado con el correo'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails',
        help_text='Usuario que envió o recibió el correo'
    )

    # Timestamps
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de envío'
    )

    received_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de recepción'
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de lectura'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación del registro'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Fecha de última actualización'
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si el envío falló'
    )

    retry_count = models.IntegerField(
        default=0,
        help_text='Número de intentos de reenvío'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['message_id']),
            models.Index(fields=['from_email']),
            models.Index(fields=['to_email']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['direction']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Email'
        verbose_name_plural = 'Emails'

    def __str__(self):
        direction_symbol = '→' if self.direction == 'outbound' else '←'
        return f"{direction_symbol} {self.subject} ({self.from_email} → {self.to_email})"


class WhatsAppMessage(models.Model):
    """
    Model to store WhatsApp messages
    Multi-tenant aware via customer relationship
    """

    DIRECTION_CHOICES = [
        ('inbound', 'Recibido'),
        ('outbound', 'Enviado'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
        ('received', 'Recibido'),
    ]

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Texto'),
        ('image', 'Imagen'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Documento'),
        ('location', 'Ubicación'),
        ('template', 'Plantilla'),
    ]

    # Message metadata
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default='outbound',
        help_text='Dirección del mensaje (enviado o recibido)'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Estado del mensaje'
    )

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        help_text='Tipo de mensaje'
    )

    # WhatsApp identifiers
    wa_message_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='ID único del mensaje de WhatsApp'
    )

    from_phone = models.CharField(
        max_length=50,
        help_text='Número de teléfono del remitente (formato E.164)'
    )

    to_phone = models.CharField(
        max_length=50,
        help_text='Número de teléfono del destinatario (formato E.164)'
    )

    # Content
    content = models.TextField(
        blank=True,
        null=True,
        help_text='Contenido del mensaje (texto)'
    )

    media_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text='URL del archivo multimedia (imagen, video, audio, documento)'
    )

    media_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Tipo MIME del archivo multimedia'
    )

    caption = models.TextField(
        blank=True,
        null=True,
        help_text='Leyenda para archivos multimedia'
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Metadata adicional del mensaje (ubicación, botones, etc.)'
    )

    # Relationships
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_messages',
        help_text='Cliente relacionado con el mensaje'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_messages',
        help_text='Usuario que envió o recibió el mensaje'
    )

    # Conversation grouping
    conversation_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text='ID de la conversación (normalmente el número del cliente)'
    )

    # Timestamps
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de envío'
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de entrega'
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora de lectura'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación del registro'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Fecha de última actualización'
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Mensaje de error si el envío falló'
    )

    retry_count = models.IntegerField(
        default=0,
        help_text='Número de intentos de reenvío'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wa_message_id']),
            models.Index(fields=['from_phone']),
            models.Index(fields=['to_phone']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
            models.Index(fields=['direction']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Mensaje de WhatsApp'
        verbose_name_plural = 'Mensajes de WhatsApp'

    def __str__(self):
        direction_symbol = '→' if self.direction == 'outbound' else '←'
        content_preview = self.content[:50] if self.content else f'[{self.message_type}]'
        return f"{direction_symbol} {content_preview} ({self.from_phone} → {self.to_phone})"


class Task(models.Model):
    """
    Task model for Kanban board task management
    Multi-tenant aware (shared model, isolated by tenant schema)
    """

    STATUS_CHOICES = [
        ('todo', 'Por Hacer'),
        ('in_progress', 'En Progreso'),
        ('review', 'En Revisión'),
        ('done', 'Completado'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='ID único de la tarea'
    )

    title = models.CharField(
        max_length=255,
        help_text='Título de la tarea'
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text='Descripción detallada de la tarea'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo',
        help_text='Estado actual de la tarea'
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        help_text='Prioridad de la tarea'
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text='Usuario asignado a la tarea'
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text='Cliente/Contacto relacionado con la tarea'
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha límite de la tarea'
    )

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Etiquetas de la tarea (lista de strings)'
    )

    position = models.IntegerField(
        default=0,
        help_text='Posición de la tarea en la columna (para ordenamiento)'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        help_text='Usuario que creó la tarea'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Fecha de creación'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Fecha de última actualización'
    )

    class Meta:
        ordering = ['position', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['assignee']),
            models.Index(fields=['customer']),
            models.Index(fields=['due_date']),
            models.Index(fields=['position']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        from datetime import date
        if self.due_date and self.status != 'done':
            return self.due_date < date.today()
        return False
