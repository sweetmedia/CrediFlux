"""
Celery tasks for WhatsApp message processing.

These tasks handle asynchronous processing of webhook events:
- Inbound messages: Save to database, associate with customer
- Status updates: Update message delivery status
"""
import logging
from datetime import datetime
from celery import shared_task
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)


@shared_task(name='communications.process_whatsapp_webhook')
def process_whatsapp_webhook(tenant_schema: str, payload: dict):
    """
    Main task to process a WhatsApp webhook payload.

    This task is called from the webhook view after initial validation.
    It processes the payload within the tenant's schema context.

    Args:
        tenant_schema: The schema name of the tenant
        payload: The full webhook payload dict
    """
    try:
        from apps.tenants.models import Tenant
        from apps.communications.webhooks.handlers import WhatsAppWebhookHandler

        tenant = Tenant.objects.get(schema_name=tenant_schema)

        with schema_context(tenant_schema):
            handler = WhatsAppWebhookHandler(tenant)
            handler.process(payload)

        logger.info(f"Successfully processed webhook for tenant {tenant_schema}")

    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook for {tenant_schema}: {str(e)}")
        raise


@shared_task(name='communications.process_inbound_whatsapp_message')
def process_inbound_whatsapp_message(tenant_schema: str, message_data: dict):
    """
    Process an inbound WhatsApp message and save to database.

    Args:
        tenant_schema: The schema name of the tenant
        message_data: The enriched message data dict
    """
    try:
        from apps.communications.models import WhatsAppMessage
        from apps.communications.webhooks.utils import (
            find_customer_by_phone,
            extract_message_content,
            extract_media_info,
        )

        with schema_context(tenant_schema):
            # Extract message fields
            wa_message_id = message_data.get('id')
            from_phone = message_data.get('from', '')
            to_phone = message_data.get('to_phone', '')
            message_type = message_data.get('type', 'text')
            timestamp = message_data.get('timestamp')

            # Check for duplicate (idempotency)
            if WhatsAppMessage.objects.filter(wa_message_id=wa_message_id).exists():
                logger.info(f"Duplicate message {wa_message_id} ignored")
                return

            # Extract content and media
            content = extract_message_content(message_data)
            media_id, media_type = extract_media_info(message_data)

            # Find associated customer
            customer = find_customer_by_phone(from_phone)

            # Get contact profile name if available
            contact_profile = message_data.get('contact_profile', {})
            profile_name = contact_profile.get('profile', {}).get('name', '')

            # Create the message record
            message = WhatsAppMessage.objects.create(
                wa_message_id=wa_message_id,
                direction='inbound',
                status='received',
                message_type=message_type,
                from_phone=from_phone,
                to_phone=to_phone,
                content=content,
                media_url=media_id,  # Store media_id for later download
                media_type=media_type,
                customer=customer,
                conversation_id=from_phone,  # Use sender phone as conversation ID
                metadata={
                    'raw_message': message_data,
                    'profile_name': profile_name,
                    'timestamp': timestamp,
                },
            )

            logger.info(
                f"Saved inbound message {wa_message_id} from {from_phone} "
                f"(customer: {customer.id if customer else 'unknown'})"
            )

            return message.id

    except Exception as e:
        logger.error(f"Error processing inbound message in {tenant_schema}: {str(e)}")
        raise


@shared_task(name='communications.update_whatsapp_message_status')
def update_whatsapp_message_status(
    tenant_schema: str,
    wa_message_id: str,
    new_status: str,
    timestamp: int,
    error_message: str = None
):
    """
    Update the status of an outbound WhatsApp message.

    Args:
        tenant_schema: The schema name of the tenant
        wa_message_id: The WhatsApp message ID to update
        new_status: The new status (sent, delivered, read, failed)
        timestamp: Unix timestamp of the status change
        error_message: Error message if status is 'failed'
    """
    try:
        from apps.communications.models import WhatsAppMessage

        with schema_context(tenant_schema):
            message = WhatsAppMessage.objects.filter(wa_message_id=wa_message_id).first()

            if not message:
                logger.warning(f"Message {wa_message_id} not found for status update")
                return

            # Update status
            message.status = new_status

            # Convert timestamp to datetime
            if timestamp:
                event_time = datetime.fromtimestamp(timestamp)

                if new_status == 'sent':
                    message.sent_at = event_time
                elif new_status == 'delivered':
                    message.delivered_at = event_time
                elif new_status == 'read':
                    message.read_at = event_time

            # Handle failed status
            if new_status == 'failed' and error_message:
                message.error_message = error_message
                message.retry_count = (message.retry_count or 0) + 1

            message.save()

            logger.info(f"Updated message {wa_message_id} status to {new_status}")

    except Exception as e:
        logger.error(f"Error updating message status in {tenant_schema}: {str(e)}")
        raise


@shared_task(name='communications.send_whatsapp_message')
def send_whatsapp_message(
    tenant_schema: str,
    to_phone: str,
    message_text: str,
    customer_id: int = None
):
    """
    Send a WhatsApp message and save to database.

    Args:
        tenant_schema: The schema name of the tenant
        to_phone: Recipient phone number
        message_text: Text message to send
        customer_id: Optional customer ID to associate with the message

    Returns:
        The created WhatsAppMessage ID or None if failed
    """
    try:
        from apps.tenants.models import Tenant
        from apps.loans.utils_whatsapp import get_whatsapp_service
        from apps.communications.models import WhatsAppMessage
        from apps.loans.models import Customer
        import uuid

        tenant = Tenant.objects.get(schema_name=tenant_schema)

        with schema_context(tenant_schema):
            # Get WhatsApp service
            wa_service = get_whatsapp_service(tenant)

            if not wa_service.is_configured():
                logger.error(f"WhatsApp not configured for tenant {tenant_schema}")
                return None

            # Format phone number
            formatted_phone = wa_service._format_phone(to_phone)

            # Send message via PyWa
            try:
                result = wa_service.wa_client.send_message(
                    to=formatted_phone,
                    text=message_text
                )
                wa_message_id = result  # PyWa returns the message ID
            except Exception as e:
                logger.error(f"Failed to send WhatsApp message: {e}")
                wa_message_id = f"failed_{uuid.uuid4().hex[:16]}"

            # Get customer if ID provided
            customer = None
            if customer_id:
                customer = Customer.objects.filter(id=customer_id).first()

            # Save message to database
            message = WhatsAppMessage.objects.create(
                wa_message_id=wa_message_id if wa_message_id else f"local_{uuid.uuid4().hex[:16]}",
                direction='outbound',
                status='pending' if wa_message_id else 'failed',
                message_type='text',
                from_phone=tenant.whatsapp_phone_id or '',
                to_phone=to_phone,
                content=message_text,
                customer=customer,
                conversation_id=to_phone,
            )

            logger.info(f"Sent WhatsApp message to {to_phone}, ID: {message.id}")

            return message.id

    except Exception as e:
        logger.error(f"Error sending WhatsApp message in {tenant_schema}: {str(e)}")
        raise
