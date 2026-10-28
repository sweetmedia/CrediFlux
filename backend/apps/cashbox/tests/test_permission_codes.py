"""Caja sobre códigos de permiso (D6, Task 10).

La matriz (tests/test_authz_matrix.py) fija que los roles de sistema siguen pudiendo lo mismo;
aquí se comprueba que el chequeo mira el código y no el rol, y que cada acción de cada viewset
tiene su código (R12 niega lo demás).
"""
import inspect

import pytest
from rest_framework import viewsets

from apps.cashbox import views
from apps.users.models import Role

ACCIONES_CRUD = ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')
METODO_DE = {'list': 'get', 'retrieve': 'get', 'create': 'post', 'update': 'put',
             'partial_update': 'patch', 'destroy': 'delete'}
UUID = '00000000-0000-0000-0000-000000000000'


def _viewsets():
    for _, cls in inspect.getmembers(views, inspect.isclass):
        if issubclass(cls, viewsets.GenericViewSet) and cls.__module__ == views.__name__:
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


def test_borrar_caja_exige_cashbox_registers(api_client, user_factory, tenant_schema):
    url = f'/api/cashbox/registers/{UUID}/'
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = api_client.delete(url)
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.registers'
    _cambiar(tenant_schema, 'manager', dar=['cashbox.registers'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.delete(url).status_code == 404


def test_abrir_y_cerrar_turno_tienen_codigos_distintos(api_client, user_factory, tenant_schema):
    _cambiar(tenant_schema, 'cashier', quitar=['cashbox.close'])
    api_client.force_authenticate(user=user_factory(role='cashier'))
    assert api_client.post('/api/cashbox/sessions/open/', {}, format='json').status_code == 400
    resp = api_client.post(f'/api/cashbox/sessions/{UUID}/close/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.close'


def test_leer_cajas_exige_cashbox_view(api_client, user_factory, tenant_schema):
    _cambiar(tenant_schema, 'viewer', quitar=['cashbox.view'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    for url in ('/api/cashbox/registers/', '/api/cashbox/sessions/', '/api/cashbox/movements/'):
        resp = api_client.get(url)
        assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.view', url
