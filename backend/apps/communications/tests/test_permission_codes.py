"""Comunicaciones sobre códigos de permiso (D6, Task 10)."""
import pytest

from apps.communications import views, views_whatsapp
from tests.authz_helpers import UUID, cambiar_rol, comprobar_completitud, viewsets_de


@pytest.mark.parametrize('cls', viewsets_de(views, views_whatsapp), ids=lambda c: c.__name__)
def test_cada_accion_de_cada_viewset_tiene_su_codigo(cls):
    comprobar_completitud(cls)


def test_enviar_whatsapp_exige_comms_whatsapp(api_client, user_factory, tenant_schema):
    url = '/api/communications/whatsapp/conversations/18095550000/send/'
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.post(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.whatsapp'
    cambiar_rol(tenant_schema, 'viewer', dar=['comms.whatsapp'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.post(url, {}, format='json').status_code == 400


def test_tareas_leer_y_escribir_tienen_codigos_distintos(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'manager', quitar=['comms.tasks'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.get('/api/communications/tasks/').status_code == 200
    resp = api_client.post('/api/communications/tasks/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.tasks'
    cambiar_rol(tenant_schema, 'manager', quitar=['comms.view'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = api_client.get('/api/communications/tasks/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'comms.view'
