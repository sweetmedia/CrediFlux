"""Facturación sobre códigos de permiso (D6, Task 10): cada acción tiene su código y el
chequeo mira el código, no el rol."""
import pytest

from apps.billing import views
from tests.authz_helpers import UUID, cambiar_rol, comprobar_completitud, viewsets_de


@pytest.mark.parametrize('cls', viewsets_de(views), ids=lambda c: c.__name__)
def test_cada_accion_de_cada_viewset_tiene_su_codigo(cls):
    comprobar_completitud(cls)


def test_config_ecf_get_con_view_y_patch_con_billing_config(api_client, user_factory, tenant_schema):
    url = '/api/billing/ecf-provider/config/'
    api_client.force_authenticate(user=user_factory(role='accountant'))
    assert api_client.get(url).status_code == 200
    resp = api_client.patch(url, {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.config'
    cambiar_rol(tenant_schema, 'accountant', dar=['billing.config'])
    api_client.force_authenticate(user=user_factory(role='accountant'))
    assert api_client.patch(url, {}, format='json').status_code == 200


def test_acciones_dgii_exigen_billing_submit_y_firmar_billing_sign(
    api_client, user_factory, tenant_schema
):
    cambiar_rol(tenant_schema, 'accountant', quitar=['billing.submit'])
    api_client.force_authenticate(user=user_factory(role='accountant'))
    resp = api_client.get(f'/api/billing/invoices/{UUID}/dgii-status/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.submit'
    assert api_client.post(f'/api/billing/invoices/{UUID}/sign/', {}, format='json').status_code == 400


def test_config_ecf_patch_exige_solo_billing_config(api_client, user_factory, tenant_schema):
    """Decisión: el PATCH pide billing.config y no exige además billing.view; el GET, billing.view."""
    url = '/api/billing/ecf-provider/config/'
    cambiar_rol(tenant_schema, 'accountant', quitar=['billing.view'], dar=['billing.config'])
    api_client.force_authenticate(user=user_factory(role='accountant'))
    assert api_client.patch(url, {}, format='json').status_code == 200
    resp = api_client.get(url)
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.view'


def test_reportes_dgii_exigen_billing_reports(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['billing.reports'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get('/api/billing/dgii-reports/607/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.reports'
