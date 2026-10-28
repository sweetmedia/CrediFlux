"""Caja sobre códigos de permiso (D6, Task 10).

La matriz (tests/test_authz_matrix.py) fija que los roles de sistema siguen pudiendo lo mismo;
aquí se comprueba que el chequeo mira el código y no el rol, y que cada acción de cada viewset
tiene su código (R12 niega lo demás).
"""
import pytest

from apps.cashbox import views
from tests.authz_helpers import UUID, cambiar_rol, comprobar_completitud, viewsets_de


@pytest.mark.parametrize('cls', viewsets_de(views), ids=lambda c: c.__name__)
def test_cada_accion_de_cada_viewset_tiene_su_codigo(cls):
    comprobar_completitud(cls)


def test_borrar_caja_exige_cashbox_registers(api_client, user_factory, tenant_schema):
    url = f'/api/cashbox/registers/{UUID}/'
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = api_client.delete(url)
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.registers'
    cambiar_rol(tenant_schema, 'manager', dar=['cashbox.registers'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.delete(url).status_code == 404


def test_abrir_y_cerrar_turno_tienen_codigos_distintos(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'cashier', quitar=['cashbox.close'])
    api_client.force_authenticate(user=user_factory(role='cashier'))
    assert api_client.post('/api/cashbox/sessions/open/', {}, format='json').status_code == 400
    resp = api_client.post(f'/api/cashbox/sessions/{UUID}/close/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.close'


def test_leer_cajas_exige_cashbox_view(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['cashbox.view'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    for url in ('/api/cashbox/registers/', '/api/cashbox/sessions/', '/api/cashbox/movements/'):
        resp = api_client.get(url)
        assert resp.status_code == 403 and resp.json()['required_permission'] == 'cashbox.view', url
