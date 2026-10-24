"""Plantillas Utility de WhatsApp: catálogo, sincronización con Meta y envío.

La Graph API se simula con `responses`: nada sale a la red.
"""

import json
import re

import pytest
import responses

from apps.communications import meta_whatsapp
from apps.communications.whatsapp_templates import CATALOG, create_payload, send_components

WABA = '4687006278248765'
PHONE_ID = '1256661814204576'
TEMPLATES_URL = f'{meta_whatsapp.GRAPH_URL}/{WABA}/message_templates'
MESSAGES_URL = f'{meta_whatsapp.GRAPH_URL}/{PHONE_ID}/messages'


@pytest.fixture
def wa_tenant(tenant_schema):
    """Tenant de pruebas con credenciales de WhatsApp (copia: no tocar el de sesión)."""
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_schema.pk).update(
        whatsapp_phone_id=PHONE_ID,
        whatsapp_token='token-de-prueba',
        whatsapp_business_account_id=WABA,
        business_name='Financiera de Prueba SRL',
    )
    return Tenant.objects.get(pk=tenant_schema.pk)


def _approve_all():
    from apps.communications.models import WhatsAppTemplate

    for spec in CATALOG.values():
        WhatsAppTemplate.objects.update_or_create(
            name=spec.name, language='es', defaults={'key': spec.key, 'status': 'APPROVED'},
        )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('spec', CATALOG.values(), ids=lambda s: s.key)
def test_catalogo_cumple_las_reglas_de_meta_y_de_la_marca(spec):
    numeros = [int(n) for n in re.findall(r'\{\{(\d+)\}\}', spec.body)]
    assert sorted(set(numeros)) == list(range(1, spec.param_count + 1))  # {{1}}..{{n}} sin huecos
    assert len(spec.example) == spec.param_count
    assert not spec.body.startswith('{{') and not spec.body.rstrip('.').endswith('}}')
    assert 'CrediFlux' not in spec.body
    assert 'usted' in spec.body.lower() or 'su ' in spec.body  # trato de usted (VOICE.md §4.3)
    assert spec.name.startswith('crediflux_')
    assert len(spec.body) <= 1024


def test_los_cinco_avisos_del_diseno():
    assert set(CATALOG) == {'recordatorio_cuota', 'cuota_vencida', 'recibo_pago', 'firma_contrato',
                            'prestamo_aprobado'}


def test_firma_contrato_lleva_boton_url_con_sufijo_variable():
    payload = create_payload(CATALOG['firma_contrato'], 'https://demo.crediflux.com.do/sign/')
    boton = payload['components'][1]['buttons'][0]
    assert payload['category'] == 'UTILITY' and payload['language'] == 'es'
    assert boton == {
        'type': 'URL', 'text': 'Revisar y firmar',
        'url': 'https://demo.crediflux.com.do/sign/{{1}}',
        'example': ['https://demo.crediflux.com.do/sign/ejemplo-token'],
    }


def test_componentes_de_envio_validan_la_cantidad_de_valores():
    spec = CATALOG['recibo_pago']
    with pytest.raises(ValueError):
        send_components(spec, ['solo uno'])
    body = send_components(spec, list(spec.example))[0]
    assert [p['text'] for p in body['parameters']] == list(spec.example)


# ---------------------------------------------------------------------------
# Sincronización con la cuenta de la financiera
# ---------------------------------------------------------------------------


@responses.activate
def test_sincronizar_crea_las_que_faltan_y_toma_el_estado_de_las_existentes(wa_tenant):
    from apps.communications.models import WhatsAppTemplate
    from apps.communications.whatsapp_template_service import sync_tenant_templates

    responses.get(TEMPLATES_URL, json={'data': [
        {'id': '901', 'name': 'crediflux_recibo_pago', 'language': 'es', 'status': 'APPROVED'},
        {'id': '902', 'name': 'otra_plantilla_de_la_financiera', 'language': 'es', 'status': 'APPROVED'},
    ]})
    for i in range(4):
        responses.post(TEMPLATES_URL, json={'id': f'95{i}', 'status': 'PENDING', 'category': 'UTILITY'})

    summary = sync_tenant_templates(wa_tenant)

    assert summary['updated'] == ['crediflux_recibo_pago']
    assert sorted(summary['created']) == sorted(
        s.name for s in CATALOG.values() if s.key != 'recibo_pago'
    )
    creados = [json.loads(c.request.body) for c in responses.calls if c.request.method == 'POST']
    assert {c['name'] for c in creados} == set(summary['created'])
    assert all(c['category'] == 'UTILITY' for c in creados)
    assert responses.calls[0].request.headers['Authorization'] == 'Bearer token-de-prueba'

    assert WhatsAppTemplate.objects.get(name='crediflux_recibo_pago').status == 'APPROVED'
    firma = WhatsAppTemplate.objects.get(name='crediflux_firma_contrato')
    assert firma.status == 'PENDING' and firma.meta_template_id.startswith('95')
    assert firma.button_base_url.endswith('/sign/')
    assert not WhatsAppTemplate.objects.filter(name='otra_plantilla_de_la_financiera').exists()


@responses.activate
def test_sincronizar_otra_vez_no_duplica(wa_tenant):
    from apps.communications.whatsapp_template_service import sync_tenant_templates

    responses.get(TEMPLATES_URL, json={'data': [
        {'id': str(900 + i), 'name': s.name, 'language': 'es', 'status': 'PENDING', 'rejected_reason': 'NONE'}
        for i, s in enumerate(CATALOG.values())
    ]})

    summary = sync_tenant_templates(wa_tenant)

    assert summary['created'] == []
    from apps.communications.models import WhatsAppTemplate

    assert set(WhatsAppTemplate.objects.values_list('rejected_reason', flat=True)) == {''}  # 'NONE' no es motivo
    assert not [c for c in responses.calls if c.request.method == 'POST']


@responses.activate
def test_un_rechazo_al_crear_queda_registrado(wa_tenant):
    from apps.communications.models import WhatsAppTemplate
    from apps.communications.whatsapp_template_service import sync_tenant_templates

    responses.get(TEMPLATES_URL, json={'data': []})
    responses.post(TEMPLATES_URL, status=400, json={'error': {'message': 'Invalid parameter', 'code': 100}})
    for i in range(4):
        responses.post(TEMPLATES_URL, json={'id': f'96{i}', 'status': 'PENDING'})

    summary = sync_tenant_templates(wa_tenant)

    assert len(summary['errors']) == 1
    fallida = WhatsAppTemplate.objects.get(name=summary['errors'][0])
    assert fallida.status == 'ERROR' and 'Invalid parameter' in fallida.rejected_reason


def test_sin_credenciales_no_llama_a_meta(tenant_schema):
    from apps.communications.whatsapp_template_service import sync_tenant_templates

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        assert sync_tenant_templates(tenant_schema) == {'created': [], 'updated': [], 'errors': []}
        assert len(rsps.calls) == 0


def test_aviso_de_estado_de_meta_actualiza_la_plantilla(wa_tenant):
    from apps.communications.models import WhatsAppTemplate
    from apps.communications.whatsapp_template_service import apply_status_update

    WhatsAppTemplate.objects.create(key='recibo_pago', name='crediflux_recibo_pago', meta_template_id='901')

    assert apply_status_update({'event': 'APPROVED', 'message_template_id': 901, 'reason': 'NONE'})
    assert WhatsAppTemplate.objects.get(meta_template_id='901').status == 'APPROVED'

    apply_status_update({'event': 'REJECTED', 'message_template_id': 901, 'reason': 'INVALID_FORMAT'})
    rechazada = WhatsAppTemplate.objects.get(meta_template_id='901')
    assert (rechazada.status, rechazada.rejected_reason) == ('REJECTED', 'INVALID_FORMAT')

    assert apply_status_update({'event': 'APPROVED', 'message_template_id': 999}) is False


# ---------------------------------------------------------------------------
# Envío
# ---------------------------------------------------------------------------


@responses.activate
def test_envia_plantilla_aprobada_y_guarda_el_mensaje(wa_tenant):
    from apps.communications.whatsapp_template_service import send_template

    _approve_all()
    responses.post(MESSAGES_URL, json={'messages': [{'id': 'wamid.TPL1'}]})
    values = ['Juan', 'Financiera de Prueba SRL', 'LN-1', '15 de abril de 2026', 'RD$4,500.00']

    message = send_template(wa_tenant, 'recordatorio_cuota', '(809) 555-0000', values)

    body = json.loads(responses.calls[0].request.body)
    assert body['to'] == '18095550000'
    assert body['type'] == 'template'
    assert body['template']['name'] == 'crediflux_recordatorio_cuota'
    assert body['template']['language'] == {'code': 'es'}
    assert [p['text'] for p in body['template']['components'][0]['parameters']] == values
    assert message.wa_message_id == 'wamid.TPL1'
    assert message.message_type == 'template' and message.status == 'pending'
    assert message.content.startswith('Hola Juan, Financiera de Prueba SRL le recuerda')
    assert message.metadata['template'] == 'crediflux_recordatorio_cuota'


def test_no_envia_si_la_plantilla_no_esta_aprobada(wa_tenant):
    from apps.communications.models import WhatsAppMessage, WhatsAppTemplate
    from apps.communications.whatsapp_template_service import send_template

    WhatsAppTemplate.objects.create(key='recibo_pago', name='crediflux_recibo_pago', status='PENDING')

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        assert send_template(wa_tenant, 'recibo_pago', '8095550000', list(CATALOG['recibo_pago'].example)) is None
        assert len(rsps.calls) == 0
    assert not WhatsAppMessage.objects.exists()


@responses.activate
def test_error_de_meta_queda_como_mensaje_fallido(wa_tenant):
    from apps.communications.models import WhatsAppMessage
    from apps.communications.whatsapp_template_service import send_template

    _approve_all()
    responses.post(MESSAGES_URL, status=400, json={'error': {'message': 'Recipient not in allowed list',
                                                             'code': 131030}})

    assert send_template(wa_tenant, 'recibo_pago', '8095550000', list(CATALOG['recibo_pago'].example)) is None

    fallido = WhatsAppMessage.objects.get()
    assert fallido.status == 'failed'
    assert 'Recipient not in allowed list' in fallido.error_message


# ---------------------------------------------------------------------------
# Webhook de estado y tarea de sincronización
# ---------------------------------------------------------------------------


def test_webhook_de_estado_de_plantilla_identifica_al_tenant_por_la_cuenta(wa_tenant, public_client):
    from apps.communications.webhooks.utils import extract_phone_number_id, extract_waba_id, find_tenant_by_waba_id

    payload = {
        'object': 'whatsapp_business_account',
        'entry': [{'id': WABA, 'changes': [{
            'field': 'message_template_status_update',
            'value': {'event': 'APPROVED', 'message_template_id': 901,
                      'message_template_name': 'crediflux_recibo_pago', 'message_template_language': 'es',
                      'reason': 'NONE'},
        }]}],
    }
    assert extract_phone_number_id(payload) is None
    assert extract_waba_id(payload) == WABA
    assert find_tenant_by_waba_id(WABA).pk == wa_tenant.pk


def test_el_manejador_del_webhook_aplica_el_estado(wa_tenant):
    from apps.communications.models import WhatsAppTemplate
    from apps.communications.webhooks.handlers import WhatsAppWebhookHandler

    WhatsAppTemplate.objects.create(key='recibo_pago', name='crediflux_recibo_pago', meta_template_id='901')
    WhatsAppWebhookHandler(wa_tenant).process({
        'object': 'whatsapp_business_account',
        'entry': [{'id': WABA, 'changes': [{
            'field': 'message_template_status_update',
            'value': {'event': 'APPROVED', 'message_template_id': 901, 'reason': 'NONE'},
        }]}],
    })

    assert WhatsAppTemplate.objects.get(meta_template_id='901').status == 'APPROVED'


def test_tarea_de_sincronizacion_solo_toca_tenants_con_credenciales(wa_tenant):
    from unittest import mock

    from apps.communications.tasks import sync_whatsapp_templates

    with mock.patch('apps.communications.whatsapp_template_service.sync_tenant_templates',
                    return_value={'created': [], 'updated': [], 'errors': []}) as sync:
        result = sync_whatsapp_templates.run()

    assert [c.args[0].schema_name for c in sync.call_args_list] == [wa_tenant.schema_name]
    assert result['failed'] == []


def test_setup_periodic_tasks_programa_la_sincronizacion(public_schema):
    from unittest import mock

    from django.core.management import call_command
    from django_celery_beat.models import PeriodicTask

    call_command('setup_periodic_tasks', stdout=mock.MagicMock())

    task = PeriodicTask.objects.get(task='communications.sync_whatsapp_templates')
    assert task.enabled and (task.crontab.minute, task.crontab.hour) == ('15', '*')
