"""
Cash Management Models (Gestión de Caja).

Tracks daily cash register operations for financieras:
- Opening/closing of cash register
- Cash inflows (loan payments received)
- Cash outflows (loan disbursements, expenses, withdrawals)
- Daily reconciliation
- Denomination counting (billetes y monedas)
"""
from django.db import models
from django.conf import settings
from djmoney.models.fields import MoneyField
from apps.core.models import UUIDModel, AuditModel, TimeStampedModel


class CashRegister(UUIDModel, AuditModel):
    """
    A physical or logical cash register (caja).
    A financiera may have multiple registers (e.g., Caja Principal, Caja Cobros).
    """
    name = models.CharField(max_length=100, help_text='Nombre de la caja (ej: Caja Principal)')
    code = models.CharField(max_length=20, unique=True, help_text='Código único (ej: CAJA-01)')
    location = models.CharField(max_length=200, blank=True, help_text='Ubicación física')
    is_active = models.BooleanField(default=True)

    # Assigned cashier (optional — can be changed per session)
    default_cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_registers',
        help_text='Cajero asignado por defecto'
    )

    class Meta:
        db_table = 'cashbox_registers'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class CashSession(UUIDModel, AuditModel):
    """
    A cash register session (apertura/cierre de caja).
    Each day the cashier opens and closes the register.
    """
    register = models.ForeignKey(CashRegister, on_delete=models.CASCADE, related_name='sessions')
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cash_sessions',
        help_text='Cajero que abrió la caja'
    )

    # Opening
    opened_at = models.DateTimeField(auto_now_add=True)
    opening_balance = MoneyField(
        max_digits=14, decimal_places=2, default_currency='DOP',
        help_text='Balance de apertura (efectivo contado al abrir)'
    )
    opening_notes = models.TextField(blank=True)

    # Closing (filled when closing)
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_balance = MoneyField(
        max_digits=14, decimal_places=2, default_currency='DOP',
        null=True, blank=True,
        help_text='Balance de cierre (efectivo contado al cerrar)'
    )
    expected_balance = MoneyField(
        max_digits=14, decimal_places=2, default_currency='DOP',
        null=True, blank=True,
        help_text='Balance esperado (calculado por sistema)'
    )
    difference = MoneyField(
        max_digits=14, decimal_places=2, default_currency='DOP',
        null=True, blank=True,
        help_text='Diferencia (faltante o sobrante)'
    )
    closing_notes = models.TextField(blank=True)

    # Supervisor who approved closing (optional)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='closed_sessions',
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Abierta'),
            ('closing', 'En cierre'),
            ('closed', 'Cerrada'),
            ('reconciled', 'Conciliada'),
        ],
        default='open',
    )

    class Meta:
        db_table = 'cashbox_sessions'
        ordering = ['-opened_at']

    def __str__(self):
        date_str = self.opened_at.strftime('%Y-%m-%d') if self.opened_at else 'N/A'
        return f'{self.register.name} — {date_str} ({self.get_status_display()})'

    @property
    def total_inflows(self):
        """Sum of all cash inflows in this session."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='inflow'
        ).aggregate(total=Sum('amount'))
        return result['total'] or 0

    @property
    def total_outflows(self):
        """Sum of all cash outflows in this session."""
        from django.db.models import Sum
        result = self.movements.filter(
            movement_type='outflow'
        ).aggregate(total=Sum('amount'))
        return result['total'] or 0


class CashMovement(UUIDModel, TimeStampedModel):
    """
    Individual cash movement (entrada o salida).
    Linked to a session and optionally to a loan payment or disbursement.
    """
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='movements')

    movement_type = models.CharField(
        max_length=10,
        choices=[
            ('inflow', 'Entrada'),
            ('outflow', 'Salida'),
        ],
    )

    category = models.CharField(
        max_length=30,
        choices=[
            # Inflows
            ('loan_payment', 'Pago de préstamo'),
            ('loan_payoff', 'Saldo de préstamo'),
            ('commission', 'Comisión cobrada'),
            ('late_fee', 'Mora cobrada'),
            ('insurance', 'Seguro cobrado'),
            ('other_income', 'Otro ingreso'),
            # Outflows
            ('loan_disbursement', 'Desembolso de préstamo'),
            ('expense', 'Gasto operativo'),
            ('withdrawal', 'Retiro de efectivo'),
            ('refund', 'Devolución'),
            ('salary', 'Pago de nómina'),
            ('other_expense', 'Otro gasto'),
        ],
    )

    amount = MoneyField(
        max_digits=14, decimal_places=2, default_currency='DOP',
    )

    description = models.CharField(max_length=300)
    reference = models.CharField(max_length=100, blank=True, help_text='Número de referencia, recibo, etc.')

    # Optional links to loan module
    loan_payment = models.ForeignKey(
        'loans.LoanPayment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements',
    )
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements',
    )
    customer_name = models.CharField(max_length=200, blank=True, help_text='Nombre del cliente (desnormalizado)')

    # Who recorded this
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cash_movements',
    )

    class Meta:
        db_table = 'cashbox_movements'
        ordering = ['-created_at']

    def __str__(self):
        direction = '↑' if self.movement_type == 'inflow' else '↓'
        return f'{direction} {self.amount} — {self.description}'


class DenominationCount(UUIDModel):
    """
    Denomination counting for a cash session (conteo de billetes y monedas).
    Used during opening and closing to verify the physical cash count.
    """
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='denomination_counts')
    count_type = models.CharField(
        max_length=10,
        choices=[
            ('opening', 'Apertura'),
            ('closing', 'Cierre'),
        ],
    )

    # Dominican Peso denominations
    # Bills
    bills_2000 = models.IntegerField(default=0, help_text='Billetes de RD$2,000')
    bills_1000 = models.IntegerField(default=0, help_text='Billetes de RD$1,000')
    bills_500 = models.IntegerField(default=0, help_text='Billetes de RD$500')
    bills_200 = models.IntegerField(default=0, help_text='Billetes de RD$200')
    bills_100 = models.IntegerField(default=0, help_text='Billetes de RD$100')
    bills_50 = models.IntegerField(default=0, help_text='Billetes de RD$50')
    # Coins
    coins_25 = models.IntegerField(default=0, help_text='Monedas de RD$25')
    coins_10 = models.IntegerField(default=0, help_text='Monedas de RD$10')
    coins_5 = models.IntegerField(default=0, help_text='Monedas de RD$5')
    coins_1 = models.IntegerField(default=0, help_text='Monedas de RD$1')

    @property
    def total(self):
        """Calculate total from denomination count."""
        return (
            self.bills_2000 * 2000 +
            self.bills_1000 * 1000 +
            self.bills_500 * 500 +
            self.bills_200 * 200 +
            self.bills_100 * 100 +
            self.bills_50 * 50 +
            self.coins_25 * 25 +
            self.coins_10 * 10 +
            self.coins_5 * 5 +
            self.coins_1 * 1
        )

    class Meta:
        db_table = 'cashbox_denomination_counts'

    def __str__(self):
        return f'{self.get_count_type_display()} — RD${self.total:,.2f}'
