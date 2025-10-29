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
            'total_loans', 'active_loans', 'created_at', 'updated_at'
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

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'full_name', 'email', 'phone',
            'status', 'created_at'
        ]


class CollateralSerializer(serializers.ModelSerializer):
    """Serializer for Collateral model"""
    # Convert Money fields to decimal for frontend
    estimated_value = serializers.DecimalField(source='estimated_value.amount', max_digits=14, decimal_places=2)
    appraisal_value = serializers.DecimalField(source='appraisal_value.amount', max_digits=14, decimal_places=2, allow_null=True, required=False)

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
    # Convert Money fields to decimal for frontend
    total_amount = serializers.DecimalField(source='total_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    principal_amount = serializers.DecimalField(source='principal_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    interest_amount = serializers.DecimalField(source='interest_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(source='paid_amount.amount', max_digits=14, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(source='balance.amount', max_digits=14, decimal_places=2, read_only=True)

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
    """Serializer for LoanPayment model (read-only)"""
    loan_number = serializers.CharField(source='loan.loan_number', read_only=True)
    customer_name = serializers.CharField(source='loan.customer.get_full_name', read_only=True)

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
        """Calculate principal_paid and interest_paid automatically"""
        from moneyed import Money
        from decimal import Decimal

        loan = validated_data['loan']
        amount = validated_data['amount']
        schedule = validated_data.get('schedule')

        # Get currency from the amount
        currency = amount.currency if hasattr(amount, 'currency') else 'USD'

        # Remove any manually provided values (should not be in validated_data but just in case)
        validated_data.pop('principal_paid', None)
        validated_data.pop('interest_paid', None)
        validated_data.pop('late_fee_paid', None)

        # Set default status to completed if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'completed'

        # If schedule is provided, use it to determine interest vs principal
        if schedule:
            # Calculate remaining amounts in the schedule
            paid_amount = schedule.paid_amount if schedule.paid_amount else Money(0, schedule.total_amount.currency)
            remaining_total = schedule.total_amount - paid_amount

            # Calculate what portion is interest vs principal in this payment
            if remaining_total.amount > 0:
                interest_ratio = schedule.interest_amount.amount / schedule.total_amount.amount
                payment_interest = Money(min(amount.amount * interest_ratio, schedule.interest_amount.amount), currency)
                payment_principal = Money(amount.amount - payment_interest.amount, currency)
            else:
                # Schedule already paid, everything goes to principal
                payment_interest = Money(0, currency)
                payment_principal = amount

            validated_data['interest_paid'] = payment_interest
            validated_data['principal_paid'] = payment_principal
        else:
            # No schedule - calculate interest based on outstanding balance and rate
            # Simple calculation: pay interest first based on monthly rate
            monthly_rate = loan.interest_rate / Decimal('100') / Decimal('12')
            interest_amount = loan.outstanding_balance.amount * monthly_rate

            if amount.amount >= interest_amount:
                validated_data['interest_paid'] = Money(interest_amount, currency)
                validated_data['principal_paid'] = Money(amount.amount - interest_amount, currency)
            else:
                # Payment doesn't cover all interest
                validated_data['interest_paid'] = amount
                validated_data['principal_paid'] = Money(0, currency)

        # Set late_fee_paid to 0
        validated_data['late_fee_paid'] = Money(0, currency)

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
    collaterals = CollateralSerializer(many=True, read_only=True)
    payment_schedules = LoanScheduleSerializer(many=True, read_only=True)
    recent_payments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer', 'customer_name', 'customer_details',
            'loan_type', 'principal_amount', 'interest_rate', 'term_months',
            'payment_frequency', 'payment_amount', 'application_date',
            'approval_date', 'rejection_date', 'disbursement_date', 'first_payment_date',
            'maturity_date', 'status', 'outstanding_balance', 'total_paid',
            'total_interest_paid', 'late_fees', 'loan_officer',
            'loan_officer_name', 'approved_by', 'approved_by_name',
            'rejected_by', 'rejected_by_name', 'approval_notes',
            'purpose', 'notes', 'terms_accepted',
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

    # Use SerializerMethodField to convert Money to decimal
    principal_amount = serializers.SerializerMethodField()
    outstanding_balance = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_number', 'customer_name', 'loan_type',
            'principal_amount', 'interest_rate', 'outstanding_balance', 'total_paid', 'status',
            'disbursement_date', 'is_overdue', 'created_at'
        ]

    def get_principal_amount(self, obj):
        return float(obj.principal_amount.amount) if obj.principal_amount else 0

    def get_outstanding_balance(self, obj):
        return float(obj.outstanding_balance.amount) if obj.outstanding_balance else 0

    def get_total_paid(self, obj):
        return float(obj.total_paid.amount) if obj.total_paid else 0


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
