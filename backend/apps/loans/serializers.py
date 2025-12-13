"""
Serializers for loan module
"""
from rest_framework import serializers
from .models import Customer, CustomerDocument, Loan, LoanSchedule, LoanPayment, Collateral
from .models_collections import CollectionReminder, CollectionContact
from .models_contracts import ContractTemplate, Contract


class CustomerDocumentSerializer(serializers.ModelSerializer):
    """Serializer for CustomerDocument model"""
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True, allow_null=True)
    is_expired = serializers.BooleanField(read_only=True)
    file_size_mb = serializers.FloatField(read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)

    class Meta:
        model = CustomerDocument
        fields = [
            'id', 'customer', 'document_type', 'document_type_display',
            'title', 'description', 'document_file', 'file_size', 'file_type',
            'file_size_mb', 'verification_status', 'verification_status_display',
            'verified_by', 'verified_by_name', 'verified_at', 'rejection_reason',
            'issue_date', 'expiry_date', 'is_expired', 'notes', 'is_primary',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'file_type', 'verified_by', 'verified_at',
            'created_at', 'updated_at'
        ]

    def validate_document_file(self, value):
        """Validate document file size and type"""
        # Max file size: 10MB
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed 10MB. Current size: {value.size / (1024 * 1024):.2f}MB")

        # Allowed file types
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/gif',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]

        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed. "
                "Allowed types: PDF, JPG, PNG, GIF, Word, Excel"
            )

        return value

    def create(self, validated_data):
        """Auto-populate file metadata on creation"""
        document_file = validated_data.get('document_file')
        if document_file:
            validated_data['file_size'] = document_file.size
            validated_data['file_type'] = document_file.content_type

        return super().create(validated_data)


class CustomerDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document list"""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomerDocument
        fields = [
            'id', 'document_type', 'document_type_display', 'title',
            'verification_status', 'verification_status_display',
            'is_expired', 'expiry_date', 'is_primary', 'created_at'
        ]


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_loans = serializers.SerializerMethodField()
    active_loans = serializers.SerializerMethodField()
    documents = CustomerDocumentListSerializer(many=True, read_only=True)

    # Convert Money fields to decimal for frontend
    monthly_income = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'first_name', 'middle_name', 'last_name', 'full_name',
            'date_of_birth', 'gender', 'email', 'phone', 'alternate_phone',
            'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
            'id_type', 'id_number', 'id_expiry_date', 'id_document',
            'employment_status', 'employer_name', 'occupation', 'monthly_income',
            'credit_score', 'status', 'notes', 'photo',
            'total_loans', 'active_loans', 'documents', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_id', 'created_at', 'updated_at']

    def get_total_loans(self, obj):
        return obj.loans.count()

    def get_active_loans(self, obj):
        return obj.loans.filter(status='active').count()

    def get_monthly_income(self, obj):
        return float(obj.monthly_income.amount) if obj.monthly_income else None


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer list"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_loans = serializers.SerializerMethodField()
    active_loans = serializers.SerializerMethodField()
    loan_details = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'id_number', 'address_line1', 'address_line2',
            'city', 'state', 'country', 'postal_code',
            'status', 'total_loans', 'active_loans', 'loan_details',
            'total_balance', 'created_at'
        ]

    def get_total_loans(self, obj):
        """Get total number of loans"""
        return obj.loans.count()

    def get_active_loans(self, obj):
        """Get number of active loans"""
        return obj.loans.filter(status='active').count()

    def get_loan_details(self, obj):
        """Get list of loan numbers and their balances"""
        loans = obj.loans.all()
        return [
            {
                'loan_number': loan.loan_number,
                'remaining_balance': float(loan.outstanding_balance.amount) if loan.outstanding_balance else 0
            }
            for loan in loans
        ]

    def get_total_balance(self, obj):
        """Get total balance across all loans"""
        from django.db.models import Sum
        total = obj.loans.aggregate(
            total=Sum('outstanding_balance')
        )['total']
        return float(total) if total else 0


class CollateralSerializer(serializers.ModelSerializer):
    """Serializer for Collateral model"""
    # For reading, convert Money fields to decimal
    estimated_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    appraisal_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True, required=False)
    description = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Collateral
        fields = [
            'id', 'loan', 'collateral_type', 'description',
            'estimated_value', 'appraisal_value', 'appraisal_date',
            'documents', 'photos', 'status', 'notes', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Convert Money fields to decimal for reading"""
        data = super().to_representation(instance)
        if instance.estimated_value:
            data['estimated_value'] = float(instance.estimated_value.amount)
        if instance.appraisal_value:
            data['appraisal_value'] = float(instance.appraisal_value.amount)
        return data

    def create(self, validated_data):
        """Handle Money field creation"""
        from djmoney.money import Money

        # Convert decimal to Money for estimated_value
        if 'estimated_value' in validated_data:
            validated_data['estimated_value'] = Money(
                validated_data['estimated_value'], 'USD'
            )

        # Convert decimal to Money for appraisal_value if present
        if validated_data.get('appraisal_value'):
            validated_data['appraisal_value'] = Money(
                validated_data['appraisal_value'], 'USD'
            )

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle Money field updates"""
        from djmoney.money import Money

        # Convert decimal to Money for estimated_value
        if 'estimated_value' in validated_data:
            validated_data['estimated_value'] = Money(
                validated_data['estimated_value'], 'USD'
            )

        # Convert decimal to Money for appraisal_value if present
        if validated_data.get('appraisal_value'):
            validated_data['appraisal_value'] = Money(
                validated_data['appraisal_value'], 'USD'
            )

        return super().update(instance, validated_data)


class LoanScheduleSerializer(serializers.ModelSerializer):
    """Serializer for LoanSchedule model"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)

    # Convert Money fields to decimal for frontend
    total_amount = serializers.DecimalField(source='total_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    principal_amount = serializers.DecimalField(source='principal_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    interest_amount = serializers.DecimalField(source='interest_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(source='paid_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(source='balance.amount', max_digits=14, decimal_places=2, read_only=True)
    late_fee_amount = serializers.DecimalField(source='late_fee_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    late_fee_paid = serializers.DecimalField(source='late_fee_paid.amount', max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LoanSchedule
        fields = [
            'id', 'loan', 'loan_number', 'customer_name', 'installment_number', 'due_date',
            'total_amount', 'principal_amount', 'interest_amount',
            'paid_amount', 'paid_date', 'status', 'balance',
            'actual_payment_date', 'days_overdue', 'late_fee_amount', 'late_fee_paid',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'loan_number', 'customer_name', 'days_overdue', 'created_at', 'updated_at']


class LoanPaymentSerializer(serializers.ModelSerializer):
    """Serializer for LoanPayment model (read-only)"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)

    # Convert UUID fields to strings for frontend compatibility
    loan = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()

    # Convert Money fields to decimal for frontend
    amount = serializers.DecimalField(source='amount.amount', max_digits=14, decimal_places=2, read_only=True)
    principal_paid = serializers.DecimalField(source='principal_paid.amount', max_digits=14, decimal_places=2, read_only=True)
    interest_paid = serializers.DecimalField(source='interest_paid.amount', max_digits=14, decimal_places=2, read_only=True)
    late_fee_paid = serializers.DecimalField(source='late_fee_paid.amount', max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LoanPayment
        fields = [
            'id', 'payment_number', 'loan', 'loan_number', 'customer_name',
            'schedule', 'payment_date', 'amount', 'principal_paid',
            'interest_paid', 'late_fee_paid', 'payment_method',
            'reference_number', 'status', 'notes', 'receipt',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'payment_number', 'created_at', 'updated_at']

    def get_loan(self, obj):
        """Return loan UUID as string"""
        return str(obj.loan.id) if obj.loan else None

    def get_schedule(self, obj):
        """Return schedule UUID as string"""
        return str(obj.schedule.id) if obj.schedule else None


class LoanPaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating LoanPayment (write-only)"""

    class Meta:
        model = LoanPayment
        fields = [
            'loan', 'schedule', 'payment_date', 'amount',
            'payment_method', 'reference_number', 'status', 'notes'
        ]
        # principal_paid, interest_paid, and late_fee_paid are calculated automatically

    def validate_amount(self, value):
        """Validate that amount is positive"""
        from decimal import Decimal
        if value.amount <= Decimal('0'):
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value

    def create(self, validated_data):
        """
        Calculate payment distribution automatically.
        Payment priority: Late Fees -> Interest -> Principal
        """
        from moneyed import Money
        from decimal import Decimal

        loan = validated_data['loan']
        amount = validated_data['amount']
        schedule = validated_data.get('schedule')

        # Get currency from the amount
        currency = amount.currency if hasattr(amount, 'currency') else 'USD'

        # Remove any manually provided values
        validated_data.pop('principal_paid', None)
        validated_data.pop('interest_paid', None)
        validated_data.pop('late_fee_paid', None)

        # Set default status to completed if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'completed'

        remaining_payment = amount.amount

        # Initialize distribution amounts
        late_fee_payment = Decimal('0')
        interest_payment = Decimal('0')
        principal_payment = Decimal('0')

        if schedule:
            # STEP 1: Pay late fees first (mora)
            late_fee_balance = schedule.late_fee_amount.amount - schedule.late_fee_paid.amount
            if late_fee_balance > 0 and remaining_payment > 0:
                late_fee_payment = min(remaining_payment, late_fee_balance)
                remaining_payment -= late_fee_payment

            # STEP 2: Pay interest
            interest_balance = schedule.interest_amount.amount - (
                schedule.paid_amount.amount * (schedule.interest_amount.amount / schedule.total_amount.amount)
                if schedule.paid_amount and schedule.total_amount.amount > 0 else Decimal('0')
            )
            if interest_balance > 0 and remaining_payment > 0:
                interest_payment = min(remaining_payment, interest_balance)
                remaining_payment -= interest_payment

            # STEP 3: Pay principal
            principal_balance = schedule.principal_amount.amount - (
                schedule.paid_amount.amount * (schedule.principal_amount.amount / schedule.total_amount.amount)
                if schedule.paid_amount and schedule.total_amount.amount > 0 else Decimal('0')
            )
            if principal_balance > 0 and remaining_payment > 0:
                principal_payment = min(remaining_payment, principal_balance)
                remaining_payment -= principal_payment

            # If there's still money left (overpayment), add to principal
            if remaining_payment > 0:
                principal_payment += remaining_payment
        else:
            # No schedule specified - find the oldest overdue schedule and apply payment there
            from django.utils import timezone

            oldest_overdue = loan.payment_schedules.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'overdue', 'partial']
            ).order_by('due_date').first()

            if oldest_overdue:
                # Apply payment to the oldest overdue schedule with late fees
                # STEP 1: Pay late fees first
                late_fee_balance = oldest_overdue.late_fee_amount.amount - oldest_overdue.late_fee_paid.amount
                if late_fee_balance > 0 and remaining_payment > 0:
                    late_fee_payment = min(remaining_payment, late_fee_balance)
                    remaining_payment -= late_fee_payment

                # STEP 2: Pay interest for this schedule
                interest_balance = oldest_overdue.interest_amount.amount - (
                    oldest_overdue.paid_amount.amount * (oldest_overdue.interest_amount.amount / oldest_overdue.total_amount.amount)
                    if oldest_overdue.paid_amount and oldest_overdue.total_amount.amount > 0 else Decimal('0')
                )
                if interest_balance > 0 and remaining_payment > 0:
                    interest_payment = min(remaining_payment, interest_balance)
                    remaining_payment -= interest_payment

                # STEP 3: Pay principal for this schedule
                principal_balance = oldest_overdue.principal_amount.amount - (
                    oldest_overdue.paid_amount.amount * (oldest_overdue.principal_amount.amount / oldest_overdue.total_amount.amount)
                    if oldest_overdue.paid_amount and oldest_overdue.total_amount.amount > 0 else Decimal('0')
                )
                if principal_balance > 0 and remaining_payment > 0:
                    principal_payment = min(remaining_payment, principal_balance)
                    remaining_payment -= principal_payment

                # Link this payment to the schedule we found
                validated_data['schedule'] = oldest_overdue

                # If there's still money left (overpayment), add to principal
                if remaining_payment > 0:
                    principal_payment += remaining_payment
            else:
                # No overdue schedules - apply to loan balances generically
                late_fee_payment = Decimal('0')

                # STEP 2: Pay interest based on monthly rate
                monthly_rate = loan.interest_rate / Decimal('100') / Decimal('12')
                interest_due = loan.outstanding_balance.amount * monthly_rate

                if remaining_payment >= interest_due:
                    interest_payment = interest_due
                    remaining_payment -= interest_payment
                else:
                    interest_payment = remaining_payment
                    remaining_payment = Decimal('0')

                # STEP 3: Rest goes to principal
                if remaining_payment > 0:
                    principal_payment = remaining_payment

        # Set the distribution in validated_data
        validated_data['late_fee_paid'] = Money(late_fee_payment, currency)
        validated_data['interest_paid'] = Money(interest_payment, currency)
        validated_data['principal_paid'] = Money(principal_payment, currency)

        return super().create(validated_data)


class LoanSerializer(serializers.ModelSerializer):
    """Full serializer for Loan model"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_details = CustomerListSerializer(source='customer', read_only=True)
    loan_officer_name = serializers.CharField(source='loan_officer.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    rejected_by_name = serializers.CharField(source='rejected_by.get_full_name', read_only=True, allow_null=True)

    # Convert Money fields to decimal for frontend
    principal_amount = serializers.DecimalField(source='principal_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    payment_amount = serializers.DecimalField(source='payment_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    outstanding_balance = serializers.DecimalField(source='outstanding_balance.amount', max_digits=14, decimal_places=2, read_only=True)
    total_paid = serializers.DecimalField(source='total_paid.amount', max_digits=14, decimal_places=2, read_only=True)
    total_interest_paid = serializers.DecimalField(source='total_interest_paid.amount', max_digits=14, decimal_places=2, read_only=True)
    late_fees = serializers.DecimalField(source='late_fees.amount', max_digits=14, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(source='total_amount.amount', max_digits=14, decimal_places=2, read_only=True)

    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.SerializerMethodField()
    collaterals = CollateralSerializer(many=True, read_only=True)
    payment_schedules = LoanScheduleSerializer(many=True, read_only=True)
    recent_payments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer', 'customer_name', 'customer_details',
            'loan_type', 'principal_amount', 'interest_rate', 'interest_type', 'term_months',
            'payment_frequency', 'payment_amount', 'application_date',
            'approval_date', 'rejection_date', 'disbursement_date', 'first_payment_date',
            'maturity_date', 'status', 'outstanding_balance', 'total_paid',
            'total_interest_paid', 'late_fees', 'loan_officer',
            'loan_officer_name', 'approved_by', 'approved_by_name',
            'rejected_by', 'rejected_by_name', 'approval_notes',
            'purpose', 'notes', 'terms_accepted',
            'contract_document', 'total_amount', 'is_overdue', 'days_overdue',
            'collaterals', 'payment_schedules', 'recent_payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'loan_number', 'outstanding_balance', 'total_paid',
            'total_interest_paid', 'created_at', 'updated_at'
        ]

    def get_days_overdue(self, obj):
        """
        Calculate the maximum days overdue from all pending/overdue schedules
        """
        from django.utils import timezone

        # Get the most overdue payment schedule (pending, overdue, or partial)
        most_overdue = obj.payment_schedules.filter(
            status__in=['pending', 'overdue', 'partial'],
            due_date__lt=timezone.now().date()
        ).order_by('due_date').first()

        if most_overdue:
            return (timezone.now().date() - most_overdue.due_date).days
        return 0

    def get_recent_payments(self, obj):
        payments = obj.payments.filter(status='completed').order_by('-payment_date')[:5]
        return LoanPaymentSerializer(payments, many=True).data


class LoanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for loan list"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_overdue = serializers.SerializerMethodField()
    next_payment_date = serializers.SerializerMethodField()
    total_installments = serializers.SerializerMethodField()
    paid_installments = serializers.SerializerMethodField()
    late_fees = serializers.SerializerMethodField()

    # Use SerializerMethodField to convert Money to decimal
    principal_amount = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    payment_amount = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer_name', 'loan_type',
            'principal_amount', 'interest_rate', 'interest_type', 'term_months',
            'payment_frequency', 'payment_amount', 'outstanding_balance', 'total_paid',
            'status', 'disbursement_date', 'first_payment_date', 'maturity_date',
            'next_payment_date', 'is_overdue', 'days_overdue', 'late_fees',
            'total_installments', 'paid_installments', 'created_at'
        ]

    def get_principal_amount(self, obj):
        return float(obj.principal_amount.amount) if obj.principal_amount else 0

    def get_outstanding_balance(self, obj):
        return float(obj.outstanding_balance.amount) if obj.outstanding_balance else 0

    def get_total_paid(self, obj):
        return float(obj.total_paid.amount) if obj.total_paid else 0

    def get_payment_amount(self, obj):
        return float(obj.payment_amount.amount) if obj.payment_amount else 0

    def get_late_fees(self, obj):
        return float(obj.late_fees.amount) if obj.late_fees else 0

    def get_total_installments(self, obj):
        return obj.payment_schedules.count()

    def get_paid_installments(self, obj):
        return obj.payment_schedules.filter(status='paid').count()

    def get_next_payment_date(self, obj):
        """Get next pending payment date"""
        from django.utils import timezone

        next_schedule = obj.payment_schedules.filter(
            status__in=['pending', 'overdue', 'partial']
        ).order_by('due_date').first()

        return next_schedule.due_date if next_schedule else None

    def get_days_overdue(self, obj):
        """Calculate days overdue from all pending/overdue/partial schedules"""
        from django.utils import timezone

        most_overdue = obj.payment_schedules.filter(
            status__in=['pending', 'overdue', 'partial'],
            due_date__lt=timezone.now().date()
        ).order_by('due_date').first()

        if most_overdue:
            return (timezone.now().date() - most_overdue.due_date).days
        return 0


class LoanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating loans"""

    class Meta:
        model = Loan
        fields = [
            'customer', 'loan_type', 'principal_amount', 'interest_rate', 'interest_type',
            'term_months', 'payment_frequency', 'payment_amount',
            'application_date', 'first_payment_date', 'loan_officer',
            'purpose', 'notes'
        ]

    def validate(self, attrs):
        from decimal import Decimal
        from moneyed import Money

        # Add custom validation here
        # For Money fields, compare with Money objects or use .amount attribute
        if attrs['principal_amount'].amount <= 0:
            raise serializers.ValidationError("Principal amount must be greater than 0")

        if attrs['interest_rate'] < 0 or attrs['interest_rate'] > 100:
            raise serializers.ValidationError("Interest rate must be between 0 and 100")

        if attrs['term_months'] < 1:
            raise serializers.ValidationError("Term must be at least 1 month")

        return attrs


class CollectionReminderSerializer(serializers.ModelSerializer):
    """Serializer for CollectionReminder model"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    sent_by_name = serializers.CharField(source='sent_by.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = CollectionReminder
        fields = [
            'id', 'loan_schedule', 'loan', 'loan_number', 'customer', 'customer_name',
            'reminder_type', 'reminder_type_display', 'channel', 'channel_display',
            'scheduled_for', 'sent_at', 'status', 'status_display',
            'message_content', 'sent_by', 'sent_by_name', 'error_message',
            'customer_response', 'response_received_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_at', 'sent_by', 'created_at', 'updated_at']

    def validate_scheduled_for(self, value):
        """Ensure scheduled_for is not in the past"""
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("El recordatorio no puede programarse en el pasado")
        return value


class CollectionReminderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating collection reminders"""

    class Meta:
        model = CollectionReminder
        fields = [
            'loan_schedule', 'loan', 'customer', 'reminder_type',
            'channel', 'scheduled_for', 'message_content'
        ]

    def validate(self, attrs):
        """Validate that loan, customer, and schedule are related"""
        loan = attrs.get('loan')
        customer = attrs.get('customer')
        loan_schedule = attrs.get('loan_schedule')

        if loan and customer and loan.customer != customer:
            raise serializers.ValidationError("El cliente no corresponde al préstamo seleccionado")

        if loan_schedule and loan_schedule.loan != loan:
            raise serializers.ValidationError("El cronograma no corresponde al préstamo seleccionado")

        return attrs


class CollectionContactSerializer(serializers.ModelSerializer):
    """Serializer for CollectionContact model"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    contact_type_display = serializers.CharField(source='get_contact_type_display', read_only=True)
    outcome_display = serializers.CharField(source='get_outcome_display', read_only=True)
    contacted_by_name = serializers.CharField(source='contacted_by.get_full_name', read_only=True, allow_null=True)
    promise_amount = serializers.DecimalField(source='promise_amount.amount', max_digits=12, decimal_places=2, read_only=True, allow_null=True)

    class Meta:
        model = CollectionContact
        fields = [
            'id', 'loan', 'loan_number', 'customer', 'customer_name',
            'contact_date', 'contact_type', 'contact_type_display',
            'contacted_by', 'contacted_by_name', 'outcome', 'outcome_display',
            'promise_date', 'promise_amount', 'promise_kept',
            'notes', 'next_contact_date', 'requires_escalation',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'contacted_by', 'created_at', 'updated_at']


class CollectionContactCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating collection contacts"""

    class Meta:
        model = CollectionContact
        fields = [
            'loan', 'customer', 'contact_date', 'contact_type',
            'outcome', 'promise_date', 'promise_amount', 'promise_kept',
            'notes', 'next_contact_date', 'requires_escalation'
        ]

    def validate(self, attrs):
        """Validate that customer belongs to the loan"""
        loan = attrs.get('loan')
        customer = attrs.get('customer')

        if loan and customer and loan.customer != customer:
            raise serializers.ValidationError("El cliente no corresponde al préstamo seleccionado")

        # If outcome is promise_to_pay, require promise_date and promise_amount
        outcome = attrs.get('outcome')
        if outcome in ['promise_to_pay', 'payment_plan']:
            if not attrs.get('promise_date'):
                raise serializers.ValidationError("Se requiere fecha de promesa de pago")
            if not attrs.get('promise_amount'):
                raise serializers.ValidationError("Se requiere monto de promesa de pago")

        return attrs

    def create(self, validated_data):
        """Auto-assign contacted_by to current user"""
        # The view will set this via perform_create
        return super().create(validated_data)


# ============================================================================
# CONTRACT SERIALIZERS
# ============================================================================

class ContractTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ContractTemplate model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = ContractTemplate
        fields = [
            'id', 'name', 'description', 'content', 'is_active', 'is_default',
            'loan_types', 'header_image', 'footer_text',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ContractTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contract template list"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = ContractTemplate
        fields = [
            'id', 'name', 'description', 'is_active', 'is_default',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for Contract model"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_number', 'loan', 'loan_number', 'customer_name',
            'template', 'template_name', 'content', 'pdf_file', 'status',
            'customer_signed_at', 'customer_signature', 'officer_signed_at',
            'officer_signature', 'witness_name', 'witness_id', 'witness_signature',
            'witness_signed_at', 'special_terms', 'notes',
            'generated_by', 'generated_by_name', 'generated_at', 'updated_at',
            'is_fully_signed'
        ]
        read_only_fields = [
            'id', 'contract_number', 'generated_by', 'generated_at',
            'updated_at', 'is_fully_signed'
        ]


class ContractListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for contract list"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'contract_number', 'loan_number', 'customer_name',
            'template_name', 'status', 'is_fully_signed',
            'generated_at', 'updated_at'
        ]
        read_only_fields = fields


class ContractCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new contract"""

    class Meta:
        model = Contract
        fields = ['id', 'contract_number', 'loan', 'template', 'special_terms', 'notes', 'status', 'generated_at']
        read_only_fields = ['id', 'contract_number', 'status', 'generated_at']

    def validate_loan(self, value):
        """Validate that loan doesn't already have an active contract"""
        existing = Contract.objects.filter(
            loan=value,
            status__in=['active', 'signed', 'pending_signature']
        ).exists()

        if existing:
            raise serializers.ValidationError(
                "Este préstamo ya tiene un contrato activo"
            )

        return value
