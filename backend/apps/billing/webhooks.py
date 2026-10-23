"""
Endpoint público de webhooks de NexConnect.

    POST /api/webhooks/nexconnect/<schema_name>/

Sin autenticación de sesión/JWT: la autenticidad la da la firma HMAC
(``X-NexConnect-Signature``) con el secret del webhook del tenant. La lógica
vive en ``services/nexconnect/webhooks.py``.
"""
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import get_tenant_model, schema_context

from .services.nexconnect.credentials import webhook_secret_for_tenant
from .services.nexconnect.webhooks import (
    SIGNATURE_HEADER,
    WebhookPayloadError,
    WebhookSignatureError,
    parse_event,
    process_event,
    verify_signature,
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class NexConnectWebhookView(View):
    http_method_names = ['post']

    def post(self, request, schema_name):
        tenant = get_tenant_model().objects.filter(schema_name=schema_name).first()
        secret = webhook_secret_for_tenant(tenant) if tenant is not None else ''
        if not secret:
            return JsonResponse({'detail': 'Webhook no configurado'}, status=404)

        header = request.headers.get(SIGNATURE_HEADER, '')
        body = request.body
        try:
            verify_signature(secret, header, body)
        except WebhookSignatureError as e:
            # El header crudo ayuda a depurar (no es secreto); el cuerpo no se loguea.
            logger.warning('Webhook NexConnect rechazado (%s): %s; header=%r',
                           schema_name, e, header[:200])
            return JsonResponse({'detail': str(e)}, status=401)

        try:
            event = parse_event(body)
        except WebhookPayloadError as e:
            return JsonResponse({'detail': str(e)}, status=400)

        with schema_context(tenant.schema_name):
            outcome = process_event(tenant, event)
        return JsonResponse({'received': True, 'event_id': event['id'], 'outcome': outcome})
