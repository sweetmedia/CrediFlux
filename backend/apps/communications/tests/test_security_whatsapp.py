"""Seguridad de WhatsApp: envío con rol y destino ligado, phone_number_id único y webhook por entrada."""
from datetime import date
from unittest.mock import patch

import pytest

from apps.communications.models import WhatsAppMessage
from apps.communications.webhooks.handlers import WhatsAppWebhookHandler

SEND_TASK = 'apps.communications.views_whatsapp.send_whatsapp_message'
INBOUND_TASK = 'apps.communications.tasks.process_inbound_whatsapp_message'


def _send_url(conversation_id):
    return f'/api/communications/whatsapp/conversations/{conversation_id}/send/'


@pytest.fixture
def conversation(tenant_schema):
    return WhatsAppMessage.objects.create(
        direction='inbound', status='received', wa_message_id='wamid.CONV1',
        from_phone='18095551111', to_phone='18095550000',
        content='Hola', conversation_id='18095551111',
    )


@pytest.fixture
def customer(tenant_schema):
    from apps.loans.models import Customer

    return Customer.objects.create(
        first_name='Juana', last_name='Pérez', date_of_birth=date(1990, 1, 1), gender='F',
        email='cliente.whatsapp@crediflux.test', phone='+18095552222',
        address_line1='Calle 1', city='Santo Domingo', state='DN', postal_code='10101',
        id_type='cedula', id_number='001-7777777-1', employment_status='employed',
    )


@pytest.fixture
def tenant_with_phone_id(tenant_schema):
    """Tenant de pruebas con phone_number_id; se restaura el objeto de sesión al final."""
    original = tenant_schema.whatsapp_phone_id
    tenant_schema.whatsapp_phone_id = 'PID-A'
    tenant_schema.save(update_fields=['whatsapp_phone_id'])
    yield tenant_schema
    tenant_schema.whatsapp_phone_id = original


def _set_phone_id(tenant, phone_id):
    # update() evita el chequeo de schema de django-tenants en Tenant.save().
    type(tenant).objects.filter(pk=tenant.pk).update(whatsapp_phone_id=phone_id)
    tenant.whatsapp_phone_id = phone_id


def _client_as(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def test_viewer_cannot_send(api_client, user_factory, conversation):
    client = _client_as(api_client, user_factory(role='viewer'))
    with patch(SEND_TASK) as task:
        response = client.post(_send_url(conversation.conversation_id), {'message': 'Hola'}, format='json')

    assert response.status_code == 403
    assert response.json()['required_permission'] == 'comms.whatsapp'
    task.delay.assert_not_called()


def test_collector_cannot_send_to_unknown_number(api_client, user_factory):
    client = _client_as(api_client, user_factory(role='collector'))
    with patch(SEND_TASK) as task:
        response = client.post(_send_url('18095559999'), {'message': 'Hola'}, format='json')

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'No existe una conversación ni un cliente con ese número en este tenant.'
    }
    task.delay.assert_not_called()


def test_collector_can_send_to_existing_conversation(api_client, user_factory, conversation, tenant_schema):
    client = _client_as(api_client, user_factory(role='collector'))
    with patch(SEND_TASK) as task:
        task.delay.return_value.id = 'task-1'
        response = client.post(_send_url(conversation.conversation_id), {'message': 'Hola'}, format='json')

    assert response.status_code == 202
    assert response.json()['task_id'] == 'task-1'
    task.delay.assert_called_once_with(
        tenant_schema=tenant_schema.schema_name,
        to_phone='18095551111',
        message_text='Hola',
        customer_id=None,
    )


def test_collector_can_send_to_customer_phone(api_client, user_factory, customer, tenant_schema):
    client = _client_as(api_client, user_factory(role='collector'))
    with patch(SEND_TASK) as task:
        task.delay.return_value.id = 'task-2'
        response = client.post(_send_url('18095552222'), {'message': 'Hola'}, format='json')

    assert response.status_code == 202
    task.delay.assert_called_once_with(
        tenant_schema=tenant_schema.schema_name,
        to_phone='18095552222',
        message_text='Hola',
        customer_id=customer.id,
    )


def test_settings_rejects_phone_id_used_by_other_tenant(other_tenant, api_client, user_factory, tenant_schema):
    _set_phone_id(other_tenant, 'PID-SHARED')
    original = tenant_schema.whatsapp_phone_id
    client = _client_as(api_client, user_factory(role='admin', is_tenant_owner=True))

    response = client.patch('/api/tenants/settings/', {'whatsapp_phone_id': 'PID-SHARED'}, format='json')

    assert response.status_code == 400
    assert response.json()['whatsapp_phone_id'] == ['Este phone_number_id ya está en uso.']
    tenant_schema.refresh_from_db()
    assert tenant_schema.whatsapp_phone_id == original


def _change(phone_number_id, wamid):
    return {
        'field': 'messages',
        'value': {
            'messaging_product': 'whatsapp',
            'metadata': {'display_phone_number': '18095550000', 'phone_number_id': phone_number_id},
            'contacts': [{'profile': {'name': 'Cliente'}, 'wa_id': '18095551111'}],
            'messages': [{
                'from': '18095551111', 'id': wamid, 'timestamp': '1700000000',
                'type': 'text', 'text': {'body': 'Hola'},
            }],
        },
    }


def test_handler_only_enqueues_entries_of_its_tenant(tenant_with_phone_id, other_tenant):
    _set_phone_id(other_tenant, 'PID-B')
    payload = {
        'object': 'whatsapp_business_account',
        'entry': [
            {'id': 'WABA-A', 'changes': [_change('PID-A', 'wamid.A')]},
            {'id': 'WABA-B', 'changes': [_change('PID-B', 'wamid.B')]},
        ],
    }

    with patch(INBOUND_TASK) as task:
        WhatsAppWebhookHandler(tenant_with_phone_id).process(payload)

    task.delay.assert_called_once()
    kwargs = task.delay.call_args.kwargs
    assert kwargs['tenant_schema'] == tenant_with_phone_id.schema_name
    assert kwargs['message_data']['id'] == 'wamid.A'


def test_migration_normalizes_blank_and_dedupes_without_aborting(public_schema):
    """La migración 0015 deja vacíos en NULL y conserva el duplicado de id más alto."""
    from importlib import import_module

    from django.apps import apps as django_apps
    from django.db import connection

    from apps.tenants.models import Tenant

    migration = import_module('apps.tenants.migrations.0015_tenant_whatsapp_phone_id_unique')
    table = Tenant._meta.db_table
    # Se quita la restricción dentro de la transacción del test (se deshace al final)
    # para poder reproducir los datos previos a la migración.
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)
        for name, info in constraints.items():
            if info['unique'] and info['columns'] == ['whatsapp_phone_id']:
                cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"')

    def _tenant(schema, phone_id):
        return Tenant(schema_name=schema, name=schema, business_name=schema,
                      email=f'{schema}@crediflux.test', whatsapp_phone_id=phone_id)

    created = Tenant.objects.bulk_create([
        _tenant('dup_old', 'PID-DUP'), _tenant('dup_new', 'PID-DUP'), _tenant('blank_pid', '  '),
    ])

    migration.normalize_and_dedupe_phone_ids(django_apps, None)
    migration.normalize_and_dedupe_phone_ids(django_apps, None)  # idempotente

    values = dict(
        Tenant.objects.filter(pk__in=[t.pk for t in created]).values_list('schema_name', 'whatsapp_phone_id')
    )
    assert values == {'dup_old': None, 'dup_new': 'PID-DUP', 'blank_pid': None}
