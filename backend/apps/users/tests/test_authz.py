"""Resolutor de permisos y PermissionRequired (D6, Task 8)."""
import pytest
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.users.authz import PermissionRequired, has_perm, user_permissions
from apps.users.models import Role, User
from apps.users.models_roles import ensure_system_roles
from apps.users.permissions_catalog import ALL_CODES, DEFAULT_ROLE_PERMISSIONS


@pytest.fixture
def roles(tenant_schema):
    ensure_system_roles(tenant_schema)
    return tenant_schema


class VistaMetodos(APIView):
    permission_classes = [PermissionRequired.for_methods(
        {'GET': 'customers.view', 'POST': 'customers.create'})]

    def get(self, request):
        return Response({'ok': True})

    post = delete = get


def _llamar(user, metodo='get'):
    request = getattr(APIRequestFactory(), metodo)('/x/')
    force_authenticate(request, user=user)
    return VistaMetodos.as_view()(request)


def test_duenio_y_superusuario_tienen_todo(roles, user_factory):
    duenio = user_factory(role='viewer', is_tenant_owner=True)
    assert user_permissions(duenio) == ALL_CODES
    su = user_factory(role='viewer', is_superuser=True)
    assert user_permissions(su) == ALL_CODES


def test_rol_da_sus_permisos(roles, user_factory):
    u = user_factory(role='loan_officer')
    assert user_permissions(u) == frozenset(DEFAULT_ROLE_PERMISSIONS['loan_officer']) & ALL_CODES
    assert has_perm(u, 'loans.create')
    assert not has_perm(u, 'team.delete')


def test_anonimo_e_inactivo_sin_permisos(roles, user_factory):
    from django.contrib.auth.models import AnonymousUser
    assert user_permissions(AnonymousUser()) == frozenset()
    u = user_factory(role='admin', is_tenant_owner=True, is_active=False)
    assert user_permissions(u) == frozenset()


def test_codigos_desconocidos_se_ignoran(roles, user_factory):
    Role.objects.filter(tenant=roles, key='viewer').update(permissions=['customers.view', 'ya.no.existe'])
    assert user_permissions(user_factory(role='viewer')) == frozenset({'customers.view'})


def test_rol_borrado_vacio_y_403_con_required_permission(roles, user_factory):
    u = user_factory(role='cashier')
    Role.objects.filter(tenant=roles, key='cashier').delete()
    u = User.objects.get(pk=u.pk)
    assert user_permissions(u) == frozenset()
    resp = _llamar(u)
    assert resp.status_code == 403
    assert resp.data['required_permission'] == 'customers.view'
    assert resp.data['detail'] == 'No tienes permiso para esta acción.'


def test_permitido_y_metodo_no_mapeado_denegado(roles, user_factory):
    u = user_factory(role='admin', is_tenant_owner=True)
    assert _llamar(u).status_code == 200
    assert _llamar(u, 'post').status_code == 200
    resp = _llamar(u, 'delete')  # no está en el mapa: deniega aun al dueño
    assert resp.status_code == 403
    assert 'required_permission' not in resp.data


def test_sin_sesion_no_es_403_de_permiso(roles):
    request = APIRequestFactory().get('/x/')
    resp = VistaMetodos.as_view()(request)
    assert resp.status_code in (401, 403)
    assert 'required_permission' not in resp.data


def test_for_actions(roles, user_factory):
    class VistaAcciones(APIView):
        permission_classes = [PermissionRequired.for_actions({'approve': 'loans.approve'})]

        def get(self, request):
            return Response({})

    def llamar(user, action):
        request = APIRequestFactory().get('/x/')
        force_authenticate(request, user=user)
        original = VistaAcciones.initial

        def initial(self, request, *a, **kw):
            self.action = action
            return original(self, request, *a, **kw)
        VistaAcciones.initial = initial
        try:
            return VistaAcciones.as_view()(request)
        finally:
            VistaAcciones.initial = original

    oficial = user_factory(role='loan_officer')
    cajero = user_factory(role='cashier')
    assert llamar(oficial, 'approve').status_code == 200
    resp = llamar(cajero, 'approve')
    assert resp.status_code == 403 and resp.data['required_permission'] == 'loans.approve'
    assert llamar(oficial, 'otra').status_code == 403  # acción desconocida


def test_rol_de_otra_financiera_no_se_toma(roles, user_factory):
    from apps.tenants.models import Tenant
    from django.db import connection
    connection.set_schema_to_public()
    otra = Tenant(schema_name='authz_b', name='B', business_name='B', email='b@financiera.test')
    otra.auto_create_schema = False
    otra.save()
    connection.set_tenant(roles)
    ensure_system_roles(otra)
    Role.objects.filter(tenant=otra, key='manager').update(permissions=['ai.access'])
    u = user_factory(role='manager')  # financiera A (test)
    assert user_permissions(u) == frozenset(DEFAULT_ROLE_PERMISSIONS['manager']) & ALL_CODES
    assert user_permissions(u) != frozenset({'ai.access'})


def test_memo_no_persiste_entre_requests(roles, user_factory):
    u = user_factory(role='viewer')
    assert _llamar(User.objects.get(pk=u.pk)).status_code == 200  # viewer ve clientes
    Role.objects.filter(tenant=roles, key='viewer').update(permissions=[])
    resp = _llamar(User.objects.get(pk=u.pk))  # instancia nueva, como cada request de DRF
    assert resp.status_code == 403
    Role.objects.filter(tenant=roles, key='viewer').update(permissions=['customers.view'])
    assert _llamar(User.objects.get(pk=u.pk)).status_code == 200


def test_memo_en_la_instancia(roles, user_factory, django_assert_num_queries):
    u = user_factory(role='viewer')
    user_permissions(u)
    with django_assert_num_queries(0):
        user_permissions(u)
