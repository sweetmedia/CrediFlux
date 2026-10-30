"""
2FA obligatoria para dueño y administradores (F2, Task 15).

Revertir un pago exige el código TOTP del dueño o de un administrador, así que
todo dueño y todo `admin` de una financiera debe tener 2FA. Mientras no la
active, la API le responde 403 `code: 2fa_required` en todo salvo lo que
necesita para activarla.

La regla se aplica en `APIView.perform_authentication` (ver
`apps/users/permissions_2fa.py`), así que cubre también las vistas que
reemplazan `permission_classes` y las de función con `@api_view`; estos tests
lo prueban con una de cada tipo y con un JWT de verdad.
"""
import pyotp
import pytest

from apps.users.tokens import issue_tokens

pytestmark = pytest.mark.django_db

CODIGO = '2fa_required'
MENSAJE = 'Activa la verificación en dos pasos para continuar.'

# Vistas de negocio de tres tipos: ModelViewSet que reemplaza permission_classes,
# @api_view de función y APIView.
NEGOCIO = [
    '/api/loans/customers/',
    '/api/validate-cedula/?cedula=00100000001',
    '/api/users/team/',
]


def es_bloqueo_2fa(resp):
    return resp.status_code == 403 and resp.data.get('code') == CODIGO


def cliente_de(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def dueno(user_factory):
    return user_factory(role='admin', is_tenant_owner=True, is_2fa_enabled=False, totp_secret=None)


# ---------------------------------------------------------------------------
# Bloqueo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('url', NEGOCIO)
def test_dueno_sin_2fa_bloqueado_en_negocio(api_client, dueno, url):
    resp = cliente_de(api_client, dueno).get(url)
    assert es_bloqueo_2fa(resp), (resp.status_code, resp.data)
    assert resp.data['detail'] == MENSAJE


def test_dueno_sin_2fa_bloqueado_al_escribir(api_client, dueno):
    resp = cliente_de(api_client, dueno).post('/api/loans/customers/', {}, format='json')
    assert es_bloqueo_2fa(resp)


@pytest.mark.parametrize('url', NEGOCIO)
def test_admin_no_dueno_sin_2fa_bloqueado(api_client, user_factory, url):
    admin = user_factory(role='admin', is_tenant_owner=False, is_2fa_enabled=False)
    resp = cliente_de(api_client, admin).get(url)
    assert es_bloqueo_2fa(resp), (resp.status_code, resp.data)


def test_dueno_con_otro_rol_sin_2fa_bloqueado(api_client, user_factory):
    dueno = user_factory(role='manager', is_tenant_owner=True, is_2fa_enabled=False)
    assert es_bloqueo_2fa(cliente_de(api_client, dueno).get('/api/users/team/'))


@pytest.mark.parametrize('url', NEGOCIO)
def test_con_jwt_real_tambien_bloquea(api_client, dueno, url):
    """La puerta JWT de producción (sin force_authenticate) pasa por la misma regla."""
    token = issue_tokens(dueno).access_token
    resp = api_client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
    assert es_bloqueo_2fa(resp), (resp.status_code, resp.data)


def test_lista_blanca_no_cubre_otros_metodos(api_client, dueno):
    """El perfil se lee, pero no se edita; los ajustes se leen, pero no se cambian."""
    c = cliente_de(api_client, dueno)
    assert es_bloqueo_2fa(c.put('/api/users/profile/update/', {}, format='json'))
    assert es_bloqueo_2fa(c.patch('/api/tenants/settings/', {}, format='json'))
    assert es_bloqueo_2fa(c.post('/api/users/permissions/catalog/', {}, format='json'))


# ---------------------------------------------------------------------------
# Lista blanca: lo necesario para activar la 2FA
# ---------------------------------------------------------------------------


def test_lista_blanca_lecturas(api_client, dueno):
    c = cliente_de(api_client, dueno)
    for url in ('/api/users/profile/', '/api/config/', '/api/tenants/settings/',
                '/api/users/permissions/catalog/', '/api/users/auth/2fa/backup-codes/'):
        resp = c.get(url)
        assert resp.status_code == 200, (url, resp.status_code, getattr(resp, 'data', None))


def test_flujo_completo_de_activacion(api_client, dueno):
    c = cliente_de(api_client, dueno)
    setup = c.post('/api/users/auth/2fa/setup/', {}, format='json')
    assert setup.status_code == 200, setup.data
    assert setup.data['qr_code']

    dueno.refresh_from_db()
    codigo = pyotp.TOTP(dueno.totp_secret).now()
    verify = c.post('/api/users/auth/2fa/verify/', {'code': codigo}, format='json')
    assert verify.status_code == 200, verify.data
    assert len(verify.data['backup_codes']) == 10

    dueno.refresh_from_db()
    assert dueno.is_2fa_enabled
    c.force_authenticate(user=dueno)
    assert c.get('/api/users/team/').status_code == 200


def test_backup_codes_post_no_bloqueado(api_client, dueno):
    resp = cliente_de(api_client, dueno).post('/api/users/auth/2fa/backup-codes/', {}, format='json')
    assert not es_bloqueo_2fa(resp)


def test_logout_y_refresh_no_bloqueados(api_client, dueno):
    refresh = issue_tokens(dueno)
    hdr = {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    resp = api_client.post('/api/auth/token/refresh/', {'refresh': str(refresh)}, format='json', **hdr)
    assert resp.status_code == 200, resp.data
    vigente = resp.data.get('refresh', str(refresh))  # con rotación, el anterior queda en lista negra

    resp = api_client.post('/api/users/auth/logout/', {'refresh_token': vigente}, format='json', **hdr)
    assert not es_bloqueo_2fa(resp)
    assert resp.status_code < 400, resp.data


# ---------------------------------------------------------------------------
# A quién no aplica
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('url', NEGOCIO)
def test_dueno_con_2fa_normal(api_client, user_factory, url):
    dueno = user_factory(role='admin', is_tenant_owner=True, is_2fa_enabled=True,
                         totp_secret=pyotp.random_base32())
    resp = cliente_de(api_client, dueno).get(url)
    assert resp.status_code == 200, (url, resp.status_code, resp.data)


@pytest.mark.parametrize('rol', ['manager', 'loan_officer', 'cashier', 'viewer'])
def test_otros_roles_sin_2fa_no_afectados(api_client, user_factory, rol):
    user = user_factory(role=rol, is_2fa_enabled=False)
    resp = cliente_de(api_client, user).get('/api/loans/customers/')
    assert not es_bloqueo_2fa(resp)


def test_manager_sin_2fa_trabaja_normal(api_client, user_factory):
    manager = user_factory(role='manager', is_2fa_enabled=False)
    assert cliente_de(api_client, manager).get('/api/loans/customers/').status_code == 200


def test_superusuario_de_plataforma_no_afectado(api_client, user_factory):
    su = user_factory(tenant=None, role='admin', is_superuser=True, is_staff=True,
                      is_2fa_enabled=False)
    for url in NEGOCIO:
        assert not es_bloqueo_2fa(cliente_de(api_client, su).get(url)), url


def test_anonimo_no_afectado(api_client):
    resp = api_client.get('/api/loans/customers/')
    assert resp.status_code == 401
    assert resp.data.get('code') != CODIGO


def test_financiera_sin_2fa_obligatoria_no_bloquea(api_client, dueno):
    tenant = dueno.tenant  # el tenant de prueba es el mismo objeto en toda la sesión
    tenant.require_2fa = False
    tenant.save(update_fields=['require_2fa'])
    try:
        resp = cliente_de(api_client, dueno).get('/api/loans/customers/')
        assert resp.status_code == 200, (resp.status_code, resp.data)
    finally:
        tenant.require_2fa = True
        tenant.save(update_fields=['require_2fa'])


def test_2fa_obligatoria_por_defecto(dueno):
    assert dueno.tenant.require_2fa is True


def test_require_2fa_no_se_cambia_desde_ajustes_de_la_financiera():
    from apps.tenants.serializers import TenantUpdateSerializer
    assert 'require_2fa' not in TenantUpdateSerializer.Meta.fields
