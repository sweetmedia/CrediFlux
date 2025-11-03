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
from django.http import HttpResponse
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

    @action(detail=True, methods=['get'])
    def balance_report(self, request, pk=None):
        """
        Generate and download Balance de Cuotas PDF report for a loan
        """
        from .reports import LoanBalanceReport

        loan = self.get_object()

        # Generate PDF
        report = LoanBalanceReport(loan)
        pdf_data = report.generate()

        # Create HTTP response with PDF
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="balance_cuotas_{loan.loan_number}.pdf"'

        return response

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

            # Calculate period rate based on payment frequency
            # For monthly: annual_rate / 12
            # For quarterly: annual_rate / 4
            # For weekly: annual_rate / 52
            # For daily: annual_rate / 365
            periods_per_year = {
                'daily': 365,
                'weekly': 52,
                'biweekly': 26,
                'monthly': 12,
                'quarterly': 4,
            }
            period_divisor = Decimal(periods_per_year.get(loan.payment_frequency, 12))

            for i in range(1, int(num_payments) + 1):
                # Calcular interés sobre capital restante
                # interes(i) = capital_restante * (tasa_anual / periodos_por_año)
                # Ejemplo mensual: capital_restante * (10% / 12) = capital_restante * 0.00833
                interest_amount = (capital_restante * loan.interest_rate / 100 / period_divisor).quantize(Decimal('0.01'))

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

        elif interest_type == 'variable_rd':
            # ========================================
            # INTERÉS VARIABLE RD (Tasa directa por período)
            # ========================================
            # El interés se calcula aplicando la tasa DIRECTAMENTE al capital restante
            # SIN dividir entre períodos (método República Dominicana)
            # NOTA: Esto NO es estándar financiero internacional

            principal_per_payment = (loan.principal_amount.amount / num_payments).quantize(Decimal('0.01'))
            capital_restante = loan.principal_amount.amount

            for i in range(1, int(num_payments) + 1):
                # Calcular interés aplicando la tasa DIRECTAMENTE
                # interes(i) = capital_restante * tasa / 100
                # Ejemplo: $100,000 * 10% = $10,000
                interest_amount = (capital_restante * loan.interest_rate / 100).quantize(Decimal('0.01'))

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

        # Update outstanding_balance to reflect the total amount in the payment schedule
        # This is important for Variable RD and other interest types where the total
        # differs from the principal amount
        if schedules:
            from moneyed import Money
            total_schedule_amount = sum(s.total_amount.amount for s in schedules)
            loan.outstanding_balance = Money(total_schedule_amount, loan.principal_amount.currency)

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

# ============================================================================
# CONTRACT TEMPLATE VIEWSET
# ============================================================================

class ContractTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contract templates
    """
    from .models_contracts import ContractTemplate
    from .serializers import ContractTemplateSerializer, ContractTemplateListSerializer

    queryset = ContractTemplate.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'is_default']
    ordering = ['-is_default', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            from .serializers import ContractTemplateListSerializer
            return ContractTemplateListSerializer
        from .serializers import ContractTemplateSerializer
        return ContractTemplateSerializer

    def perform_create(self, serializer):
        """Auto-assign created_by user"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this template as the default"""
        template = self.get_object()
        template.is_default = True
        template.save()
        return Response({'message': 'Plantilla establecida como predeterminada'})

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a template"""
        from .models_contracts import ContractTemplate
        template = self.get_object()

        # Create a copy
        new_template = ContractTemplate.objects.create(
            name=f"{template.name} (Copia)",
            description=template.description,
            content=template.content,
            is_active=False,
            is_default=False,
            loan_types=template.loan_types,
            footer_text=template.footer_text,
            created_by=request.user
        )

        serializer = self.get_serializer(new_template)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def variables(self, request):
        """Get list of available variables for templates"""
        from .utils_contracts import get_available_variables
        return Response({'variables': get_available_variables()})


# ============================================================================
# CONTRACT VIEWSET
# ============================================================================

class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contracts
    """
    from .models_contracts import Contract

    queryset = Contract.objects.select_related(
        'loan', 'loan__customer', 'template', 'generated_by'
    ).all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'loan', 'is_archived']
    search_fields = ['contract_number', 'loan__loan_number', 'loan__customer__first_name', 'loan__customer__last_name']
    ordering_fields = ['generated_at', 'status']
    ordering = ['-generated_at']

    def get_queryset(self):
        """
        Filter archived contracts by default unless explicitly requested.
        Only applies to list action, not to retrieve/detail actions.
        """
        queryset = super().get_queryset()

        # Only filter archived contracts in list view
        if self.action == 'list':
            # Check if user wants to see archived contracts
            show_archived = self.request.query_params.get('show_archived', 'false').lower() == 'true'

            if not show_archived:
                # By default, exclude archived contracts from list
                queryset = queryset.filter(is_archived=False)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            from .serializers import ContractListSerializer
            return ContractListSerializer
        elif self.action == 'create':
            from .serializers import ContractCreateSerializer
            return ContractCreateSerializer
        from .serializers import ContractSerializer
        return ContractSerializer

    def perform_create(self, serializer):
        """Generate contract from template"""
        from .utils_contracts import replace_contract_variables

        contract = serializer.save(generated_by=self.request.user)

        template = contract.template
        tenant = getattr(self.request, 'tenant', None)

        if template:
            rendered_content = replace_contract_variables(
                template.content,
                contract.loan,
                tenant
            )
            contract.content = rendered_content
            contract.save()

        return contract

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate contract content from template"""
        from .utils_contracts import replace_contract_variables

        contract = self.get_object()

        if not contract.template:
            return Response(
                {'error': 'No se puede regenerar un contrato sin plantilla'},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant = getattr(request, 'tenant', None)

        rendered_content = replace_contract_variables(
            contract.template.content,
            contract.loan,
            tenant
        )

        contract.content = rendered_content
        contract.save()

        serializer = self.get_serializer(contract)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sign_customer(self, request, pk=None):
        """Mark contract as signed by customer"""
        contract = self.get_object()

        if contract.customer_signed_at:
            return Response(
                {'error': 'El cliente ya firmó este contrato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle signature - can be file or base64 string
        signature_file = request.FILES.get('signature')
        signature_data = request.data.get('signature_data')  # base64 from canvas

        if signature_file:
            contract.customer_signature = signature_file
        elif signature_data:
            # Handle base64 signature from canvas
            import base64
            from django.core.files.base import ContentFile
            import uuid

            try:
                # Remove data URL prefix if present
                if ',' in signature_data:
                    signature_data = signature_data.split(',')[1]

                signature_binary = base64.b64decode(signature_data)
                signature_file = ContentFile(signature_binary, name=f'signature_{uuid.uuid4()}.png')
                contract.customer_signature = signature_file
            except Exception as e:
                return Response(
                    {'error': f'Error al procesar firma: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        contract.customer_signed_at = timezone.now()

        if contract.status == 'draft':
            contract.status = 'pending_signature'
        elif contract.is_fully_signed:
            contract.status = 'signed'

        contract.save()

        return Response({'message': 'Contrato firmado por el cliente'})

    @action(detail=True, methods=['post'])
    def sign_officer(self, request, pk=None):
        """Mark contract as signed by loan officer"""
        contract = self.get_object()

        if contract.officer_signed_at:
            return Response(
                {'error': 'El oficial ya firmó este contrato'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle signature - can be file or base64 string
        signature_file = request.FILES.get('signature')
        signature_data = request.data.get('signature_data')  # base64 from canvas

        if signature_file:
            contract.officer_signature = signature_file
        elif signature_data:
            # Handle base64 signature from canvas
            import base64
            from django.core.files.base import ContentFile
            import uuid

            try:
                # Remove data URL prefix if present
                if ',' in signature_data:
                    signature_data = signature_data.split(',')[1]

                signature_binary = base64.b64decode(signature_data)
                signature_file = ContentFile(signature_binary, name=f'signature_{uuid.uuid4()}.png')
                contract.officer_signature = signature_file
            except Exception as e:
                return Response(
                    {'error': f'Error al procesar firma: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        contract.officer_signed_at = timezone.now()

        if contract.status == 'draft':
            contract.status = 'pending_signature'
        elif contract.is_fully_signed:
            contract.status = 'signed'

        contract.save()

        return Response({'message': 'Contrato firmado por el oficial'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a signed contract"""
        contract = self.get_object()

        if not contract.is_fully_signed:
            return Response(
                {'error': 'El contrato debe estar firmado por todas las partes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contract.status = 'active'
        contract.save()

        return Response({'message': 'Contrato activado'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a contract"""
        contract = self.get_object()

        if contract.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'No se puede cancelar un contrato completado o ya cancelado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contract.status = 'cancelled'
        contract.notes = f"{contract.notes}\n\nCancelado el {timezone.now().strftime('%Y-%m-%d %H:%M')} por {request.user.get_full_name()}"
        contract.save()

        return Response({'message': 'Contrato cancelado'})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a contract (only for cancelled contracts)"""
        contract = self.get_object()

        if contract.status != 'cancelled':
            return Response(
                {'error': 'Solo se pueden archivar contratos cancelados'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if contract.is_archived:
            return Response(
                {'error': 'Este contrato ya está archivado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contract.is_archived = True
        contract.archived_at = timezone.now()
        contract.archived_by = request.user
        contract.save()

        return Response({'message': 'Contrato archivado exitosamente'})

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive a contract"""
        contract = self.get_object()

        if not contract.is_archived:
            return Response(
                {'error': 'Este contrato no está archivado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        contract.is_archived = False
        contract.archived_at = None
        contract.archived_by = None
        contract.save()

        return Response({'message': 'Contrato desarchivado exitosamente'})

    @action(detail=True, methods=['post'])
    def send_for_signature(self, request, pk=None):
        """Send contract via email for signature"""
        import secrets
        from datetime import timedelta
        from django.core.mail import send_mail
        from django.conf import settings
        from .models_contracts import ContractSignatureToken

        contract = self.get_object()
        email = request.data.get('email')
        days_valid = request.data.get('days_valid', 7)  # Default 7 days

        if not email:
            return Response(
                {'error': 'Se requiere un email'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=days_valid)

        # Update contract status to pending_signature if it's draft
        if contract.status == 'draft':
            contract.status = 'pending_signature'
            contract.save()

        # Create signature token
        signature_token = ContractSignatureToken.objects.create(
            contract=contract,
            token=token,
            email=email,
            expires_at=expires_at,
            can_sign_as_customer=True,
            can_sign_as_officer=False,
        )

        # Get tenant for email
        tenant = getattr(request, 'tenant', None)
        company_name = tenant.business_name if tenant else 'CrediFlux'

        # Build signature URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        signature_url = f"{frontend_url}/sign/{token}"

        # Send email
        try:
            subject = f'Firma de Contrato - {contract.contract_number}'
            message = f"""
Hola,

{company_name} te ha enviado un contrato para tu firma.

Contrato: {contract.contract_number}
Cliente: {contract.customer_name}

Haz clic en el siguiente enlace para revisar y firmar el contrato:
{signature_url}

Este enlace expirará en {days_valid} días.

Si no solicitaste este contrato, puedes ignorar este mensaje.

Saludos,
{company_name}
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return Response({
                'message': f'Contrato enviado a {email}',
                'token_id': str(signature_token.id),
                'expires_at': signature_token.expires_at,
            })
        except Exception as e:
            # Delete token if email fails
            signature_token.delete()
            return Response(
                {'error': f'Error al enviar email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download contract as PDF"""
        from django.http import FileResponse
        from .utils_pdf import generate_contract_pdf

        contract = self.get_object()
        tenant = getattr(request, 'tenant', None)

        # Generate PDF with tenant information
        pdf_buffer = generate_contract_pdf(contract, tenant)

        # Create the FileResponse
        response = FileResponse(
            pdf_buffer,
            content_type='application/pdf',
            as_attachment=True,
            filename=f'{contract.contract_number}.pdf'
        )

        return response

    @action(detail=True, methods=['get'])
    def view_pdf(self, request, pk=None):
        """View contract PDF in browser"""
        from django.http import FileResponse
        from .utils_pdf import generate_contract_pdf

        contract = self.get_object()
        tenant = getattr(request, 'tenant', None)

        # Generate PDF with tenant information
        pdf_buffer = generate_contract_pdf(contract, tenant)

        # Create the FileResponse (for viewing, not download)
        response = FileResponse(
            pdf_buffer,
            content_type='application/pdf',
            as_attachment=False,
            filename=f'{contract.contract_number}.pdf'
        )

        return response


# Public API views (no authentication required)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def public_contract_view(request, token):
    """
    Public endpoint to view contract details with a signature token.
    No authentication required - uses token for access.
    """
    from .models_contracts import ContractSignatureToken, Contract
    from .serializers import ContractSerializer

    try:
        # Get signature token
        signature_token = ContractSignatureToken.objects.select_related(
            'contract', 'contract__loan', 'contract__loan__customer'
        ).get(token=token)

        # Check if token is valid
        if not signature_token.is_valid:
            if signature_token.is_expired:
                return Response(
                    {'error': 'Este enlace ha expirado'},
                    status=status.HTTP_410_GONE
                )
            elif signature_token.is_used:
                return Response(
                    {'error': 'Este enlace ya ha sido utilizado'},
                    status=status.HTTP_410_GONE
                )

        contract = signature_token.contract

        # Return contract details with token info
        serializer = ContractSerializer(contract)
        return Response({
            'contract': serializer.data,
            'token_permissions': {
                'can_sign_as_customer': signature_token.can_sign_as_customer,
                'can_sign_as_officer': signature_token.can_sign_as_officer,
            },
            'expires_at': signature_token.expires_at,
        })

    except ContractSignatureToken.DoesNotExist:
        return Response(
            {'error': 'Enlace de firma inválido'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def public_contract_sign(request, token):
    """
    Public endpoint to sign a contract with a signature token.
    No authentication required - uses token for authorization.
    """
    import base64
    import uuid
    from django.core.files.base import ContentFile
    from .models_contracts import ContractSignatureToken

    try:
        # Get signature token
        signature_token = ContractSignatureToken.objects.select_related('contract').get(token=token)

        # Check if token is valid
        if not signature_token.is_valid:
            if signature_token.is_expired:
                return Response(
                    {'error': 'Este enlace ha expirado'},
                    status=status.HTTP_410_GONE
                )
            elif signature_token.is_used:
                return Response(
                    {'error': 'Este enlace ya ha sido utilizado'},
                    status=status.HTTP_410_GONE
                )

        contract = signature_token.contract

        # Get signature data
        signature_data = request.data.get('signature_data')

        if not signature_data:
            return Response(
                {'error': 'Se requiere una firma'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process signature
        try:
            # Remove data URL prefix if present
            if ',' in signature_data:
                signature_data = signature_data.split(',')[1]

            signature_binary = base64.b64decode(signature_data)
            signature_file = ContentFile(signature_binary, name=f'signature_{uuid.uuid4()}.png')
        except Exception as e:
            return Response(
                {'error': f'Error al procesar firma: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Apply signature based on permissions
        if signature_token.can_sign_as_customer and not contract.customer_signed_at:
            contract.customer_signature = signature_file
            contract.customer_signed_at = timezone.now()
            signature_type = 'customer'
        elif signature_token.can_sign_as_officer and not contract.officer_signed_at:
            contract.officer_signature = signature_file
            contract.officer_signed_at = timezone.now()
            signature_type = 'officer'
        else:
            return Response(
                {'error': 'No tienes permisos para firmar este contrato o ya ha sido firmado'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update contract status
        if contract.status == 'draft':
            contract.status = 'pending_signature'
        elif contract.is_fully_signed:
            contract.status = 'signed'

        contract.save()

        # Mark token as used
        signature_token.mark_as_used()

        return Response({
            'message': 'Contrato firmado exitosamente',
            'signed_as': signature_type,
            'contract_status': contract.status,
            'is_fully_signed': contract.is_fully_signed,
        })

    except ContractSignatureToken.DoesNotExist:
        return Response(
            {'error': 'Enlace de firma inválido'},
            status=status.HTTP_404_NOT_FOUND
        )
