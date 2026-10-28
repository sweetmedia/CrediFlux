"""Serializers de la API de roles y del catálogo de permisos (D6, Task 12)."""
from django.utils.text import slugify
from rest_framework import serializers

from .models_roles import Role
from .permissions_catalog import ALL_CODES, SYSTEM_ROLES

LARGO_CLAVE = Role._meta.get_field('key').max_length  # 30, igual que User.role

NOMBRE_SIN_CLAVE = 'El nombre debe tener al menos una letra o un número.'
NOMBRE_DE_SISTEMA = 'El nombre de un rol de sistema no se cambia.'


class RoleSerializer(serializers.ModelSerializer):
    """Rol de la financiera. `key` y `is_system` son de sólo lectura (la clave se genera del
    nombre al crear y no cambia); `user_count` la anota el queryset de la vista."""

    permissions = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = ['key', 'name', 'description', 'is_system', 'permissions', 'user_count']
        read_only_fields = ['key', 'is_system']

    def validate_name(self, value):
        value = value.strip()
        if self.instance is not None and self.instance.is_system and value != self.instance.name:
            raise serializers.ValidationError(NOMBRE_DE_SISTEMA)
        if not clave_base(value):
            raise serializers.ValidationError(NOMBRE_SIN_CLAVE)
        return value

    def validate_permissions(self, value):
        desconocidos = sorted(set(value) - ALL_CODES)
        if desconocidos:
            raise serializers.ValidationError(
                f'Códigos de permiso desconocidos: {", ".join(desconocidos)}.'
            )
        return sorted(set(value))  # sin duplicados, orden estable (como Role.clean)


def clave_base(nombre):
    """Clave candidata para `nombre` (R15): slugify en minúsculas, sin guiones en los bordes y
    recortada a la longitud de la clave."""
    return slugify(nombre).lower()[:LARGO_CLAVE].strip('-_')


def clave_libre(tenant_id, nombre):
    """Primera clave libre en la financiera para `nombre`: la base, o base-2, base-3…

    Las claves de los roles de sistema están reservadas aunque la financiera no tuviera ese
    rol. El sufijo se hace sitio recortando la base para que el total quepa en 30.
    """
    base = clave_base(nombre)
    usadas = set(Role.objects.filter(tenant_id=tenant_id).values_list('key', flat=True)) | set(SYSTEM_ROLES)
    if base not in usadas:
        return base
    n = 2
    while True:
        sufijo = f'-{n}'
        candidata = base[:LARGO_CLAVE - len(sufijo)].rstrip('-_') + sufijo
        if candidata not in usadas:
            return candidata
        n += 1


def catalogo():
    """Catálogo de permisos para el editor de roles: módulos con sus códigos y etiquetas."""
    from .permissions_catalog import MODULES

    return [
        {
            'key': key,
            'label': label,
            'permissions': [{'code': code, 'label': code_label} for code, code_label in items],
        }
        for key, label, items in MODULES
    ]
