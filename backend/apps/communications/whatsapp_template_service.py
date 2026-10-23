"""
Plantillas de WhatsApp por financiera: sincronizar con Meta y enviar.

- `sync_tenant_templates(tenant)` crea en la cuenta de WhatsApp de la financiera
  las plantillas del catálogo que falten y actualiza el estado de las demás.
  Meta además avisa los cambios de estado por webhook
  (`message_template_status_update`, ver `apply_status_update`).
- `send_template(...)` envía SÓLO plantillas aprobadas. Si no lo está, no cae a
  texto libre (fuera de la ventana de 24 h Meta lo rechazaría): no envía y lo
  deja en el log.

Ambas corren dentro del schema del tenant (`schema_context`): el estado de las
plantillas (`WhatsAppTemplate`) y los mensajes viven ahí.
"""
import logging
import uuid
from typing import Optional

from django.conf import settings
from django.utils import timezone

from . import meta_whatsapp
from .models import WhatsAppMessage, WhatsAppTemplate
from .whatsapp_templates import CATALOG, NAME_PREFIX, TEMPLATE_LANGUAGE, create_payload, send_components

logger = logging.getLogger(__name__)


def format_whatsapp_phone(phone) -> str:
    """Sólo dígitos; un número dominicano de 10 dígitos lleva el 1 delante."""
    cleaned = ''.join(filter(str.isdigit, str(phone)))
    if not cleaned.startswith('1') and len(cleaned) == 10:
        cleaned = '1' + cleaned
    return cleaned


def has_template_credentials(tenant) -> bool:
    return bool(
        getattr(tenant, 'whatsapp_phone_id', '')
        and getattr(tenant, 'whatsapp_token', '')
        and getattr(tenant, 'whatsapp_business_account_id', '')
    )


def signature_base_url(tenant) -> str:
    """URL fija del botón de firma: https://<dominio de la financiera>/sign/."""
    frontend = (getattr(settings, 'FRONTEND_URL', '') or '').strip().rstrip('/')
    if frontend and 'localhost' not in frontend and '127.0.0.1' not in frontend:
        return f'{frontend}/sign/'
    domain = tenant.domains.filter(is_primary=True).first() or tenant.domains.first()
    host = domain.domain if domain else 'localhost'
    return f'https://{host}/sign/'


def sync_tenant_templates(tenant) -> dict:
    """Crea las plantillas que falten y refresca los estados. Devuelve un resumen."""
    summary = {'created': [], 'updated': [], 'errors': []}
    if not has_template_credentials(tenant):
        return summary

    waba_id, token = tenant.whatsapp_business_account_id, tenant.whatsapp_token
    now = timezone.now()
    remote = {
        (t['name'], t.get('language')): t
        for t in meta_whatsapp.list_templates(waba_id, token, name_prefix=NAME_PREFIX)
    }

    for spec in CATALOG.values():
        local, _ = WhatsAppTemplate.objects.get_or_create(
            name=spec.name, language=TEMPLATE_LANGUAGE, defaults={'key': spec.key},
        )
        found = remote.get((spec.name, TEMPLATE_LANGUAGE))
        if found:
            local.status = found.get('status', local.status)
            local.meta_template_id = found.get('id', local.meta_template_id)
            local.rejected_reason = found.get('rejected_reason') or ''
            summary['updated'].append(spec.name)
        else:
            base_url = signature_base_url(tenant) if spec.button_text else ''
            try:
                created = meta_whatsapp.create_template(waba_id, token, create_payload(spec, base_url or None))
            except meta_whatsapp.MetaAPIError as exc:
                local.status = 'ERROR'
                local.rejected_reason = str(exc)
                summary['errors'].append(spec.name)
                logger.error('No se pudo crear la plantilla %s para %s: %s', spec.name, tenant.schema_name, exc)
            else:
                local.status = created.get('status', 'PENDING')
                local.meta_template_id = created.get('id', '')
                local.rejected_reason = ''
                local.button_base_url = base_url
                summary['created'].append(spec.name)
        local.key = spec.key
        local.synced_at = now
        local.save()
    return summary


def apply_status_update(event: dict) -> bool:
    """
    Webhook `message_template_status_update`:
    {"event": "APPROVED", "message_template_id": 123, "message_template_name": "...",
     "message_template_language": "es", "reason": "NONE"}
    """
    template = None
    template_id = str(event.get('message_template_id') or '')
    if template_id:
        template = WhatsAppTemplate.objects.filter(meta_template_id=template_id).first()
    if template is None and event.get('message_template_name'):
        template = WhatsAppTemplate.objects.filter(
            name=event['message_template_name'],
            language=event.get('message_template_language') or TEMPLATE_LANGUAGE,
        ).first()
    if template is None:
        return False
    template.status = event.get('event') or template.status
    reason = event.get('reason') or ''
    template.rejected_reason = '' if reason in ('', 'NONE') else reason
    if template_id:
        template.meta_template_id = template_id
    template.synced_at = timezone.now()
    template.save(update_fields=['status', 'rejected_reason', 'meta_template_id', 'synced_at'])
    return True


def send_template(tenant, key, to_phone, values, *, customer=None, button_value: Optional[str] = None,
                  user=None) -> Optional[WhatsAppMessage]:
    """
    Envía la plantilla `key` del catálogo. Devuelve el WhatsAppMessage guardado,
    o None si no se envió (sin credenciales, plantilla no aprobada o error de Meta).
    """
    spec = CATALOG[key]
    if not has_template_credentials(tenant):
        logger.warning('WhatsApp sin credenciales completas en %s: no se envía %s', tenant.schema_name, spec.name)
        return None

    template = WhatsAppTemplate.objects.filter(name=spec.name, language=TEMPLATE_LANGUAGE).first()
    if template is None or not template.is_approved:
        logger.warning(
            'La plantilla %s no está aprobada en %s (%s): no se envía',
            spec.name, tenant.schema_name, template.status if template else 'sin sincronizar',
        )
        return None

    to = format_whatsapp_phone(to_phone)
    components = send_components(spec, values, button_value)
    content = spec.render(values)
    metadata = {'template': spec.name, 'language': TEMPLATE_LANGUAGE, 'values': [str(v) for v in values]}
    if button_value:
        metadata['button'] = button_value

    try:
        wamid = meta_whatsapp.send_template(
            tenant.whatsapp_phone_id, tenant.whatsapp_token, to, spec.name, TEMPLATE_LANGUAGE, components,
        )
    except meta_whatsapp.MetaAPIError as exc:
        logger.error('Meta rechazó %s para %s: %s', spec.name, to, exc)
        WhatsAppMessage.objects.create(
            wa_message_id=f'failed_{uuid.uuid4().hex[:16]}',
            direction='outbound', status='failed', message_type='template',
            from_phone=tenant.whatsapp_phone_id, to_phone=to, content=content,
            metadata=metadata, customer=customer, user=user, conversation_id=to,
            error_message=str(exc),
        )
        return None

    return WhatsAppMessage.objects.create(
        wa_message_id=wamid,
        direction='outbound', status='pending', message_type='template',
        from_phone=tenant.whatsapp_phone_id, to_phone=to, content=content,
        metadata=metadata, customer=customer, user=user, conversation_id=to,
        sent_at=timezone.now(),
    )
