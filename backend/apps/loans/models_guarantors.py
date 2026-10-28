"""
Guarantor model for loan guarantors (garantes/fiadores)
"""
from django.db import models
from djmoney.models.fields import MoneyField
from phonenumber_field.modelfields import PhoneNumberField
from apps.core.models import UUIDModel, AuditModel
from apps.core.storage import tenant_upload_to
from .utils_ids import normalize_id_number


class Guarantor(UUIDModel, AuditModel):
    """
    Guarantor (Garante/Fiador) linked to a loan.
    Dominican financieras typically require 1-3 guarantors per loan.
    """
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.CASCADE,
        related_name='guarantors'
    )

    # Personal Info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    id_type = models.CharField(
        max_length=20,
        choices=[('cedula', 'Cédula'), ('passport', 'Pasaporte'), ('rnc', 'RNC')]
    )
    id_number = models.CharField(max_length=50)
    # Sólo dígitos de id_number: permite buscar «garante de otros clientes» con índice.
    id_number_digits = models.CharField(max_length=20, db_index=True, editable=False, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        blank=True
    )

    # Contact
    phone = PhoneNumberField()
    alternate_phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Address
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)

    # Employment
    employer_name = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    monthly_income = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='DOP',
        null=True,
        blank=True
    )

    # Relationship to borrower
    relationship = models.CharField(
        max_length=20,
        choices=[
            ('spouse', 'Cónyuge'),
            ('parent', 'Padre/Madre'),
            ('sibling', 'Hermano/a'),
            ('friend', 'Amigo/a'),
            ('business_partner', 'Socio'),
            ('coworker', 'Compañero trabajo'),
            ('other', 'Otro'),
        ]
    )

    # Documents
    id_document = models.FileField(
        upload_to=tenant_upload_to('guarantor_documents/ids'),
        max_length=255,
        blank=True,
        null=True
    )
    proof_of_income = models.FileField(
        upload_to=tenant_upload_to('guarantor_documents/income'),
        max_length=255,
        blank=True,
        null=True
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Activo'),
            ('released', 'Liberado'),
            ('defaulted', 'En mora'),
        ],
        default='active'
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'loan_guarantors'
        ordering = ['loan', 'last_name']

    def save(self, *args, **kwargs):
        self.id_number_digits = normalize_id_number(self.id_number)[:20]
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'id_number' in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'id_number_digits'}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.loan.loan_number}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
