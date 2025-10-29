"""
Loan models for managing loans, customers, payments, and schedules
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from djmoney.models.fields import MoneyField
from phonenumber_field.modelfields import PhoneNumberField
from apps.core.models import TimeStampedModel, UUIDModel, AuditModel
from decimal import Decimal
import uuid


class Customer(UUIDModel, AuditModel):
    """
    Customer model for loan applicants
    """
    # Personal Information
    customer_id = models.CharField(max_length=50, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True, null=True
    )

    # Contact Information
    email = models.EmailField()
    phone = PhoneNumberField()
    alternate_phone = PhoneNumberField(blank=True, null=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Dominican Republic')
    postal_code = models.CharField(max_length=20)

    # Identification
    id_type = models.CharField(
        max_length=50,
        choices=[
            ('cedula', 'Cédula'),
            ('passport', 'Passport'),
            ('driver_license', 'Driver License'),
        ]
    )
    id_number = models.CharField(max_length=50, unique=True)
    id_expiry_date = models.DateField(blank=True, null=True)
    id_document = models.FileField(upload_to='customer_documents/ids/', blank=True, null=True)

    # Employment Information
    employment_status = models.CharField(
        max_length=50,
        choices=[
            ('employed', 'Employed'),
            ('self_employed', 'Self Employed'),
            ('unemployed', 'Unemployed'),
            ('retired', 'Retired'),
        ],
        blank=True, null=True
    )
    employer_name = models.CharField(max_length=200, blank=True, null=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    monthly_income = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        blank=True,
        null=True
    )

    # Financial Information
    credit_score = models.IntegerField(
        validators=[MinValueValidator(300), MaxValueValidator(850)],
        blank=True,
        null=True
    )

    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)

    # Profile Photo
    photo = models.ImageField(upload_to='customer_photos/', blank=True, null=True)

    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer_id']),
            models.Index(fields=['id_number']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.customer_id} - {self.get_full_name()}"

    def get_full_name(self):
        """Return customer's full name"""
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(filter(None, parts))

    def save(self, *args, **kwargs):
        if not self.customer_id:
            # Generate unique customer ID
            self.customer_id = f"CUS-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Loan(UUIDModel, AuditModel):
    """
    Loan model representing a loan agreement
    """
    # Loan Identification
    loan_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='loans'
    )

    # Loan Type
    LOAN_TYPE_CHOICES = [
        ('personal', 'Personal Loan'),
        ('auto', 'Auto Loan'),
        ('mortgage', 'Mortgage'),
        ('business', 'Business Loan'),
        ('student', 'Student Loan'),
        ('payday', 'Payday Loan'),
    ]
    loan_type = models.CharField(max_length=50, choices=LOAN_TYPE_CHOICES)

    # Loan Amount Details
    principal_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Annual interest rate in percentage"
    )
    term_months = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Loan term in months"
    )

    # Payment Details
    PAYMENT_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    payment_frequency = models.CharField(
        max_length=20,
        choices=PAYMENT_FREQUENCY_CHOICES,
        default='monthly'
    )
    payment_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        help_text="Regular payment amount"
    )

    # Dates
    application_date = models.DateField(default=timezone.now)
    approval_date = models.DateField(blank=True, null=True)
    rejection_date = models.DateField(blank=True, null=True)
    disbursement_date = models.DateField(blank=True, null=True)
    first_payment_date = models.DateField(blank=True, null=True)
    maturity_date = models.DateField(blank=True, null=True)

    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('paid', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('written_off', 'Written Off'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Balances
    outstanding_balance = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    total_paid = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    total_interest_paid = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    late_fees = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )

    # Loan Officer
    loan_officer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_loans'
    )

    # Approval/Rejection tracking
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans',
        help_text='User who approved this loan'
    )
    rejected_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_loans',
        help_text='User who rejected this loan'
    )
    approval_notes = models.TextField(blank=True, null=True, help_text='Notes from approval/rejection')

    # Additional Information
    purpose = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    terms_accepted = models.BooleanField(default=False)
    contract_document = models.FileField(
        upload_to='loan_contracts/',
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['loan_number']),
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"{self.loan_number} - {self.customer.get_full_name()}"

    def clean(self):
        """Validate Money fields"""
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        errors = {}

        # Validate principal_amount
        if self.principal_amount and self.principal_amount.amount <= Decimal('0'):
            errors['principal_amount'] = 'Principal amount must be greater than 0'

        # Validate payment_amount
        if self.payment_amount and self.payment_amount.amount <= Decimal('0'):
            errors['payment_amount'] = 'Payment amount must be greater than 0'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.loan_number:
            # Generate unique loan number
            self.loan_number = f"LN-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}"
        if self.status == 'approved' and not self.approval_date:
            self.approval_date = timezone.now().date()
        if self.status == 'rejected' and not self.rejection_date:
            self.rejection_date = timezone.now().date()
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        """Calculate total amount to be repaid (principal + interest)"""
        from decimal import Decimal
        # Convert all operations to Decimal to avoid float/Decimal mixing
        interest_rate_decimal = Decimal(str(self.interest_rate))
        term_months_decimal = Decimal(str(self.term_months))

        # Calculate: principal * (1 + (rate/100) * (months/12))
        interest_multiplier = Decimal('1') + (interest_rate_decimal / Decimal('100')) * (term_months_decimal / Decimal('12'))

        # For Money objects, multiply the amount and keep the currency
        from moneyed import Money
        total = Money(self.principal_amount.amount * interest_multiplier, self.principal_amount.currency)
        return total

    @property
    def is_overdue(self):
        """Check if loan has overdue payments"""
        if self.status != 'active':
            return False
        overdue_schedules = self.payment_schedules.filter(
            due_date__lt=timezone.now().date(),
            status='pending'
        )
        return overdue_schedules.exists()


class LoanSchedule(UUIDModel, TimeStampedModel):
    """
    Payment schedule for a loan
    """
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='payment_schedules'
    )
    installment_number = models.IntegerField()
    due_date = models.DateField()

    # Amount breakdown
    total_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )
    principal_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )
    interest_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )

    # Payment tracking
    paid_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    paid_date = models.DateField(blank=True, null=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('partial', 'Partially Paid'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'loan_schedules'
        ordering = ['loan', 'installment_number']
        unique_together = ['loan', 'installment_number']

    def __str__(self):
        return f"{self.loan.loan_number} - Installment {self.installment_number}"

    @property
    def balance(self):
        """Calculate remaining balance for this installment"""
        return self.total_amount - self.paid_amount


class LoanPayment(UUIDModel, AuditModel):
    """
    Payment made towards a loan
    """
    payment_number = models.CharField(max_length=50, unique=True, editable=False)
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    schedule = models.ForeignKey(
        LoanSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )

    # Payment Details
    payment_date = models.DateField(default=timezone.now)
    amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )

    # Amount allocation
    principal_paid = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    interest_paid = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )
    late_fee_paid = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        default=0
    )

    # Payment Method
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Credit/Debit Card'),
        ('mobile_payment', 'Mobile Payment'),
    ]
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, null=True)

    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    notes = models.TextField(blank=True, null=True)
    receipt = models.FileField(upload_to='payment_receipts/', blank=True, null=True)

    class Meta:
        db_table = 'loan_payments'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['loan']),
            models.Index(fields=['payment_date']),
        ]

    def __str__(self):
        return f"{self.payment_number} - {self.amount}"

    def clean(self):
        """Validate Money fields"""
        from django.core.exceptions import ValidationError
        from decimal import Decimal

        errors = {}

        # Validate amount
        if self.amount and self.amount.amount <= Decimal('0'):
            errors['amount'] = 'Payment amount must be greater than 0'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.payment_number:
            # Generate unique payment number
            self.payment_number = f"PMT-{timezone.now().year}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class Collateral(UUIDModel, AuditModel):
    """
    Collateral/guarantee for a loan
    """
    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='collaterals'
    )

    # Collateral Type
    COLLATERAL_TYPE_CHOICES = [
        ('vehicle', 'Vehicle'),
        ('property', 'Property/Real Estate'),
        ('equipment', 'Equipment'),
        ('inventory', 'Inventory'),
        ('securities', 'Securities/Stocks'),
        ('cash_deposit', 'Cash Deposit'),
        ('other', 'Other'),
    ]
    collateral_type = models.CharField(max_length=50, choices=COLLATERAL_TYPE_CHOICES)

    # Collateral Details
    description = models.TextField()
    estimated_value = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD'
    )
    appraisal_value = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency='USD',
        blank=True,
        null=True
    )
    appraisal_date = models.DateField(blank=True, null=True)

    # Documentation
    documents = models.FileField(
        upload_to='collateral_documents/',
        blank=True,
        null=True
    )
    photos = models.ImageField(
        upload_to='collateral_photos/',
        blank=True,
        null=True
    )

    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('released', 'Released'),
        ('liquidated', 'Liquidated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'loan_collaterals'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_collateral_type_display()} - {self.loan.loan_number}"
