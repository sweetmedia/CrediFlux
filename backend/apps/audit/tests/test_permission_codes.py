"""Auditoría, IA y ajustes del tenant sobre códigos de permiso (D6, Task 10)."""
import pytest

from apps.users.models import Role


def _cambiar(tenant, rol, quitar=(), dar=()):
    role = Role.objects.get(tenant=tenant, key=rol)
    role.permissions = sorted((set(role.permissions) - set(quitar)) | set(dar))
    role.save()


def test_stats_de_auditoria_exige_settings_audit(api_client, user_factory, tenant_schema):
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/audit/stats/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.audit'
    _cambiar(tenant_schema, 'viewer', dar=['settings.audit'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    assert api_client.get('/api/audit/stats/').status_code == 200


def test_quitar_settings_audit_a_gerente_vacia_la_lista(api_client, user_factory, tenant_schema):
    _cambiar(tenant_schema, 'manager', quitar=['settings.audit'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert api_client.get('/api/audit/stats/').status_code == 403
    assert api_client.get(f'/api/audit/{"0" * 8}-0000-0000-0000-{"0" * 12}/').status_code == 404


@pytest.mark.parametrize('metodo, url', [
    ('put', '/api/ai/config/'),
    ('patch', '/api/tenants/settings/'),
])
def test_editar_ajustes_e_ia_exige_settings_edit(api_client, user_factory, tenant_schema, metodo, url):
    api_client.force_authenticate(user=user_factory(role='manager'))
    resp = getattr(api_client, metodo)(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.edit'
    _cambiar(tenant_schema, 'manager', dar=['settings.edit'])
    api_client.force_authenticate(user=user_factory(role='manager'))
    assert getattr(api_client, metodo)(url, {}, format='json').status_code == 200


@pytest.mark.parametrize('url', ['/api/ai/config/', '/api/tenants/settings/'])
def test_leer_ajustes_e_ia_exige_settings_view(api_client, user_factory, tenant_schema, url):
    _cambiar(tenant_schema, 'viewer', quitar=['settings.view'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get(url)
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'settings.view'
