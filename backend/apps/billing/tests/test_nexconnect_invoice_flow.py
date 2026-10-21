"""
Tests de los endpoints de factura para tenants con NexConnect.

Sin base de datos, como en ``test_nexconnect``: ``get_object`` devuelve una
Invoice sin guardar, ``save`` y ``ECFSubmission.objects.create`` parcheados, y
NexConnect simulado con ``FakeSession``.
"""
import uuid
from types import SimpleNamespace
from unittest import mock

import requests
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.billing import views
from apps.billing.models import ECFSubmission, Invoice
from apps.billing.serializers import (
    ECFSubmissionSerializer,
    InvoiceDetailSerializer,
)
from apps.billing.services.nexconnect import mapping
from apps.billing.services.nexconnect.credentials import credentials_for_tenant
from apps.billing.services.nexconnect.provider import NexConnectProvider
from apps.core.crypto import encrypt_secret, is_encrypted

from .test_nexconnect import (
    NX_ID, TEST_KEY, FakeResponse, make_client, make_invoice, make_items, signed_response,
)

factory = APIRequestFactory()
NOTE_UUID = uuid.UUID('99999999-8888-7777-6666-555555555555')


def make_tenant(**overrides):
    fields = dict(ecf_provider='nexconnect', dgii_environment='testecf',
                  ecf_provider_api_key=encrypt_secret(TEST_KEY),
                  nexconnect_webhook_id='', save=mock.Mock())
    fields.update(overrides)
    return SimpleNamespace(**fields)


def make_user(**overrides):
    fields = dict(is_authenticated=True, is_superuser=False, is_tenant_owner=False, role='loan_officer')
    fields.update(overrides)
    return SimpleNamespace(**fields)


class FakeDetailSerializer:
    """InvoiceDetailSerializer toca ``items`` (consulta a la DB); aquí basta el estado."""

    def __init__(self, invoice, context=None):
        self.data = {'id': str(invoice.id), 'status': invoice.status, 'encf_number': invoice.encf_number}


def call(viewset, action_map, method='post', path='/x/', data=None, user=None, **kwargs):
    request = getattr(factory, method)(path, data or {}, format='json')
    force_authenticate(request, user=user or make_user())
    # Sin throttling: usa la caché (Redis), que aquí no existe.
    return viewset.as_view(action_map, throttle_classes=[])(request, **kwargs)


class TenantPatchMixin:
    """Fija el tenant de la petición y deja NexConnect contestando con ``responses``."""

    def use_tenant(self, tenant):
        patcher = mock.patch.object(views, 'current_tenant', return_value=tenant)
        patcher.start()
        self.addCleanup(patcher.stop)

    def use_nexconnect(self, tenant, *responses):
        client, session = make_client(*responses)
        provider = NexConnectProvider(tenant, client=client)
        patcher = mock.patch.object(views, 'get_ecf_provider', return_value=provider)
        patcher.start()
        self.addCleanup(patcher.stop)
        return session


# ----------------------------------------------------------------------
# Emitir / actualizar estado
# ----------------------------------------------------------------------

@mock.patch('apps.billing.services.nexconnect.provider.ECFSubmission.objects.create')
@mock.patch.object(Invoice, 'save')
@mock.patch.object(views, 'InvoiceDetailSerializer', FakeDetailSerializer)
class EmitEndpointTests(TenantPatchMixin, SimpleTestCase):

    def setUp(self):
        self.tenant = make_tenant()
        self.use_tenant(self.tenant)
        self.invoice = make_invoice()
        items = make_items(self.invoice)
        patcher = mock.patch.object(mapping, 'build_invoice_payload',
                                    side_effect=lambda inv: _real_build(inv, items=items))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(views.InvoiceViewSet, 'get_object', return_value=self.invoice)
        patcher.start()
        self.addCleanup(patcher.stop)

    def emit(self):
        return call(views.InvoiceViewSet, {'post': 'emit'}, pk=str(self.invoice.id))

    def refresh(self):
        return call(views.InvoiceViewSet, {'post': 'refresh_status'}, pk=str(self.invoice.id))

    def test_emit(self, save, log):
        session = self.use_nexconnect(self.tenant, FakeResponse(201, signed_response()))
        response = self.emit()

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(session.calls[0]['url'], 'http://nexconnect.test/v1/invoices')
        self.assertEqual(response.data['ncf'], 'E310000000007')
        self.assertEqual(response.data['status'], 'signed')
        self.assertEqual(response.data['invoice']['status'], 'signed')
        self.assertEqual(self.invoice.security_code, 'AbC123')
        self.assertEqual(log.call_args.kwargs['action'], 'submit')

    def test_emit_uses_tenant_from_request(self, save, log):
        with mock.patch.object(views, 'get_ecf_provider') as factory_:
            factory_.return_value.submit_invoice.return_value = {'status': 'signed'}
            self.emit()
        factory_.assert_called_once_with(self.tenant)

    def test_emit_refused_for_direct_tenant(self, save, log):
        self.tenant.ecf_provider = 'direct'
        session = self.use_nexconnect(self.tenant)
        response = self.emit()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'provider_not_nexconnect')
        self.assertEqual(session.calls, [])

    def test_emit_twice_is_400(self, save, log):
        self.use_nexconnect(self.tenant, FakeResponse(201, signed_response()))
        self.emit()
        response = self.emit()
        self.assertEqual(response.status_code, 400)
        self.assertIn('ya fue emitida', response.data['error'])

    def test_emit_validation_error_is_400(self, save, log):
        self.use_nexconnect(self.tenant, FakeResponse(400, {'customer_rnc': ['RNC inválido']}))
        response = self.emit()
        self.assertEqual(response.status_code, 400)
        self.assertIn('customer_rnc: RNC inválido', response.data['error'])
        self.assertEqual(self.invoice.status, 'draft')

    def test_emit_nexconnect_down_is_502(self, save, log):
        self.use_nexconnect(self.tenant, requests.ConnectionError('refused'))
        response = self.emit()
        self.assertEqual(response.status_code, 502)

    def test_emit_nexconnect_5xx_is_502(self, save, log):
        self.use_nexconnect(self.tenant, FakeResponse(503, None, text='Service Unavailable'))
        self.assertEqual(self.emit().status_code, 502)

    def test_emit_without_api_key(self, save, log):
        self.tenant.ecf_provider_api_key = None
        with mock.patch.object(views, 'get_ecf_provider', return_value=NexConnectProvider(self.tenant)):
            response = self.emit()
        self.assertEqual(response.status_code, 400)
        self.assertIn('API key de NexConnect no configurada', response.data['error'])

    def test_refresh_status_accepted(self, save, log):
        session = self.use_nexconnect(
            self.tenant,
            FakeResponse(201, signed_response()),
            FakeResponse(200, {'id': NX_ID, 'status': 'accepted', 'dgii_tracking_id': 'TRK-1'}),
        )
        self.emit()
        response = self.refresh()

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(session.calls[1]['url'], f'http://nexconnect.test/v1/invoices/{NX_ID}/status')
        self.assertEqual(response.data['status'], 'accepted')
        self.assertTrue(response.data['is_final'])
        self.assertEqual(response.data['invoice']['status'], 'accepted')
        self.assertEqual(log.call_args.kwargs['action'], 'query_status')

    def test_refresh_status_pending(self, save, log):
        self.use_nexconnect(
            self.tenant,
            FakeResponse(201, signed_response()),
            FakeResponse(200, {'id': NX_ID, 'status': 'submitted'}),
        )
        self.emit()
        response = self.refresh()
        self.assertEqual(response.data['status'], 'submitted')
        self.assertFalse(response.data['is_final'])

    def test_refresh_status_not_emitted(self, save, log):
        session = self.use_nexconnect(self.tenant)
        response = self.refresh()
        self.assertEqual(response.status_code, 400)
        self.assertIn('no ha sido emitida vía NexConnect', response.data['error'])
        self.assertEqual(session.calls, [])

    def test_refresh_status_nexconnect_error_is_502(self, save, log):
        self.use_nexconnect(
            self.tenant,
            FakeResponse(201, signed_response()),
            FakeResponse(500, None, text='boom'),
        )
        self.emit()
        self.assertEqual(self.refresh().status_code, 502)


# ----------------------------------------------------------------------
# El flujo directo queda bloqueado para tenants NexConnect
# ----------------------------------------------------------------------

@mock.patch.object(Invoice, 'save')
class DirectFlowGuardTests(TenantPatchMixin, SimpleTestCase):

    def setUp(self):
        self.invoice = make_invoice()
        patcher = mock.patch.object(views.InvoiceViewSet, 'get_object', return_value=self.invoice)
        patcher.start()
        self.addCleanup(patcher.stop)

    def direct(self, action, method='post'):
        return call(views.InvoiceViewSet, {method: action}, method=method, pk=str(self.invoice.id))

    def test_direct_endpoints_refused_for_nexconnect(self, save):
        self.use_tenant(make_tenant())
        for action in ('generate_ecf', 'sign_ecf', 'submit_to_dgii'):
            with self.subTest(action=action):
                response = self.direct(action)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['code'], 'provider_nexconnect')
                self.assertIn('Emitir vía NexConnect', response.data['error'])
        save.assert_not_called()

    def test_default_provider_is_nexconnect(self, save):
        self.use_tenant(make_tenant(ecf_provider=''))
        self.assertEqual(self.direct('generate_ecf').status_code, 400)

    def test_direct_tenant_passes_the_guard(self, save):
        self.use_tenant(make_tenant(ecf_provider='direct'))
        self.invoice.status = 'draft'
        # Pasa la guarda y llega a la validación de estado del flujo directo.
        response = self.direct('sign_ecf')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'Solo se puede firmar una factura con XML generado')

    def test_dgii_status_refused_for_nexconnect_invoice(self, save):
        self.use_tenant(make_tenant(ecf_provider='direct'))
        self.invoice.dgii_response = {'provider': 'nexconnect', 'id': NX_ID}
        self.invoice.dgii_trackid = 'TRK-1'
        response = self.direct('check_dgii_status', method='get')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'provider_nexconnect')


# ----------------------------------------------------------------------
# Serializers
# ----------------------------------------------------------------------

class InvoiceSerializerTests(SimpleTestCase):

    def serializer(self, tenant):
        return InvoiceDetailSerializer(context={'tenant': tenant})

    def test_provider_follows_tenant(self):
        invoice = make_invoice()
        self.assertEqual(self.serializer(make_tenant()).get_ecf_provider(invoice), 'nexconnect')
        self.assertEqual(self.serializer(make_tenant(ecf_provider='direct')).get_ecf_provider(invoice), 'direct')
        self.assertEqual(self.serializer(make_tenant(ecf_provider=None)).get_ecf_provider(invoice), 'nexconnect')

    def test_invoice_emitted_by_nexconnect_stays_nexconnect(self):
        invoice = make_invoice(dgii_response={'provider': 'nexconnect', 'id': NX_ID})
        self.assertEqual(self.serializer(make_tenant(ecf_provider='direct')).get_ecf_provider(invoice),
                         'nexconnect')

    def test_is_final(self):
        s = self.serializer(make_tenant())
        for state in ('draft', 'generated', 'signed', 'submitted'):
            self.assertFalse(s.get_is_final(make_invoice(status=state)), state)
        for state in ('accepted', 'conditionally_accepted', 'rejected', 'cancelled'):
            self.assertTrue(s.get_is_final(make_invoice(status=state)), state)

    def test_dgii_error_message(self):
        s = self.serializer(make_tenant())
        invoice = make_invoice(status='rejected', dgii_response={
            'provider': 'nexconnect', 'status': 'rejected', 'dgii_error_message': 'RNC del comprador inválido'})
        self.assertEqual(s.get_dgii_error_message(invoice), 'RNC del comprador inválido')
        self.assertEqual(s.get_dgii_error_message(make_invoice(dgii_response=None)), '')

    def test_credit_notes(self):
        note = make_invoice(id=NOTE_UUID, ecf_type='34', encf_number='E340000000003', status='submitted')
        manager = mock.Mock()
        manager.all.return_value.order_by.return_value = [note]
        original = SimpleNamespace(credit_debit_notes=manager)
        self.assertEqual(self.serializer(make_tenant()).get_credit_notes(original), [{
            'id': str(NOTE_UUID), 'ecf_type': '34', 'encf_number': 'E340000000003',
            'status': 'submitted', 'status_display': 'Enviado a DGII', 'created_at': None,
        }])
        manager.all.return_value.order_by.assert_called_once_with('created_at')

    def test_fields_are_exposed(self):
        fields = InvoiceDetailSerializer.Meta.fields
        for name in ('ecf_provider', 'is_final', 'dgii_error_message', 'credit_notes',
                     'security_code', 'encf_number'):
            self.assertIn(name, fields)

    def test_webhook_submission_is_labelled(self):
        submission = ECFSubmission(invoice=make_invoice(), action='webhook', environment='testecf',
                                   response_status='accepted')
        data = ECFSubmissionSerializer(submission).data
        self.assertEqual(data['action'], 'webhook')
        self.assertEqual(data['action_display'], 'Webhook del proveedor')


# ----------------------------------------------------------------------
# Configuración del proveedor (ajustes)
# ----------------------------------------------------------------------

class ProviderConfigEndpointTests(TenantPatchMixin, SimpleTestCase):

    def setUp(self):
        self.tenant = make_tenant(ecf_provider_api_key=None)
        self.use_tenant(self.tenant)

    def get(self, user=None):
        return call(views.ECFProviderViewSet, {'get': 'config'}, method='get', user=user)

    def patch(self, data, user=None):
        return call(views.ECFProviderViewSet, {'patch': 'config'}, method='patch', data=data,
                    user=user or make_user(role='admin'))

    def test_get_without_key(self):
        data = self.get().data
        self.assertEqual(data['ecf_provider'], 'nexconnect')
        self.assertEqual(data['dgii_environment'], 'testecf')
        self.assertFalse(data['has_api_key'])
        self.assertIsNone(data['is_test_key'])
        self.assertIn({'value': 'direct', 'label': 'DGII Directo (certificado propio)'},
                      data['ecf_provider_choices'])
        self.assertEqual([c['value'] for c in data['dgii_environment_choices']], ['testecf', 'certecf', 'ecf'])

    def test_set_key_is_encrypted_and_never_returned(self):
        response = self.patch({'api_key': f' {TEST_KEY} '})

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(is_encrypted(self.tenant.ecf_provider_api_key))
        self.assertEqual(credentials_for_tenant(self.tenant).api_key, TEST_KEY)
        self.tenant.save.assert_called_once_with(update_fields=['ecf_provider_api_key'])
        self.assertTrue(response.data['has_api_key'])
        self.assertTrue(response.data['is_test_key'])
        self.assertNotIn('api_key', response.data)
        self.assertNotIn(TEST_KEY, str(response.data))
        self.assertNotIn(self.tenant.ecf_provider_api_key, str(response.data))

    def test_blank_key_keeps_the_stored_one(self):
        self.tenant.ecf_provider_api_key = encrypt_secret(TEST_KEY)
        response = self.patch({'api_key': '', 'dgii_environment': 'certecf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(credentials_for_tenant(self.tenant).api_key, TEST_KEY)
        self.assertEqual(self.tenant.dgii_environment, 'certecf')
        self.tenant.save.assert_called_once_with(update_fields=['dgii_environment'])

    def test_clear_key(self):
        self.tenant.ecf_provider_api_key = encrypt_secret(TEST_KEY)
        response = self.patch({'clear_api_key': True})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.tenant.ecf_provider_api_key)
        self.assertFalse(response.data['has_api_key'])

    def test_switch_provider(self):
        response = self.patch({'ecf_provider': 'direct'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.tenant.ecf_provider, 'direct')
        self.assertEqual(response.data['ecf_provider'], 'direct')

    def test_invalid_values(self):
        for data in ({'api_key': 'sk_live_otro'}, {'ecf_provider': 'otro'},
                     {'dgii_environment': 'prod'}, {'api_key': TEST_KEY, 'clear_api_key': True}):
            with self.subTest(data=data):
                self.assertEqual(self.patch(data).status_code, 400)
        self.tenant.save.assert_not_called()

    def test_only_owner_or_admin_can_change(self):
        response = self.patch({'ecf_provider': 'direct'}, user=make_user())
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tenant.ecf_provider, 'nexconnect')
        self.assertEqual(self.patch({'ecf_provider': 'direct'},
                                    user=make_user(is_tenant_owner=True)).status_code, 200)
        # Leer sí puede cualquiera autenticado.
        self.assertEqual(self.get(user=make_user()).status_code, 200)

    def test_provider_status_tests_the_tenant_connection(self):
        self.tenant.ecf_provider_api_key = encrypt_secret(TEST_KEY)
        client, _ = make_client(FakeResponse(200, {'legal_name': 'Prestamos SRL'}))
        with mock.patch.object(views, 'get_ecf_provider',
                               return_value=NexConnectProvider(self.tenant, client=client)) as factory_:
            response = call(views.ECFProviderViewSet, {'get': 'provider_status'}, method='get')
        factory_.assert_called_once_with(self.tenant)
        self.assertEqual(response.data['status'], 'online')
        self.assertEqual(response.data['organization'], 'Prestamos SRL')

    def test_provider_status_without_key(self):
        response = call(views.ECFProviderViewSet, {'get': 'provider_status'}, method='get')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'not_configured')


_real_build = mapping.build_invoice_payload
