"""Auditoría, IA y ajustes del tenant sobre códigos de permiso (D6, Task 10)."""
import pytest

from apps.audit.models import AuditLog
from tests.authz_helpers import cambiar_rol


def _registro(tenant, user):
    return AuditLog.log(
        tenant=tenant, user=user, action='create', model_name='Customer', object_repr='registro',
    )


def test_stats_de_auditoria_exige_settings_audit(api_client, user_factory, tenant_schema):
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/audit/stats/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.audit'
    cambiar_rol(tenant_schema, 'viewer', dar=['settings.audit'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.get('/api/audit/stats/').status_code == 200


def test_lista_y_detalle_de_auditoria_siguen_a_settings_audit(api_client, user_factory, tenant_schema):
    registro = _registro(tenant_schema, user_factory(role='collector'))
    detalle = f'/api/audit/{registro.id}/'

    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.get(detalle).status_code == 200
    ids = {str(r['id']) for r in api_client.get('/api/audit/').json()['results']}
    assert str(registro.id) in ids

    cambiar_rol(tenant_schema, 'manager', quitar=['settings.audit'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.get('/api/audit/stats/').status_code == 403
    assert api_client.get(detalle).status_code == 404  # fuera de alcance: queryset vacío
    assert api_client.get('/api/audit/').json()['results'] == []


@pytest.mark.parametrize('metodo, url', [
    ('put', '/api/ai/config/'),
    ('patch', '/api/tenants/settings/'),
])
def test_editar_ajustes_e_ia_exige_settings_edit(api_client, user_factory, tenant_schema, metodo, url):
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = getattr(api_client, metodo)(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.edit'
    cambiar_rol(tenant_schema, 'manager', dar=['settings.edit'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert getattr(api_client, metodo)(url, {}, format='json').status_code == 200


def test_leer_config_ia_exige_settings_view(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['settings.view'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/ai/config/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.view'


def test_ajustes_de_la_financiera_se_leen_sin_codigo_pero_no_se_editan(
    api_client, user_factory, tenant_schema
):
    """R13: el shell lee los ajustes para cualquier miembro, aun con un rol sin settings.view."""
    cambiar_rol(tenant_schema, 'viewer', quitar=['settings.view', 'settings.edit'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.get('/api/tenants/settings/').status_code == 200
    resp = api_client.patch('/api/tenants/settings/', {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.edit'
