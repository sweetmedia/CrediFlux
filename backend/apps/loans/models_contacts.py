"""
Multi-contact model for customers.
Supports multiple phone numbers and emails per customer,
each with a type/label (personal, work, home, office, WhatsApp, etc.)
"""
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from apps.core.models import UUIDModel, TimeStampedModel


class CustomerPhone(UUIDModel, TimeStampedModel):
    """
    Multiple phone numbers per customer.
    """
    customer = models.ForeignKey(
        'loans.Customer',
        on_delete=models.CASCADE,
        related_name='phone_numbers',
    )
    phone = PhoneNumberField()
    phone_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile', 'Celular'),
            ('home', 'Casa'),
            ('work', 'Oficina'),
            ('landline', 'Fijo'),
            ('whatsapp', 'WhatsApp'),
            ('fax', 'Fax'),
            ('other', 'Otro'),
        ],
        default='mobile',
    )
    label = models.CharField(
        max_length=50, blank=True,
        help_text='Etiqueta personalizada (ej: "Celular esposa", "Oficina 2do piso")',
    )
    is_primary = models.BooleanField(default=False)
    is_whatsapp = models.BooleanField(default=False, help_text='Este número tiene WhatsApp')
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'customer_phones'
        ordering = ['-is_primary', 'phone_type']

    def __str__(self):
        label = self.label or self.get_phone_type_display()
        return f'{self.phone} ({label})'

    def save(self, *args, **kwargs):
        # If this is set as primary, unset other primaries
        if self.is_primary:
            CustomerPhone.objects.filter(
                customer=self.customer, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class CustomerEmail(UUIDModel, TimeStampedModel):
    """
    Multiple email addresses per customer.
    """
    customer = models.ForeignKey(
        'loans.Customer',
        on_delete=models.CASCADE,
        related_name='email_addresses',
    )
    email = models.EmailField()
    email_type = models.CharField(
        max_length=20,
        choices=[
            ('personal', 'Personal'),
            ('work', 'Trabajo'),
            ('business', 'Empresa'),
            ('other', 'Otro'),
        ],
        default='personal',
    )
    label = models.CharField(max_length=50, blank=True)
    is_primary = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'customer_emails'
        ordering = ['-is_primary', 'email_type']

    def __str__(self):
        label = self.label or self.get_email_type_display()
        return f'{self.email} ({label})'

    def save(self, *args, **kwargs):
        if self.is_primary:
            CustomerEmail.objects.filter(
                customer=self.customer, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
