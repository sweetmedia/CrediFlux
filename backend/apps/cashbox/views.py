"""Views for Cash Management."""
import logging
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.users.authz import ViewPermissionRequired

from .models import CashRegister, CashSession, CashMovement, DenominationCount
from .serializers import (
    CashRegisterSerializer,
    CashSessionSerializer,
    CashSessionOpenSerializer,
    CashSessionCloseSerializer,
    CashMovementSerializer,
    CashMovementCreateSerializer,
    DenominationCountSerializer,
)

logger = logging.getLogger(__name__)


class CanManageCashOperations(ViewPermissionRequired):
    """Caja: el código sale de `view.permission_codes` (cashbox.* del catálogo, D6).

    Conserva el nombre histórico para los imports. Ya no mira el rol: dueño y superusuario
    tienen todos los códigos; el resto, los de su Role. Lo que el mapa no nombra se niega.
    """


class CashRegisterViewSet(viewsets.ModelViewSet):
    """CRUD for cash registers."""
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer
    permission_classes = [IsAuthenticated, CanManageCashOperations]
    # Crear y editar una caja exigen lo mismo que abrir turno; borrarla, administrar cajas.
    permission_codes = {
        'list': 'cashbox.view',
        'retrieve': 'cashbox.view',
        'create': 'cashbox.open',
        'update': 'cashbox.open',
        'partial_update': 'cashbox.open',
        'destroy': 'cashbox.registers',
    }
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']

    def perform_destroy(self, instance):
        # Borrar una caja arrastraría sus sesiones cerradas (y su diferencia) del libro.
        if instance.sessions.exists():
            raise ValidationError({'detail': 'La caja tiene sesiones registradas; desactívela en lugar de eliminarla.'})
        instance.delete()


class CashSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Cash session management — open, close, view sessions.
    """
    queryset = CashSession.objects.select_related('register', 'cashier', 'closed_by').all()
    serializer_class = CashSessionSerializer
    permission_classes = [IsAuthenticated, CanManageCashOperations]
    permission_codes = {
        'list': 'cashbox.view',
        'retrieve': 'cashbox.view',
        'open_session': 'cashbox.open',
        'close_session': 'cashbox.close',
        'session_movements': 'cashbox.view',
        'session_summary': 'cashbox.view',
        'active_sessions': 'cashbox.view',
    }
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['register', 'status', 'cashier']
    ordering_fields = ['opened_at', 'closed_at']
    ordering = ['-opened_at']

    @action(detail=False, methods=['post'], url_path='open')
    def open_session(self, request):
        """Open a new cash session (apertura de caja)."""
        serializer = CashSessionOpenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        register_id = serializer.validated_data['register']

        # Check no open session exists for this register
        open_session = CashSession.objects.filter(
            register_id=register_id, status='open'
        ).first()
        if open_session:
            return Response(
                {'error': f'Ya existe una sesión abierta para esta caja (desde {open_session.opened_at.strftime("%d/%m/%Y %H:%M")})'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            register = CashRegister.objects.get(id=register_id)
        except CashRegister.DoesNotExist:
            return Response({'error': 'Caja no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        session = CashSession.objects.create(
            register=register,
            cashier=request.user,
            opening_balance=serializer.validated_data['opening_balance'],
            opening_notes=serializer.validated_data.get('opening_notes', ''),
            status='open',
            created_by=request.user,
        )

        return Response(
            CashSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='close')
    def close_session(self, request, pk=None):
        """Close a cash session (cierre de caja)."""
        session = self.get_object()

        if session.status != 'open':
            return Response(
                {'error': 'Esta sesión no está abierta'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CashSessionCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        closing_balance = serializer.validated_data['closing_balance']

        # Calculate expected balance
        opening = Decimal(str(session.opening_balance.amount))
        inflows = session.movements.filter(movement_type='inflow').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        outflows = session.movements.filter(movement_type='outflow').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        expected = opening + inflows - outflows
        difference = closing_balance - expected

        session.closing_balance = closing_balance
        session.expected_balance = expected
        session.difference = difference
        session.closing_notes = serializer.validated_data.get('closing_notes', '')
        session.closed_at = timezone.now()
        session.closed_by = request.user
        session.status = 'closed'
        session.save()

        return Response(CashSessionSerializer(session).data)

    @action(detail=True, methods=['get'], url_path='movements')
    def session_movements(self, request, pk=None):
        """Get all movements for a session."""
        session = self.get_object()
        movements = session.movements.all().order_by('-created_at')
        serializer = CashMovementSerializer(movements, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='summary')
    def session_summary(self, request, pk=None):
        """Get session summary with category totals."""
        session = self.get_object()
        movements = session.movements.all()

        inflows_by_cat = movements.filter(movement_type='inflow').values('category').annotate(
            total=Sum('amount')
        )
        outflows_by_cat = movements.filter(movement_type='outflow').values('category').annotate(
            total=Sum('amount')
        )

        total_inflows = sum(i['total'] or 0 for i in inflows_by_cat)
        total_outflows = sum(o['total'] or 0 for o in outflows_by_cat)

        return Response({
            'session_id': str(session.id),
            'register': session.register.name,
            'status': session.status,
            'opened_at': session.opened_at,
            'closed_at': session.closed_at,
            'opening_balance': float(session.opening_balance.amount),
            'total_inflows': float(total_inflows),
            'total_outflows': float(total_outflows),
            'expected_balance': float(session.opening_balance.amount) + float(total_inflows) - float(total_outflows),
            'closing_balance': float(session.closing_balance.amount) if session.closing_balance else None,
            'difference': float(session.difference.amount) if session.difference else None,
            'inflows_by_category': [
                {'category': i['category'], 'total': float(i['total'])} for i in inflows_by_cat
            ],
            'outflows_by_category': [
                {'category': o['category'], 'total': float(o['total'])} for o in outflows_by_cat
            ],
            'movement_count': movements.count(),
        })

    @action(detail=False, methods=['get'], url_path='active')
    def active_sessions(self, request):
        """Get all currently open sessions."""
        sessions = CashSession.objects.filter(status='open').select_related('register', 'cashier')
        return Response(CashSessionSerializer(sessions, many=True).data)


class CashMovementViewSet(viewsets.ModelViewSet):
    """CRUD for cash movements."""
    queryset = CashMovement.objects.select_related(
        'session', 'session__register', 'recorded_by', 'loan_payment', 'loan'
    ).all()
    permission_classes = [IsAuthenticated, CanManageCashOperations]
    permission_codes = {
        'list': 'cashbox.view',
        'retrieve': 'cashbox.view',
        'create': 'cashbox.movements',
        'update': 'cashbox.movements',
        'partial_update': 'cashbox.movements',
        'destroy': 'cashbox.movements',
    }
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['session', 'movement_type', 'category']
    search_fields = ['description', 'reference', 'customer_name']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CashMovementCreateSerializer
        return CashMovementSerializer

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

    @staticmethod
    def _ensure_session_open(movement):
        if movement.session.status != 'open':
            raise ValidationError({'detail': 'La sesión de caja no está abierta.'})

    def perform_update(self, serializer):
        self._ensure_session_open(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_session_open(instance)
        instance.delete()


class DenominationCountViewSet(viewsets.ModelViewSet):
    """CRUD for denomination counts."""
    queryset = DenominationCount.objects.select_related('session').all()
    serializer_class = DenominationCountSerializer
    permission_classes = [IsAuthenticated, CanManageCashOperations]
    permission_codes = {
        'list': 'cashbox.view',
        'retrieve': 'cashbox.view',
        'create': 'cashbox.movements',
        'update': 'cashbox.movements',
        'partial_update': 'cashbox.movements',
        'destroy': 'cashbox.movements',
    }
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session', 'count_type']

    @staticmethod
    def _ensure_session_open(session):
        # Mismo invariante que los movimientos: el conteo físico de un turno cerrado no se reescribe.
        if session.status != 'open':
            raise ValidationError({'detail': 'La sesión de caja no está abierta.'})

    def perform_create(self, serializer):
        self._ensure_session_open(serializer.validated_data['session'])
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_session_open(serializer.instance.session)
        self._ensure_session_open(serializer.validated_data.get('session', serializer.instance.session))
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_session_open(instance.session)
        instance.delete()
