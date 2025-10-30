"""
Views and viewsets for loan module
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Sum, Count
from decimal import Decimal

from .models import Customer, CustomerDocument, Loan, LoanSchedule, LoanPayment, Collateral
from .serializers import (
    CustomerSerializer, CustomerListSerializer,
    CustomerDocumentSerializer, CustomerDocumentListSerializer,
    LoanSerializer, LoanListSerializer, LoanCreateSerializer,
    LoanScheduleSerializer, LoanPaymentSerializer, CollateralSerializer
)
from .permissions import CanApproveLoan, CanManageLoans


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers
    """
    queryset = Customer.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'employment_status', 'id_type']
    search_fields = [
        'customer_id', 'first_name', 'last_name', 'email',
        'phone', 'id_number'
    ]
    ordering_fields = ['created_at', 'first_name', 'last_name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        return CustomerSerializer

    @action(detail=True, methods=['get'])
    def loans(self, request, pk=None):
        """Get all loans for a customer"""
        customer = self.get_object()
        loans = customer.loans.all()
        serializer = LoanListSerializer(loans, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get customer statistics"""
        customer = self.get_object()
        loans = customer.loans.all()

        stats = {
            'total_loans': loans.count(),
            'active_loans': loans.filter(status='active').count(),
            'paid_loans': loans.filter(status='paid').count(),
            'defaulted_loans': loans.filter(status='defaulted').count(),
            'total_borrowed': loans.aggregate(
                total=Sum('principal_amount')
            )['total'] or 0,
            'total_outstanding': loans.filter(status='active').aggregate(
                total=Sum('outstanding_balance')
            )['total'] or 0,
        }

        return Response(stats)


class CustomerDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customer documents
    """
    queryset = CustomerDocument.objects.select_related('customer', 'verified_by').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'document_type', 'verification_status', 'is_primary']
    search_fields = ['title', 'description', 'customer__customer_id', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['created_at', 'expiry_date', 'verification_status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerDocumentListSerializer
        return CustomerDocumentSerializer

    def perform_create(self, serializer):
        """Auto-assign created_by user"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[CanManageLoans])
    def verify(self, request, pk=None):
        """
        Verify a customer document.
        Only admin, manager, or loan_officer can verify documents.
        """
        document = self.get_object()

        if document.verification_status == 'verified':
            return Response(
                {'error': 'El documento ya ha sido verificado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update document
        document.verification_status = 'verified'
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.rejection_reason = None
        document.save()

        serializer = self.get_serializer(document)
        return Response({
            'message': 'Documento verificado exitosamente',
            'document': serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[CanManageLoans])
    def reject(self, request, pk=None):
        """
        Reject a customer document.
        Only admin, manager, or loan_officer can reject documents.
        """
        document = self.get_object()

        # Get rejection reason from request (required)
        rejection_reason = request.data.get('reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Se requiere especificar el motivo del rechazo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update document
        document.verification_status = 'rejected'
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.rejection_reason = rejection_reason
        document.save()

        serializer = self.get_serializer(document)
        return Response({
            'message': 'Documento rechazado',
            'document': serializer.data
        })

    @action(detail=True, methods=['post'])
    def mark_primary(self, request, pk=None):
        """Mark this document as primary for its type"""
        document = self.get_object()

        # Unmark all other documents of same type for this customer
        CustomerDocument.objects.filter(
            customer=document.customer,
            document_type=document.document_type,
            is_primary=True
        ).exclude(id=document.id).update(is_primary=False)

        # Mark this document as primary
        document.is_primary = True
        document.save()

        return Response({
            'message': 'Documento marcado como principal',
            'document': self.get_serializer(document).data
        })

    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get all expired documents"""
        today = timezone.now().date()
        expired_docs = self.get_queryset().filter(
            expiry_date__lt=today
        ).exclude(verification_status='expired')

        serializer = self.get_serializer(expired_docs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_verification(self, request):
        """Get all documents pending verification"""
        pending_docs = self.get_queryset().filter(
            verification_status='pending'
        )

        serializer = self.get_serializer(pending_docs, many=True)
        return Response(serializer.data)


class LoanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loans
    """
    queryset = Loan.objects.select_related('customer', 'loan_officer').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'loan_type', 'customer']
    search_fields = [
        'loan_number', 'customer__customer_id',
        'customer__first_name', 'customer__last_name'
    ]
    ordering_fields = ['created_at', 'disbursement_date', 'principal_amount']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LoanListSerializer
        elif self.action == 'create':
            return LoanCreateSerializer
        return LoanSerializer

    def perform_create(self, serializer):
        loan = serializer.save(created_by=self.request.user)

        # Set outstanding balance to principal amount
        loan.outstanding_balance = loan.principal_amount
        loan.save()

    @action(detail=True, methods=['post'], permission_classes=[CanApproveLoan])
    def approve(self, request, pk=None):
        """
        Approve a loan.
        Only admin, manager, or loan_officer can approve loans.
        """
        loan = self.get_object()

        if loan.status != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar préstamos pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get approval notes from request
        approval_notes = request.data.get('notes', '')

        # Update loan
        loan.status = 'approved'
        loan.approval_date = timezone.now().date()
        loan.approved_by = request.user
        loan.approval_notes = approval_notes
        loan.save()

        serializer = self.get_serializer(loan)
        return Response({
            'message': 'Préstamo aprobado exitosamente',
            'loan': serializer.data
        })

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        """Disburse a loan (mark as active)"""
        loan = self.get_object()

        if loan.status != 'approved':
            return Response(
                {'error': 'Only approved loans can be disbursed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        loan.status = 'active'
        loan.disbursement_date = timezone.now().date()
        loan.outstanding_balance = loan.principal_amount
        loan.save()

        # Generate payment schedule
        self._generate_payment_schedule(loan)

        return Response({'status': 'loan disbursed'})

    @action(detail=True, methods=['post'], permission_classes=[CanApproveLoan])
    def reject(self, request, pk=None):
        """
        Reject a loan.
        Only admin, manager, or loan_officer can reject loans.
        """
        loan = self.get_object()

        if loan.status not in ['draft', 'pending']:
            return Response(
                {'error': 'Solo se pueden rechazar préstamos en borrador o pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get rejection notes from request (required)
        rejection_notes = request.data.get('notes', '')
        if not rejection_notes:
            return Response(
                {'error': 'Se requiere una nota explicando el motivo del rechazo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update loan
        loan.status = 'rejected'
        loan.rejection_date = timezone.now().date()
        loan.rejected_by = request.user
        loan.approval_notes = rejection_notes
        loan.save()

        serializer = self.get_serializer(loan)
        return Response({
            'message': 'Préstamo rechazado',
            'loan': serializer.data
        })

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Get payment schedule for a loan"""
        loan = self.get_object()
        schedules = loan.payment_schedules.all()
        serializer = LoanScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get all payments for a loan"""
        loan = self.get_object()
        payments = loan.payments.all()
        serializer = LoanPaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get overall loan statistics"""
        loans = self.get_queryset()

        stats = {
            'total_loans': loans.count(),
            'active_loans': loans.filter(status='active').count(),
            'pending_loans': loans.filter(status='pending').count(),
            'paid_loans': loans.filter(status='paid').count(),
            'defaulted_loans': loans.filter(status='defaulted').count(),
            'total_disbursed': loans.filter(
                status__in=['active', 'paid', 'defaulted']
            ).aggregate(total=Sum('principal_amount'))['total'] or 0,
            'total_outstanding': loans.filter(status='active').aggregate(
                total=Sum('outstanding_balance')
            )['total'] or 0,
            'total_collected': loans.aggregate(
                total=Sum('total_paid')
            )['total'] or 0,
        }

        return Response(stats)

    def _generate_payment_schedule(self, loan):
        """Generate payment schedule for a loan"""
        # Simple payment schedule generation
        # In production, use proper amortization formulas

        from dateutil.relativedelta import relativedelta

        # Calculate period based on payment frequency
        frequency_map = {
            'daily': {'days': 1},
            'weekly': {'weeks': 1},
            'biweekly': {'weeks': 2},
            'monthly': {'months': 1},
            'quarterly': {'months': 3},
        }

        period_delta = frequency_map.get(loan.payment_frequency, {'months': 1})

        # Calculate number of payments
        if loan.payment_frequency == 'monthly':
            num_payments = loan.term_months
        elif loan.payment_frequency == 'quarterly':
            num_payments = loan.term_months // 3
        elif loan.payment_frequency == 'weekly':
            num_payments = loan.term_months * 4
        elif loan.payment_frequency == 'biweekly':
            num_payments = loan.term_months * 2
        elif loan.payment_frequency == 'daily':
            num_payments = loan.term_months * 30
        else:
            num_payments = loan.term_months

        # Simple interest calculation (for demonstration)
        total_interest = loan.principal_amount * (loan.interest_rate / 100) * (loan.term_months / 12)
        total_amount = loan.principal_amount + total_interest

        payment_amount = total_amount / num_payments
        principal_per_payment = loan.principal_amount / num_payments
        interest_per_payment = total_interest / num_payments

        current_date = loan.first_payment_date or loan.disbursement_date

        # Create schedule entries
        for i in range(1, int(num_payments) + 1):
            LoanSchedule.objects.create(
                loan=loan,
                installment_number=i,
                due_date=current_date,
                total_amount=payment_amount,
                principal_amount=principal_per_payment,
                interest_amount=interest_per_payment
            )

            # Move to next payment date
            current_date = current_date + relativedelta(**period_delta)

        # Update maturity date
        loan.maturity_date = current_date
        loan.save()


class LoanPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan payments
    """
    queryset = LoanPayment.objects.select_related('loan', 'schedule').all()
    serializer_class = LoanPaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'loan']
    search_fields = ['payment_number', 'reference_number', 'loan__loan_number']
    ordering_fields = ['payment_date', 'created_at', 'amount']
    ordering = ['-payment_date']

    def get_serializer_class(self):
        """Use different serializers for create vs read"""
        from .serializers import LoanPaymentCreateSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return LoanPaymentCreateSerializer
        return LoanPaymentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a payment"""
        payment = self.get_object()

        if payment.status == 'reversed':
            return Response(
                {'error': 'Payment already reversed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.status = 'reversed'
        payment.save()

        return Response({'status': 'payment reversed'})


class LoanScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing loan schedules (read-only)
    """
    queryset = LoanSchedule.objects.select_related('loan').all()
    serializer_class = LoanScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'loan']
    ordering_fields = ['due_date', 'installment_number']
    ordering = ['loan', 'installment_number']

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue schedules"""
        overdue = self.get_queryset().filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partial']
        )
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data)


class CollateralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing collaterals
    """
    queryset = Collateral.objects.select_related('loan').all()
    serializer_class = CollateralSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['collateral_type', 'status', 'loan']
    search_fields = ['description', 'loan__loan_number']
    ordering_fields = ['created_at', 'estimated_value']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a collateral"""
        collateral = self.get_object()
        collateral.status = 'released'
        collateral.save()
        return Response({'status': 'collateral released'})

    @action(detail=True, methods=['post'])
    def liquidate(self, request, pk=None):
        """Mark collateral as liquidated"""
        collateral = self.get_object()
        collateral.status = 'liquidated'
        collateral.save()
        return Response({'status': 'collateral liquidated'})
