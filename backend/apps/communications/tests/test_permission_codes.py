"""Comunicaciones sobre códigos de permiso (D6, Task 10)."""
import inspect

import pytest
from rest_framework import viewsets

from apps.communications import views, views_whatsapp
from apps.users.models import Role

ACCIONES_CRUD = ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')
METODO_DE = {'list': 'get', 'retrieve': 'get', 'create': 'post', 'update': 'put',
             'partial_update': 'patch', 'destroy': 'delete'}
UUID = '00000000-0000-0000-0000-000000000000'


def _viewsets():
    for modulo in (views, views_whatsapp):
        for _, cls in inspect.getmembers(modulo, inspect.isclass):
            if issubclass(cls, viewsets.ViewSetMixin) and cls.__module__ == modulo.__name__:
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


def test_enviar_whatsapp_exige_comms_whatsapp(api_client, user_factory, tenant_schema):
    url = '/api/communications/whatsapp/conversations/18095550000/send/'
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.post(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.whatsapp'
    _cambiar(tenant_schema, 'viewer', dar=['comms.whatsapp'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.post(url, {}, format='json').status_code == 400


def test_tareas_leer_y_escribir_tienen_codigos_distintos(api_client, user_factory, tenant_schema):
    _cambiar(tenant_schema, 'manager', quitar=['comms.tasks'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.get('/api/communications/tasks/').status_code == 200
    resp = api_client.post('/api/communications/tasks/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.tasks'
    _cambiar(tenant_schema, 'manager', quitar=['comms.view'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = api_client.get('/api/communications/tasks/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.view'
