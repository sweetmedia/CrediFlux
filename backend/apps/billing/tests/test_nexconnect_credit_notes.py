"""
Tests de la anulación de e-CF vía NexConnect (Nota de Crédito E34).

Sin base de datos, como ``test_nexconnect``: Invoices sin guardar, con ``save``,
``ECFSubmission.objects.create``, las consultas y las transacciones parcheadas.
"""
import contextlib
import json
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase
from djmoney.money import Money
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.users.permissions_catalog import DEFAULT_ROLE_PERMISSIONS
from apps.billing import views as billing_views
from apps.billing.models import ECFSubmission, Invoice, InvoiceItem
from apps.billing.services.ecf_provider import ECFProviderError
from apps.billing.services.nexconnect import mapping, provider as provider_module
from apps.billing.services.nexconnect.provider import NexConnectProvider
from apps.core.crypto import encrypt_secret

from .test_nexconnect import NX_ID, TEST_KEY, FakeResponse, make_client, make_invoice, make_items

_real_build = mapping.build_invoice_payload
NC_NX_ID = '7a0c1e6a-0000-4000-8000-0000000000e3'
NOTE_ID = uuid.UUID('99999999-8888-7777-6666-555555555555')


class ItemsDescriptor:
    """Sustituye ``Invoice.items`` (reverse FK) por listas en memoria."""

    def __init__(self):
        self.by_invoice = {}

    def __get__(self, instance, owner):
        if instance is None:
            return self
        items = self.by_invoice.get(instance.id, [])
        return SimpleNamespace(all=lambda: _Items(items))


class _Items(list):
    def order_by(self, *_):
        return self


def emitted_original(**overrides):
    fields = dict(status='accepted', dgii_status='accepted', encf_number='E310000000007',
                  dgii_response={'provider': 'nexconnect', 'id': NX_ID, 'status': 'accepted'})
    fields.update(overrides)
    return make_invoice(**fields)


def make_note(original, **overrides):
    fields = dict(id=NOTE_ID, ecf_type='34', status='draft', payment_method='01',
                  notes=f'Anulación de {original.encf_number}: Pago revertido')
    fields.update(overrides)
    note = make_invoice(**fields)
    note.reference_invoice = original
    return note


def copy_items(items, invoice):
    return [InvoiceItem(invoice=invoice, line_number=i.line_number, description=i.description,
                        quantity=i.quantity, unit_price=i.unit_price,
                        discount_amount=i.discount_amount, itbis_rate=i.itbis_rate)
            for i in items]


def nc_signed_response(**overrides):
    data = {'id': NC_NX_ID, 'ncf': 'E340000000003', 'ecf_type': 34, 'status': 'signed',
            'dgii_tracking_id': '', 'codigo_seguridad': 'Zx9Yw8'}
    data.update(overrides)
    return data


class CreditNoteBase(SimpleTestCase):

    def setUp(self):
        self.tenant = SimpleNamespace(dgii_environment='testecf', ecf_provider='nexconnect',
                                      ecf_provider_api_key=encrypt_secret(TEST_KEY))
        self.original = emitted_original()
        self.original_items = make_items(self.original)
        self.note = make_note(self.original)
        self.note_items = copy_items(self.original_items, self.note)

        self.items = ItemsDescriptor()
        self.items.by_invoice = {self.original.id: self.original_items, self.note.id: self.note_items}
        self.logged = []
        patches = [
            mock.patch.object(Invoice, 'items', self.items),
            mock.patch.object(Invoice, 'save', autospec=True),
            mock.patch.object(ECFSubmission.objects, 'create',
                              side_effect=lambda **kw: self.logged.append(kw)),
            mock.patch.object(provider_module.transaction, 'atomic',
                              lambda *a, **k: contextlib.nullcontext()),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def provider(self, *responses):
        client, session = make_client(*responses)
        return NexConnectProvider(self.tenant, client=client), session


# ----------------------------------------------------------------------
# Mapeo
# ----------------------------------------------------------------------

class CreditNoteMappingTests(CreditNoteBase):

    def test_full_credit_is_cancellation(self):
        self.assertEqual(mapping.credit_note_indicator(self.note_items, self.original_items),
                         mapping.INDICADOR_NC_ANULACION)

    def test_partial_credit_is_discount(self):
        partial = self.note_items[:1]
        self.assertEqual(mapping.credit_note_indicator(partial, self.original_items),
                         mapping.INDICADOR_NC_DESCUENTO)

    def test_cancellation_payload(self):
        payload = _real_build(self.note)
        self.assertEqual(payload['ecf_type'], 34)
        self.assertEqual(payload['ncf_modificado'], 'E310000000007')
        self.assertEqual(payload['indicador_nota_credito'], 1)
        self.assertEqual(payload['cancellation_reason'], 'Anulación de E310000000007: Pago revertido')
        self.assertEqual(payload['tipo_pago'], mapping.TIPO_PAGO_CONTADO)
        self.assertNotIn('fecha_limite_pago', payload)
        self.assertEqual(len(payload['lines']), 2)
        # Determinista: el reintento manda el mismo cuerpo (Idempotency-Key).
        self.assertEqual(json.dumps(payload, sort_keys=True), json.dumps(_real_build(self.note), sort_keys=True))

    def test_discount_payload_has_no_cancellation_reason(self):
        self.items.by_invoice[self.note.id] = self.note_items[:1]
        payload = _real_build(self.note)
        self.assertEqual(payload['indicador_nota_credito'], 2)
        self.assertNotIn('cancellation_reason', payload)

    def test_other_types_have_no_indicator(self):
        payload = _real_build(self.original)
        self.assertNotIn('indicador_nota_credito', payload)
        self.assertNotIn('ncf_modificado', payload)


# ----------------------------------------------------------------------
# cancel_invoice
# ----------------------------------------------------------------------

class CancelInvoiceTests(CreditNoteBase):

    def setUp(self):
        super().setUp()
        fake_invoices = mock.MagicMock()
        fake_invoices.select_for_update.return_value.get.return_value = self.original
        p = mock.patch.object(provider_module.Invoice, 'objects', fake_invoices)
        p.start()
        self.addCleanup(p.stop)

    def patch_helpers(self, live=None):
        live_p = mock.patch.object(NexConnectProvider, '_live_cancellation_note', return_value=live)
        build_p = mock.patch.object(NexConnectProvider, '_build_cancellation_note',
                                    return_value=self.note)
        live_mock, build_mock = live_p.start(), build_p.start()
        self.addCleanup(live_p.stop)
        self.addCleanup(build_p.stop)
        return live_mock, build_mock

    def test_validations(self):
        provider, session = self.provider()
        cases = [
            (self.original, ''),
            (make_note(self.original), 'x'),
            (make_invoice(status='accepted'), 'x'),  # no emitida por NexConnect
            (emitted_original(status='cancelled'), 'x'),
            (emitted_original(status='submitted'), 'x'),
            (emitted_original(status='rejected'), 'x'),
        ]
        for invoice, reason in cases:
            with self.assertRaises(ECFProviderError, msg=(invoice.status, invoice.ecf_type, reason)):
                provider.cancel_invoice(invoice, reason)
        self.assertEqual(session.calls, [])

    def test_creates_and_emits_credit_note(self):
        _, build = self.patch_helpers(live=None)
        provider, session = self.provider(FakeResponse(201, nc_signed_response()))
        result = provider.cancel_invoice(self.original, '  Pago revertido ')

        build.assert_called_once_with(self.original, 'Pago revertido')
        call = session.calls[0]
        self.assertEqual(call['url'], 'http://nexconnect.test/v1/invoices')
        self.assertEqual(call['headers']['Idempotency-Key'], f'crediflux-invoice-{NOTE_ID}')
        self.assertEqual(call['json']['ncf_modificado'], 'E310000000007')
        self.assertEqual(call['json']['indicador_nota_credito'], 1)
        self.assertEqual(result['ncf'], 'E340000000003')
        self.assertTrue(result['created'])
        self.assertEqual(result['credit_note_id'], str(NOTE_ID))
        # La original NO se anula hasta que la DGII acepte la nota.
        self.assertEqual(self.original.status, 'accepted')
        self.assertEqual(self.logged[-1]['action'], 'cancel')
        self.assertEqual(self.logged[-1]['invoice'], self.original)

    def test_draft_note_from_failed_attempt_is_resubmitted(self):
        _, build = self.patch_helpers(live=self.note)
        provider, session = self.provider(FakeResponse(201, nc_signed_response()))
        result = provider.cancel_invoice(self.original, 'otra vez')
        build.assert_not_called()
        self.assertFalse(result['created'])
        self.assertEqual(session.calls[0]['headers']['Idempotency-Key'], f'crediflux-invoice-{NOTE_ID}')

    def test_note_already_emitted_is_not_sent_again(self):
        self.note.status = 'submitted'
        self.note.dgii_status = 'submitted'
        self.note.encf_number = 'E340000000003'
        self.note.dgii_response = {'provider': 'nexconnect', 'id': NC_NX_ID}
        _, build = self.patch_helpers(live=self.note)
        provider, session = self.provider()
        result = provider.cancel_invoice(self.original, 'x')
        self.assertEqual(session.calls, [])
        build.assert_not_called()
        self.assertIn('E340000000003', result['message'])

    def test_rejected_by_nexconnect_keeps_draft_for_retry(self):
        self.patch_helpers(live=None)
        provider, _ = self.provider(FakeResponse(400, {'detail': 'Sólo quedan RD$0.00 por acreditar',
                                                       'code': 'nc_tope_total'}))
        with self.assertRaises(ECFProviderError):
            provider.cancel_invoice(self.original, 'x')
        self.assertEqual(self.note.status, 'draft')
        self.assertEqual(self.original.status, 'accepted')


# ----------------------------------------------------------------------
# La original pasa a anulada cuando la E34 queda aceptada
# ----------------------------------------------------------------------

class ReferenceCancellationTests(CreditNoteBase):

    def emitted_note(self):
        self.note.status = 'submitted'
        self.note.dgii_status = 'submitted'
        self.note.encf_number = 'E340000000003'
        self.note.dgii_response = {'provider': 'nexconnect', 'id': NC_NX_ID}
        return self.note

    def test_accepted_note_cancels_original(self):
        note = self.emitted_note()
        provider, _ = self.provider(FakeResponse(200, {'id': NC_NX_ID, 'status': 'accepted'}))
        provider.query_status(note)
        self.assertEqual(note.status, 'accepted')
        self.assertEqual(self.original.status, 'cancelled')
        self.assertEqual(self.original.dgii_status, 'cancelled')
        self.assertEqual(self.original.dgii_response['cancelled_by_ncf'], 'E340000000003')
        self.assertEqual(self.original.dgii_response['id'], NX_ID)
        self.assertIn({'action': 'cancel', 'invoice': self.original},
                      [{'action': kw['action'], 'invoice': kw['invoice']} for kw in self.logged])

    def test_pending_or_rejected_note_does_not_cancel(self):
        for nx_status in ('submitted', 'rejected'):
            note = self.emitted_note()
            provider, _ = self.provider(FakeResponse(200, {'id': NC_NX_ID, 'status': nx_status}))
            provider.query_status(note)
            self.assertEqual(self.original.status, 'accepted', nx_status)

    def test_partial_note_does_not_cancel(self):
        self.items.by_invoice[self.note.id] = self.note_items[:1]
        note = self.emitted_note()
        provider, _ = self.provider(FakeResponse(200, {'id': NC_NX_ID, 'status': 'accepted'}))
        provider.query_status(note)
        self.assertEqual(self.original.status, 'accepted')

    def test_already_cancelled_original_is_left_alone(self):
        self.original.status = 'cancelled'
        note = self.emitted_note()
        provider, _ = self.provider(FakeResponse(200, {'id': NC_NX_ID, 'status': 'accepted'}))
        provider.query_status(note)
        self.assertEqual([kw['action'] for kw in self.logged], ['query_status'])


class BuildCancellationNoteTests(CreditNoteBase):

    def test_copies_original(self):
        created = {}

        def create(**kwargs):
            created.update(kwargs)
            return Invoice(id=NOTE_ID, **kwargs)

        with mock.patch.object(provider_module.Invoice.objects, 'create', side_effect=create), \
                mock.patch.object(provider_module.InvoiceItem.objects, 'bulk_create') as bulk:
            self.original.total = Money('1823.62', 'DOP')
            note = NexConnectProvider._build_cancellation_note(self.original, 'Pago revertido')

        self.assertEqual(created['ecf_type'], '34')
        self.assertIs(created['reference_invoice'], self.original)
        self.assertEqual(created['payment_method'], '01')
        self.assertEqual(created['comprador_rnc'], '101000001')
        self.assertEqual(created['total'], Money('1823.62', 'DOP'))
        self.assertEqual(created['notes'], 'Anulación de E310000000007: Pago revertido')
        lines = bulk.call_args.args[0]
        self.assertEqual([l.description for l in lines], [i.description for i in self.original_items])
        self.assertTrue(all(l.invoice is note for l in lines))
        self.assertEqual(lines[1].quantity, Decimal('2.0000'))

    def test_anonymous_original_takes_buyer_from_customer(self):
        """NexConnect exige comprador en la E34 aunque la E32 original fuera anónima."""
        original = emitted_original(ecf_type='32', comprador_rnc='', comprador_razon_social='')
        customer = SimpleNamespace(id_number='001-0000001-1', get_full_name=lambda: 'Ana Pérez')
        original.customer_id = uuid.uuid4()
        with mock.patch.object(Invoice, 'customer', customer):
            self.assertEqual(NexConnectProvider._credit_note_buyer(original),
                             ('00100000011', 'Ana Pérez'))
        self.assertEqual(NexConnectProvider._credit_note_buyer(self.original),
                         ('101000001', 'CLIENTE EJEMPLO SRL'))


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------

class CancelEndpointTests(SimpleTestCase):

    def call(self, data):
        request = APIRequestFactory().post('/api/billing/ecf-provider/cancel/', data, format='json')
        user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False,
                               is_tenant_owner=False, role='accountant',
                               _cf_perms=frozenset(DEFAULT_ROLE_PERMISSIONS['accountant']))
        force_authenticate(request, user=user)
        view = billing_views.ECFProviderViewSet.as_view({'post': 'cancel_invoice'}, throttle_classes=[])
        return view(request)

    def test_requires_reason(self):
        self.assertEqual(self.call({'invoice_id': str(NOTE_ID)}).status_code, 400)
        self.assertEqual(self.call({'reason': 'x'}).status_code, 400)

    def test_calls_provider(self):
        invoice = make_invoice()
        fake_provider = mock.Mock()
        fake_provider.cancel_invoice.return_value = {'ncf': 'E340000000003', 'status': 'signed'}
        with mock.patch.object(Invoice.objects, 'get', return_value=invoice), \
                mock.patch('apps.billing.services.ecf_provider.get_ecf_provider', return_value=fake_provider):
            response = self.call({'invoice_id': str(invoice.id), 'reason': 'Pago revertido'})
        self.assertEqual(response.status_code, 200)
        fake_provider.cancel_invoice.assert_called_once_with(invoice, 'Pago revertido')

    def call_failing(self, error):
        fake_provider = mock.Mock()
        fake_provider.cancel_invoice.side_effect = error
        with mock.patch.object(Invoice.objects, 'get', return_value=make_invoice()), \
                mock.patch('apps.billing.services.ecf_provider.get_ecf_provider', return_value=fake_provider):
            return self.call({'invoice_id': str(NOTE_ID), 'reason': 'x'})

    def test_business_rule_error_is_400(self):
        response = self.call_failing(ECFProviderError('Solo se puede anular una factura aceptada'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('aceptada', response.data['error'])

    def test_nexconnect_down_is_502(self):
        from apps.billing.services.nexconnect.client import NexConnectError
        error = ECFProviderError('NexConnect no disponible')
        error.__cause__ = NexConnectError('Service Unavailable', status_code=503)
        self.assertEqual(self.call_failing(error).status_code, 502)
