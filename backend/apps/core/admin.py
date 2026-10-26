"""
Core admin configuration
Django-Celery-Beat Integration with Unfold
Following official Unfold integration guide:
https://unfoldadmin.com/docs/integrations/django-celery-beat/
"""
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget
from unfold.decorators import action
from constance import config as constance_config
from constance.admin import ConstanceAdmin, Config
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from rest_framework.authtoken.models import TokenProxy
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
import logging
import sys

from .admin_mixins import PlatformAdminOnlyMixin, is_platform_admin, restrict_to_platform_admin
from .models import PadronJCE

logger = logging.getLogger(__name__)

# Import custom allauth admin configurations
# These are auto-registered via @admin.register decorators
# Unregistering happens inside admin_account.py to avoid order issues
from .admin_account import EmailAddressAdmin, EmailConfirmationAdmin

from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from django_celery_beat.admin import (
    ClockedScheduleAdmin as BaseClockedScheduleAdmin,
    CrontabScheduleAdmin as BaseCrontabScheduleAdmin,
    PeriodicTaskAdmin as BasePeriodicTaskAdmin,
    PeriodicTaskForm,
    TaskSelectWidget,
)

# Celery beat es de la plataforma (schema público, lo ejecuta el beat de todos los tenants):
# sus admins sólo los ve y edita el superusuario de plataforma.
# Unregister default django-celery-beat admin classes
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)


# Custom widgets for Unfold integration
class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    """Widget that combines Unfold styling with django-celery-beat task selection"""
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    """Custom form for PeriodicTask with Unfold widgets"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


# Register models with Unfold styling
@admin.register(PeriodicTask)
class PeriodicTaskAdmin(PlatformAdminOnlyMixin, BasePeriodicTaskAdmin, ModelAdmin):
    """
    Periodic Task admin with Unfold styling
    Inherits from both django-celery-beat's admin and Unfold's ModelAdmin
    """
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(PlatformAdminOnlyMixin, ModelAdmin):
    """Interval Schedule admin with Unfold styling"""
    pass


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(PlatformAdminOnlyMixin, BaseCrontabScheduleAdmin, ModelAdmin):
    """Crontab Schedule admin with Unfold styling"""
    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(PlatformAdminOnlyMixin, ModelAdmin):
    """Solar Schedule admin with Unfold styling"""
    pass


@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(PlatformAdminOnlyMixin, BaseClockedScheduleAdmin, ModelAdmin):
    """Clocked Schedule admin with Unfold styling"""
    pass


# ============================================================================
# CONSTANCE ADMIN CUSTOMIZATION
# ============================================================================

# Unregister default Constance admin
admin.site.unregister([Config])


@admin.register(Config)
class CustomConstanceAdmin(PlatformAdminOnlyMixin, ConstanceAdmin):
    """
    Custom Constance admin with RNC database update button.

    Sólo del superusuario de plataforma: la configuración es una sola para todos los tenants.
    """
    change_list_template = 'admin/constance/change_list.html'

    def get_urls(self):
        """Add custom URL for RNC database update"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'update-rnc-database/',
                self.admin_site.admin_view(self.update_rnc_database_view),
                name='constance_update_rnc_database',
            ),
        ]
        return custom_urls + urls

    def update_rnc_database_view(self, request):
        """Encola la actualización del RNC (sólo superusuarios de plataforma)."""
        if not is_platform_admin(request.user):
            raise PermissionDenied

        if request.method == 'POST':
            # Check if RNC is enabled
            if not constance_config.DGII_RNC_ENABLED:
                messages.warning(
                    request,
                    'La validación del RNC de la DGII está desactivada. '
                    'Actívela en la configuración para actualizar la base de datos.'
                )
                return redirect('admin:constance_config_changelist')

            from apps.core.tasks import update_rnc_database

            try:
                update_rnc_database.delay()
            except Exception:
                logger.exception('No se pudo encolar la actualización del RNC')
                messages.error(request, 'No se pudo encolar la actualización del RNC.')
            else:
                messages.success(request, 'Actualización del RNC encolada.')

            return redirect('admin:constance_config_changelist')

        # For GET request, show confirmation page
        # Try to get database stats from cache
        from apps.core.services.rnc_lookup import RNCLookupService
        db_stats = None
        meta = RNCLookupService.get_database_stats()
        if meta:
            total = meta.get('count', 0)
            db_stats = {
                'total_records': f'{total:,}' if isinstance(total, int) else total,
                'last_updated': meta.get('loaded_at', '—'),
            }

        context = {
            'title': 'Update RNC Database',
            'opts': self.model._meta,
            'has_permission': True,
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'rnc_enabled': constance_config.DGII_RNC_ENABLED,
            'rnc_url': constance_config.DGII_RNC_DATABASE_URL,
            'cache_timeout_days': constance_config.DGII_RNC_CACHE_TIMEOUT_DAYS,
            'auto_update': constance_config.DGII_RNC_AUTO_UPDATE,
            'update_hour': constance_config.DGII_RNC_UPDATE_HOUR,
            'db_stats': db_stats,
        }
        return render(request, 'admin/constance_update_rnc.html', context)

    def changelist_view(self, request, extra_context=None):
        """Add custom context for the change list view"""
        extra_context = extra_context or {}
        extra_context['show_rnc_update_button'] = True
        extra_context['rnc_enabled'] = constance_config.DGII_RNC_ENABLED
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================================
# PADRON JCE
# ============================================================================

@admin.register(PadronJCE)
class PadronJCEAdmin(PlatformAdminOnlyMixin, ModelAdmin):
    """Read-only admin for JCE Padrón (~7.9M citizens). Sólo plataforma: es un dato nacional, no de un tenant."""
    list_display = ['cedula', 'nombres', 'apellido1', 'apellido2', 'fecha_nacimiento']
    search_fields = ['cedula', 'nombres', 'apellido1', 'apellido2']
    list_filter = ['fecha_nacimiento']
    readonly_fields = ['cedula', 'nombres', 'apellido1', 'apellido2', 'fecha_nacimiento']
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ============================================================================
# ADMINS DE TERCEROS SOBRE ESTADO DE PLATAFORMA
# ============================================================================
# Grupos, sites, tokens (authtoken y la lista negra de simplejwt) y socialaccount viven sólo en el
# schema público y valen para todos los tenants. Sus apps los registran con los permisos de modelo
# de Django, que un superusuario atado a un tenant tiene implícitos: se vuelven a registrar con
# PlatformAdminOnlyMixin delante. Este módulo carga después de esas apps (orden de INSTALLED_APPS).

restrict_to_platform_admin(
    admin.site,
    Group,
    Site,
    TokenProxy,
    OutstandingToken,
    BlacklistedToken,
    SocialApp,
    SocialAccount,
    SocialToken,
)
