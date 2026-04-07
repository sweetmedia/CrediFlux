from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries."""

    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_email',
            'user_name',
            'action',
            'action_display',
            'model_name',
            'object_id',
            'object_repr',
            'changes',
            'ip_address',
            'user_agent',
            'extra_data',
            'timestamp',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        """Get the full name of the user."""
        if obj.user:
            return obj.user.get_full_name() or obj.user_email
        return obj.user_email


class AuditLogDetailSerializer(AuditLogSerializer):
    """Detailed serializer with expanded changes."""

    changes_detailed = serializers.SerializerMethodField()

    class Meta(AuditLogSerializer.Meta):
        fields = AuditLogSerializer.Meta.fields + ['changes_detailed']

    def get_changes_detailed(self, obj):
        """Format changes for display."""
        changes = obj.changes or {}
        detailed = []

        for field, values in changes.items():
            detailed.append({
                'field': field,
                'old_value': values.get('old'),
                'new_value': values.get('new'),
            })

        return detailed
