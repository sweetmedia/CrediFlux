"""
Reglas compartidas del admin para el estado de plataforma.

El admin se sirve también en hosts de tenant y `TenantAccessControlMiddleware` deja pasar a
cualquier staff o superusuario del tenant del host. Los permisos de modelo de Django no bastan
para los módulos de estado global (tablas que sólo existen en el schema público y valen para
todos los tenants: Constance, Celery beat, tokens, emails de allauth, grupos, sites...): un
superusuario atado a un tenant los tiene todos implícitos. Esos módulos son sólo del
superusuario de plataforma (`is_superuser` y sin tenant).
"""


def is_platform_admin(user):
    """True sólo para el superusuario de plataforma (`is_superuser` y `tenant=None`).

    Seguro con `AnonymousUser` (no tiene `tenant_id`) y con `None`.
    """
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_superuser
        and user.tenant_id is None
    )


class PlatformAdminOnlyMixin:
    """Módulo, vista, alta, edición y borrado sólo para el superusuario de plataforma.

    Ni los permisos de modelo ni ser superusuario de un tenant bastan: el admin también se
    sirve en hosts de tenant, y estos modelos son de todos los tenants. Va antes de la clase
    base del admin en la herencia; las reglas propias de la base siguen aplicando encima.
    """

    def has_module_permission(self, request):
        return is_platform_admin(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return is_platform_admin(request.user) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return is_platform_admin(request.user) and super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return is_platform_admin(request.user) and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return is_platform_admin(request.user) and super().has_delete_permission(request, obj)


def restrict_to_platform_admin(site, *models):
    """Vuelve a registrar en `site` los admins (de terceros) de `models` con el mixin delante.

    Conserva la clase registrada por la app (sus listas, acciones y reglas) y sólo antepone
    `PlatformAdminOnlyMixin`. Un modelo que no esté registrado se ignora.
    """
    for model in models:
        if model not in site._registry:
            continue
        base = type(site._registry[model])
        if issubclass(base, PlatformAdminOnlyMixin):
            continue
        restricted = type(
            base.__name__,
            (PlatformAdminOnlyMixin, base),
            {'__module__': __name__, '__doc__': base.__doc__},
        )
        site.unregister(model)
        site.register(model, restricted)
