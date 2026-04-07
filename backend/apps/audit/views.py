from rest_framework import generics, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, CharFilter, DateFromToRangeFilter

from .models import AuditLog
from .serializers import AuditLogSerializer, AuditLogDetailSerializer


class AuditLogFilter(FilterSet):
    """Filter set for audit logs."""

    user_email = CharFilter(lookup_expr='icontains')
    action = CharFilter(lookup_expr='exact')
    model_name = CharFilter(lookup_expr='iexact')
    object_id = CharFilter(lookup_expr='exact')
    timestamp = DateFromToRangeFilter()

    class Meta:
        model = AuditLog
        fields = ['user', 'user_email', 'action', 'model_name', 'object_id', 'timestamp']


class AuditLogListView(generics.ListAPIView):
    """
    List all audit logs for the current tenant.
    Supports filtering by user, action, model, and date range.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AuditLogFilter
    search_fields = ['user_email', 'object_repr', 'model_name']
    ordering_fields = ['timestamp', 'action', 'model_name', 'user_email']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Filter audit logs by the current user's tenant."""
        user = self.request.user

        # Only allow admin and manager roles to view audit logs
        if user.role not in ['admin', 'manager']:
            return AuditLog.objects.none()

        return AuditLog.objects.filter(
            tenant=user.tenant
        ).select_related('user')


class AuditLogDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single audit log entry with detailed changes.
    """

    serializer_class = AuditLogDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Filter audit logs by the current user's tenant."""
        user = self.request.user

        # Only allow admin and manager roles to view audit logs
        if user.role not in ['admin', 'manager']:
            return AuditLog.objects.none()

        return AuditLog.objects.filter(
            tenant=user.tenant
        ).select_related('user')


class AuditLogStatsView(generics.GenericAPIView):
    """
    Get statistics about audit logs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Only allow admin and manager roles
        if user.role not in ['admin', 'manager']:
            return Response(
                {'error': 'No tienes permiso para ver los registros de auditoria'},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from datetime import timedelta
        from django.utils import timezone

        # Get logs for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)

        logs = AuditLog.objects.filter(
            tenant=user.tenant,
            timestamp__gte=thirty_days_ago
        )

        # Actions by type
        actions_by_type = logs.values('action').annotate(
            count=Count('id')
        ).order_by('-count')

        # Actions by model
        actions_by_model = logs.values('model_name').annotate(
            count=Count('id')
        ).order_by('-count')

        # Actions by user
        actions_by_user = logs.values('user_email').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Actions by day
        actions_by_day = logs.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        return Response({
            'total_logs': logs.count(),
            'actions_by_type': list(actions_by_type),
            'actions_by_model': list(actions_by_model),
            'actions_by_user': list(actions_by_user),
            'actions_by_day': list(actions_by_day),
        })
