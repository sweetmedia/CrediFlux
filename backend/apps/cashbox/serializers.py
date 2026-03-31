"""Serializers for Cash Management."""
from rest_framework import serializers
from .models import CashRegister, CashSession, CashMovement, DenominationCount


class CashRegisterSerializer(serializers.ModelSerializer):
    default_cashier_name = serializers.CharField(
        source='default_cashier.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = CashRegister
        fields = [
            'id', 'name', 'code', 'location', 'is_active',
            'default_cashier', 'default_cashier_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DenominationCountSerializer(serializers.ModelSerializer):
    total = serializers.ReadOnlyField()

    class Meta:
        model = DenominationCount
        fields = [
            'id', 'session', 'count_type',
            'bills_2000', 'bills_1000', 'bills_500', 'bills_200', 'bills_100', 'bills_50',
            'coins_25', 'coins_10', 'coins_5', 'coins_1',
            'total',
        ]
        read_only_fields = ['id']


class CashMovementSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        source='amount.amount', max_digits=14, decimal_places=2
    )
    recorded_by_name = serializers.CharField(
        source='recorded_by.get_full_name', read_only=True, default=''
    )
    category_display = serializers.CharField(
        source='get_category_display', read_only=True
    )
    type_display = serializers.CharField(
        source='get_movement_type_display', read_only=True
    )

    class Meta:
        model = CashMovement
        fields = [
            'id', 'session', 'movement_type', 'type_display',
            'category', 'category_display',
            'amount', 'description', 'reference',
            'loan_payment', 'loan', 'customer_name',
            'recorded_by', 'recorded_by_name',
            'created_at',
        ]
        read_only_fields = ['id', 'recorded_by', 'recorded_by_name', 'created_at']


class CashMovementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating movements — accepts plain amount."""

    class Meta:
        model = CashMovement
        fields = [
            'session', 'movement_type', 'category',
            'amount', 'description', 'reference',
            'loan_payment', 'loan', 'customer_name',
        ]


class CashSessionSerializer(serializers.ModelSerializer):
    cashier_name = serializers.CharField(
        source='cashier.get_full_name', read_only=True
    )
    register_name = serializers.CharField(
        source='register.name', read_only=True
    )
    opening_balance = serializers.DecimalField(
        source='opening_balance.amount', max_digits=14, decimal_places=2, read_only=True
    )
    closing_balance = serializers.DecimalField(
        source='closing_balance.amount', max_digits=14, decimal_places=2,
        read_only=True, allow_null=True
    )
    expected_balance = serializers.DecimalField(
        source='expected_balance.amount', max_digits=14, decimal_places=2,
        read_only=True, allow_null=True
    )
    difference = serializers.DecimalField(
        source='difference.amount', max_digits=14, decimal_places=2,
        read_only=True, allow_null=True
    )
    total_inflows = serializers.ReadOnlyField()
    total_outflows = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CashSession
        fields = [
            'id', 'register', 'register_name',
            'cashier', 'cashier_name',
            'opened_at', 'opening_balance', 'opening_notes',
            'closed_at', 'closing_balance', 'expected_balance', 'difference',
            'closing_notes', 'closed_by',
            'status', 'status_display',
            'total_inflows', 'total_outflows',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'cashier', 'opened_at', 'closed_at',
            'expected_balance', 'difference', 'closed_by',
            'created_at', 'updated_at',
        ]


class CashSessionOpenSerializer(serializers.Serializer):
    """Serializer for opening a cash session."""
    register = serializers.UUIDField()
    opening_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    opening_notes = serializers.CharField(required=False, default='')


class CashSessionCloseSerializer(serializers.Serializer):
    """Serializer for closing a cash session."""
    closing_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    closing_notes = serializers.CharField(required=False, default='')
