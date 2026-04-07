from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    """Admin for viewing audit logs."""

    list_display = [
        'timestamp',
        'user_email',
        'action',
        'model_name',
        'object_repr',
        'ip_address',
    ]
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user_email', 'object_repr', 'object_id']
    readonly_fields = [
        'id',
        'tenant',
        'user',
        'user_email',
        'action',
        'model_name',
        'object_id',
        'object_repr',
        'changes',
        'ip_address',
        'user_agent',
        'extra_data',
        'timestamp',
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        """Audit logs cannot be created manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs cannot be changed."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted."""
        return False
