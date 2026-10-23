from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.communications.models import WhatsAppMessage
from apps.communications.tasks import send_whatsapp_message


def _fake_service(send_result):
    service = MagicMock()
    service.is_configured.return_value = True
    service._format_phone.side_effect = lambda phone: phone
    service.wa_client.send_message.return_value = send_result
    return service


def _send(tenant):
    return send_whatsapp_message.run(
        tenant_schema=tenant.schema_name,
        to_phone='13479727340',
        message_text='Prueba',
    )


def test_stores_bare_wamid_when_pywa_returns_sent_message(tenant_schema):
    """pywa >= 2 returns a SentMessage object; status webhooks look up the bare wamid."""
    sent = SimpleNamespace(id='wamid.ABC123')
    with patch('apps.loans.utils_whatsapp.get_whatsapp_service', return_value=_fake_service(sent)):
        message_id = _send(tenant_schema)

    assert WhatsAppMessage.objects.get(id=message_id).wa_message_id == 'wamid.ABC123'


def test_stores_wamid_when_pywa_returns_plain_string(tenant_schema):
    with patch('apps.loans.utils_whatsapp.get_whatsapp_service', return_value=_fake_service('wamid.XYZ789')):
        message_id = _send(tenant_schema)

    assert WhatsAppMessage.objects.get(id=message_id).wa_message_id == 'wamid.XYZ789'
