"""
Serializers for Communications app - Tasks
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Task
from apps.loans.models import Customer

User = get_user_model()


class TaskCustomerSerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer info in tasks"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'full_name', 'first_name', 'last_name',
            'email', 'phone', 'alternate_phone'
        ]
        read_only_fields = fields


class TaskListSerializer(serializers.ModelSerializer):
    """Serializer for task list view (lightweight)"""
    assignee_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    customer_info = TaskCustomerSerializer(source='customer', read_only=True)
    customer_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'priority', 'priority_display', 'assignee', 'assignee_name',
            'customer', 'customer_name', 'customer_info',
            'due_date', 'tags', 'position', 'is_overdue',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_assignee_name(self, obj):
        if obj.assignee:
            return obj.assignee.get_full_name() or obj.assignee.email
        return None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return None


class TaskSerializer(TaskListSerializer):
    """Serializer for task detail view (full)"""
    pass  # Currently same as list, can be extended


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tasks"""
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'status', 'priority',
            'assignee', 'customer', 'due_date', 'tags', 'position'
        ]

    def validate_assignee(self, value):
        """Validate that assignee belongs to the same tenant"""
        if value:
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                # In multi-tenant setup, users are in same tenant
                if request.user.tenant and value.tenant != request.user.tenant:
                    raise serializers.ValidationError(
                        "El usuario asignado no pertenece a esta organización."
                    )
        return value

    def validate_tags(self, value):
        """Ensure tags is a list of strings"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags debe ser una lista.")
        return [str(tag).strip() for tag in value if tag]

    def create(self, validated_data):
        """Set created_by from request user"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class TaskMoveSerializer(serializers.Serializer):
    """Serializer for moving a task to another column"""
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES)
    position = serializers.IntegerField(min_value=0, required=False, default=0)


class TaskReorderSerializer(serializers.Serializer):
    """Serializer for reordering multiple tasks"""
    tasks = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        min_length=1
    )

    def validate_tasks(self, value):
        """Validate task reorder data"""
        for item in value:
            if 'id' not in item or 'position' not in item:
                raise serializers.ValidationError(
                    "Cada tarea debe tener 'id' y 'position'."
                )
            try:
                item['position'] = int(item['position'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "La posición debe ser un número entero."
                )
        return value
