"""
Tests del receptor de webhooks de NexConnect.

Sin base de datos: ORM y transacciones parcheados, como en ``test_nexconnect``.
"""
import contextlib
import hashlib
import hmac
import json
import time
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import RequestFactory, SimpleTestCase

from apps.billing import webhooks as webhook_view
from apps.billing.management.commands import nexconnect_webhook_register as register_cmd
from apps.billing.models import ECFSubmission, Invoice, NexConnectWebhookEvent
from apps.billing.services.nexconnect import webhooks
from apps.billing.services.nexconnect.client import NexConnectClient
from apps.billing.services.nexconnect.credentials import (
    NexConnectCredentials,
    NexConnectCredentialsError,
    set_tenant_api_key,
    set_tenant_webhook,
    webhook_secret_for_tenant,
)
from apps.core.crypto import is_encrypted

from .test_nexconnect import NX_ID, TEST_KEY, FakeResponse, FakeSession, make_invoice

SECRET = 'ab' * 32  # 64 hex = 32 bytes, como lo devuelve POST /v1/webhooks/
EVENT_ID = 'evt_3f2504e04f8911d39a0c0305e82c3301'
LOCAL_ID = '11111111-2222-3333-4444-555555555555'


def make_event(event_type='invoice.accepted', status='accepted', event_id=EVENT_ID,
               created_at='2026-10-21T15:00:00+00:00', metadata=None, **obj_overrides):
    obj = {
        'id': NX_ID,
        'ncf': 'E310000000007',
        'status': status,
        'dgii_tracking_id': 'trk-123',
        'metadata': {'crediflux_invoice_id': LOCAL_ID} if metadata is None else metadata,
        'lines': [{'description': 'x'}],
        'xml_signed_b64': 'PEVDRj4=',
    }
    obj.update(obj_overrides)
    return {
        'id': event_id,
        'type': event_type,
        'created_at': created_at,
        'data': {'emitter_id': 'em-1', 'object': obj, 'error_source': None},
    }


def sign(body: bytes, secret=SECRET, timestamp=None):
    """Firma como ``integrations.tasks.deliver_webhook`` de NexConnect."""
    timestamp = int(time.time()) if timestamp is None else timestamp
    sig = hmac.new(bytes.fromhex(secret), f'{timestamp}.'.encode() + body, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={sig}'


def encode(event) -> bytes:
    return json.dumps(event, sort_keys=True).encode()


def linked_invoice(**overrides):
    """Factura ya emitida por NexConnect (dgii_response con su id)."""
    fields = dict(status='submitted', dgii_status='submitted',
                  dgii_response={'provider': 'nexconnect', 'id': NX_ID, 'status': 'submitted'})
    fields.update(overrides)
    return make_invoice(**fields)


class FakeInvoices:
    """``Invoice.objects.select_for_update().filter(**kw).first()`` sobre una lista."""

    def __init__(self, *invoices):
        self.invoices = list(invoices)
        self.filters = []

    def select_for_update(self):
        return self

    def filter(self, **kwargs):
        self.filters.append(kwargs)
        self._kwargs = kwargs
        return self

    def first(self):
        for inv in self.invoices:
            if 'id' in self._kwargs and str(inv.id) == str(self._kwargs['id']):
                return inv
            if 'dgii_response__id' in self._kwargs and (inv.dgii_response or {}).get('id') == self._kwargs['dgii_response__id']:
                return inv
        return None


class ProcessEventMixin:
    """Parchea transacciones, ORM y logs para ``webhooks.process_event``."""

    def setUp(self):
        self.tenant = SimpleNamespace(schema_name='public', dgii_environment='testecf')
        self.created_events = []
        self.logged = []
        patches = [
            mock.patch.object(webhooks.transaction, 'atomic', lambda *a, **k: contextlib.nullcontext()),
            mock.patch.object(NexConnectWebhookEvent.objects, 'create', side_effect=self._create_event),
            mock.patch.object(NexConnectWebhookEvent, 'save', autospec=True),
            mock.patch.object(Invoice, 'save', autospec=True),
            mock.patch.object(ECFSubmission.objects, 'create',
                              side_effect=lambda **kw: self.logged.append(kw)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _create_event(self, **kwargs):
        if kwargs['event_id'] in {e.event_id for e in self.created_events}:
            raise IntegrityError('duplicate key value violates unique constraint')
        record = NexConnectWebhookEvent(**kwargs)
        self.created_events.append(record)
        return record

    def run_event(self, event, *invoices):
        fake = FakeInvoices(*invoices)
        with mock.patch.object(webhooks, 'Invoice', SimpleNamespace(objects=fake)):
            outcome = webhooks.process_event(self.tenant, event)
        return outcome, fake


# ----------------------------------------------------------------------
# Firma
# ----------------------------------------------------------------------

class SignatureTests(SimpleTestCase):

    body = b'{"data": {}, "id": "evt_1", "type": "invoice.accepted"}'

    def test_valid_signature(self):
        now = 1714745923
        header = sign(self.body, timestamp=now)
        self.assertEqual(webhooks.verify_signature(SECRET, header, self.body, now=now + 10), now)

    def test_tampered_body_or_wrong_secret(self):
        header = sign(self.body)
        with self.assertRaises(webhooks.WebhookSignatureError):
            webhooks.verify_signature(SECRET, header, self.body + b' ')
        with self.assertRaises(webhooks.WebhookSignatureError):
            webhooks.verify_signature('cd' * 32, header, self.body)

    def test_hmac_key_is_hex_decoded(self):
        """Firmar con la cadena hex en vez de sus bytes (el error típico) no verifica."""
        ts = int(time.time())
        wrong = hmac.new(SECRET.encode(), f'{ts}.'.encode() + self.body, hashlib.sha256).hexdigest()
        with self.assertRaises(webhooks.WebhookSignatureError):
            webhooks.verify_signature(SECRET, f't={ts},v1={wrong}', self.body)

    def test_replay_outside_tolerance(self):
        now = 1714745923
        for ts in (now - 301, now + 301):
            with self.assertRaises(webhooks.WebhookSignatureError):
                webhooks.verify_signature(SECRET, sign(self.body, timestamp=ts), self.body, now=now)
        webhooks.verify_signature(SECRET, sign(self.body, timestamp=now - 300), self.body, now=now)

    def test_malformed_headers(self):
        for header in ('', 'v1=abc', 't=123', 't=abc,v1=def', 'garbage'):
            with self.assertRaises(webhooks.WebhookSignatureError, msg=header):
                webhooks.verify_signature(SECRET, header, self.body)

    def test_any_v1_may_match(self):
        ts = int(time.time())
        good = sign(self.body, timestamp=ts).split('v1=')[1]
        header = f't={ts},v1={"0" * 64},v1={good}'
        self.assertEqual(webhooks.verify_signature(SECRET, header, self.body), ts)

    def test_no_secret(self):
        with self.assertRaises(webhooks.WebhookSignatureError):
            webhooks.verify_signature('', sign(self.body), self.body)


class EventParsingTests(SimpleTestCase):

    def test_parse_valid(self):
        event = webhooks.parse_event(encode(make_event()))
        self.assertEqual(event['id'], EVENT_ID)

    def test_parse_invalid(self):
        for body in (b'no json', b'[]', b'{"type": "x", "data": {}}',
                     b'{"id": "123", "type": "x", "data": {}}',
                     b'{"id": "evt_1", "data": {}}', b'{"id": "evt_1", "type": "x"}'):
            with self.assertRaises(webhooks.WebhookPayloadError, msg=body):
                webhooks.parse_event(body)

    def test_sixteen_documented_events(self):
        self.assertEqual(len(webhooks.ALL_EVENTS), 16)
        self.assertEqual(len(set(webhooks.ALL_EVENTS)), 16)
        self.assertTrue(set(webhooks.DEFAULT_SUBSCRIBED_EVENTS) <= set(webhooks.OUTBOUND_EVENTS))

    def test_slim_event_drops_heavy_fields(self):
        slim = webhooks.slim_event(make_event())
        self.assertNotIn('xml_signed_b64', slim['data']['object'])
        self.assertNotIn('lines', slim['data']['object'])
        self.assertEqual(slim['data']['object']['status'], 'accepted')


# ----------------------------------------------------------------------
# Procesamiento (resolver + _apply + idempotencia)
# ----------------------------------------------------------------------

class ProcessEventTests(ProcessEventMixin, SimpleTestCase):

    def test_applies_status_via_metadata(self):
        invoice = linked_invoice()
        outcome, fake = self.run_event(make_event(), invoice)

        self.assertEqual(outcome, 'applied')
        self.assertEqual(fake.filters[0], {'id': invoice.id})
        self.assertEqual(invoice.status, 'accepted')
        self.assertEqual(invoice.dgii_status, 'accepted')
        self.assertEqual(invoice.dgii_trackid, 'trk-123')
        self.assertEqual(invoice.dgii_response['webhook_event_id'], EVENT_ID)
        self.assertEqual(invoice.dgii_response['webhook_event_at'], '2026-10-21T15:00:00+00:00')
        self.assertNotIn('xml_signed_b64', invoice.dgii_response)
        Invoice.save.assert_called_once()
        self.assertEqual(self.logged[0]['action'], 'webhook')
        self.assertEqual(self.logged[0]['response_status'], 'accepted')
        record = self.created_events[0]
        self.assertEqual((record.outcome, record.invoice), ('applied', invoice))

    def test_falls_back_to_nexconnect_id(self):
        invoice = linked_invoice()
        outcome, fake = self.run_event(make_event(metadata={}), invoice)
        self.assertEqual(outcome, 'applied')
        self.assertEqual(fake.filters[0], {'dgii_response__provider': 'nexconnect',
                                           'dgii_response__id': NX_ID})
        self.assertEqual(invoice.status, 'accepted')

    def test_metadata_invoice_not_yet_linked_is_adopted(self):
        """El evento llegó antes de que submit_invoice guardara la respuesta."""
        invoice = make_invoice(status='draft')
        outcome, _ = self.run_event(make_event(event_type='invoice.submitted', status='submitted'), invoice)
        self.assertEqual(outcome, 'applied')
        self.assertEqual(invoice.dgii_response['id'], NX_ID)
        self.assertEqual(invoice.status, 'submitted')

    def test_rejected_and_conditional(self):
        invoice = linked_invoice()
        self.run_event(make_event(event_type='invoice.rejected', status='rejected'), invoice)
        self.assertEqual(invoice.status, 'rejected')
        invoice = linked_invoice()
        self.run_event(make_event(event_type='invoice.accepted_conditional',
                                  status='accepted_conditional', event_id='evt_2'), invoice)
        self.assertEqual(invoice.status, 'conditionally_accepted')

    def test_duplicate_event_is_noop(self):
        invoice = linked_invoice()
        self.assertEqual(self.run_event(make_event(), invoice)[0], 'applied')
        outcome, fake = self.run_event(make_event(), invoice)
        self.assertEqual(outcome, webhooks.DUPLICATE)
        self.assertEqual(fake.filters, [])
        Invoice.save.assert_called_once()

    def test_stale_pending_after_final(self):
        invoice = linked_invoice(status='accepted', dgii_status='accepted')
        outcome, _ = self.run_event(make_event(event_type='invoice.submitted', status='submitted'), invoice)
        self.assertEqual(outcome, 'stale')
        self.assertEqual(invoice.status, 'accepted')
        Invoice.save.assert_not_called()
        self.assertEqual(self.created_events[0].outcome, 'stale')

    def test_stale_older_than_last_applied_event(self):
        invoice = linked_invoice()
        invoice.dgii_response['webhook_event_at'] = '2026-10-21T16:00:00+00:00'
        outcome, _ = self.run_event(make_event(event_type='invoice.rejected', status='rejected'), invoice)
        self.assertEqual(outcome, 'stale')
        self.assertEqual(invoice.status, 'submitted')

    def test_final_to_final_is_applied(self):
        invoice = linked_invoice(status='accepted', dgii_status='accepted')
        outcome, _ = self.run_event(make_event(event_type='invoice.cancelled', status='cancelled'), invoice)
        self.assertEqual(outcome, 'applied')
        self.assertEqual(invoice.status, 'cancelled')

    def test_mismatch_does_not_touch_invoice(self):
        invoice = linked_invoice(dgii_response={'provider': 'nexconnect', 'id': 'otro-id'})
        outcome, _ = self.run_event(make_event(), invoice)
        self.assertEqual(outcome, 'mismatch')
        self.assertEqual(invoice.status, 'submitted')
        Invoice.save.assert_not_called()

    def test_unmatched(self):
        outcome, _ = self.run_event(make_event(metadata={'crediflux_invoice_id': 'no-uuid'}))
        self.assertEqual(outcome, 'unmatched')
        self.assertEqual(self.created_events[0].outcome, 'unmatched')

    def test_receiver_event_is_recorded_and_ignored(self):
        event = make_event(event_type='invoice.received')
        event['data'] = {'received_invoice': {'id': 'r-1'}}
        outcome, fake = self.run_event(event)
        self.assertEqual(outcome, 'ignored')
        self.assertEqual(fake.filters, [])
        self.assertEqual(self.created_events[0].event_type, 'invoice.received')


# ----------------------------------------------------------------------
# Vista HTTP
# ----------------------------------------------------------------------

class WebhookViewTests(SimpleTestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(schema_name='acme', nexconnect_webhook_secret='')
        set_tenant_webhook(self.tenant, 'wh-1', SECRET, save=False)
        tenants = mock.MagicMock()
        tenants.objects.filter.return_value.first.side_effect = (
            lambda: self.tenant if self.lookup == 'acme' else None
        )
        self.lookup = 'acme'
        patches = [
            mock.patch.object(webhook_view, 'get_tenant_model', return_value=tenants),
            mock.patch.object(webhook_view, 'schema_context', lambda s: contextlib.nullcontext()),
            mock.patch.object(webhook_view, 'process_event', return_value='applied'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.factory = RequestFactory()

    def post(self, body: bytes, header=None, schema='acme'):
        self.lookup = schema
        extra = {'HTTP_X_NEXCONNECT_SIGNATURE': header} if header is not None else {}
        request = self.factory.post(f'/api/webhooks/nexconnect/{schema}/', data=body,
                                    content_type='application/json', **extra)
        return webhook_view.NexConnectWebhookView.as_view()(request, schema_name=schema)

    def test_valid_delivery(self):
        body = encode(make_event())
        response = self.post(body, sign(body))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content),
                         {'received': True, 'event_id': EVENT_ID, 'outcome': 'applied'})
        tenant, event = webhook_view.process_event.call_args.args
        self.assertIs(tenant, self.tenant)
        self.assertEqual(event['type'], 'invoice.accepted')

    def test_bad_or_missing_signature(self):
        body = encode(make_event())
        self.assertEqual(self.post(body, sign(body, secret='cd' * 32)).status_code, 401)
        self.assertEqual(self.post(body).status_code, 401)
        old = sign(body, timestamp=int(time.time()) - 3600)
        self.assertEqual(self.post(body, old).status_code, 401)
        webhook_view.process_event.assert_not_called()

    def test_unknown_tenant_or_no_secret(self):
        body = encode(make_event())
        self.assertEqual(self.post(body, sign(body), schema='otro').status_code, 404)
        self.tenant.nexconnect_webhook_secret = ''
        self.assertEqual(self.post(body, sign(body)).status_code, 404)

    def test_signed_but_invalid_event(self):
        body = b'{"hola": 1}'
        self.assertEqual(self.post(body, sign(body)).status_code, 400)

    def test_get_not_allowed(self):
        request = self.factory.get('/api/webhooks/nexconnect/acme/')
        response = webhook_view.NexConnectWebhookView.as_view()(request, schema_name='acme')
        self.assertEqual(response.status_code, 405)

    def test_url_is_routed(self):
        from django.urls import resolve, reverse
        path = reverse('nexconnect-webhook', kwargs={'schema_name': 'acme'})
        self.assertEqual(path, '/api/webhooks/nexconnect/acme/')
        self.assertIs(resolve(path).func.view_class, webhook_view.NexConnectWebhookView)


# ----------------------------------------------------------------------
# Secret y registro del webhook
# ----------------------------------------------------------------------

class WebhookSecretTests(SimpleTestCase):

    def test_secret_is_stored_encrypted(self):
        tenant = SimpleNamespace()
        set_tenant_webhook(tenant, 'wh-1', SECRET, save=False)
        self.assertTrue(is_encrypted(tenant.nexconnect_webhook_secret))
        self.assertNotIn(SECRET, tenant.nexconnect_webhook_secret)
        self.assertLessEqual(len(tenant.nexconnect_webhook_secret), 255)
        self.assertEqual(webhook_secret_for_tenant(tenant), SECRET)
        self.assertEqual(tenant.nexconnect_webhook_id, 'wh-1')

    def test_non_hex_secret_rejected(self):
        with self.assertRaises(NexConnectCredentialsError):
            set_tenant_webhook(SimpleNamespace(), 'wh-1', 'no-es-hex', save=False)

    def test_client_create_and_delete(self):
        session = FakeSession(FakeResponse(201, {'id': 'wh-1', 'secret': SECRET}), FakeResponse(204, text=''))
        client = NexConnectClient(NexConnectCredentials(api_key=TEST_KEY),
                                  base_url='http://nexconnect.test', session=session)
        data = client.create_webhook('https://x.test/hook', ['invoice.accepted'], description='d')
        client.delete_webhook('wh-1')
        self.assertEqual(data['secret'], SECRET)
        self.assertEqual(session.calls[0]['url'], 'http://nexconnect.test/v1/webhooks/')
        self.assertEqual(session.calls[0]['json'],
                         {'url': 'https://x.test/hook', 'events': ['invoice.accepted'], 'description': 'd'})
        self.assertEqual((session.calls[1]['method'], session.calls[1]['url']),
                         ('DELETE', 'http://nexconnect.test/v1/webhooks/wh-1/'))


class RegisterCommandTests(SimpleTestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(schema_name='acme', nexconnect_webhook_id='',
                                      nexconnect_webhook_secret='', save=mock.Mock())
        set_tenant_api_key(self.tenant, TEST_KEY, save=False)
        tenants = mock.MagicMock()
        tenants.DoesNotExist = Exception
        tenants.objects.get.return_value = self.tenant
        p = mock.patch.object(register_cmd, 'get_tenant_model', return_value=tenants)
        p.start()
        self.addCleanup(p.stop)

    def run_cmd(self, *responses, **options):
        session = FakeSession(*responses)
        real = NexConnectClient

        def make(credentials):
            return real(credentials, base_url='http://nexconnect.test', session=session)

        out = StringIO()
        with mock.patch.object(register_cmd, 'NexConnectClient', side_effect=make):
            call_command('nexconnect_webhook_register', schema='acme', stdout=out, **options)
        return session, out.getvalue()

    def test_registers_and_stores_secret(self):
        session, out = self.run_cmd(FakeResponse(201, {'id': 'wh-9', 'secret': SECRET}),
                                    base_url='https://api.crediflux.test/')
        body = session.calls[0]['json']
        self.assertEqual(body['url'], 'https://api.crediflux.test/api/webhooks/nexconnect/acme/')
        self.assertEqual(body['events'], list(webhooks.DEFAULT_SUBSCRIBED_EVENTS))
        self.assertEqual(self.tenant.nexconnect_webhook_id, 'wh-9')
        self.assertEqual(webhook_secret_for_tenant(self.tenant), SECRET)
        self.tenant.save.assert_called_once_with(
            update_fields=['nexconnect_webhook_id', 'nexconnect_webhook_secret'])
        self.assertNotIn(SECRET, out)

    def test_requires_https_and_valid_events(self):
        with self.assertRaises(CommandError):
            self.run_cmd(url='http://inseguro.test/hook')
        with self.assertRaises(CommandError):
            self.run_cmd(base_url='https://x.test', events='invoice.accepted,invoice.inventado')

    def test_existing_webhook_needs_replace(self):
        self.tenant.nexconnect_webhook_id = 'wh-old'
        with self.assertRaises(CommandError):
            self.run_cmd(base_url='https://x.test')
        session, _ = self.run_cmd(
            FakeResponse(404, {'detail': 'No encontrado'}),
            FakeResponse(201, {'id': 'wh-new', 'secret': SECRET}),
            base_url='https://x.test', replace=True,
        )
        self.assertEqual(session.calls[0]['method'], 'DELETE')
        self.assertEqual(self.tenant.nexconnect_webhook_id, 'wh-new')

    def test_replace_deactivates_when_delete_is_refused(self):
        self.tenant.nexconnect_webhook_id = 'wh-old'
        session, out = self.run_cmd(
            FakeResponse(500, text='ProtectedError'),
            FakeResponse(200, {'id': 'wh-old', 'active': False}),
            FakeResponse(201, {'id': 'wh-new', 'secret': SECRET}),
            base_url='https://x.test', replace=True,
        )
        self.assertEqual([c['method'] for c in session.calls], ['DELETE', 'PATCH', 'POST'])
        self.assertEqual(session.calls[1]['json'], {'active': False})
        self.assertIn('desactivado', out)
        self.assertEqual(self.tenant.nexconnect_webhook_id, 'wh-new')

    def test_api_error_is_reported(self):
        with self.assertRaises(CommandError) as ctx:
            self.run_cmd(FakeResponse(400, {'url': ['Webhook URL must be https://']}),
                         base_url='https://x.test')
        self.assertIn('https', str(ctx.exception))
        self.assertEqual(self.tenant.nexconnect_webhook_id, '')
