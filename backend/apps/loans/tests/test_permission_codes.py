"""Préstamos, clientes, pagos y cobranza sobre códigos de permiso (D6, Task 9).

La matriz (tests/test_authz_matrix.py) fija que los roles de sistema siguen pudiendo lo mismo;
aquí se comprueba que el chequeo mira el código y no el rol: quitar o dar un código a un Role
cambia el resultado. Y que cada acción de cada viewset tiene su código (R12 niega lo demás).
"""
import inspect
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from rest_framework import viewsets

from apps.loans import views, views_geolocation
from apps.users.models import Role

HOST = 'tenant.test.localhost'
ACCIONES_CRUD = ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')
METODO_DE = {'list': 'get', 'retrieve': 'get', 'create': 'post', 'update': 'put',
             'partial_update': 'patch', 'destroy': 'delete'}


def _viewsets():
    for modulo in (views, views_geolocation):
        for _, cls in inspect.getmembers(modulo, inspect.isclass):
            if issubclass(cls, viewsets.GenericViewSet) and cls.__module__ == modulo.__name__:
                yield cls


def _acciones(cls):
    """Acciones enrutables: las CRUD que la clase define (y su método HTTP admite) y las @action."""
    acciones = {
        a for a in ACCIONES_CRUD
        if hasattr(cls, a) and METODO_DE[a] in cls.http_method_names
    }
    return acciones | {a.__name__ for a in cls.get_extra_actions()}


@pytest.mark.parametrize('cls', list(_viewsets()), ids=lambda c: c.__name__)
def test_cada_accion_de_cada_viewset_tiene_su_codigo(cls):
    from apps.users.permissions_catalog import ALL_CODES

    mapa = getattr(cls, 'permission_codes', None)
    assert mapa, f'{cls.__name__} sin permission_codes'
    assert set(mapa) == _acciones(cls), set(mapa) ^ _acciones(cls)
    assert set(mapa.values()) <= ALL_CODES


def _quitar(tenant, rol, *codigos):
    role = Role.objects.get(tenant=tenant, key=rol)
    role.permissions = [c for c in role.permissions if c not in codigos]
    role.save()


def _dar(tenant, rol, *codigos):
    role = Role.objects.get(tenant=tenant, key=rol)
    role.permissions = sorted(set(role.permissions) | set(codigos))
    role.save()


def test_aprobar_mira_loans_approve_no_el_rol(api_client, user_factory, loan_factory, tenant_schema):
    loan = loan_factory(status='active')
    url = f'/api/loans/{loan.pk}/approve/'

    _quitar(tenant_schema, 'loan_officer', 'loans.approve')
    api_client.force_authenticate(user=user_factory(role='loan_officer'))
    resp = api_client.post(url, {}, format='json')
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'loans.approve'
    # Rechazar sigue con su propio código.
    assert api_client.post(f'/api/loans/{loan.pk}/reject/', {}, format='json').status_code == 400

    _dar(tenant_schema, 'viewer', 'loans.approve')
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.post(url, {}, format='json').status_code == 400  # pasa: el préstamo no está pendiente


def test_cliente_crear_y_editar_tienen_codigos_distintos(api_client, user_factory, tenant_schema):
    _quitar(tenant_schema, 'manager', 'customers.create')
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = api_client.post('/api/loans/customers/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'customers.create'
    resp = api_client.patch('/api/loans/customers/00000000-0000-0000-0000-000000000000/', {}, format='json')
    assert resp.status_code == 404  # customers.edit sigue


def test_guarantor_check_exige_customers_view(api_client, user_factory, tenant_schema):
    url = '/api/loans/customers/guarantor-check/?id_number=00112345678'
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.get(url).status_code == 200
    _quitar(tenant_schema, 'viewer', 'customers.view')
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get(url)
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'customers.view'


def test_confirmar_pago_exige_payments_void(api_client, user_factory, tenant_schema):
    url = '/api/loans/payments/00000000-0000-0000-0000-000000000000/confirm/'
    api_client.force_authenticate(user=user_factory(role='cashier'))  # registra pagos, no anula
    resp = api_client.post(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'payments.void'
    _dar(tenant_schema, 'cashier', 'payments.void')
    api_client.force_authenticate(user=user_factory(role='cashier'))
    assert api_client.post(url, {}, format='json').status_code == 404


def test_reverso_sigue_siendo_solo_del_duenio_aunque_tenga_payments_void(
    api_client, user_factory, tenant_schema
):
    """R3: hasta Task 14 el reverso no se abre con payments.void."""
    from apps.loans.models import LoanPayment
    from moneyed import Money

    from tests.test_authz_matrix import _prestamo

    pago = LoanPayment.objects.create(
        loan=_prestamo(), amount=Money(Decimal('500.00'), 'DOP'),
        payment_method='bank_transfer', status='completed',
    )
    api_client.force_authenticate(user=user_factory(role='manager'))  # tiene payments.void
    resp = api_client.post(f'/api/loans/payments/{pago.pk}/reverse/', {'reason': 'x'}, format='json')
    assert resp.status_code == 403


def test_pagos_siguen_siendo_inmutables_405(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role='manager'))
    url = '/api/loans/payments/00000000-0000-0000-0000-000000000000/'
    assert api_client.patch(url, {}, format='json').status_code == 405
    assert api_client.delete(url).status_code == 405


def test_alcance_de_visitas_mira_collections_supervise(api_client, user_factory, tenant_schema):
    from apps.loans.models_geolocation import CollectorVisit
    from tests.test_authz_matrix import _cliente

    ajena = CollectorVisit.objects.create(
        collector=user_factory(role='collector'), customer=_cliente(),
        latitude=Decimal('18.4861000'), longitude=Decimal('-69.9312000'),
    )

    def ids(user):
        api_client.force_authenticate(user=user)
        data = api_client.get('/api/loans/collector-visits/').json()
        return {row['id'] for row in data.get('results', data)}

    assert str(ajena.pk) not in ids(user_factory(role='collector'))
    _dar(tenant_schema, 'collector', 'collections.supervise')
    assert str(ajena.pk) in ids(user_factory(role='collector'))
    _quitar(tenant_schema, 'manager', 'collections.supervise')
    assert str(ajena.pk) not in ids(user_factory(role='manager'))


def test_rol_propio_sin_lectura_no_ve_prestamos(api_client, user_factory, tenant_schema):
    _quitar(tenant_schema, 'viewer', 'loans.view')
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/loans/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'loans.view'


# --- Admin de Django: los guardas miran el código del catálogo ---------------------------------


def _staff(user_factory, role, perms):
    user = user_factory(is_staff=True, role=role)
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label='loans', codename__in=perms)
    )
    client = Client(HTTP_HOST=HOST)
    client.force_login(user)
    return client


def test_admin_acciones_del_ciclo_de_vida_por_codigo(user_factory, loan_factory, tenant_schema):
    loan_factory(status='pending', disbursement_date=None)
    _quitar(tenant_schema, 'loan_officer', 'loans.approve')
    client = _staff(user_factory, 'loan_officer', ('view_loan', 'change_loan'))
    content = client.get(reverse('admin:loans_loan_changelist')).content.decode()
    assert 'value="approve_loans"' not in content
    assert 'value="reject_loans"' in content
    assert 'value="disburse_loans"' in content


def test_admin_alta_y_edicion_de_prestamo_por_codigo(user_factory, tenant_schema):
    from apps.loans.admin import LoanAdmin
    from apps.loans.models import Loan
    from django.contrib import admin
    from django.test import RequestFactory

    _quitar(tenant_schema, 'loan_officer', 'loans.create')
    user = user_factory(is_staff=True, role='loan_officer')
    user.user_permissions.add(*Permission.objects.filter(
        content_type__app_label='loans', codename__in=('add_loan', 'change_loan')))
    user = type(user).objects.get(pk=user.pk)  # sin caché de permisos de modelo
    request = RequestFactory().get('/admin/')
    request.user = user
    model_admin = LoanAdmin(Loan, admin.site)
    assert not model_admin.has_add_permission(request)
    assert model_admin.has_change_permission(request)

    _dar(tenant_schema, 'viewer', 'loans.create', 'loans.edit')
    viewer = user_factory(is_staff=True, role='viewer')
    viewer.user_permissions.add(*Permission.objects.filter(
        content_type__app_label='loans', codename__in=('add_loan', 'change_loan')))
    request.user = type(viewer).objects.get(pk=viewer.pk)
    assert model_admin.has_add_permission(request)
    assert model_admin.has_change_permission(request)
