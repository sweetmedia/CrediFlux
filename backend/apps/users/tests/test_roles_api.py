"""API de roles y catálogo de permisos (D6, Task 12).

* `GET /api/users/permissions/catalog/`: módulos con sus códigos y etiquetas (cualquier autenticado).
* `/api/users/roles/`: lectura con team.view; alta, edición y borrado con team.assign_roles.
* La clave se genera del nombre (slugify, minúsculas, 30 caracteres, única en la financiera,
  `-2`, `-3`… si choca); las claves de los roles de sistema están reservadas (R15).
* `admin` no se edita ni se borra; los demás de sistema editan permisos y descripción, no se
  borran y conservan clave y nombre. Un rol con usuarios no se borra (409 con la cuenta).
* R14: quien no es dueño ni superusuario no pone en un rol (ni edita uno que ya tenga) códigos
  que él no tiene, ni team.assign_roles/team.edit/team.delete; tampoco edita su propio rol.
* Auditoría: `role_change` con `added`/`removed`; `create` con la lista y `delete` con la clave.
* El usuario actual recibe `permissions` en el perfil y en el login; el equipo no.
"""
import pytest

from apps.audit.models import AuditLog
from apps.users import views_roles
from apps.users.models import Role
from apps.users.permissions_catalog import ALL_CODES, MODULES
from tests.authz_helpers import cambiar_rol, comprobar_completitud, viewsets_de

pytestmark = pytest.mark.django_db

ROLES = '/api/users/roles/'
CATALOGO = '/api/users/permissions/catalog/'
PASSWORD = 'clave-de-prueba-123'


def _como(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def _dueno(user_factory):
    return user_factory(role='admin', is_tenant_owner=True)


def _gestor(tenant_schema, user_factory, dar=('team.assign_roles',)):
    """Gerente con team.assign_roles (y lo que se pida): no es dueño, R14 le aplica."""
    cambiar_rol(tenant_schema, 'manager', dar=list(dar))
    return user_factory(role='manager')


def _rol(tenant, key, permisos, name=None):
    return Role.objects.create(tenant=tenant, key=key, name=name or key, permissions=sorted(permisos))


def test_cada_accion_del_viewset_tiene_su_codigo():
    for cls in viewsets_de(views_roles):
        comprobar_completitud(cls)
    assert viewsets_de(views_roles)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


def test_catalogo_para_cualquier_autenticado(api_client, user_factory):
    resp = _como(api_client, user_factory(role='viewer')).get(CATALOGO)
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert [m['key'] for m in data] == [key for key, _, _ in MODULES]
    assert data[0]['label'] == 'Clientes'
    assert data[0]['permissions'][0] == {'code': 'customers.view', 'label': 'Ver clientes'}
    assert {p['code'] for m in data for p in m['permissions']} == ALL_CODES


def test_catalogo_sin_sesion_es_401(api_client):
    assert api_client.get(CATALOGO).status_code in (401, 403)


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------


def test_lista_los_roles_de_la_financiera_con_su_cuenta_de_usuarios(api_client, user_factory, tenant_schema):
    user_factory(role='collector')
    user_factory(role='collector', is_active=False)
    resp = _como(api_client, user_factory(role='viewer')).get(ROLES)
    assert resp.status_code == 200, resp.content
    roles = {r['key']: r for r in resp.json()}
    assert {'admin', 'manager', 'collector', 'viewer'} <= set(roles)
    assert roles['collector']['user_count'] == 2  # también los inactivos: siguen teniendo el rol
    assert roles['collector']['is_system'] is True
    assert set(roles['admin']['permissions']) == ALL_CODES
    assert set(roles['viewer']) == {'key', 'name', 'description', 'is_system', 'permissions', 'user_count'}


def test_detalle_por_clave(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'}, 'Cobrador Norte')
    resp = _como(api_client, user_factory(role='viewer')).get(f'{ROLES}cobrador-norte/')
    assert resp.status_code == 200, resp.content
    assert resp.json()['name'] == 'Cobrador Norte'
    assert resp.json()['user_count'] == 0


def test_sin_team_view_no_lista(api_client, user_factory, tenant_schema):
    cambiar_rol(tenant_schema, 'viewer', quitar=['team.view'])
    resp = _como(api_client, user_factory(role='viewer')).get(ROLES)
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'team.view'


# ---------------------------------------------------------------------------
# Alta
# ---------------------------------------------------------------------------


def test_crear_genera_la_clave_del_nombre_y_audita(api_client, user_factory, tenant_schema):
    dueno = _dueno(user_factory)
    resp = _como(api_client, dueno).post(ROLES, {
        'name': 'Cobrador Norte', 'description': 'Ruta norte',
        'permissions': ['payments.create', 'collections.view', 'payments.create'],
    }, format='json')
    assert resp.status_code == 201, resp.content
    data = resp.json()
    assert data['key'] == 'cobrador-norte'
    assert data['is_system'] is False
    assert data['permissions'] == ['collections.view', 'payments.create']
    assert data['user_count'] == 0
    role = Role.objects.get(tenant=tenant_schema, key='cobrador-norte')
    assert role.name == 'Cobrador Norte'

    log = AuditLog.objects.get(action='create', model_name='Role')
    assert log.tenant_id == tenant_schema.pk
    assert log.user_id == dueno.pk
    assert log.object_id == 'cobrador-norte'
    assert log.changes == {'permissions': ['collections.view', 'payments.create']}


def test_clave_repetida_lleva_sufijo_y_cabe_en_30(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _dueno(user_factory))
    claves = [
        cliente.post(ROLES, {'name': 'Cobrador Norte', 'permissions': []}, format='json').json()['key']
        for _ in range(3)
    ]
    assert claves == ['cobrador-norte', 'cobrador-norte-2', 'cobrador-norte-3']

    largo = 'Supervisión de la Cartera Vencida del Norte'
    k1 = cliente.post(ROLES, {'name': largo, 'permissions': []}, format='json').json()['key']
    k2 = cliente.post(ROLES, {'name': largo, 'permissions': []}, format='json').json()['key']
    assert k1 == 'supervision-de-la-cartera-venc'
    assert len(k2) <= 30 and k2.endswith('-2') and k2 != k1


def test_clave_de_sistema_reservada(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _dueno(user_factory))
    assert cliente.post(ROLES, {'name': 'Admin', 'permissions': []}, format='json').json()['key'] == 'admin-2'
    assert cliente.post(ROLES, {'name': 'MANAGER', 'permissions': []}, format='json').json()['key'] == 'manager-2'
    assert Role.objects.get(tenant=tenant_schema, key='admin').is_system


def test_nombre_sin_letras_ni_numeros_es_400(api_client, user_factory):
    resp = _como(api_client, _dueno(user_factory)).post(ROLES, {'name': '¡¡ !!', 'permissions': []}, format='json')
    assert resp.status_code == 400
    assert 'name' in resp.json()


def test_codigo_inexistente_es_400(api_client, user_factory, tenant_schema):
    resp = _como(api_client, _dueno(user_factory)).post(
        ROLES, {'name': 'Raro', 'permissions': ['loans.view', 'loans.fly']}, format='json')
    assert resp.status_code == 400
    assert 'permissions' in resp.json()
    assert not Role.objects.filter(tenant=tenant_schema, name='Raro').exists()


def test_sin_assign_roles_no_crea(api_client, user_factory, tenant_schema):
    resp = _como(api_client, user_factory(role='manager')).post(
        ROLES, {'name': 'X', 'permissions': []}, format='json')
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'team.assign_roles'


def test_r14_no_crea_con_codigos_que_no_tiene(api_client, user_factory, tenant_schema):
    gestor = _gestor(tenant_schema, user_factory)
    assert 'billing.sign' not in Role.objects.get(tenant=tenant_schema, key='manager').permissions
    resp = _como(api_client, gestor).post(
        ROLES, {'name': 'Facturador', 'permissions': ['loans.view', 'billing.sign']}, format='json')
    assert resp.status_code == 403, resp.content
    assert resp.json()['required_permission'] == 'billing.sign'
    assert not Role.objects.filter(tenant=tenant_schema, name='Facturador').exists()
    # Con los que sí tiene, pasa.
    resp = api_client.post(ROLES, {'name': 'Lector', 'permissions': ['loans.view']}, format='json')
    assert resp.status_code == 201, resp.content


@pytest.mark.parametrize('codigo', ['team.assign_roles', 'team.edit', 'team.delete'])
def test_r14_codigos_de_gestion_solo_los_pone_el_dueno(api_client, user_factory, tenant_schema, codigo):
    gestor = _gestor(tenant_schema, user_factory, dar=('team.assign_roles', 'team.edit', 'team.delete'))
    resp = _como(api_client, gestor).post(ROLES, {'name': 'Jefe', 'permissions': [codigo]}, format='json')
    assert resp.status_code == 403, resp.content
    assert resp.json()['required_permission'] == codigo

    resp = _como(api_client, _dueno(user_factory)).post(
        ROLES, {'name': 'Jefe', 'permissions': [codigo]}, format='json')
    assert resp.status_code == 201, resp.content


# ---------------------------------------------------------------------------
# Edición
# ---------------------------------------------------------------------------


def test_editar_permisos_audita_lo_agregado_y_lo_quitado(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view', 'payments.create'}, 'Cobrador Norte')
    dueno = _dueno(user_factory)
    resp = _como(api_client, dueno).patch(
        f'{ROLES}cobrador-norte/', {'permissions': ['collections.view', 'loans.view']}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['permissions'] == ['collections.view', 'loans.view']
    assert resp.json()['key'] == 'cobrador-norte'

    log = AuditLog.objects.get(action='role_change')
    assert log.tenant_id == tenant_schema.pk and log.user_id == dueno.pk
    assert log.model_name == 'Role' and log.object_id == 'cobrador-norte'
    assert log.changes['added'] == ['loans.view']
    assert log.changes['removed'] == ['payments.create']


def test_editar_sin_cambios_no_audita(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'}, 'Cobrador Norte')
    resp = _como(api_client, _dueno(user_factory)).patch(
        f'{ROLES}cobrador-norte/', {'permissions': ['collections.view']}, format='json')
    assert resp.status_code == 200
    assert not AuditLog.objects.filter(action='role_change').exists()


def test_quitar_un_codigo_vale_desde_el_siguiente_request(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view', 'payments.create', 'payments.view'})
    cobrador = user_factory(role='cobrador-norte')
    token = api_client.post('/api/tenants/login/', {'email': cobrador.email, 'password': PASSWORD},
                            format='json').json()['access_token']
    hdr = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
    # Con payments.create pasa el permiso (cuerpo vacío → 400).
    assert api_client.post('/api/loans/payments/', {}, format='json', **hdr).status_code == 400

    dueno_client = type(api_client)(HTTP_HOST='tenant.test.localhost')
    dueno_client.force_authenticate(user=_dueno(user_factory))
    resp = dueno_client.patch(f'{ROLES}cobrador-norte/',
                              {'permissions': ['collections.view', 'payments.view']}, format='json')
    assert resp.status_code == 200, resp.content

    resp = api_client.post('/api/loans/payments/', {}, format='json', **hdr)
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'payments.create'


def test_admin_no_se_edita(api_client, user_factory, tenant_schema):
    resp = _como(api_client, _dueno(user_factory)).patch(
        f'{ROLES}admin/', {'permissions': ['loans.view']}, format='json')
    assert resp.status_code == 400, resp.content
    assert set(Role.objects.get(tenant=tenant_schema, key='admin').permissions) == ALL_CODES


def test_rol_de_sistema_edita_permisos_y_descripcion_no_nombre(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _dueno(user_factory))
    resp = cliente.patch(f'{ROLES}viewer/', {'permissions': ['loans.view'], 'description': 'Mira'},
                         format='json')
    assert resp.status_code == 200, resp.content
    role = Role.objects.get(tenant=tenant_schema, key='viewer')
    assert role.permissions == ['loans.view'] and role.description == 'Mira'

    resp = cliente.patch(f'{ROLES}viewer/', {'name': 'Mirón'}, format='json')
    assert resp.status_code == 400
    assert 'name' in resp.json()
    # Mandar el mismo nombre no es un cambio.
    assert cliente.patch(f'{ROLES}viewer/', {'name': role.name}, format='json').status_code == 200


def test_rol_propio_cambia_nombre_pero_no_clave(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'}, 'Cobrador Norte')
    resp = _como(api_client, _dueno(user_factory)).patch(
        f'{ROLES}cobrador-norte/', {'name': 'Cobrador Zona Norte', 'key': 'otra'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['key'] == 'cobrador-norte'
    assert resp.json()['name'] == 'Cobrador Zona Norte'
    log = AuditLog.objects.get(action='role_change')
    assert log.changes['name'] == {'old': 'Cobrador Norte', 'new': 'Cobrador Zona Norte'}


def test_put_no_esta_permitido(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'})
    resp = _como(api_client, _dueno(user_factory)).put(
        f'{ROLES}cobrador-norte/', {'name': 'X', 'permissions': []}, format='json')
    assert resp.status_code == 405


def test_r14_editar_no_agrega_codigos_que_no_tiene(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'})
    resp = _como(api_client, _gestor(tenant_schema, user_factory)).patch(
        f'{ROLES}cobrador-norte/', {'permissions': ['collections.view', 'billing.sign']}, format='json')
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'billing.sign'
    assert Role.objects.get(tenant=tenant_schema, key='cobrador-norte').permissions == ['collections.view']


def test_r14_no_edita_un_rol_mas_fuerte_que_el(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'facturador', {'billing.sign', 'loans.view'})
    _rol(tenant_schema, 'jefe', {'team.edit', 'loans.view'})
    cliente = _como(api_client, _gestor(tenant_schema, user_factory))
    resp = cliente.patch(f'{ROLES}facturador/', {'permissions': ['loans.view']}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.sign'
    resp = cliente.patch(f'{ROLES}jefe/', {'permissions': ['loans.view']}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.edit'
    resp = cliente.delete(f'{ROLES}jefe/')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.edit'
    assert Role.objects.filter(tenant=tenant_schema, key='jefe').exists()


def test_no_edita_el_rol_que_el_mismo_tiene(api_client, user_factory, tenant_schema):
    gestor = _gestor(tenant_schema, user_factory)
    resp = _como(api_client, gestor).patch(
        f'{ROLES}manager/', {'permissions': ['loans.view', 'team.assign_roles']}, format='json')
    assert resp.status_code == 403, resp.content
    assert 'team.view' in Role.objects.get(tenant=tenant_schema, key='manager').permissions


def test_el_dueno_edita_su_propio_rol(api_client, user_factory, tenant_schema):
    dueno = user_factory(role='viewer', is_tenant_owner=True)
    resp = _como(api_client, dueno).patch(f'{ROLES}viewer/', {'permissions': ['loans.view']}, format='json')
    assert resp.status_code == 200, resp.content


# ---------------------------------------------------------------------------
# Borrado
# ---------------------------------------------------------------------------


def test_rol_de_sistema_no_se_borra(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _dueno(user_factory))
    for key in ('manager', 'admin'):
        assert cliente.delete(f'{ROLES}{key}/').status_code == 400
        assert Role.objects.filter(tenant=tenant_schema, key=key).exists()


def test_rol_con_usuarios_no_se_borra(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'})
    user_factory(role='cobrador-norte')
    resp = _como(api_client, _dueno(user_factory)).delete(f'{ROLES}cobrador-norte/')
    assert resp.status_code == 409
    assert resp.json()['user_count'] == 1
    assert resp.json()['detail']
    assert Role.objects.filter(tenant=tenant_schema, key='cobrador-norte').exists()


def test_rol_sin_usuarios_se_borra_y_audita(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'}, 'Cobrador Norte')
    dueno = _dueno(user_factory)
    resp = _como(api_client, dueno).delete(f'{ROLES}cobrador-norte/')
    assert resp.status_code == 204
    assert not Role.objects.filter(tenant=tenant_schema, key='cobrador-norte').exists()
    log = AuditLog.objects.get(action='delete', model_name='Role')
    assert log.tenant_id == tenant_schema.pk and log.user_id == dueno.pk
    assert log.object_id == 'cobrador-norte'
    assert log.changes == {'key': 'cobrador-norte', 'permissions': ['collections.view']}


# ---------------------------------------------------------------------------
# Aislamiento entre financieras
# ---------------------------------------------------------------------------


def test_otra_financiera_no_ve_ni_toca_estos_roles(api_client, user_factory, tenant_schema, other_tenant):
    from django.db import connection

    connection.set_schema_to_public()
    _rol(other_tenant, 'cobrador-sur', {'collections.view'})
    _rol(other_tenant, 'cobrador-norte', {'loans.view'})
    connection.set_tenant(tenant_schema)

    cliente = _como(api_client, _dueno(user_factory))
    keys = {r['key'] for r in cliente.get(ROLES).json()}
    assert 'cobrador-sur' not in keys
    assert cliente.get(f'{ROLES}cobrador-sur/').status_code == 404
    assert cliente.patch(f'{ROLES}cobrador-sur/', {'permissions': []}, format='json').status_code == 404
    assert cliente.delete(f'{ROLES}cobrador-sur/').status_code == 404
    assert Role.objects.get(tenant=other_tenant, key='cobrador-sur').permissions == ['collections.view']

    # La clave es única por financiera: otra con el mismo nombre no lleva sufijo.
    resp = cliente.post(ROLES, {'name': 'Cobrador Norte', 'permissions': []}, format='json')
    assert resp.json()['key'] == 'cobrador-norte'
    assert Role.objects.get(tenant=other_tenant, key='cobrador-norte').permissions == ['loans.view']
    logs = AuditLog.objects.filter(model_name='Role')
    assert logs.exists() and all(log.tenant_id == tenant_schema.pk for log in logs)


# ---------------------------------------------------------------------------
# Permisos del usuario actual
# ---------------------------------------------------------------------------


def test_perfil_trae_los_permisos_del_usuario(api_client, user_factory, tenant_schema):
    from apps.users.permissions_catalog import DEFAULT_ROLE_PERMISSIONS

    resp = _como(api_client, user_factory(role='collector')).get('/api/users/profile/')
    assert resp.status_code == 200
    assert resp.json()['permissions'] == sorted(DEFAULT_ROLE_PERMISSIONS['collector'])

    resp = _como(api_client, user_factory(role='viewer', is_tenant_owner=True)).get('/api/users/profile/')
    assert resp.json()['permissions'] == sorted(ALL_CODES)


def test_login_trae_los_permisos(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view', 'payments.create'})
    user = user_factory(role='cobrador-norte')
    resp = api_client.post('/api/tenants/login/', {'email': user.email, 'password': PASSWORD}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['user']['permissions'] == ['collections.view', 'payments.create']


def test_login_2fa_trae_los_permisos(api_client, user_factory, tenant_schema):
    import pyotp

    secreto = pyotp.random_base32()
    user = user_factory(role='collector', is_2fa_enabled=True, totp_secret=secreto)
    resp = api_client.post('/api/tenants/login/', {'email': user.email, 'password': PASSWORD}, format='json')
    temp = resp.json()['temp_token']
    resp = api_client.post('/api/users/auth/2fa/login/',
                           {'temp_token': temp, 'code': pyotp.TOTP(secreto).now()}, format='json')
    assert resp.status_code == 200, resp.content
    assert 'collections.view' in resp.json()['user']['permissions']


def test_el_equipo_no_expone_permisos_de_otros(api_client, user_factory, tenant_schema):
    user_factory(role='collector')
    resp = _como(api_client, _dueno(user_factory)).get('/api/users/team/')
    assert resp.status_code == 200
    assert all('permissions' not in row for row in resp.json()['results'])
