"""Andamiaje común de los tests de permisos por código (D6): completitud del mapa
`permission_codes` de cada viewset y edición de los permisos de un Role."""
import inspect

from rest_framework import viewsets

from apps.users.models import Role

ACCIONES_CRUD = ('list', 'retrieve', 'create', 'update', 'partial_update', 'destroy')
METODO_DE = {'list': 'get', 'retrieve': 'get', 'create': 'post', 'update': 'put',
             'partial_update': 'patch', 'destroy': 'delete'}
UUID = '00000000-0000-0000-0000-000000000000'


def viewsets_de(*modulos):
    """Los viewsets definidos en cada módulo (no los importados)."""
    return [
        cls for modulo in modulos
        for _, cls in inspect.getmembers(modulo, inspect.isclass)
        if issubclass(cls, viewsets.ViewSetMixin) and cls.__module__ == modulo.__name__
    ]


def acciones_enrutables(cls):
    """Acciones CRUD que la clase define (y su método HTTP admite) más las @action."""
    acciones = {a for a in ACCIONES_CRUD if hasattr(cls, a) and METODO_DE[a] in cls.http_method_names}
    return acciones | {a.__name__ for a in cls.get_extra_actions()}


def comprobar_completitud(cls):
    """Cada acción enrutable del viewset tiene su código, y todos están en el catálogo."""
    from apps.users.permissions_catalog import ALL_CODES

    mapa = getattr(cls, 'permission_codes', None)
    assert mapa, f'{cls.__name__} sin permission_codes'
    assert set(mapa) == acciones_enrutables(cls), set(mapa) ^ acciones_enrutables(cls)
    codigos = set()
    for valor in mapa.values():
        codigos |= set(valor.values()) if isinstance(valor, dict) else {valor}
    assert codigos - {None} <= ALL_CODES


def cambiar_rol(tenant, rol, quitar=(), dar=()):
    """Quita y/o da códigos al Role de sistema `rol` del tenant."""
    role = Role.objects.get(tenant=tenant, key=rol)
    role.permissions = sorted((set(role.permissions) - set(quitar)) | set(dar))
    role.save()


def comprobar_completitud_apiview(cls):
    """Como comprobar_completitud, para una APIView: exige ViewPermissionRequired y un código (o
    `None` explícito) por cada método HTTP con manejador (OPTIONS y HEAD siguen a DRF/GET)."""
    from apps.users.authz import ViewPermissionRequired
    from apps.users.permissions_catalog import ALL_CODES

    assert any(issubclass(p, ViewPermissionRequired) for p in cls.permission_classes), cls.__name__
    mapa = getattr(cls, 'permission_codes', None)
    assert mapa, f'{cls.__name__} sin permission_codes'
    metodos = {m.upper() for m in cls.http_method_names
               if m not in ('options', 'head') and hasattr(cls, m)}
    assert set(mapa) == metodos, set(mapa) ^ metodos
    assert {c for c in mapa.values() if c is not None} <= ALL_CODES
