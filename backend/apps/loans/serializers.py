"""
Serializers for loan module
"""
from rest_framework import serializers
from .models import Customer, Loan, LoanSchedule, LoanPayment, Collateral


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_loans = serializers.SerializerMethodField()
    active_loans = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'first_name', 'middle_name', 'last_name', 'full_name',
            'date_of_birth', 'gender', 'email', 'phone', 'alternate_phone',
            'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
            'id_type', 'id_number', 'id_expiry_date', 'id_document',
            'employment_status', 'employer_name', 'occupation', 'monthly_income',
            'credit_score', 'status', 'notes', 'photo',
            'total_loans', 'active_loans', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_id', 'created_at', 'updated_at']

    def get_total_loans(self, obj):
        return obj.loans.count()

    def get_active_loans(self, obj):
        return obj.loans.filter(status='active').count()


class CustomerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer list"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'full_name', 'email', 'phone',
            'status', 'created_at'
        ]


class CollateralSerializer(serializers.ModelSerializer):
    """Serializer for Collateral model"""

    class Meta:
        model = Collateral
        fields = [
            'id', 'loan', 'collateral_type', 'description',
            'estimated_value', 'appraisal_value', 'appraisal_date',
            'documents', 'photos', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoanScheduleSerializer(serializers.ModelSerializer):
    """Serializer for LoanSchedule model"""
    balance = serializers.DecimalField(
        source='balance.amount',
        max_digits=14,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = LoanSchedule
        fields = [
            'id', 'loan', 'installment_number', 'due_date',
            'total_amount', 'principal_amount', 'interest_amount',
            'paid_amount', 'paid_date', 'status', 'balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoanPaymentSerializer(serializers.ModelSerializer):
    """Serializer for LoanPayment model"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)

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


class LoanSerializer(serializers.ModelSerializer):
    """Full serializer for Loan model"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_details = CustomerListSerializer(source='customer', read_only=True)
    loan_officer_name = serializers.CharField(source='loan_officer.get_full_name', read_only=True)
    total_amount = serializers.DecimalField(
        source='total_amount.amount',
        max_digits=14,
        decimal_places=2,
        read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)
    collaterals = CollateralSerializer(many=True, read_only=True)
    payment_schedules = LoanScheduleSerializer(many=True, read_only=True)
    recent_payments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer', 'customer_name', 'customer_details',
            'loan_type', 'principal_amount', 'interest_rate', 'term_months',
            'payment_frequency', 'payment_amount', 'application_date',
            'approval_date', 'disbursement_date', 'first_payment_date',
            'maturity_date', 'status', 'outstanding_balance', 'total_paid',
            'total_interest_paid', 'late_fees', 'loan_officer',
            'loan_officer_name', 'purpose', 'notes', 'terms_accepted',
            'contract_document', 'total_amount', 'is_overdue',
            'collaterals', 'payment_schedules', 'recent_payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'loan_number', 'outstanding_balance', 'total_paid',
            'total_interest_paid', 'created_at', 'updated_at'
        ]

    def get_recent_payments(self, obj):
        payments = obj.payments.filter(status='completed').order_by('-payment_date')[:5]
        return LoanPaymentSerializer(payments, many=True).data


class LoanListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for loan list"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer_name', 'loan_type',
            'principal_amount', 'outstanding_balance', 'status',
            'disbursement_date', 'is_overdue', 'created_at'
        ]


class LoanCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating loans"""

    class Meta:
        model = Loan
        fields = [
            'customer', 'loan_type', 'principal_amount', 'interest_rate',
            'term_months', 'payment_frequency', 'payment_amount',
            'application_date', 'first_payment_date', 'loan_officer',
            'purpose', 'notes'
        ]

    def validate(self, attrs):
        # Add custom validation here
        if attrs['principal_amount'] <= 0:
            raise serializers.ValidationError("Principal amount must be greater than 0")

        if attrs['interest_rate'] < 0 or attrs['interest_rate'] > 100:
            raise serializers.ValidationError("Interest rate must be between 0 and 100")

        if attrs['term_months'] < 1:
            raise serializers.ValidationError("Term must be at least 1 month")

        return attrs
