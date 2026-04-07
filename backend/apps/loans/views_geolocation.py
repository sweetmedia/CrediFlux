"""
Geolocation API views for collector tracking.
"""
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers as drf_serializers
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models_geolocation import CollectorVisit, CollectorLocation

logger = logging.getLogger(__name__)


# === Serializers ===

class CollectorVisitSerializer(drf_serializers.ModelSerializer):
    collector_name = drf_serializers.CharField(source='collector.get_full_name', read_only=True)
    customer_name = drf_serializers.CharField(source='customer.get_full_name', read_only=True)
    loan_number = drf_serializers.CharField(source='loan.loan_number', read_only=True, default='')
    visit_type_display = drf_serializers.CharField(source='get_visit_type_display', read_only=True)
    outcome_display = drf_serializers.CharField(source='get_outcome_display', read_only=True)

    class Meta:
        model = CollectorVisit
        fields = [
            'id', 'collector', 'collector_name',
            'customer', 'customer_name',
            'loan', 'loan_number', 'schedule',
            'latitude', 'longitude', 'accuracy', 'altitude',
            'visit_type', 'visit_type_display',
            'outcome', 'outcome_display',
            'notes', 'amount_collected',
            'promise_date', 'promise_amount',
            'photo',
            'checked_in_at', 'checked_out_at',
            'created_at',
        ]
        read_only_fields = ['id', 'collector', 'collector_name', 'created_at']


class CollectorVisitCreateSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = CollectorVisit
        fields = [
            'customer', 'loan', 'schedule',
            'latitude', 'longitude', 'accuracy', 'altitude',
            'visit_type', 'outcome', 'notes',
            'amount_collected', 'promise_date', 'promise_amount',
            'photo',
        ]


class CollectorLocationSerializer(drf_serializers.ModelSerializer):
    collector_name = drf_serializers.CharField(source='collector.get_full_name', read_only=True)

    class Meta:
        model = CollectorLocation
        fields = [
            'id', 'collector', 'collector_name',
            'latitude', 'longitude', 'accuracy',
            'speed', 'heading', 'battery_level',
            'timestamp',
        ]
        read_only_fields = ['id', 'collector', 'timestamp']


class LocationPingSerializer(drf_serializers.Serializer):
    """Lightweight serializer for GPS pings from mobile."""
    latitude = drf_serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = drf_serializers.DecimalField(max_digits=10, decimal_places=7)
    accuracy = drf_serializers.FloatField(required=False)
    speed = drf_serializers.FloatField(required=False)
    heading = drf_serializers.FloatField(required=False)
    battery_level = drf_serializers.IntegerField(required=False)


# === ViewSets ===

class CollectorVisitViewSet(viewsets.ModelViewSet):
    """CRUD for collector visits."""
    queryset = CollectorVisit.objects.select_related(
        'collector', 'customer', 'loan', 'schedule'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['collector', 'customer', 'loan', 'visit_type', 'outcome']
    search_fields = ['notes', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['checked_in_at', 'created_at']
    ordering = ['-checked_in_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectorVisitCreateSerializer
        return CollectorVisitSerializer

    def perform_create(self, serializer):
        serializer.save(collector=self.request.user)

    @action(detail=True, methods=['post'], url_path='checkout')
    def checkout(self, request, pk=None):
        """Mark a visit as checked out."""
        visit = self.get_object()
        if visit.checked_out_at:
            return Response({'error': 'Ya se hizo checkout'}, status=status.HTTP_400_BAD_REQUEST)

        visit.checked_out_at = timezone.now()
        # Update outcome if provided
        outcome = request.data.get('outcome')
        if outcome:
            visit.outcome = outcome
        notes = request.data.get('notes')
        if notes:
            visit.notes = (visit.notes + '\n' + notes).strip() if visit.notes else notes
        amount = request.data.get('amount_collected')
        if amount:
            visit.amount_collected = amount

        visit.save()
        return Response(CollectorVisitSerializer(visit).data)

    @action(detail=False, methods=['get'], url_path='my-visits')
    def my_visits(self, request):
        """Get current user's visits for today."""
        today = timezone.now().date()
        visits = self.get_queryset().filter(
            collector=request.user,
            checked_in_at__date=today,
        )
        return Response(CollectorVisitSerializer(visits, many=True).data)

    @action(detail=False, methods=['get'], url_path='today')
    def today_visits(self, request):
        """Get all visits for today (admin view)."""
        today = timezone.now().date()
        visits = self.get_queryset().filter(checked_in_at__date=today)
        return Response(CollectorVisitSerializer(visits, many=True).data)

    @action(detail=False, methods=['get'], url_path='stats')
    def visit_stats(self, request):
        """Get visit statistics for a date range."""
        from django.db.models import Count, Sum

        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        visits = self.get_queryset().filter(checked_in_at__gte=since)

        stats = {
            'total_visits': visits.count(),
            'by_outcome': list(visits.values('outcome').annotate(count=Count('id'))),
            'total_collected': float(visits.aggregate(total=Sum('amount_collected'))['total'] or 0),
            'by_collector': list(
                visits.values('collector__first_name', 'collector__last_name')
                .annotate(count=Count('id'), collected=Sum('amount_collected'))
            ),
            'period_days': days,
        }
        return Response(stats)


class CollectorLocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GPS location tracking for collectors.
    Read-only for admin, collectors POST pings.
    """
    queryset = CollectorLocation.objects.select_related('collector').all()
    serializer_class = CollectorLocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['collector']
    ordering = ['-timestamp']

    @action(detail=False, methods=['post'], url_path='ping')
    def ping(self, request):
        """Record a GPS ping from the collector's device."""
        serializer = LocationPingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = CollectorLocation.objects.create(
            collector=request.user,
            **serializer.validated_data,
        )

        return Response(
            CollectorLocationSerializer(location).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'], url_path='latest')
    def latest_locations(self, request):
        """Get the latest location for each active collector (admin dashboard)."""
        from django.db.models import Max

        # Get latest timestamp per collector
        cutoff = timezone.now() - timedelta(hours=12)
        latest = CollectorLocation.objects.filter(
            timestamp__gte=cutoff,
        ).values('collector').annotate(
            latest_ts=Max('timestamp'),
        )

        locations = []
        for entry in latest:
            loc = CollectorLocation.objects.filter(
                collector_id=entry['collector'],
                timestamp=entry['latest_ts'],
            ).select_related('collector').first()
            if loc:
                locations.append(CollectorLocationSerializer(loc).data)

        return Response(locations)

    @action(detail=False, methods=['get'], url_path='route')
    def collector_route(self, request):
        """Get GPS route for a collector on a specific date."""
        collector_id = request.query_params.get('collector')
        date_str = request.query_params.get('date', timezone.now().date().isoformat())

        if not collector_id:
            return Response({'error': 'collector parameter required'}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import date as date_type
        target_date = date_type.fromisoformat(date_str)

        points = CollectorLocation.objects.filter(
            collector_id=collector_id,
            timestamp__date=target_date,
        ).order_by('timestamp')

        return Response(CollectorLocationSerializer(points, many=True).data)
