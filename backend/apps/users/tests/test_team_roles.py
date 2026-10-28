"""Equipo y asignación de roles sobre códigos de permiso (D6, Task 11).

`User.role` ya no es una lista fija: es la clave de un `Role` de la financiera del usuario.
Reglas que fija este archivo:

* Lista/detalle/alta/edición/borrado del equipo exigen team.view/create/edit/delete.
* Cambiar el rol (o darlo explícito en el alta) exige además team.assign_roles; editar sólo
  otros campos, o mandar el mismo rol que ya tiene, exige sólo team.edit. Un alta sin rol
  queda en `viewer` con team.create.
* El rol debe existir en la financiera del usuario destino: de otra financiera o inexistente → 400.
* Dar `admin` es sólo del dueño o el superusuario (R4), nunca un código → 400 para el resto.
* Anti-escalada: quien no es dueño ni superusuario no puede dar un rol con códigos que él no
  tiene → 403 con `required_permission` = el primer código que le falta (orden alfabético).
"""
import pytest

from apps.users.authz import user_permissions
from apps.users.models import Role, User
from tests.authz_helpers import cambiar_rol

pytestmark = pytest.mark.django_db

TEAM = '/api/users/team/'


def _detalle(user):
    return f'{TEAM}{user.pk}/'


def _rol(tenant, key, permisos, name=None):
    return Role.objects.create(tenant=tenant, key=key, name=name or key, permissions=sorted(permisos))


def _gestor(tenant_schema, user_factory, dar=('team.edit', 'team.assign_roles')):
    """Gerente con los códigos de equipo indicados (el gerente de sistema no tiene ninguno de escritura)."""
    cambiar_rol(tenant_schema, 'manager', dar=list(dar))
    return user_factory(role='manager')


def _como(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


def _alta(n, **extra):
    return {
        'email': f'equipo{n}@crediflux.test', 'username': f'equipo{n}',
        'first_name': 'Ana', 'last_name': 'Pérez', 'password': 'clave-segura-123', **extra,
    }


# ---------------------------------------------------------------------------
# Asignar roles (edición)
# ---------------------------------------------------------------------------


def test_con_assign_roles_se_asigna_un_rol_propio_de_la_financiera(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view', 'payments.view'}, 'Cobrador Norte')
    destino = user_factory(role='viewer')
    resp = _como(api_client, _gestor(tenant_schema, user_factory)).patch(
        _detalle(destino), {'role': 'cobrador-norte'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.json()['role'] == 'cobrador-norte'
    destino.refresh_from_db()
    assert destino.role == 'cobrador-norte'
    assert user_permissions(destino) == frozenset({'collections.view', 'payments.view'})


def test_rol_de_otra_financiera_es_400(api_client, user_factory, tenant_schema, other_tenant):
    from django.db import connection

    connection.set_schema_to_public()
    _rol(other_tenant, 'cobrador-sur', {'collections.view'})
    connection.set_tenant(tenant_schema)
    destino = user_factory(role='viewer')
    resp = _como(api_client, _gestor(tenant_schema, user_factory)).patch(
        _detalle(destino), {'role': 'cobrador-sur'}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'role' in resp.json()
    destino.refresh_from_db()
    assert destino.role == 'viewer'


def test_rol_inexistente_es_400(api_client, user_factory, tenant_schema):
    destino = user_factory(role='viewer')
    resp = _como(api_client, _gestor(tenant_schema, user_factory)).patch(
        _detalle(destino), {'role': 'no-existe'}, format='json')
    assert resp.status_code == 400, resp.content
    assert 'role' in resp.json()


def test_sin_assign_roles_cambiar_rol_es_403(api_client, user_factory, tenant_schema):
    destino = user_factory(role='viewer')
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.edit']))
    resp = cliente.patch(_detalle(destino), {'role': 'cashier'}, format='json')
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'team.assign_roles'
    destino.refresh_from_db()
    assert destino.role == 'viewer'
    # Editar sólo otros campos, o mandar el mismo rol, no es asignar: basta team.edit.
    resp = cliente.patch(_detalle(destino), {'job_title': 'Analista', 'role': 'viewer'}, format='json')
    assert resp.status_code == 200, resp.content
    destino.refresh_from_db()
    assert destino.job_title == 'Analista'


def test_editar_exige_team_edit_y_borrar_team_delete(api_client, user_factory, tenant_schema):
    destino = user_factory(role='viewer')
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.assign_roles']))
    resp = cliente.patch(_detalle(destino), {'role': 'cashier'}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.edit'
    resp = cliente.put(_detalle(destino), {}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.edit'
    resp = cliente.delete(_detalle(destino))
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.delete'


def test_listar_y_ver_exigen_team_view(api_client, user_factory, tenant_schema):
    destino = user_factory(role='cashier')
    cambiar_rol(tenant_schema, 'viewer', quitar=['team.view'])
    cliente = _como(api_client, user_factory(role='viewer'))
    for url in (TEAM, _detalle(destino)):
        resp = cliente.get(url)
        assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.view', url


def test_un_admin_no_asigna_admin_y_el_dueno_si(api_client, user_factory, tenant_schema):
    destino = user_factory(role='viewer')
    resp = _como(api_client, user_factory(role='admin')).patch(
        _detalle(destino), {'role': 'admin'}, format='json')
    assert resp.status_code == 400 and 'role' in resp.json()
    destino.refresh_from_db()
    assert destino.role == 'viewer'
    resp = _como(api_client, user_factory(role='viewer', is_tenant_owner=True)).patch(
        _detalle(destino), {'role': 'admin'}, format='json')
    assert resp.status_code == 200, resp.content
    destino.refresh_from_db()
    assert destino.role == 'admin'


def test_rol_del_dueno_no_cambia_ni_con_assign_roles(api_client, user_factory, tenant_schema):
    dueno = user_factory(role='admin', is_tenant_owner=True)
    resp = _como(api_client, user_factory(role='admin')).patch(
        _detalle(dueno), {'role': 'viewer'}, format='json')
    assert resp.status_code == 400 and 'role' in resp.json()
    dueno.refresh_from_db()
    assert dueno.role == 'admin'


# ---------------------------------------------------------------------------
# Anti-escalada
# ---------------------------------------------------------------------------


def test_no_se_da_un_rol_con_codigos_que_uno_no_tiene(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'super-gerente', {'team.view', 'settings.edit', 'billing.config'})
    gestor = _gestor(tenant_schema, user_factory)
    assert 'billing.config' not in user_permissions(gestor)
    destino = user_factory(role='viewer')
    cliente = _como(api_client, gestor)

    resp = cliente.patch(_detalle(destino), {'role': 'super-gerente'}, format='json')
    assert resp.status_code == 403
    assert resp.json()['required_permission'] == 'billing.config'  # el primero que falta
    destino.refresh_from_db()
    assert destino.role == 'viewer'

    # Tampoco a sí mismo.
    resp = cliente.patch(_detalle(gestor), {'role': 'super-gerente'}, format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.config'
    gestor.refresh_from_db()
    assert gestor.role == 'manager'


def test_si_se_da_un_rol_contenido_en_los_propios_codigos(api_client, user_factory, tenant_schema):
    gestor = _gestor(tenant_schema, user_factory)
    _rol(tenant_schema, 'gerente-mini', set(user_permissions(gestor)) - {'team.assign_roles'})
    destino = user_factory(role='viewer')
    resp = _como(api_client, gestor).patch(_detalle(destino), {'role': 'gerente-mini'}, format='json')
    assert resp.status_code == 200, resp.content


def test_el_dueno_da_cualquier_rol_propio(api_client, user_factory, tenant_schema):
    from apps.users.permissions_catalog import ALL_CODES

    _rol(tenant_schema, 'todo-menos-admin', ALL_CODES)
    destino = user_factory(role='viewer')
    resp = _como(api_client, user_factory(role='viewer', is_tenant_owner=True)).patch(
        _detalle(destino), {'role': 'todo-menos-admin'}, format='json')
    assert resp.status_code == 200, resp.content


# ---------------------------------------------------------------------------
# Alta
# ---------------------------------------------------------------------------


def test_alta_sin_rol_queda_viewer_con_solo_team_create(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.create']))
    resp = cliente.post(f'{TEAM}create/', _alta(1), format='json')
    assert resp.status_code == 201, resp.content
    assert User.objects.get(email='equipo1@crediflux.test').role == 'viewer'


def test_alta_con_rol_exige_assign_roles(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.create']))
    resp = cliente.post(f'{TEAM}create/', _alta(2, role='viewer'), format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.assign_roles'
    assert not User.objects.filter(email='equipo2@crediflux.test').exists()


def test_alta_sin_team_create_es_403(api_client, user_factory, tenant_schema):
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.assign_roles']))
    resp = cliente.post(f'{TEAM}create/', _alta(3), format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'team.create'


def test_alta_valida_el_rol_contra_la_financiera_y_la_escalada(api_client, user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', {'collections.view'})
    _rol(tenant_schema, 'super-gerente', {'billing.config'})
    cliente = _como(api_client, _gestor(tenant_schema, user_factory, dar=['team.create', 'team.assign_roles']))

    resp = cliente.post(f'{TEAM}create/', _alta(4, role='no-existe'), format='json')
    assert resp.status_code == 400 and 'role' in resp.json()
    resp = cliente.post(f'{TEAM}create/', _alta(5, role='admin'), format='json')
    assert resp.status_code == 400 and 'role' in resp.json()
    resp = cliente.post(f'{TEAM}create/', _alta(6, role='super-gerente'), format='json')
    assert resp.status_code == 403 and resp.json()['required_permission'] == 'billing.config'
    resp = cliente.post(f'{TEAM}create/', _alta(7, role='cobrador-norte'), format='json')
    assert resp.status_code == 201, resp.content
    assert User.objects.get(email='equipo7@crediflux.test').role == 'cobrador-norte'
    assert not User.objects.filter(email__in=[f'equipo{n}@crediflux.test' for n in (4, 5, 6)]).exists()


# ---------------------------------------------------------------------------
# Modelo y memo de permisos
# ---------------------------------------------------------------------------


def test_role_sin_choices_y_sin_propiedades_viejas():
    campo = User._meta.get_field('role')
    assert not campo.choices
    assert campo.max_length == Role._meta.get_field('key').max_length
    for viejo in ('is_admin', 'is_manager', 'can_manage_users', 'ROLE_CHOICES'):
        assert not hasattr(User, viejo), viejo


def test_get_role_display_usa_el_nombre_del_rol(user_factory, tenant_schema):
    _rol(tenant_schema, 'cobrador-norte', set(), 'Cobrador Norte')
    assert user_factory(role='cobrador-norte').get_role_display() == 'Cobrador Norte'
    assert user_factory(role='borrado').get_role_display() == 'borrado'


def test_cambiar_el_rol_invalida_el_memo_de_permisos(user_factory, tenant_schema, rf):
    from apps.users.serializers import TeamMemberUpdateSerializer

    destino = user_factory(role='viewer')
    assert 'customers.create' not in user_permissions(destino)  # deja el memo puesto
    request = rf.patch('/')
    request.user = user_factory(role='admin')
    serializer = TeamMemberUpdateSerializer(
        destino, data={'role': 'loan_officer'}, partial=True,
        context={'request': request, 'tenant': tenant_schema},
    )
    assert serializer.is_valid(), serializer.errors
    serializer.save()
    assert 'customers.create' in user_permissions(destino)


# ---------------------------------------------------------------------------
# Admin de Django
# ---------------------------------------------------------------------------


def test_admin_ofrece_solo_los_roles_de_la_financiera_del_usuario(user_factory, tenant_schema, other_tenant):
    from django.db import connection
    from django.test import Client
    from django.urls import reverse

    connection.set_schema_to_public()
    _rol(other_tenant, 'cobrador-sur', set())
    connection.set_tenant(tenant_schema)
    _rol(tenant_schema, 'cobrador-norte', set())
    dueno = user_factory(role='admin', is_tenant_owner=True, is_staff=True)
    miembro = user_factory(role='viewer')
    client = Client(HTTP_HOST='tenant.test.localhost')
    client.force_login(dueno)

    for url in (reverse('admin:users_user_change', args=[miembro.pk]), reverse('admin:users_user_add')):
        opciones = {k for k, _ in client.get(url).context['adminform'].form.fields['role'].choices}
        assert 'cobrador-norte' in opciones and 'manager' in opciones, url
        assert 'cobrador-sur' not in opciones, url


def test_admin_no_acepta_rol_de_otra_financiera(user_factory, tenant_schema, other_tenant):
    from django.db import connection
    from django.test import Client
    from django.urls import reverse

    connection.set_schema_to_public()
    _rol(other_tenant, 'cobrador-sur', set())
    connection.set_tenant(tenant_schema)
    dueno = user_factory(role='admin', is_tenant_owner=True, is_staff=True)
    miembro = user_factory(role='viewer')
    client = Client(HTTP_HOST='tenant.test.localhost')
    client.force_login(dueno)
    body = {
        'username': miembro.username, 'email': miembro.email, 'first_name': 'N', 'last_name': 'A',
        'role': 'cobrador-sur', 'is_active': 'on', 'receive_notifications': 'on',
    }
    r = client.post(reverse('admin:users_user_change', args=[miembro.pk]), body)
    assert r.status_code == 200
    assert 'role' in r.context['adminform'].form.errors
    miembro.refresh_from_db()
    assert miembro.role == 'viewer'


def test_admin_aplica_assign_roles_y_anti_escalada(user_factory, tenant_schema):
    from django.test import Client
    from django.urls import reverse

    _rol(tenant_schema, 'super-gerente', {'billing.config'})
    gestor = _gestor(tenant_schema, user_factory, dar=['team.edit'])
    gestor.is_staff = True
    gestor.save()
    miembro = user_factory(role='viewer')
    client = Client(HTTP_HOST='tenant.test.localhost')
    client.force_login(gestor)
    url = reverse('admin:users_user_change', args=[miembro.pk])
    body = {
        'username': miembro.username, 'email': miembro.email, 'first_name': 'N', 'last_name': 'A',
        'is_active': 'on', 'receive_notifications': 'on',
    }

    r = client.post(url, {**body, 'role': 'cashier'})
    assert r.status_code == 200 and 'team.assign_roles' in str(r.context['adminform'].form.errors['role'])

    cambiar_rol(tenant_schema, 'manager', dar=['team.assign_roles'])
    r = client.post(url, {**body, 'role': 'super-gerente'})
    assert r.status_code == 200 and 'billing.config' in str(r.context['adminform'].form.errors['role'])
    miembro.refresh_from_db()
    assert miembro.role == 'viewer'

    r = client.post(url, {**body, 'role': 'viewer', 'first_name': 'Otro'})  # sin cambiar el rol
    assert r.status_code == 302, r.context['adminform'].form.errors if r.context else r.content
