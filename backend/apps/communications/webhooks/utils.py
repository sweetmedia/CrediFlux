"""
Utility functions for WhatsApp webhook processing.

This module provides helper functions for:
- Identifying tenants by verify_token or phone_number_id
- Finding customers by phone number
- Extracting data from webhook payloads
"""
import re
import logging
from typing import Optional, Tuple
from django.db import models

logger = logging.getLogger(__name__)


def find_tenant_by_verify_token(verify_token: str):
    """
    Find a tenant by their WhatsApp verify token.
    Used during webhook verification (GET request).

    Args:
        verify_token: The hub.verify_token from Meta's verification request

    Returns:
        Tenant instance or None if not found
    """
    if not verify_token:
        return None

    from apps.tenants.models import Tenant

    return Tenant.objects.filter(
        whatsapp_verify_token=verify_token,
        is_active=True
    ).first()


def find_tenant_by_phone_id(phone_number_id: str):
    """
    Find a tenant by their WhatsApp phone_number_id.
    Used when processing incoming messages (POST request).

    Args:
        phone_number_id: The phone_number_id from webhook metadata

    Returns:
        Tenant instance or None if not found
    """
    if not phone_number_id:
        return None

    from apps.tenants.models import Tenant

    return Tenant.objects.filter(
        whatsapp_phone_id=phone_number_id,
        is_active=True
    ).first()


def extract_phone_number_id(payload: dict) -> Optional[str]:
    """
    Extract the phone_number_id from a webhook payload.

    WhatsApp webhook structure:
    {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "phone_number_id": "123456789"
                    }
                }
            }]
        }]
    }

    Args:
        payload: The full webhook payload dict

    Returns:
        phone_number_id string or None if not found
    """
    try:
        entries = payload.get('entry', [])
        if entries:
            changes = entries[0].get('changes', [])
            if changes:
                value = changes[0].get('value', {})
                metadata = value.get('metadata', {})
                return metadata.get('phone_number_id')
    except (IndexError, KeyError, TypeError) as e:
        logger.warning(f"Could not extract phone_number_id from payload: {e}")
    return None


def find_customer_by_phone(phone: str):
    """
    Find a Customer by phone number.
    Normalizes the phone number and searches both phone and alternate_phone fields.

    Args:
        phone: Phone number string (may include country code, formatting)

    Returns:
        Customer instance or None if not found
    """
    if not phone:
        return None

    from apps.loans.models import Customer

    # Normalize: remove all non-numeric characters
    cleaned = re.sub(r'\D', '', phone)

    if not cleaned:
        return None

    # Try different matching strategies
    # 1. Exact match on cleaned number
    # 2. Match last 10 digits (without country code)
    # 3. Match with country code prefix

    last_10 = cleaned[-10:] if len(cleaned) >= 10 else cleaned

    try:
        # PhoneNumberField stores numbers, we search with contains
        customer = Customer.objects.filter(
            models.Q(phone__contains=cleaned) |
            models.Q(phone__contains=last_10) |
            models.Q(alternate_phone__contains=cleaned) |
            models.Q(alternate_phone__contains=last_10)
        ).first()

        if customer:
            logger.debug(f"Found customer {customer.id} for phone {phone}")
        return customer

    except Exception as e:
        logger.error(f"Error finding customer by phone {phone}: {e}")
        return None


def extract_message_content(message_data: dict) -> str:
    """
    Extract the text content from a message based on its type.

    Args:
        message_data: The message object from the webhook

    Returns:
        Text content or descriptive placeholder for media messages
    """
    message_type = message_data.get('type', 'text')

    if message_type == 'text':
        return message_data.get('text', {}).get('body', '')

    elif message_type == 'image':
        return message_data.get('image', {}).get('caption', '[Imagen]')

    elif message_type == 'video':
        return message_data.get('video', {}).get('caption', '[Video]')

    elif message_type == 'audio':
        return '[Audio]'

    elif message_type == 'document':
        doc = message_data.get('document', {})
        filename = doc.get('filename', 'archivo')
        caption = doc.get('caption', '')
        return caption if caption else f'[Documento: {filename}]'

    elif message_type == 'location':
        loc = message_data.get('location', {})
        lat = loc.get('latitude', '')
        lon = loc.get('longitude', '')
        name = loc.get('name', '')
        if name:
            return f'[Ubicacion: {name}]'
        return f'[Ubicacion: {lat}, {lon}]'

    elif message_type == 'contacts':
        contacts = message_data.get('contacts', [])
        if contacts:
            name = contacts[0].get('name', {}).get('formatted_name', 'Contacto')
            return f'[Contacto: {name}]'
        return '[Contacto]'

    elif message_type == 'sticker':
        return '[Sticker]'

    elif message_type == 'button':
        return message_data.get('button', {}).get('text', '[Boton]')

    elif message_type == 'interactive':
        interactive = message_data.get('interactive', {})
        interactive_type = interactive.get('type', '')

        if interactive_type == 'button_reply':
            return interactive.get('button_reply', {}).get('title', '[Respuesta de boton]')
        elif interactive_type == 'list_reply':
            return interactive.get('list_reply', {}).get('title', '[Seleccion de lista]')

        return '[Interactivo]'

    elif message_type == 'reaction':
        emoji = message_data.get('reaction', {}).get('emoji', '')
        return f'[Reaccion: {emoji}]'

    return ''


def extract_media_info(message_data: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract media information from a message.

    Args:
        message_data: The message object from the webhook

    Returns:
        Tuple of (media_id, mime_type) or (None, None) if no media
    """
    message_type = message_data.get('type', 'text')

    media_types = ['image', 'video', 'audio', 'document', 'sticker']

    for media_type in media_types:
        if message_type == media_type:
            media_data = message_data.get(media_type, {})
            media_id = media_data.get('id')
            mime_type = media_data.get('mime_type', '')
            return media_id, mime_type

    return None, None


def format_phone_for_display(phone: str) -> str:
    """
    Format a phone number for display in the UI.

    Args:
        phone: Raw phone number string

    Returns:
        Formatted phone number (e.g., "+1 (809) 555-1234")
    """
    cleaned = re.sub(r'\D', '', phone)

    if len(cleaned) == 11 and cleaned.startswith('1'):
        # US/Canada format: +1 (XXX) XXX-XXXX
        return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
    elif len(cleaned) == 10:
        # Assume Dominican Republic: +1 (XXX) XXX-XXXX
        return f"+1 ({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    else:
        # Just return with + prefix
        return f"+{cleaned}"
