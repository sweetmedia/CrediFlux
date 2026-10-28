"""API de roles de la financiera y catálogo de permisos (D6, Task 12).

* `GET /api/users/permissions/catalog/`: el catálogo agrupado por módulo (cualquier autenticado).
* `/api/users/roles/` (por `key`): lectura con team.view; alta, edición (PATCH) y borrado con
  team.assign_roles. Sólo los roles de la financiera del usuario: los de otra dan 404.

Reglas:
* La clave se genera del nombre al crear (R15, `serializers_roles.clave_libre`) y no cambia.
* `admin` no se edita ni se borra; los demás de sistema editan permisos y descripción, pero no
  su nombre, y no se borran (400). Un rol con usuarios (también inactivos) no se borra (409).
* R14: quien no es dueño ni superusuario no deja en un rol, ni toca un rol que ya tenga, un
  código que él no tiene ni los de gestión del equipo (team.assign_roles, team.edit,
  team.delete), que sólo pone el dueño: 403 con `required_permission`. Tampoco edita el rol que
  él mismo tiene (sería escalarse a sí mismo).
* Auditoría en la financiera del actor: `create` con la lista de permisos, `role_change` con
  `added`/`removed` (y nombre/descripción si cambian) y `delete` con la clave.

Quitar un código de un rol vale desde el siguiente request de sus usuarios: el resolutor
(`authz.user_permissions`) memoiza por instancia de usuario, y DRF crea una por request.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.middleware import get_client_ip, get_user_agent
from apps.audit.models import AuditLog
from apps.tenants.models import Tenant

from .authz import (
    ViewPermissionRequired,
    denegar,
    invalidate_permissions,
    puede_dar_admin,
    user_permissions,
)
from .models_roles import Role
from .permissions_catalog import ALL_CODES
from .serializers_roles import RoleSerializer, catalogo, clave_libre

User = get_user_model()

# Códigos que sólo pone en un rol el dueño o el superusuario (R14).
CODIGOS_DE_GESTION = frozenset({'team.assign_roles', 'team.edit', 'team.delete'})

ADMIN_INTOCABLE = 'El rol Administrador no se edita ni se elimina.'
SISTEMA_NO_SE_BORRA = 'Un rol de sistema no se elimina.'
ROL_PROPIO = 'No puedes editar el rol que tienes asignado.'
SIN_FINANCIERA = 'Debes pertenecer a una financiera.'
CON_USUARIOS = 'No se puede eliminar un rol con usuarios asignados. Cámbiales el rol primero.'


def exigir_r14(actor, codigos):
    """403 si `actor` (no dueño ni superusuario) toca alguno de `codigos` que no tiene o que es
    de gestión del equipo; el primero en orden alfabético va en `required_permission`."""
    if puede_dar_admin(actor):
        return
    codigos = set(codigos) & ALL_CODES
    prohibidos = (codigos & CODIGOS_DE_GESTION) | (codigos - user_permissions(actor))
    if prohibidos:
        denegar(min(prohibidos))


def _rechazo(mensaje):
    return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)


class PermissionCatalogView(APIView):
    """Catálogo de permisos: `[{key, label, permissions: [{code, label}]}]`."""

    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {'GET': None}

    def get(self, request):
        return Response(catalogo())


class RoleViewSet(viewsets.ModelViewSet):
    """Roles (de sistema y propios) de la financiera del usuario."""

    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, ViewPermissionRequired]
    permission_codes = {
        'list': 'team.view',
        'retrieve': 'team.view',
        'create': 'team.assign_roles',
        'partial_update': 'team.assign_roles',
        'destroy': 'team.assign_roles',
    }
    # Sin PUT: la clave y (en los de sistema) el nombre no cambian; se edita con PATCH.
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    lookup_field = 'key'
    lookup_value_regex = '[-a-zA-Z0-9_]+'
    pagination_class = None  # pocos por financiera; el editor los quiere todos

    def get_queryset(self):
        tenant_id = self.request.user.tenant_id
        if tenant_id is None:
            return Role.objects.none()
        usuarios = (
            User.objects.filter(tenant_id=OuterRef('tenant_id'), role=OuterRef('key'))
            .order_by().values('tenant_id').annotate(n=Count('pk')).values('n')
        )
        return (
            Role.objects.filter(tenant_id=tenant_id)
            .annotate(user_count=Coalesce(Subquery(usuarios, output_field=IntegerField()), Value(0)))
            .order_by('-is_system', 'name')
        )

    def _respuesta(self, role, codigo):
        role = self.get_queryset().get(pk=role.pk)  # con user_count
        return Response(self.get_serializer(role).data, status=codigo)

    def _auditar(self, action, role, changes):
        request = self.request
        AuditLog.log(
            tenant=request.user.tenant, user=request.user, action=action, model_name='Role',
            object_id=role.key, object_repr=str(role), changes=changes,
            ip_address=get_client_ip(request), user_agent=get_user_agent(request),
        )

    def create(self, request, *args, **kwargs):
        tenant_id = request.user.tenant_id
        if tenant_id is None:
            raise PermissionDenied({'detail': SIN_FINANCIERA})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exigir_r14(request.user, serializer.validated_data['permissions'])
        with transaction.atomic():
            # El bloqueo de la financiera serializa las altas: dos con el mismo nombre no
            # eligen la misma clave.
            Tenant.objects.select_for_update().only('pk').get(pk=tenant_id)
            role = serializer.save(
                tenant_id=tenant_id, is_system=False,
                key=clave_libre(tenant_id, serializer.validated_data['name']),
            )
            self._auditar('create', role, {'permissions': role.permissions})
        return self._respuesta(role, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        actor = request.user
        with transaction.atomic():
            role = self.get_object()
            role = Role.objects.select_for_update().get(pk=role.pk)
            if role.key == 'admin':
                return _rechazo(ADMIN_INTOCABLE)
            if actor.role == role.key and not puede_dar_admin(actor):
                raise PermissionDenied({'detail': ROL_PROPIO})
            serializer = self.get_serializer(role, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            antes = set(role.permissions)
            despues = set(serializer.validated_data.get('permissions', role.permissions))
            exigir_r14(actor, antes | despues)

            cambios = {}
            for campo in ('name', 'description'):
                nuevo = serializer.validated_data.get(campo, getattr(role, campo))
                if nuevo != getattr(role, campo):
                    cambios[campo] = {'old': getattr(role, campo), 'new': nuevo}
            if antes != despues:
                cambios['added'] = sorted(despues - antes)
                cambios['removed'] = sorted(antes - despues)
            role = serializer.save()
            if cambios:
                self._auditar('role_change', role, cambios)
        # Los usuarios del rol lo ven en su siguiente request; el actor, ya.
        invalidate_permissions(actor)
        return self._respuesta(role, status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            role = self.get_object()
            if role.key == 'admin':
                return _rechazo(ADMIN_INTOCABLE)
            if role.is_system:
                return _rechazo(SISTEMA_NO_SE_BORRA)
            exigir_r14(request.user, role.permissions)
            role = Role.objects.select_for_update().get(pk=role.pk)
            n = User.objects.filter(tenant_id=role.tenant_id, role=role.key).count()
            if n:
                return Response({'detail': CON_USUARIOS, 'user_count': n}, status=status.HTTP_409_CONFLICT)
            cambios = {'key': role.key, 'permissions': role.permissions}
            self._auditar('delete', role, cambios)
            role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
