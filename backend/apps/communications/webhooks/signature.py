"""
WhatsApp Webhook signature validation using HMAC-SHA256.

Meta signs all webhook payloads with your App Secret.
This module validates those signatures to ensure webhooks are authentic.
"""
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """
    Validate the HMAC-SHA256 signature from Meta's webhook.

    Meta includes X-Hub-Signature-256 header with format: sha256=HASH
    We compute our own hash using the app_secret and compare.

    Args:
        payload: Raw request body as bytes
        signature: X-Hub-Signature-256 header value (format: sha256=HASH)
        app_secret: Meta App Secret for this WhatsApp Business Account

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not app_secret:
        logger.warning("Missing signature or app_secret for webhook validation")
        return False

    try:
        # Extract hash from signature header (remove 'sha256=' prefix)
        if signature.startswith('sha256='):
            expected_signature = signature[7:]  # Remove 'sha256=' prefix
        else:
            expected_signature = signature

        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            key=app_secret.encode('utf-8'),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Timing-safe comparison to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature.lower(), computed_hash.lower())

        if not is_valid:
            logger.warning("Invalid webhook signature detected")

        return is_valid

    except Exception as e:
        logger.error(f"Error validating webhook signature: {str(e)}")
        return False
