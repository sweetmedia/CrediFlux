"""GET /api/tenants/settings/ (run-8 L4): cualquier miembro lee la identidad y marca de la
financiera que usa el shell (R13); la configuración completa sólo con settings.view."""
import pytest

from tests.authz_helpers import cambiar_rol

pytestmark = pytest.mark.django_db

URL = '/api/tenants/settings/'
IDENTIDAD = {
    'id', 'name', 'business_name', 'logo', 'primary_color', 'default_currency',
    'currency_symbol', 'timezone', 'is_active', 'subscription_plan',
}
# Campos que un rol sin settings.view no debe recibir (muestra de la configuración completa).
CONFIGURACION = {
    'smtp_host', 'smtp_username', 'imap_username', 'whatsapp_phone_id',
    'whatsapp_business_account_id', 'tax_id', 'ai_provider', 'email', 'max_users',
    'require_disbursement_approval', 'has_smtp_password',
}
SECRETOS = {'smtp_password', 'imap_password', 'whatsapp_token', 'whatsapp_verify_token', 'ai_api_key'}


def test_sin_settings_view_solo_identidad(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['settings.view'])
    api_client.force_authenticate(user=user_factory(role='viewer'))
    resp = api_client.get(URL)
    assert resp.status_code == 200, resp.content
    assert set(resp.json()) == IDENTIDAD


def test_con_settings_view_toda_la_configuracion_sin_secretos(api_client, user_factory):
    api_client.force_authenticate(user=user_factory(role='viewer'))
    data = api_client.get(URL).json()
    assert IDENTIDAD | CONFIGURACION <= set(data)
    assert not SECRETOS & set(data)
