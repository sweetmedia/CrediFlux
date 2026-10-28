"""Roles editables por financiera (D6).

Un `Role` pertenece a una financiera (tenant) y guarda la lista de códigos del catálogo
(`permissions_catalog.ALL_CODES`) que concede. Vive en el esquema público, como `User`, porque
`apps.users` está sólo en SHARED_APPS. Cada financiera nace con los 8 roles de sistema
(`ensure_system_roles`); los puede editar y crear otros (p. ej. `cobrador-norte`), y una clave
repetida en dos financieras son filas independientes.
"""
from django.core.exceptions import ValidationError
from django.db import models

from .permissions_catalog import ALL_CODES, DEFAULT_ROLE_PERMISSIONS, SYSTEM_ROLES


class Role(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='roles',
        help_text='Financiera dueña del rol.',
    )
    key = models.SlugField(max_length=50, help_text='Clave del rol (la que guarda User.role).')
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default='')
    is_system = models.BooleanField(
        default=False,
        help_text='Rol de sistema creado con la financiera.',
    )
    permissions = models.JSONField(default=list, blank=True, help_text='Códigos del catálogo de permisos.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('tenant', 'key')]
        ordering = ['tenant', 'name']
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return f'{self.name} ({self.key})'

    def clean(self):
        super().clean()
        if not isinstance(self.permissions, list) or not all(isinstance(c, str) for c in self.permissions):
            raise ValidationError({'permissions': 'Debe ser una lista de códigos de permiso.'})
        desconocidos = sorted(set(self.permissions) - ALL_CODES)
        if desconocidos:
            raise ValidationError({'permissions': f'Códigos de permiso desconocidos: {", ".join(desconocidos)}.'})


def crear_roles_de_sistema(tenant, role_model=Role):
    """Crea los roles de sistema que falten en `tenant`; nunca toca uno existente.

    Recibe el modelo para que la migración de datos pase el histórico (`apps.get_model`).
    """
    existentes = set(role_model.objects.filter(tenant=tenant).values_list('key', flat=True))
    role_model.objects.bulk_create([
        role_model(
            tenant=tenant,
            key=key,
            name=name,
            description=description,
            is_system=True,
            permissions=sorted(DEFAULT_ROLE_PERMISSIONS[key]),
        )
        for key, (name, description) in SYSTEM_ROLES.items()
        if key not in existentes
    ], ignore_conflicts=True)  # dos altas simultáneas no chocan con unique_together


def crear_roles_de_sistema_para_todos(tenant_model, role_model=Role):
    """Roles de sistema para cada financiera existente (migración de datos)."""
    for tenant in tenant_model.objects.all().iterator():
        crear_roles_de_sistema(tenant, role_model)


def ensure_system_roles(tenant):
    """Asegura los 8 roles de sistema de la financiera. Idempotente."""
    crear_roles_de_sistema(tenant, Role)
