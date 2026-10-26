from django.contrib import admin
from unfold.admin import ModelAdmin
from apps.core.admin_mixins import is_platform_admin
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

    def get_queryset(self, request):
        """
        Superusuario de plataforma (tenant=None): todo, incluidas las filas de plataforma.
        Staff de un tenant: sólo su tenant. Cualquier otro: nada.
        """
        qs = super().get_queryset(request)
        user = request.user
        if is_platform_admin(user):
            return qs
        if user.tenant_id is not None:
            return qs.filter(tenant_id=user.tenant_id)
        return qs.none()

    def has_add_permission(self, request):
        """Audit logs cannot be created manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs cannot be changed."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs cannot be deleted."""
        return False
