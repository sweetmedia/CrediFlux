"""
Collection management models for loan collections
"""
from django.db import models
from django.utils import timezone
from djmoney.models.fields import MoneyField
from decimal import Decimal
from apps.core.models import UUIDModel, TimeStampedModel


class CollectionReminder(UUIDModel, TimeStampedModel):
    """Sistema de recordatorios de pago"""

    loan_schedule = models.ForeignKey(
        'LoanSchedule',
        on_delete=models.CASCADE,
        related_name='collection_reminders'
    )
    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='collection_reminders'
    )
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='collection_reminders'
    )

    # Tipo de recordatorio
    REMINDER_TYPE_CHOICES = [
        ('upcoming_3', 'Pago Próximo (3 días antes)'),
        ('upcoming_1', 'Pago Próximo (1 día antes)'),
        ('due_today', 'Vence Hoy'),
        ('overdue_1', 'Atrasado 1 día'),
        ('overdue_3', 'Atrasado 3 días'),
        ('overdue_7', 'Atrasado 7 días'),
        ('overdue_15', 'Atrasado 15 días'),
        ('overdue_30', 'Atrasado 30 días'),
    ]
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)

    # Canal de comunicación
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('call', 'Llamada Telefónica'),
    ]
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)

    # Programación
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)

    # Estado
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Contenido
    message_content = models.TextField()

    # Tracking
    sent_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_reminders'
    )
    error_message = models.TextField(blank=True, null=True)

    # Respuesta del cliente (si aplica)
    customer_response = models.TextField(blank=True, null=True)
    response_received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'collection_reminders'
        ordering = ['-scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['loan', 'status']),
        ]

    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.customer} - {self.scheduled_for}"


class CollectionContact(UUIDModel, TimeStampedModel):
    """Historial de contactos con el cliente para cobranza"""

    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='collection_contacts'
    )
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='collection_contacts'
    )

    contact_date = models.DateTimeField(default=timezone.now)

    # Tipo de contacto
    CONTACT_TYPE_CHOICES = [
        ('phone_call', 'Llamada Telefónica'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('home_visit', 'Visita Domicilio'),
        ('office_visit', 'Visita Oficina'),
        ('meeting', 'Reunión Acordada'),
    ]
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPE_CHOICES)

    # Quien realizó el contacto
    contacted_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='collection_contacts_made'
    )

    # Resultado del contacto
    OUTCOME_CHOICES = [
        ('answered', 'Cliente Contestó/Atendió'),
        ('no_answer', 'No Contestó'),
        ('wrong_number', 'Número Equivocado'),
        ('promise_to_pay', 'Promesa de Pago'),
        ('payment_plan', 'Plan de Pagos Acordado'),
        ('partial_payment', 'Pago Parcial Recibido'),
        ('full_payment', 'Pago Completo Recibido'),
        ('dispute', 'Cliente Disputa la Deuda'),
        ('hardship', 'Dificultad Económica'),
        ('refused_to_pay', 'Se Niega a Pagar'),
        ('not_reachable', 'No Localizable'),
    ]
    outcome = models.CharField(max_length=30, choices=OUTCOME_CHOICES)

    # Promesa de pago
    promise_date = models.DateField(null=True, blank=True)
    promise_amount = MoneyField(
        max_digits=12,
        decimal_places=2,
        default_currency='USD',
        null=True,
        blank=True
    )
    promise_kept = models.BooleanField(
        null=True,
        blank=True,
        help_text='¿Cumplió la promesa de pago?'
    )

    # Notas del contacto
    notes = models.TextField(help_text='Detalles de la conversación')

    # Seguimiento
    next_contact_date = models.DateField(null=True, blank=True)
    requires_escalation = models.BooleanField(
        default=False,
        help_text='Requiere escalamiento a supervisor'
    )

    class Meta:
        db_table = 'collection_contacts'
        ordering = ['-contact_date']
        verbose_name = 'Collection Contact'
        verbose_name_plural = 'Collection Contacts'

    def __str__(self):
        return f"{self.get_contact_type_display()} - {self.customer} - {self.contact_date}"
