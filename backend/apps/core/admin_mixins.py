"""
Reglas compartidas del admin para el estado de plataforma.

El admin se sirve también en hosts de tenant y `TenantAccessControlMiddleware` deja pasar a
cualquier staff o superusuario del tenant del host. Los permisos de modelo de Django no bastan
para los módulos de estado global (tablas que sólo existen en el schema público y valen para
todos los tenants: Constance, Celery beat, tokens, emails de allauth, grupos, sites...): un
superusuario atado a un tenant los tiene todos implícitos. Esos módulos son sólo del
superusuario de plataforma (`is_superuser` y sin tenant).

La tabla de usuarios también es compartida: los admins de modelos de tenant con FK a usuarios
usan `TenantUserFKMixin` para no listar ni aceptar usuarios de otro tenant.

El log del admin (`django_admin_log`) también es una sola tabla en public: los admins de modelos
de tenant usan `TenantHistoryMixin` para que el historial de un objeto no muestre las entradas de
la fila con el mismo pk de otro tenant.
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


def _is_user_field(db_field):
    from django.contrib.auth import get_user_model
    return getattr(db_field, 'related_model', None) is get_user_model()


def tenant_users(user):
    """Usuarios activos del tenant de `user` (ninguno si no tiene tenant)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    tenant_id = getattr(user, 'tenant_id', None)
    if not tenant_id:
        return User.objects.none()
    return User.objects.filter(tenant_id=tenant_id, is_active=True)


class TenantUserFKMixin:
    """FKs y M2M a usuarios acotados al tenant de quien pide en formularios y filtros de lista.

    La tabla de usuarios es compartida (schema public): sin esto, los selects, los inlines y
    los filtros de lista del admin de un modelo de tenant listan a los usuarios de todos los
    tenants y de la plataforma, y el formulario acepta un usuario ajeno (igual que
    `loans.fields.TenantUserField` en la API). Para quien no es superusuario de plataforma el
    queryset del campo son los usuarios activos de su tenant, y como el formfield valida contra
    él, un POST con otro usuario no pasa. El usuario ya asignado al objeto que se edita se
    conserva aunque esté inactivo, para no vaciar el campo al guardar. Va antes de la clase
    base del admin (o del inline) en la herencia; los métodos que esa base no tiene (p. ej.
    `get_formset` en un ModelAdmin o `get_list_filter` en un inline) nunca se llaman.
    """

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if _is_user_field(db_field) and not is_platform_admin(request.user):
            kwargs['queryset'] = tenant_users(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if _is_user_field(db_field) and not is_platform_admin(request.user):
            kwargs['queryset'] = tenant_users(request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_list_filter(self, request):
        # Un FK a usuarios en `list_filter` usa el filtro acotado al tenant.
        from django.contrib.admin.utils import get_fields_from_path

        from apps.core.admin_filters import TenantUserListFilter

        list_filter = []
        for entry in super().get_list_filter(request):
            if isinstance(entry, str) and _is_user_field(get_fields_from_path(self.model, entry)[-1]):
                entry = (entry, TenantUserListFilter)
            list_filter.append(entry)
        return list_filter

    def get_form(self, request, obj=None, **kwargs):
        return _keep_assigned_users(super().get_form(request, obj, **kwargs), request)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # inlineformset_factory crea una clase nueva por llamada: el atributo no se comparte.
        formset.form = _keep_assigned_users(formset.form, request)
        return formset

    def get_changelist_form(self, request, **kwargs):
        return _keep_assigned_users(super().get_changelist_form(request, **kwargs), request)


def _keep_assigned_users(form_class, request):
    """Subclase de `form_class` que añade al select el usuario ya asignado al objeto.

    Sólo si es del tenant de quien pide (p. ej. un empleado que se desactivó): un usuario de
    otro tenant asignado por datos antiguos no entra en las opciones.
    """
    from django import forms

    tenant_id = getattr(request.user, 'tenant_id', None)
    if is_platform_admin(request.user) or not tenant_id:
        return form_class
    user_fks = {
        f.name for f in form_class._meta.model._meta.concrete_fields
        if f.many_to_one or f.one_to_one
        if _is_user_field(f)
    }
    # Un campo declarado con el nombre del FK pero de otro tipo (sin queryset) no se toca.
    names = [
        name for name, field in form_class.base_fields.items()
        if name in user_fks and isinstance(field, forms.ModelChoiceField)
    ]
    if not names:
        return form_class

    def __init__(self, *args, **kwargs):
        form_class.__init__(self, *args, **kwargs)
        for name in names:
            current = getattr(self.instance, f'{name}_id', None) if self.instance.pk else None
            if current:
                field = self.fields[name]
                field.queryset = field.queryset | field.queryset.model.objects.filter(
                    pk=current, tenant_id=tenant_id,
                )

    return type(form_class.__name__, (form_class,), {'__init__': __init__, '__module__': form_class.__module__})


def tenant_log_entries(entries):
    """`entries` (LogEntry) acotadas al tenant del host: sólo las escritas por sus usuarios.

    En el host público no se tocan. Las acciones del superusuario de plataforma sobre filas de
    un tenant quedan fuera del historial en el host del tenant (siguen visibles en el público):
    su usuario no tiene tenant y el log no guarda el schema de la fila.
    """
    from django.db import connection
    from django_tenants.utils import get_public_schema_name

    if connection.schema_name == get_public_schema_name():
        return entries
    tenant_id = getattr(connection.tenant, 'pk', None)
    if tenant_id is None:
        return entries.none()
    return entries.filter(user__tenant_id=tenant_id)


class TenantHistoryMixin:
    """Historial de objetos del admin acotado al tenant del host.

    `django_admin_log` es una sola tabla en public (`django.contrib.admin` sólo está en
    SHARED_APPS) y `history_view` la filtra sólo por `content_type` y `object_id`, que se
    repiten entre schemas: en el host del tenant A, `/admin/<app>/<modelo>/3/history/` mostraba
    quién cambió la fila 3 del tenant B, cuándo y el mensaje de cambio. Se deja a Django la
    búsqueda del objeto y los permisos, y se vuelve a paginar la lista con
    `tenant_log_entries`. Va antes de la clase base del admin en la herencia.
    """

    def history_view(self, request, object_id, extra_context=None):
        from django.contrib.admin.views.main import PAGE_VAR

        response = super().history_view(request, object_id, extra_context)
        context = getattr(response, 'context_data', None) or {}
        page = context.get('action_list')
        if page is None:  # redirección (objeto inexistente)
            return response
        paginator = self.get_paginator(
            request, tenant_log_entries(page.paginator.object_list), page.paginator.per_page,
        )
        page = paginator.get_page(request.GET.get(PAGE_VAR, 1))
        context.update(
            action_list=page,
            page_range=paginator.get_elided_page_range(page.number),
            pagination_required=paginator.count > paginator.per_page,
        )
        return response


def _prepend_mixin(site, mixin, models):
    """Vuelve a registrar en `site` los admins de `models` con `mixin` delante.

    Conserva la clase registrada por la app (sus listas, acciones y reglas) y sólo antepone el
    mixin. Un modelo que no esté registrado, o cuyo admin ya lo lleve, se ignora.
    """
    for model in models:
        if model not in site._registry:
            continue
        base = type(site._registry[model])
        if issubclass(base, mixin):
            continue
        wrapped = type(
            base.__name__,
            (mixin, base),
            {'__module__': __name__, '__doc__': base.__doc__},
        )
        site.unregister(model)
        site.register(model, wrapped)


def restrict_to_platform_admin(site, *models):
    """Vuelve a registrar en `site` los admins (de terceros) de `models` con
    `PlatformAdminOnlyMixin` delante."""
    _prepend_mixin(site, PlatformAdminOnlyMixin, models)


def scope_history_to_tenant(site, *models):
    """Vuelve a registrar en `site` los admins (de terceros) de modelos de tenant con
    `TenantHistoryMixin` delante."""
    _prepend_mixin(site, TenantHistoryMixin, models)
