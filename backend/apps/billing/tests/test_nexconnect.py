"""
Tests de la integración con NexConnect.

Sin base de datos: HTTP simulado con un Session falso e Invoices sin guardar,
con ``save`` y ``ECFSubmission.objects.create`` parcheados.
"""
import base64
import json
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings
from djmoney.money import Money

from apps.billing.models import Invoice, InvoiceItem
from apps.billing.services.ecf_provider import ECFProviderError, get_ecf_provider
from apps.billing.services.nexconnect import mapping
from apps.billing.services.nexconnect.client import NexConnectClient, NexConnectError
from apps.billing.services.nexconnect.credentials import (
    NexConnectCredentials,
    NexConnectCredentialsError,
    credentials_for_tenant,
    set_tenant_api_key,
)
from apps.billing.services.nexconnect.provider import NexConnectProvider
from apps.core.crypto import decrypt_secret, encrypt_secret, is_encrypted

TEST_KEY = 'nxc_test_' + 'a' * 32
NX_ID = '9f1c2e6a-0000-4000-8000-00000000d4b8'


class FakeResponse:
    def __init__(self, status_code, data=None, text=None):
        self.status_code = status_code
        self._data = data
        self.text = text if text is not None else json.dumps(data)

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        if self._data is None:
            raise ValueError('no json')
        return self._data


class FakeSession:
    """Graba las peticiones y devuelve respuestas en orden."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, json=None, headers=None, timeout=None):
        self.calls.append({'method': method, 'url': url, 'json': json, 'headers': headers})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_client(*responses):
    session = FakeSession(*responses)
    client = NexConnectClient(
        NexConnectCredentials(api_key=TEST_KEY),
        base_url='http://nexconnect.test/', session=session,
    )
    return client, session


def make_invoice(**overrides):
    fields = dict(
        id=uuid.UUID('11111111-2222-3333-4444-555555555555'),
        ecf_type='31',
        status='draft',
        comprador_rnc='101000001',
        comprador_razon_social='CLIENTE EJEMPLO SRL',
        issue_date=date(2026, 10, 21),
        due_date=date(2026, 11, 21),
        payment_method='01',
    )
    fields.update(overrides)
    return Invoice(**fields)


def make_items(invoice):
    return [
        InvoiceItem(invoice=invoice, line_number=1, description='Intereses cuota 3',
                    quantity=Decimal('1.0000'), unit_price=Money('1500.50', 'DOP'),
                    discount_amount=Money('0', 'DOP'), itbis_rate='0'),
        InvoiceItem(invoice=invoice, line_number=2, description='Cargo por gestión',
                    quantity=Decimal('2.0000'), unit_price=Money('100.005', 'DOP'),
                    discount_amount=Money('10', 'DOP'), itbis_rate='18'),
    ]


def signed_response(**overrides):
    data = {
        'id': NX_ID,
        'ncf': 'E310000000007',
        'ecf_type': 31,
        'status': 'signed',
        'environment': 'testecf',
        'dgii_tracking_id': '',
        'codigo_seguridad': 'AbC123',
        'monto_total_cents': 170551,
        'xml_signed_b64': base64.b64encode(b'<ECF>firmado</ECF>').decode(),
        'lines': [{'description': 'x'}],
    }
    data.update(overrides)
    return data


# ----------------------------------------------------------------------
# Cifrado / credenciales
# ----------------------------------------------------------------------

class CryptoTests(SimpleTestCase):

    def test_roundtrip(self):
        token = encrypt_secret(TEST_KEY)
        self.assertTrue(is_encrypted(token))
        self.assertNotIn(TEST_KEY, token)
        self.assertLessEqual(len(token), 255)  # cabe en Tenant.ecf_provider_api_key
        self.assertEqual(decrypt_secret(token), TEST_KEY)

    def test_plaintext_legacy_passthrough_and_no_double_encrypt(self):
        self.assertEqual(decrypt_secret('plain'), 'plain')
        token = encrypt_secret('x')
        self.assertEqual(encrypt_secret(token), token)
        self.assertEqual(encrypt_secret(''), '')

    @override_settings(FIELD_ENCRYPTION_KEY='')
    def test_derived_key_changes_with_secret_key(self):
        token = encrypt_secret('secreto')
        with override_settings(SECRET_KEY='otra-llave'):
            from apps.core.crypto import SecretDecryptionError
            with self.assertRaises(SecretDecryptionError):
                decrypt_secret(token)


class CredentialsTests(SimpleTestCase):

    def test_set_and_read_tenant_key(self):
        tenant = SimpleNamespace(ecf_provider_api_key=None)
        set_tenant_api_key(tenant, f'  {TEST_KEY} ', save=False)
        self.assertTrue(is_encrypted(tenant.ecf_provider_api_key))
        creds = credentials_for_tenant(tenant)
        self.assertEqual(creds.api_key, TEST_KEY)
        self.assertEqual(creds.headers(), {'Authorization': f'Bearer {TEST_KEY}'})
        self.assertTrue(creds.is_test_key)
        self.assertNotIn(TEST_KEY, repr(creds))

    def test_missing_or_malformed_key(self):
        with self.assertRaises(NexConnectCredentialsError):
            credentials_for_tenant(SimpleNamespace(ecf_provider_api_key=None))
        with self.assertRaises(NexConnectCredentialsError):
            set_tenant_api_key(SimpleNamespace(), 'sk_live_otro', save=False)

    def test_platform_key_sends_account_header(self):
        creds = NexConnectCredentials(api_key='nxc_platform_x', account_id='acc-1')
        self.assertEqual(creds.headers()['NexConnect-Account'], 'acc-1')


# ----------------------------------------------------------------------
# Cliente HTTP
# ----------------------------------------------------------------------

class ClientTests(SimpleTestCase):

    def test_create_invoice_sends_auth_and_idempotency(self):
        client, session = make_client(FakeResponse(201, signed_response()))
        data = client.create_invoice({'ecf_type': 31}, 'key-1')
        self.assertEqual(data['ncf'], 'E310000000007')
        call = session.calls[0]
        self.assertEqual(call['method'], 'POST')
        self.assertEqual(call['url'], 'http://nexconnect.test/v1/invoices')
        self.assertEqual(call['headers']['Authorization'], f'Bearer {TEST_KEY}')
        self.assertEqual(call['headers']['Idempotency-Key'], 'key-1')

    def test_create_invoice_requires_idempotency_key(self):
        client, _ = make_client()
        with self.assertRaises(ValueError):
            client.create_invoice({}, '')

    def test_coded_error(self):
        client, _ = make_client(FakeResponse(403, {'detail': 'Clave de pruebas', 'code': 'clave_de_pruebas'}))
        with self.assertRaises(NexConnectError) as ctx:
            client.create_invoice({}, 'k')
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.code, 'clave_de_pruebas')
        self.assertFalse(ctx.exception.is_retryable)

    def test_validation_error_is_flattened(self):
        client, _ = make_client(FakeResponse(400, {'lines': ['Este campo es requerido.'], 'tipo_pago': ['x']}))
        with self.assertRaises(NexConnectError) as ctx:
            client.create_invoice({}, 'k')
        self.assertIn('lines: Este campo es requerido.', str(ctx.exception))
        self.assertIn('tipo_pago: x', str(ctx.exception))

    def test_non_json_error_and_network_error(self):
        client, _ = make_client(FakeResponse(502, None, text='Bad Gateway'),
                                requests.ConnectionError('refused'))
        with self.assertRaises(NexConnectError) as ctx:
            client.get_invoice_status(NX_ID)
        self.assertIn('Bad Gateway', str(ctx.exception))
        self.assertTrue(ctx.exception.is_retryable)
        with self.assertRaises(NexConnectError) as ctx:
            client.me()
        self.assertIsNone(ctx.exception.status_code)
        self.assertTrue(ctx.exception.is_retryable)


# ----------------------------------------------------------------------
# Mapeo
# ----------------------------------------------------------------------

class MappingTests(SimpleTestCase):

    def test_payload(self):
        invoice = make_invoice()
        payload = mapping.build_invoice_payload(invoice, items=make_items(invoice))
        self.assertEqual(payload['ecf_type'], 31)
        self.assertEqual(payload['issued_at'], '2026-10-21T00:00:00-04:00')
        self.assertEqual(payload['tipo_ingresos'], 2)
        self.assertEqual(payload['tipo_pago'], 1)
        self.assertNotIn('fecha_limite_pago', payload)
        self.assertEqual(payload['customer_rnc'], '101000001')
        self.assertEqual(payload['metadata'], {'crediflux_invoice_id': str(invoice.id)})
        self.assertNotIn('monto_total_cents', payload)  # NexConnect calcula totales

        exenta, gravada = payload['lines']
        self.assertEqual(exenta, {
            'description': 'Intereses cuota 3', 'quantity': '1.0000',
            'unit_price_cents': 150050, 'discount_cents': 0,
            'itbis_rate': 0, 'is_exento': True, 'item_type': 'servicio',
        })
        self.assertEqual(gravada['unit_price_cents'], 10001)  # 100.005 → redondeo comercial
        self.assertEqual(gravada['discount_cents'], 1000)
        self.assertEqual(gravada['itbis_rate'], 18)
        self.assertFalse(gravada['is_exento'])

    def test_payload_is_deterministic(self):
        invoice = make_invoice()
        a = mapping.build_invoice_payload(invoice, items=make_items(invoice))
        b = mapping.build_invoice_payload(invoice, items=make_items(invoice))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(mapping.idempotency_key_for(invoice), mapping.idempotency_key_for(invoice))

    def test_credito(self):
        invoice = make_invoice(payment_method='04')
        payload = mapping.build_invoice_payload(invoice, items=make_items(invoice))
        self.assertEqual(payload['tipo_pago'], 2)
        self.assertEqual(payload['fecha_limite_pago'], '2026-11-21')

    def test_credit_note_is_always_contado_and_references_original(self):
        original = make_invoice(encf_number='E310000000001')
        note = make_invoice(ecf_type='34', payment_method='04', reference_invoice=original)
        payload = mapping.build_invoice_payload(note, items=make_items(note))
        self.assertEqual(payload['tipo_pago'], 1)
        self.assertEqual(payload['ncf_modificado'], 'E310000000001')

    def test_consumo_without_buyer(self):
        invoice = make_invoice(ecf_type='32', comprador_rnc='', comprador_razon_social='')
        payload = mapping.build_invoice_payload(invoice, items=make_items(invoice))
        self.assertNotIn('customer_rnc', payload)
        self.assertNotIn('customer_legal_name', payload)

    def test_no_lines(self):
        with self.assertRaises(ValueError):
            mapping.build_invoice_payload(make_invoice(), items=[])

    def test_status_map(self):
        self.assertEqual(mapping.local_status('accepted_conditional', 'x'), 'conditionally_accepted')
        self.assertEqual(mapping.local_status('QUEUED_OFFLINE', 'x'), 'submitted')
        self.assertEqual(mapping.local_status('desconocido', 'x'), 'x')


# ----------------------------------------------------------------------
# Proveedor
# ----------------------------------------------------------------------

@mock.patch('apps.billing.services.nexconnect.provider.ECFSubmission.objects.create')
@mock.patch.object(Invoice, 'save')
class ProviderTests(SimpleTestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(dgii_environment='testecf', ecf_provider='nexconnect',
                                      ecf_provider_api_key=encrypt_secret(TEST_KEY))
        self.invoice = make_invoice()
        items = make_items(self.invoice)
        patcher = mock.patch.object(mapping, 'build_invoice_payload',
                                    side_effect=lambda inv: _real_build(inv, items=items))
        patcher.start()
        self.addCleanup(patcher.stop)

    def provider(self, *responses):
        client, session = make_client(*responses)
        return NexConnectProvider(self.tenant, client=client), session

    def test_factory_returns_nexconnect_by_default(self, *_):
        self.assertIsInstance(get_ecf_provider(self.tenant), NexConnectProvider)
        self.assertIsInstance(get_ecf_provider(SimpleNamespace(ecf_provider='')), NexConnectProvider)

    def test_submit_updates_invoice(self, save, log):
        provider, session = self.provider(FakeResponse(201, signed_response()))
        result = provider.submit_invoice(self.invoice)

        self.assertEqual(session.calls[0]['headers']['Idempotency-Key'],
                         'crediflux-invoice-11111111-2222-3333-4444-555555555555')
        self.assertEqual(result['ncf'], 'E310000000007')
        self.assertEqual(result['status'], 'signed')
        self.assertEqual(self.invoice.encf_number, 'E310000000007')
        self.assertEqual(self.invoice.status, 'signed')
        self.assertEqual(self.invoice.security_code, 'AbC123')
        self.assertEqual(self.invoice.signed_xml, '<ECF>firmado</ECF>')
        self.assertEqual(self.invoice.dgii_response['provider'], 'nexconnect')
        self.assertEqual(self.invoice.dgii_response['id'], NX_ID)
        self.assertNotIn('xml_signed_b64', self.invoice.dgii_response)
        self.assertIsNotNone(self.invoice.dgii_submitted_at)
        self.assertIn('encf_number', save.call_args.kwargs['update_fields'])
        self.assertEqual(log.call_args.kwargs['action'], 'submit')
        self.assertEqual(log.call_args.kwargs['http_status_code'], 201)

    def test_submit_twice_is_refused(self, save, log):
        provider, _ = self.provider(FakeResponse(201, signed_response()))
        provider.submit_invoice(self.invoice)
        with self.assertRaisesMessage(ECFProviderError, 'ya fue emitida'):
            provider.submit_invoice(self.invoice)

    def test_submit_requires_emittable_status(self, save, log):
        provider, session = self.provider()
        self.invoice.status = 'accepted'
        with self.assertRaises(ECFProviderError):
            provider.submit_invoice(self.invoice)
        self.assertEqual(session.calls, [])

    def test_submit_error_is_logged_and_invoice_untouched(self, save, log):
        provider, _ = self.provider(FakeResponse(403, {'detail': 'x', 'code': 'clave_de_pruebas'}))
        with self.assertRaisesMessage(ECFProviderError, 'emisor de producción'):
            provider.submit_invoice(self.invoice)
        self.assertEqual(self.invoice.status, 'draft')
        self.assertFalse(self.invoice.encf_number)
        save.assert_not_called()
        self.assertEqual(log.call_args.kwargs['response_status'], 'error')
        self.assertEqual(log.call_args.kwargs['http_status_code'], 403)

    def test_submit_idempotency_conflict(self, save, log):
        provider, _ = self.provider(FakeResponse(409, {'detail': 'conflict'}))
        with self.assertRaisesMessage(ECFProviderError, 'conflicto de idempotencia'):
            provider.submit_invoice(self.invoice)

    def test_query_status(self, save, log):
        provider, session = self.provider(
            FakeResponse(201, signed_response()),
            FakeResponse(200, {'id': NX_ID, 'status': 'accepted', 'dgii_tracking_id': 'TRK-1',
                               'environment': 'testecf'}),
        )
        provider.submit_invoice(self.invoice)
        result = provider.query_status(self.invoice)

        self.assertEqual(session.calls[1]['url'], f'http://nexconnect.test/v1/invoices/{NX_ID}/status')
        self.assertEqual(result['status'], 'accepted')
        self.assertTrue(result['is_final'])
        self.assertEqual(self.invoice.status, 'accepted')
        self.assertEqual(self.invoice.dgii_trackid, 'TRK-1')
        self.assertEqual(self.invoice.dgii_response['ncf'], 'E310000000007')  # se conserva lo previo
        self.assertEqual(log.call_args.kwargs['trackid'], 'TRK-1')

    def test_query_rejected(self, save, log):
        provider, _ = self.provider(
            FakeResponse(201, signed_response()),
            FakeResponse(200, {'id': NX_ID, 'status': 'rejected', 'dgii_error_code': '1',
                               'dgii_error_message': 'RNC inválido'}),
        )
        provider.submit_invoice(self.invoice)
        provider.query_status(self.invoice)
        self.assertEqual(self.invoice.status, 'rejected')
        self.assertEqual(self.invoice.dgii_response['dgii_error_message'], 'RNC inválido')

    def test_query_without_emission(self, save, log):
        provider, _ = self.provider()
        with self.assertRaises(ECFProviderError):
            provider.query_status(self.invoice)

    def test_cancel_not_supported(self, save, log):
        provider, _ = self.provider()
        with self.assertRaises(ECFProviderError):
            provider.cancel_invoice(self.invoice, 'x')

    def test_test_connection(self, save, log):
        provider, _ = self.provider(FakeResponse(200, {'legal_name': 'Prestamos SRL'}))
        result = provider.test_connection()
        self.assertEqual(result['status'], 'online')
        self.assertEqual(result['organization'], 'Prestamos SRL')
        self.assertTrue(result['test_key'])

    def test_test_connection_without_key(self, save, log):
        self.tenant.ecf_provider_api_key = None
        result = NexConnectProvider(self.tenant).test_connection()
        self.assertEqual(result['status'], 'not_configured')

    def test_test_connection_unauthorized(self, save, log):
        provider, _ = self.provider(FakeResponse(401, {'detail': 'Invalid API key'}))
        result = provider.test_connection()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['http_code'], 401)


_real_build = mapping.build_invoice_payload
