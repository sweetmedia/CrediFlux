"""
WhatsApp Webhook event handlers.

This module processes the webhook payloads from Meta's WhatsApp Cloud API
and dispatches them to the appropriate Celery tasks for async processing.
"""
import logging
from typing import Optional
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler:
    """
    Handler for WhatsApp webhook events.

    Processes incoming webhook payloads and dispatches them to Celery tasks
    for asynchronous processing within the correct tenant context.
    """

    def __init__(self, tenant: Tenant):
        """
        Initialize the handler with a tenant.

        Args:
            tenant: The Tenant instance this webhook belongs to
        """
        self.tenant = tenant

    def process(self, payload: dict):
        """
        Process the full webhook payload.

        WhatsApp webhook structure:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551234567",
                            "phone_number_id": "123456789"
                        },
                        "contacts": [...],
                        "messages": [...],
                        "statuses": [...]
                    },
                    "field": "messages"
                }]
            }]
        }

        Args:
            payload: The full webhook payload dict
        """
        try:
            if payload.get('object') != 'whatsapp_business_account':
                logger.warning(f"Unexpected webhook object type: {payload.get('object')}")
                return

            entries = payload.get('entry', [])

            for entry in entries:
                changes = entry.get('changes', [])

                for change in changes:
                    if change.get('field') != 'messages':
                        continue

                    value = change.get('value', {})

                    # Process incoming messages
                    messages = value.get('messages', [])
                    for message in messages:
                        self._handle_message(message, value)

                    # Process status updates
                    statuses = value.get('statuses', [])
                    for status_update in statuses:
                        self._handle_status(status_update)

            logger.info(f"Successfully processed webhook for tenant {self.tenant.name}")

        except Exception as e:
            logger.error(f"Error processing webhook payload for tenant {self.tenant.name}: {str(e)}")
            raise

    def _handle_message(self, message: dict, context: dict):
        """
        Handle an incoming message.

        Enriches the message data with context and dispatches to Celery task.

        Args:
            message: The message object from the webhook
            context: The 'value' object containing metadata and contacts
        """
        from apps.communications.tasks import process_inbound_whatsapp_message

        try:
            # Enrich message with context
            message_data = message.copy()

            # Add the business phone number as recipient
            metadata = context.get('metadata', {})
            message_data['to_phone'] = metadata.get('display_phone_number', '')

            # Add contact info if available
            contacts = context.get('contacts', [])
            if contacts:
                message_data['contact_profile'] = contacts[0]

            # Dispatch to Celery for async processing
            process_inbound_whatsapp_message.delay(
                tenant_schema=self.tenant.schema_name,
                message_data=message_data
            )

            logger.debug(f"Dispatched inbound message {message.get('id')} to processing queue")

        except Exception as e:
            logger.error(f"Error handling inbound message: {str(e)}")
            raise

    def _handle_status(self, status: dict):
        """
        Handle a message status update.

        Status updates track the delivery state of outbound messages:
        - sent: Message sent to WhatsApp servers
        - delivered: Message delivered to recipient's device
        - read: Recipient opened/read the message
        - failed: Message delivery failed

        Args:
            status: The status object from the webhook
        """
        from apps.communications.tasks import update_whatsapp_message_status

        try:
            wa_message_id = status.get('id')
            new_status = status.get('status')  # sent, delivered, read, failed
            timestamp = int(status.get('timestamp', 0))
            recipient_id = status.get('recipient_id', '')

            # Handle failed status with error info
            errors = status.get('errors', [])
            error_message = None
            if errors:
                error_message = errors[0].get('message', 'Unknown error')

            # Dispatch to Celery for async processing
            update_whatsapp_message_status.delay(
                tenant_schema=self.tenant.schema_name,
                wa_message_id=wa_message_id,
                new_status=new_status,
                timestamp=timestamp,
                error_message=error_message
            )

            logger.debug(f"Dispatched status update for message {wa_message_id}: {new_status}")

        except Exception as e:
            logger.error(f"Error handling status update: {str(e)}")
            raise
