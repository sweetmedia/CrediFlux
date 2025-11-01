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
from .models_collections import CollectionReminder, CollectionContact
from .serializers import (
    CustomerSerializer, CustomerListSerializer,
    CustomerDocumentSerializer, CustomerDocumentListSerializer,
    LoanSerializer, LoanListSerializer, LoanCreateSerializer,
    LoanScheduleSerializer, LoanPaymentSerializer, LoanPaymentCreateSerializer,
    CollateralSerializer, CollectionReminderSerializer, CollectionReminderCreateSerializer,
    CollectionContactSerializer, CollectionContactCreateSerializer
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
    queryset = Loan.objects.select_related(
        'customer', 'loan_officer', 'approved_by', 'rejected_by'
    ).prefetch_related(
        'payment_schedules', 'payments', 'collaterals'
    ).all()
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

        if loan.status != 'pending':
            return Response(
                {'error': 'Solo se pueden rechazar préstamos pendientes'},
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
        from django.utils import timezone

        loans = self.get_queryset()

        # Count overdue loans (loans with pending schedules past due date)
        overdue_loans = loans.filter(
            payment_schedules__status='pending',
            payment_schedules__due_date__lt=timezone.now().date()
        ).distinct().count()

        stats = {
            'total_loans': loans.count(),
            'active_loans': loans.filter(status='active').count(),
            'pending_loans': loans.filter(status='pending').count(),
            'paid_loans': loans.filter(status='paid').count(),
            'defaulted_loans': loans.filter(status='defaulted').count(),
            'overdue_loans': overdue_loans,
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
        from dateutil.relativedelta import relativedelta
        from moneyed import Money
        from decimal import Decimal

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

        current_date = loan.first_payment_date or loan.disbursement_date
        schedules = []

        # Check interest type (default to 'fixed' if not set)
        interest_type = getattr(loan, 'interest_type', 'fixed')

        if interest_type == 'variable':
            # ========================================
            # INTERÉS VARIABLE/AMORTIZADO (sobre saldo decreciente)
            # ========================================
            # El interés se calcula sobre el CAPITAL RESTANTE
            # Cada cuota paga MENOS interés que la anterior

            principal_per_payment = (loan.principal_amount.amount / num_payments).quantize(Decimal('0.01'))
            capital_restante = loan.principal_amount.amount

            for i in range(1, int(num_payments) + 1):
                # Calcular interés sobre capital restante
                # interes(i) = capital_restante * tasa_interes / 100
                interest_amount = (capital_restante * loan.interest_rate / 100 * Decimal(loan.term_months) / Decimal(12) / num_payments).quantize(Decimal('0.01'))

                # Para la última cuota, ajustar el capital para que sume exactamente el total
                if i == int(num_payments):
                    total_principal_assigned = sum(s.principal_amount.amount for s in schedules)
                    principal_amount = loan.principal_amount.amount - total_principal_assigned
                else:
                    principal_amount = principal_per_payment

                total_amount = (principal_amount + interest_amount).quantize(Decimal('0.01'))

                schedule = LoanSchedule.objects.create(
                    loan=loan,
                    installment_number=i,
                    due_date=current_date,
                    total_amount=Money(total_amount, loan.principal_amount.currency),
                    principal_amount=Money(principal_amount, loan.principal_amount.currency),
                    interest_amount=Money(interest_amount, loan.principal_amount.currency)
                )
                schedules.append(schedule)

                # Reducir capital restante
                capital_restante = (capital_restante - principal_amount).quantize(Decimal('0.01'))

                # Move to next payment date
                current_date = current_date + relativedelta(**period_delta)

        else:
            # ========================================
            # INTERÉS FIJO (distribuido equitativamente)
            # ========================================
            # El interés total se distribuye equitativamente entre todas las cuotas

            total_interest = loan.principal_amount * (loan.interest_rate / 100) * (loan.term_months / 12)
            total_amount = loan.principal_amount + total_interest

            # Calculate and round amounts to 2 decimal places
            payment_amount = (total_amount / num_payments).amount.quantize(Decimal('0.01'))
            principal_per_payment = (loan.principal_amount / num_payments).amount.quantize(Decimal('0.01'))
            interest_per_payment = (total_interest / num_payments).amount.quantize(Decimal('0.01'))

            # Create schedule entries (all except last)
            for i in range(1, int(num_payments)):
                schedule = LoanSchedule.objects.create(
                    loan=loan,
                    installment_number=i,
                    due_date=current_date,
                    total_amount=Money(payment_amount, loan.principal_amount.currency),
                    principal_amount=Money(principal_per_payment, loan.principal_amount.currency),
                    interest_amount=Money(interest_per_payment, loan.principal_amount.currency)
                )
                schedules.append(schedule)

                # Move to next payment date
                current_date = current_date + relativedelta(**period_delta)

            # Create last installment with adjusted amounts
            if num_payments > 0:
                total_principal_assigned = sum(s.principal_amount.amount for s in schedules)
                total_interest_assigned = sum(s.interest_amount.amount for s in schedules)

                last_principal = loan.principal_amount.amount - total_principal_assigned
                last_interest = total_interest.amount - total_interest_assigned
                last_total = last_principal + last_interest

                last_schedule = LoanSchedule.objects.create(
                    loan=loan,
                    installment_number=int(num_payments),
                    due_date=current_date,
                    total_amount=Money(last_total, loan.principal_amount.currency),
                    principal_amount=Money(last_principal, loan.principal_amount.currency),
                    interest_amount=Money(last_interest, loan.principal_amount.currency)
                )
                schedules.append(last_schedule)

                # Move to next payment date for maturity
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
    def confirm(self, request, pk=None):
        """
        Confirm a pending payment.
        Updates loan schedule and outstanding balance.
        """
        from moneyed import Money

        payment = self.get_object()

        if payment.status != 'pending':
            return Response(
                {'error': 'Solo se pueden confirmar pagos pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update payment status
        payment.status = 'completed'
        payment.save()

        # Update loan outstanding balance
        loan = payment.loan
        loan.outstanding_balance -= payment.principal_paid
        loan.total_paid += payment.amount
        loan.total_interest_paid += payment.interest_paid
        loan.save()

        # Update schedule if linked
        if payment.schedule:
            schedule = payment.schedule

            # Update paid amount
            schedule.paid_amount = (schedule.paid_amount or Money(0, schedule.total_amount.currency)) + payment.amount

            # Update late fee paid
            schedule.late_fee_paid = (schedule.late_fee_paid or Money(0, schedule.late_fee_amount.currency)) + payment.late_fee_paid

            # Set actual payment date if not set
            if not schedule.actual_payment_date:
                schedule.actual_payment_date = payment.payment_date

            # Update status
            if schedule.paid_amount >= schedule.total_amount + schedule.late_fee_amount:
                schedule.status = 'paid'
                schedule.paid_date = payment.payment_date
            elif schedule.paid_amount > Money(0, schedule.total_amount.currency):
                schedule.status = 'partial'

            schedule.save()

        serializer = self.get_serializer(payment)
        return Response({
            'message': 'Pago confirmado exitosamente',
            'payment': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending payment"""
        payment = self.get_object()

        if payment.status not in ['pending']:
            return Response(
                {'error': 'Solo se pueden cancelar pagos pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment.status = 'cancelled'
        payment.save()

        return Response({'message': 'Pago cancelado'})

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """
        Reverse a completed payment.
        This will reverse the updates made to loan and schedule.
        """
        from moneyed import Money

        payment = self.get_object()

        if payment.status == 'reversed':
            return Response(
                {'error': 'El pago ya ha sido reversado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.status != 'completed':
            return Response(
                {'error': 'Solo se pueden reversar pagos completados'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reverse loan balances
        loan = payment.loan
        loan.outstanding_balance += payment.principal_paid
        loan.total_paid -= payment.amount
        loan.total_interest_paid -= payment.interest_paid
        loan.save()

        # Reverse schedule updates if linked
        if payment.schedule:
            schedule = payment.schedule
            schedule.paid_amount -= payment.amount
            schedule.late_fee_paid -= payment.late_fee_paid

            # Recalculate status
            if schedule.paid_amount <= Money(0, schedule.total_amount.currency):
                schedule.status = 'pending'
                schedule.paid_date = None
            else:
                schedule.status = 'partial'

            schedule.save()

        # Mark payment as reversed
        payment.status = 'reversed'
        payment.save()

        return Response({'message': 'Pago reversado exitosamente'})


class LoanScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing loan schedules (read-only)
    """
    queryset = LoanSchedule.objects.select_related('loan', 'loan__customer').all()
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
            status__in=['pending', 'partial', 'overdue']
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


class CollectionReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing collection reminders
    """
    queryset = CollectionReminder.objects.select_related(
        'loan', 'customer', 'loan_schedule', 'sent_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'reminder_type', 'channel', 'loan', 'customer']
    search_fields = [
        'loan__loan_number', 'customer__first_name',
        'customer__last_name', 'message_content'
    ]
    ordering_fields = ['scheduled_for', 'sent_at', 'created_at']
    ordering = ['-scheduled_for']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionReminderCreateSerializer
        return CollectionReminderSerializer

    def perform_create(self, serializer):
        """Auto-set status to pending"""
        serializer.save(status='pending')

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send a reminder (mark as sent)
        In production, this would trigger actual sending via email/SMS/WhatsApp
        """
        reminder = self.get_object()

        if reminder.status != 'pending':
            return Response(
                {'error': 'Solo se pueden enviar recordatorios pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update reminder
        reminder.status = 'sent'
        reminder.sent_at = timezone.now()
        reminder.sent_by = request.user
        reminder.save()

        # TODO: Integrate with actual email/SMS/WhatsApp API
        # For now, we just mark it as sent

        serializer = self.get_serializer(reminder)
        return Response({
            'message': 'Recordatorio enviado exitosamente',
            'reminder': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending reminder"""
        reminder = self.get_object()

        if reminder.status not in ['pending']:
            return Response(
                {'error': 'Solo se pueden cancelar recordatorios pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reminder.status = 'cancelled'
        reminder.save()

        return Response({'message': 'Recordatorio cancelado'})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending reminders"""
        pending = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def scheduled_today(self, request):
        """Get reminders scheduled for today"""
        today = timezone.now().date()
        reminders = self.get_queryset().filter(
            scheduled_for__date=today,
            status='pending'
        )
        serializer = self.get_serializer(reminders, many=True)
        return Response(serializer.data)


class CollectionContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing collection contacts (contact history)
    """
    queryset = CollectionContact.objects.select_related(
        'loan', 'customer', 'contacted_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'contact_type', 'outcome', 'loan', 'customer',
        'requires_escalation', 'promise_kept'
    ]
    search_fields = [
        'loan__loan_number', 'customer__first_name',
        'customer__last_name', 'notes'
    ]
    ordering_fields = ['contact_date', 'created_at', 'promise_date']
    ordering = ['-contact_date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollectionContactCreateSerializer
        return CollectionContactSerializer

    def perform_create(self, serializer):
        """Auto-assign contacted_by to current user"""
        serializer.save(contacted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_promise_kept(self, request, pk=None):
        """Mark a promise to pay as kept"""
        contact = self.get_object()

        if contact.outcome not in ['promise_to_pay', 'payment_plan']:
            return Response(
                {'error': 'Este contacto no tiene una promesa de pago registrada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact.promise_kept = True
        contact.save()

        return Response({'message': 'Promesa de pago marcada como cumplida'})

    @action(detail=True, methods=['post'])
    def mark_promise_broken(self, request, pk=None):
        """Mark a promise to pay as broken"""
        contact = self.get_object()

        if contact.outcome not in ['promise_to_pay', 'payment_plan']:
            return Response(
                {'error': 'Este contacto no tiene una promesa de pago registrada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contact.promise_kept = False
        contact.save()

        return Response({'message': 'Promesa de pago marcada como incumplida'})

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate a contact to supervisor"""
        contact = self.get_object()
        contact.requires_escalation = True
        contact.save()

        return Response({'message': 'Contacto escalado a supervisor'})

    @action(detail=False, methods=['get'])
    def requiring_escalation(self, request):
        """Get all contacts requiring escalation"""
        contacts = self.get_queryset().filter(requires_escalation=True)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def promises_due_today(self, request):
        """Get contacts with promises due today"""
        today = timezone.now().date()
        contacts = self.get_queryset().filter(
            promise_date=today,
            promise_kept__isnull=True
        )
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def broken_promises(self, request):
        """Get contacts with broken promises"""
        contacts = self.get_queryset().filter(promise_kept=False)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_collector(self, request):
        """Get contacts by collector (current user or specified user_id)"""
        user_id = request.query_params.get('user_id', request.user.id)
        contacts = self.get_queryset().filter(contacted_by_id=user_id)

        # Optional date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if start_date:
            contacts = contacts.filter(contact_date__gte=start_date)
        if end_date:
            contacts = contacts.filter(contact_date__lte=end_date)

        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)
