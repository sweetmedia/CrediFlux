"""
Contract models for managing loan contracts and templates
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class ContractTemplate(models.Model):
    """
    Contract templates that can be used to generate loan contracts.
    Each tenant can have multiple templates for different loan types.
    """

    VARIABLE_HELP_TEXT = """
    Available variables (use {{variable_name}} in template):
    - {{customer_name}}: Full name of customer
    - {{customer_id}}: Customer ID number
    - {{customer_id_number}}: Customer cedula/ID
    - {{customer_address}}: Full customer address
    - {{customer_phone}}: Customer phone number
    - {{customer_email}}: Customer email
    - {{loan_number}}: Loan number (e.g., LN-2025-ABC123)
    - {{loan_amount}}: Principal loan amount
    - {{loan_amount_words}}: Loan amount in words
    - {{interest_rate}}: Annual interest rate
    - {{loan_term}}: Loan term in months
    - {{payment_frequency}}: Payment frequency (weekly, biweekly, monthly)
    - {{monthly_payment}}: Monthly payment amount
    - {{total_amount}}: Total amount to be repaid
    - {{disbursement_date}}: Date loan was disbursed
    - {{first_payment_date}}: Date of first payment
    - {{final_payment_date}}: Date of final payment
    - {{loan_officer}}: Name of loan officer
    - {{company_name}}: Tenant company name
    - {{company_address}}: Tenant address
    - {{company_phone}}: Tenant phone
    - {{company_email}}: Tenant email
    - {{contract_date}}: Date contract was generated
    - {{guarantor_name}}: Guarantor name (if applicable)
    - {{guarantor_id}}: Guarantor ID (if applicable)
    - {{collateral_description}}: Description of collaterals
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Template details
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Personal Loan Contract', 'Business Loan Agreement')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )

    # Template content
    content = models.TextField(
        help_text=VARIABLE_HELP_TEXT
    )

    # Template settings
    is_active = models.BooleanField(
        default=True,
        help_text="Only active templates can be used to generate contracts"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default template for new contracts"
    )

    # Applicable to
    loan_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Loan types this template applies to (empty = all types)"
    )

    # Template header/footer (optional)
    header_image = models.ImageField(
        upload_to='contract_templates/headers/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Optional header image/logo for contract"
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Optional footer text (terms, conditions, etc.)"
    )

    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_contract_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contract_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_default']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} {'(Default)' if self.is_default else ''}"

    def save(self, *args, **kwargs):
        """If this template is set as default, unset other defaults"""
        if self.is_default:
            # Unset other defaults (within same tenant context)
            ContractTemplate.objects.filter(is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class Contract(models.Model):
    """
    Generated contracts for specific loans
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_signature', 'Pending Signature'),
        ('signed', 'Signed'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Contract identifiers
    contract_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique contract number (e.g., CONT-2025-ABC123)"
    )

    # Relationships
    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='contracts'
    )
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_contracts',
        help_text="Template used to generate this contract"
    )

    # Contract content (rendered from template)
    content = models.TextField(
        help_text="Rendered contract content with all variables replaced"
    )

    # PDF version
    pdf_file = models.FileField(
        upload_to='contracts/pdfs/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text="Generated PDF version of the contract"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Signature information
    customer_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When customer signed the contract"
    )
    customer_signature = models.ImageField(
        upload_to='contracts/signatures/customers/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Customer signature image"
    )

    officer_signed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When loan officer signed the contract"
    )
    officer_signature = models.ImageField(
        upload_to='contracts/signatures/officers/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        help_text="Loan officer signature image"
    )

    # Witness information (optional)
    witness_name = models.CharField(max_length=200, blank=True)
    witness_id = models.CharField(max_length=50, blank=True)
    witness_signature = models.ImageField(
        upload_to='contracts/signatures/witnesses/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])]
    )
    witness_signed_at = models.DateTimeField(null=True, blank=True)

    # Additional terms/notes
    special_terms = models.TextField(
        blank=True,
        help_text="Any special terms or conditions added to this contract"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this contract"
    )

    # Metadata
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_contracts'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Archive
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether this contract has been archived"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this contract was archived"
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_contracts',
        help_text="User who archived this contract"
    )

    class Meta:
        db_table = 'contracts'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['contract_number']),
            models.Index(fields=['loan', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self):
        return f"Contract {self.contract_number} - {self.loan.loan_number}"

    def save(self, *args, **kwargs):
        """Auto-generate contract number if not set"""
        if not self.contract_number:
            # Generate unique contract number
            import random
            import string
            timestamp = timezone.now().strftime('%Y')
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.contract_number = f"CONT-{timestamp}-{random_part}"

        super().save(*args, **kwargs)

    @property
    def is_fully_signed(self):
        """Check if contract is fully signed by all parties"""
        return (
            self.customer_signed_at is not None and
            self.officer_signed_at is not None
        )

    @property
    def customer_name(self):
        """Get customer name from loan"""
        return self.loan.customer.get_full_name()

    @property
    def loan_number(self):
        """Get loan number"""
        return self.loan.loan_number


class ContractSignatureToken(models.Model):
    """
    Tokens for secure contract signature links.
    Allows customers to sign contracts via email link without authentication.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='signature_tokens'
    )

    # Token details
    token = models.CharField(max_length=64, unique=True, db_index=True)
    email = models.EmailField(help_text="Email address where the signature link was sent")

    # Permissions
    can_sign_as_customer = models.BooleanField(default=True)
    can_sign_as_officer = models.BooleanField(default=False)

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When this token expires")
    used_at = models.DateTimeField(null=True, blank=True, help_text="When the token was used to sign")
    sent_at = models.DateTimeField(auto_now_add=True, help_text="When the email was sent")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['contract', 'email']),
        ]

    def __str__(self):
        return f"Token for {self.contract.contract_number} - {self.email}"

    @property
    def is_expired(self):
        """Check if token has expired"""
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        """Check if token has been used"""
        return self.used_at is not None

    @property
    def is_valid(self):
        """Check if token is valid (not expired and not used)"""
        return not self.is_expired and not self.is_used

    def mark_as_used(self):
        """Mark token as used"""
        self.used_at = timezone.now()
        self.save()
