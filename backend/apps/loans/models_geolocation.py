"""
Geolocation models for collector tracking.
Tracks collector visits, check-ins, and GPS routes.
"""
from django.db import models
from django.conf import settings
from apps.core.models import UUIDModel, TimeStampedModel


class CollectorVisit(UUIDModel, TimeStampedModel):
    """
    Records a collector's visit to a customer location.
    Captures GPS coordinates, timestamp, and visit outcome.
    """
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collector_visits',
    )
    customer = models.ForeignKey(
        'loans.Customer',
        on_delete=models.CASCADE,
        related_name='collector_visits',
    )
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='collector_visits',
    )
    schedule = models.ForeignKey(
        'loans.LoanSchedule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='collector_visits',
    )

    # GPS Data
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True, help_text='GPS accuracy in meters')
    altitude = models.FloatField(null=True, blank=True, help_text='Altitude in meters')

    # Visit Details
    visit_type = models.CharField(
        max_length=20,
        choices=[
            ('collection', 'Cobro'),
            ('followup', 'Seguimiento'),
            ('verification', 'Verificación'),
            ('delivery', 'Entrega documento'),
            ('check_in', 'Check-in'),
        ],
        default='collection',
    )
    outcome = models.CharField(
        max_length=20,
        choices=[
            ('payment_collected', 'Pago cobrado'),
            ('promise_to_pay', 'Promesa de pago'),
            ('not_home', 'No se encontró'),
            ('refused', 'Se negó a pagar'),
            ('partial_payment', 'Pago parcial'),
            ('rescheduled', 'Reprogramado'),
            ('other', 'Otro'),
        ],
        blank=True,
    )
    notes = models.TextField(blank=True)

    # Payment collected (if any)
    amount_collected = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
        help_text='Amount collected during visit (if any)',
    )

    # Promise to pay
    promise_date = models.DateField(null=True, blank=True, help_text='Date customer promised to pay')
    promise_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True,
    )

    # Photo evidence (optional)
    photo = models.ImageField(
        upload_to='collector_visits/photos/',
        null=True, blank=True,
        help_text='Photo evidence of visit',
    )

    # Timestamps
    checked_in_at = models.DateTimeField(auto_now_add=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'loan_collector_visits'
        ordering = ['-checked_in_at']

    def __str__(self):
        return f'{self.collector} → {self.customer} ({self.checked_in_at.strftime("%d/%m/%Y")})'


class CollectorLocation(UUIDModel):
    """
    Real-time GPS pings from collectors in the field.
    Used for live tracking and route reconstruction.
    """
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gps_locations',
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    accuracy = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True, help_text='Speed in m/s')
    heading = models.FloatField(null=True, blank=True, help_text='Heading in degrees')
    battery_level = models.IntegerField(null=True, blank=True, help_text='Device battery %')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loan_collector_locations'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['collector', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.collector} @ {self.latitude},{self.longitude}'
