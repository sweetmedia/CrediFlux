"""Resolutor de permisos y PermissionRequired (D6, Task 8)."""
import pytest
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.users.authz import (
    PermissionRequired, ViewPermissionRequired, has_perm, invalidate_permissions, user_permissions,
)
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
    assert resp.data['detail'] == 'Acción no configurada.'


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


# --- R12: OPTIONS, huecos del mapa, HEAD, 405 e invalidate_permissions -----------------------


def test_head_usa_el_codigo_de_get(roles, user_factory):
    viewer = user_factory(role='viewer')
    assert _llamar(viewer, 'head').status_code == 200
    Role.objects.filter(tenant=roles, key='viewer').update(permissions=[])
    resp = _llamar(User.objects.get(pk=viewer.pk), 'head')
    assert resp.status_code == 403
    assert resp.data['required_permission'] == 'customers.view'


def test_options_sin_mapear_pasa_a_cualquier_autenticado(roles, user_factory):
    sin_nada = user_factory(role='cashier')
    Role.objects.filter(tenant=roles, key='cashier').update(permissions=[])
    assert _llamar(User.objects.get(pk=sin_nada.pk), 'options').status_code == 200
    request = APIRequestFactory().options('/x/')
    assert VistaMetodos.as_view()(request).status_code in (401, 403)  # sin sesión, no


def test_metodo_sin_mapear_deja_warning(roles, user_factory, caplog):
    u = user_factory(role='admin', is_tenant_owner=True)
    with caplog.at_level('WARNING', logger='apps.users.authz'):
        resp = _llamar(u, 'delete')
    assert resp.status_code == 403
    assert resp.data == {'detail': 'Acción no configurada.'}
    assert any('VistaMetodos' in r.getMessage() and 'DELETE' in r.getMessage() for r in caplog.records)


def test_metodo_sin_manejador_es_405_no_403(roles, user_factory):
    u = user_factory(role='viewer')
    request = APIRequestFactory().put('/x/')  # VistaMetodos no define put
    force_authenticate(request, user=u)
    assert VistaMetodos.as_view()(request).status_code == 405


class _VistaConMapa(APIView):
    permission_classes = [ViewPermissionRequired]
    permission_codes = {'GET': 'loans.view', 'POST': 'loans.create'}

    def get(self, request):
        return Response({'ok': True})

    post = delete = get


def test_view_permission_required_lee_el_mapa_de_la_vista(roles, user_factory, caplog):
    def llamar(user, metodo):
        request = getattr(APIRequestFactory(), metodo)('/x/')
        force_authenticate(request, user=user)
        return _VistaConMapa.as_view()(request)

    oficial, cajero = user_factory(role='loan_officer'), user_factory(role='cashier')
    assert llamar(oficial, 'get').status_code == 200
    assert llamar(oficial, 'head').status_code == 200
    assert llamar(oficial, 'post').status_code == 200
    resp = llamar(cajero, 'post')
    assert resp.status_code == 403 and resp.data['required_permission'] == 'loans.create'
    with caplog.at_level('WARNING', logger='apps.users.authz'):
        resp = llamar(oficial, 'delete')
    assert resp.data == {'detail': 'Acción no configurada.'}
    assert any('_VistaConMapa' in r.getMessage() for r in caplog.records)


def test_view_permission_required_en_un_viewset_por_accion(roles, user_factory, caplog):
    from rest_framework import viewsets

    class ViewSetConMapa(viewsets.ViewSet):
        permission_classes = [ViewPermissionRequired]
        permission_codes = {'list': 'loans.view', 'create': 'loans.create'}

        def list(self, request, **kw):
            return Response([])

        def create(self, request, **kw):
            return Response({})

        def destroy(self, request, pk=None):
            return Response(status=204)

    def llamar(user, metodo, actions):
        request = getattr(APIRequestFactory(), metodo)('/x/')
        force_authenticate(request, user=user)
        return ViewSetConMapa.as_view(actions)(request, pk='1')

    oficial, viewer = user_factory(role='loan_officer'), user_factory(role='viewer')
    assert llamar(viewer, 'get', {'get': 'list'}).status_code == 200
    assert llamar(viewer, 'options', {'get': 'list', 'post': 'create'}).status_code == 200
    resp = llamar(viewer, 'post', {'get': 'list', 'post': 'create'})
    assert resp.status_code == 403 and resp.data['required_permission'] == 'loans.create'
    assert llamar(oficial, 'post', {'get': 'list', 'post': 'create'}).status_code == 200
    with caplog.at_level('WARNING', logger='apps.users.authz'):
        resp = llamar(oficial, 'delete', {'delete': 'destroy'})
    assert resp.status_code == 403 and resp.data == {'detail': 'Acción no configurada.'}
    assert any('acción destroy' in r.getMessage() for r in caplog.records)
    # Método sin acción enrutada: 405 de DRF, sin warning.
    caplog.clear()
    with caplog.at_level('WARNING', logger='apps.users.authz'):
        assert llamar(oficial, 'put', {'get': 'list'}).status_code == 405
    assert not caplog.records


def test_invalidate_permissions_olvida_el_memo(roles, user_factory):
    u = user_factory(role='viewer')
    assert has_perm(u, 'customers.view')
    Role.objects.filter(tenant=roles, key='viewer').update(permissions=[])
    assert has_perm(u, 'customers.view')  # memo de la instancia
    invalidate_permissions(u)
    assert not has_perm(u, 'customers.view')
    invalidate_permissions(u)  # sin memo: no falla


class _VistaAbiertaYPorMetodo(APIView):
    permission_classes = [ViewPermissionRequired]
    permission_codes = {'GET': None, 'PATCH': 'loans.edit'}

    def get(self, request):
        return Response({'ok': True})

    patch = delete = get


def test_none_en_el_mapa_es_solo_autenticado_y_lo_ausente_sigue_negado(roles, user_factory):
    def llamar(user, metodo):
        request = getattr(APIRequestFactory(), metodo)('/x/')
        force_authenticate(request, user=user)
        return _VistaAbiertaYPorMetodo.as_view()(request)

    Role.objects.filter(tenant=roles, key='viewer').update(permissions=[])
    sin_nada = user_factory(role='viewer')
    assert llamar(sin_nada, 'get').status_code == 200
    assert llamar(sin_nada, 'head').status_code == 200
    resp = llamar(sin_nada, 'patch')
    assert resp.status_code == 403 and resp.data['required_permission'] == 'loans.edit'
    assert llamar(sin_nada, 'delete').data == {'detail': 'Acción no configurada.'}


class _ViewSetPorMetodo(viewsets.ViewSet):
    permission_classes = [ViewPermissionRequired]
    permission_codes = {'config': {'GET': 'loans.view', 'PATCH': 'loans.edit'}}

    @action(detail=False, methods=['get', 'patch', 'post'])
    def config(self, request):
        return Response({'ok': True})


def test_codigo_por_metodo_dentro_de_una_accion(roles, user_factory):
    def llamar(user, metodo):
        request = getattr(APIRequestFactory(), metodo)('/x/')
        force_authenticate(request, user=user)
        return _ViewSetPorMetodo.as_view({'get': 'config', 'patch': 'config', 'post': 'config'})(request)

    cajero = user_factory(role='cashier')  # loans.view sí, loans.edit no
    assert llamar(cajero, 'get').status_code == 200
    resp = llamar(cajero, 'patch')
    assert resp.status_code == 403 and resp.data['required_permission'] == 'loans.edit'
    assert llamar(cajero, 'post').data == {'detail': 'Acción no configurada.'}
    assert llamar(user_factory(role='loan_officer'), 'patch').status_code == 200
