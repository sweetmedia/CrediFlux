"""
Filtros de lista del admin acotados al tenant de quien pide.

Va aparte de `admin_mixins` porque importa `django.contrib.admin` al cargarse, y
`admin_mixins` lo importan módulos que cargan antes que el admin (permisos, settings).
"""
from django.contrib.admin import RelatedFieldListFilter

from apps.core.admin_mixins import is_platform_admin


class TenantUserListFilter(RelatedFieldListFilter):
    """Filtro por un FK a usuarios que sólo lista los usuarios del tenant de quien pide.

    La tabla de usuarios es compartida entre tenants; el filtro de Django lista todas sus
    filas. Aquí entran los usuarios del tenant (también los inactivos: el filtro sirve para
    buscar datos históricos) y nunca los de otro tenant ni los de plataforma, aunque datos
    antiguos los tengan asignados. El superusuario de plataforma ve todos.
    """

    def field_choices(self, field, request, model_admin):
        if is_platform_admin(request.user):
            return super().field_choices(field, request, model_admin)
        tenant_id = getattr(request.user, 'tenant_id', None)
        if not tenant_id:
            return []
        ordering = self.field_admin_ordering(field, request, model_admin)
        return field.get_choices(
            include_blank=False, ordering=ordering, limit_choices_to={'tenant_id': tenant_id},
        )
