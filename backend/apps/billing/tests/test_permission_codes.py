"""Facturación sobre códigos de permiso (D6, Task 10): cada acción tiene su código y el
chequeo mira el código, no el rol."""
import inspect

import pytest
from rest_framework import viewsets

from apps.billing import views
from apps.users.models import Role

ACCIONES_CRUD = ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')
METODO_DE = {'list': 'get', 'retrieve': 'get', 'create': 'post', 'update': 'put',
             'partial_update': 'patch', 'destroy': 'delete'}
UUID = '00000000-0000-0000-0000-000000000000'


def _viewsets():
    for _, cls in inspect.getmembers(views, inspect.isclass):
        if issubclass(cls, viewsets.ViewSetMixin) and cls.__module__ == views.__name__:
            yield cls


def _acciones(cls):
    acciones = {a for a in ACCIONES_CRUD if hasattr(cls, a) and METODO_DE[a] in cls.http_method_names}
    return acciones | {a.__name__ for a in cls.get_extra_actions()}


@pytest.mark.parametrize('cls', list(_viewsets()), ids=lambda c: c.__name__)
def test_cada_accion_de_cada_viewset_tiene_su_codigo(cls):
    from apps.users.permissions_catalog import ALL_CODES

    mapa = getattr(cls, 'permission_codes', None)
    assert mapa, f'{cls.__name__} sin permission_codes'
    assert set(mapa) == _acciones(cls), set(mapa) ^ _acciones(cls)
    assert set(mapa.values()) <= ALL_CODES


def _cambiar(tenant, rol, quitar=(), dar=()):
    role = Role.objects.get(tenant=tenant, key=rol)
    role.permissions = sorted((set(role.permissions) - set(quitar)) | set(dar))
    role.save()


def test_config_ecf_get_con_view_y_patch_con_billing_config(api_client, user_factory, tenant_schema):
    url = '/api/billing/ecf-provider/config/'
    api_client.force_authenticate(user=user_factory(role='accountant'))
    assert api_client.get(url).status_code == 200
    resp = api_client.patch(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.config'
    _cambiar(tenant_schema, 'accountant', dar=['billing.config'])
    api_client.force_authenticate(user=user_factory(role='accountant'))
    assert api_client.patch(url, {}, format='json').status_code == 200


def test_acciones_dgii_exigen_billing_submit_y_firmar_billing_sign(
    api_client, user_factory, tenant_schema
):
    _cambiar(tenant_schema, 'accountant', quitar=['billing.submit'])
    api_client.force_authenticate(user=user_factory(role='accountant'))
    resp = api_client.get(f'/api/billing/invoices/{UUID}/dgii-status/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.submit'
    assert api_client.post(f'/api/billing/invoices/{UUID}/sign/', {}, format='json').status_code != 403


def test_reportes_dgii_exigen_billing_reports(api_client, user_factory, tenant_schema):
    _cambiar(tenant_schema, 'viewer', quitar=['billing.reports'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/billing/dgii-reports/607/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.reports'
