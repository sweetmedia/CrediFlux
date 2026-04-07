"""
WhatsApp messaging utilities using PyWa (WhatsApp Cloud API)

This module provides functions to send WhatsApp messages for:
- Payment reminders
- Contract signature links
- Payment receipts
"""
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, date

from pywa import WhatsApp
from pywa.types import Button

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
        """
        Format phone number for WhatsApp (remove special characters, ensure country code).

        Args:
            phone: Phone number string

        Returns:
            Formatted phone number (e.g., "18095551234")
        """
        # Remove all non-numeric characters
        cleaned = ''.join(filter(str.isdigit, phone))

        # If doesn't start with country code, assume Dominican Republic (+1-809/829/849)
        if not cleaned.startswith('1') and len(cleaned) == 10:
            cleaned = '1' + cleaned

        return cleaned

    def _format_currency(self, amount: Decimal) -> str:
        """Format currency amount for display"""
        currency = self.tenant.default_currency or 'DOP'
        symbol = self.tenant.currency_symbol or 'RD$'
        return f"{symbol}{amount:,.2f} {currency}"

    def _format_date(self, date_obj: date) -> str:
        """Format date for Spanish locale"""
        months = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        return f"{date_obj.day} de {months[date_obj.month]} de {date_obj.year}"

    def send_payment_reminder(
        self,
        loan: Loan,
        phone: str,
        days_until_due: int,
        amount_due: Decimal
    ) -> bool:
        """
        Send payment reminder via WhatsApp.

        Args:
            loan: Loan instance
            phone: Recipient phone number
            days_until_due: Days until payment is due
            amount_due: Amount due for payment

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(f"WhatsApp not configured for tenant {self.tenant.name}")
            return False

        try:
            formatted_phone = self._format_phone(phone)
            customer_name = loan.customer.get_full_name()
            amount_formatted = self._format_currency(amount_due)
            company_name = self.tenant.business_name

            # Determine urgency message
            if days_until_due == 0:
                urgency = "⚠️ *HOY VENCE*"
                time_msg = "hoy"
            elif days_until_due == 1:
                urgency = "⏰ *VENCE MAÑANA*"
                time_msg = "mañana"
            elif days_until_due < 0:
                urgency = "🚨 *VENCIDO*"
                time_msg = f"hace {abs(days_until_due)} día(s)"
            else:
                urgency = "📅 Recordatorio de Pago"
                time_msg = f"en {days_until_due} día(s)"

            # Build message
            message = f"""
{urgency}

Hola {customer_name},

Le recordamos que su pago del préstamo *{loan.loan_number}* vence {time_msg}.

💰 *Monto a pagar:* {amount_formatted}
📅 *Préstamo:* {loan.loan_number}

Para más información, comuníquese con nosotros.

Gracias por su confianza en {company_name}.
""".strip()

            # Send message
            self.wa_client.send_message(
                to=formatted_phone,
                text=message
            )

            logger.info(
                f"Payment reminder sent via WhatsApp to {formatted_phone} "
                f"for loan {loan.loan_number}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending WhatsApp payment reminder for loan {loan.loan_number}: {str(e)}"
            )
            return False

    def send_contract_signature_link(
        self,
        contract: Contract,
        phone: str,
        signature_url: str
    ) -> bool:
        """
        Send contract signature link via WhatsApp.

        Args:
            contract: Contract instance
            phone: Recipient phone number
            signature_url: URL for signing the contract

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(f"WhatsApp not configured for tenant {self.tenant.name}")
            return False

        try:
            formatted_phone = self._format_phone(phone)
            customer_name = contract.customer_name
            company_name = self.tenant.business_name
            contract_number = contract.contract_number

            message = f"""
📝 *Firma de Contrato*

Hola {customer_name},

Su contrato *{contract_number}* está listo para ser firmado.

Para revisar y firmar su contrato, haga clic en el siguiente enlace:

🔗 {signature_url}

Este enlace es seguro y personal. Solo usted puede acceder a él.

Si tiene alguna pregunta, no dude en contactarnos.

Atentamente,
{company_name}
""".strip()

            # Send message
            self.wa_client.send_message(
                to=formatted_phone,
                text=message
            )

            logger.info(
                f"Contract signature link sent via WhatsApp to {formatted_phone} "
                f"for contract {contract_number}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending WhatsApp contract link for {contract.contract_number}: {str(e)}"
            )
            return False

    def send_payment_receipt(
        self,
        payment: LoanPayment,
        phone: str
    ) -> bool:
        """
        Send payment receipt via WhatsApp.

        Args:
            payment: LoanPayment instance
            phone: Recipient phone number

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(f"WhatsApp not configured for tenant {self.tenant.name}")
            return False

        try:
            formatted_phone = self._format_phone(phone)
            customer_name = payment.loan.customer.get_full_name()
            company_name = self.tenant.business_name
            amount_formatted = self._format_currency(payment.amount.amount)
            payment_date = self._format_date(payment.payment_date)

            message = f"""
✅ *Recibo de Pago*

Hola {customer_name},

Confirmamos la recepción de su pago:

💰 *Monto:* {amount_formatted}
📅 *Fecha:* {payment_date}
📋 *Préstamo:* {payment.loan.loan_number}
🔢 *Recibo:* #{payment.id}
💳 *Método:* {payment.get_payment_method_display()}

{f"📝 *Nota:* {payment.notes}" if payment.notes else ""}

Gracias por su pago puntual.

{company_name}
""".strip()

            # Send message
            self.wa_client.send_message(
                to=formatted_phone,
                text=message
            )

            logger.info(
                f"Payment receipt sent via WhatsApp to {formatted_phone} "
                f"for payment {payment.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending WhatsApp payment receipt for payment {payment.id}: {str(e)}"
            )
            return False

    def send_loan_approved(
        self,
        loan: Loan,
        phone: str
    ) -> bool:
        """
        Send loan approval notification via WhatsApp.

        Args:
            loan: Loan instance
            phone: Recipient phone number

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning(f"WhatsApp not configured for tenant {self.tenant.name}")
            return False

        try:
            formatted_phone = self._format_phone(phone)
            customer_name = loan.customer.get_full_name()
            company_name = self.tenant.business_name
            amount_formatted = self._format_currency(loan.principal_amount.amount)

            message = f"""
🎉 *¡Préstamo Aprobado!*

Hola {customer_name},

Le informamos que su préstamo ha sido *APROBADO*.

💰 *Monto aprobado:* {amount_formatted}
📋 *Número de préstamo:* {loan.loan_number}
📅 *Fecha de inicio:* {self._format_date(loan.start_date)}

En breve nos pondremos en contacto con usted para coordinar el desembolso.

¡Felicidades!

{company_name}
""".strip()

            # Send message
            self.wa_client.send_message(
                to=formatted_phone,
                text=message
            )

            logger.info(
                f"Loan approval sent via WhatsApp to {formatted_phone} "
                f"for loan {loan.loan_number}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error sending WhatsApp loan approval for {loan.loan_number}: {str(e)}"
            )
            return False


def get_whatsapp_service(tenant: Tenant) -> WhatsAppService:
    """
    Factory function to get WhatsApp service for a tenant.

    Args:
        tenant: Tenant instance

    Returns:
        WhatsAppService instance
    """
    return WhatsAppService(tenant)
