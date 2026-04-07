"""
WhatsApp Webhook Views.

This module provides the endpoint for Meta's WhatsApp Cloud API webhooks.
Handles both verification (GET) and message reception (POST).
"""
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .signature import verify_signature
from .utils import (
    find_tenant_by_verify_token,
    find_tenant_by_phone_id,
    extract_phone_number_id,
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    """
    Webhook endpoint for WhatsApp Cloud API.

    This endpoint handles:
    - GET: Webhook verification from Meta
    - POST: Incoming messages and status updates

    Authentication: None (public endpoint for Meta callbacks)
    CSRF: Exempt (external requests from Meta)
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        """
        Handle webhook verification from Meta.

        Meta sends a GET request with:
        - hub.mode: Should be 'subscribe'
        - hub.verify_token: Your configured verify token
        - hub.challenge: A random string to echo back

        Returns:
            200 with challenge value if verification succeeds
            403 if verification fails
        """
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')

        logger.info(f"Webhook verification request: mode={mode}")

        if mode == 'subscribe' and token:
            # Find tenant by verify token
            tenant = find_tenant_by_verify_token(token)

            if tenant:
                logger.info(f"Webhook verified for tenant: {tenant.name}")
                # Return challenge as integer (Meta expects this format)
                return Response(int(challenge), status=status.HTTP_200_OK)
            else:
                logger.warning(f"Webhook verification failed: invalid token")

        return Response('Forbidden', status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """
        Handle incoming webhook events from Meta.

        Process flow:
        1. Extract phone_number_id from payload to identify tenant
        2. Validate signature using tenant's app_secret
        3. Respond 200 OK immediately (Meta requirement: < 20 seconds)
        4. Dispatch to Celery for async processing

        Always returns 200 OK to prevent Meta from retrying.
        Invalid/unprocessable webhooks are logged but not retried.

        Returns:
            200 OK always (to acknowledge receipt to Meta)
        """
        try:
            # Get raw body for signature validation
            raw_body = request.body
            signature = request.headers.get('X-Hub-Signature-256', '')

            # Extract phone_number_id to identify tenant
            payload = request.data
            phone_number_id = extract_phone_number_id(payload)

            if not phone_number_id:
                logger.warning("Webhook missing phone_number_id in payload")
                return Response(status=status.HTTP_200_OK)

            # Find tenant by phone_number_id
            tenant = find_tenant_by_phone_id(phone_number_id)

            if not tenant:
                logger.warning(f"No tenant found for phone_number_id: {phone_number_id}")
                return Response(status=status.HTTP_200_OK)

            # Validate signature if app_secret is configured
            if tenant.whatsapp_app_secret:
                if not verify_signature(raw_body, signature, tenant.whatsapp_app_secret):
                    logger.warning(f"Invalid webhook signature for tenant: {tenant.name}")
                    return Response(status=status.HTTP_200_OK)
            else:
                logger.debug(f"Skipping signature validation (no app_secret) for tenant: {tenant.name}")

            # Dispatch to Celery for async processing
            from apps.communications.tasks import process_whatsapp_webhook

            process_whatsapp_webhook.delay(
                tenant_schema=tenant.schema_name,
                payload=payload
            )

            logger.info(f"Webhook received and queued for tenant: {tenant.name}")

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            # Still return 200 to prevent Meta from retrying
            # The error is logged for investigation

        return Response(status=status.HTTP_200_OK)
