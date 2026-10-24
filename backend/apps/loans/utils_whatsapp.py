"""
WhatsApp messaging for loans (WhatsApp Cloud API).

Business-initiated messages (payment reminders, overdue notices, receipts,
contract signature links, loan approval) go out as approved Utility TEMPLATES
(apps.communications.whatsapp_templates): outside the 24 h customer service
window Meta rejects free text. The pywa client stays for free-text replies
inside that window (apps.communications.tasks.send_whatsapp_message).
"""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import date, timedelta

from pywa import WhatsApp
from django.utils import timezone

from apps.communications.whatsapp_template_service import format_whatsapp_phone, send_template
from apps.tenants.models import Tenant
from .models import Loan, LoanPayment
from .models_contracts import Contract

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages using PyWa"""

    def __init__(self, tenant: Tenant):
        """
        Initialize WhatsApp service for a specific tenant.

        Args:
            tenant: Tenant instance with WhatsApp configuration
        """
        self.tenant = tenant
        self.wa_client = None

        # Initialize WhatsApp client if credentials are configured
        if self._has_credentials():
            try:
                self.wa_client = WhatsApp(
                    phone_id=tenant.whatsapp_phone_id,
                    token=tenant.whatsapp_token,
                    business_account_id=tenant.whatsapp_business_account_id,
                )
                logger.info(f"WhatsApp client initialized for tenant: {tenant.name}")
            except Exception as e:
                logger.error(f"Error initializing WhatsApp client for {tenant.name}: {str(e)}")
                self.wa_client = None

    def _has_credentials(self) -> bool:
        """Check if tenant has WhatsApp credentials configured"""
        return bool(
            self.tenant.whatsapp_phone_id
            and self.tenant.whatsapp_token
        )

    def is_configured(self) -> bool:
        """Check if WhatsApp is properly configured and enabled"""
        return (
            self.tenant.enable_whatsapp_reminders
            and self._has_credentials()
            and self.wa_client is not None
        )

    def _format_phone(self, phone: str) -> str:
        """Format phone number for WhatsApp (digits only, DR numbers get the leading 1)."""
        return format_whatsapp_phone(phone)

    def _format_currency(self, amount: Decimal) -> str:
        """RD$4,500.00 (VOICE.md: «RD$» y el monto, sin el código ISO)."""
        symbol = self.tenant.currency_symbol or 'RD$'
        return f"{symbol}{Decimal(str(amount)):,.2f}"

    def _format_date(self, date_obj: date) -> str:
        """Format date for Spanish locale"""
        months = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        return f"{date_obj.day} de {months[date_obj.month]} de {date_obj.year}"

    def _send(self, key: str, phone: str, values: list, *, customer=None, button_value=None) -> bool:
        """Envía una plantilla aprobada del catálogo (ver apps.communications.whatsapp_templates)."""
        if not self.is_configured():
            logger.warning(f"WhatsApp not configured for tenant {self.tenant.name}")
            return False
        message = send_template(
            self.tenant, key, phone, values, customer=customer, button_value=button_value,
        )
        return message is not None

    def send_payment_reminder(
        self,
        loan: Loan,
        phone: str,
        days_until_due: int,
        amount_due: Decimal,
        due_date: Optional[date] = None,
        late_fee: Decimal = Decimal('0'),
    ) -> bool:
        """
        Recordatorio de cuota (plantilla Utility).

        days_until_due >= 0 → `recordatorio_cuota`; < 0 → `cuota_vencida` con la
        mora incluida en el monto pendiente.
        """
        customer = loan.customer
        if due_date is None:
            due_date = timezone.localdate() + timedelta(days=days_until_due)
        if days_until_due >= 0:
            values = [
                customer.first_name, self.tenant.business_name, loan.loan_number,
                self._format_date(due_date), self._format_currency(amount_due),
            ]
            return self._send('recordatorio_cuota', phone, values, customer=customer)
        return self.send_overdue_notice(
            loan, phone, days_overdue=-days_until_due, due_date=due_date,
            amount_due=Decimal(str(amount_due)) + Decimal(str(late_fee or 0)),
        )

    def send_overdue_notice(
        self,
        loan: Loan,
        phone: str,
        days_overdue: int,
        due_date: date,
        amount_due: Decimal,
    ) -> bool:
        """Aviso de cuota vencida (`cuota_vencida`); amount_due ya incluye la mora."""
        customer = loan.customer
        values = [
            customer.first_name, self.tenant.business_name, loan.loan_number,
            self._format_date(due_date), str(days_overdue), self._format_currency(amount_due),
        ]
        return self._send('cuota_vencida', phone, values, customer=customer)

    def send_contract_signature_link(
        self,
        contract: Contract,
        phone: str,
        signature_url: str
    ) -> bool:
        """
        Enlace de firma (`firma_contrato`). El botón de la plantilla tiene la URL
        base fija (https://<dominio>/sign/); aquí sólo va el token del final.
        """
        customer = contract.loan.customer
        token = signature_url.rstrip('/').rsplit('/', 1)[-1]
        values = [customer.first_name, contract.contract_number, self.tenant.business_name]
        return self._send('firma_contrato', phone, values, customer=customer, button_value=token)

    def send_payment_receipt(
        self,
        payment: LoanPayment,
        phone: str
    ) -> bool:
        """Recibo de pago (`recibo_pago`), con el número del pago como recibo."""
        customer = payment.loan.customer
        values = [
            customer.first_name, self.tenant.business_name, self._format_currency(payment.amount.amount),
            self._format_date(payment.payment_date), payment.loan.loan_number, payment.payment_number,
        ]
        return self._send('recibo_pago', phone, values, customer=customer)

    def send_loan_approved(
        self,
        loan: Loan,
        phone: str
    ) -> bool:
        """Préstamo aprobado (`prestamo_aprobado`)."""
        customer = loan.customer
        values = [
            customer.first_name, self.tenant.business_name, loan.loan_number,
            self._format_currency(loan.principal_amount.amount),
        ]
        return self._send('prestamo_aprobado', phone, values, customer=customer)


def get_whatsapp_service(tenant: Tenant) -> WhatsAppService:
    """
    Factory function to get WhatsApp service for a tenant.

    Args:
        tenant: Tenant instance

    Returns:
        WhatsAppService instance
    """
    return WhatsAppService(tenant)
