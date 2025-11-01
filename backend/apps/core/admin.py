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
from django.http import JsonResponse
from django.core.management import call_command
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget
from unfold.decorators import action
from constance import config as constance_config
from constance.admin import ConstanceAdmin, Config
import io
import sys

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
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    """
    Periodic Task admin with Unfold styling
    Inherits from both django-celery-beat's admin and Unfold's ModelAdmin
    """
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):
    """Interval Schedule admin with Unfold styling"""
    pass


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    """Crontab Schedule admin with Unfold styling"""
    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(ModelAdmin):
    """Solar Schedule admin with Unfold styling"""
    pass


@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    """Clocked Schedule admin with Unfold styling"""
    pass


# ============================================================================
# CONSTANCE ADMIN CUSTOMIZATION
# ============================================================================

# Unregister default Constance admin
admin.site.unregister([Config])


@admin.register(Config)
class CustomConstanceAdmin(ConstanceAdmin):
    """
    Custom Constance admin with RNC database update button
    """
    change_list_template = 'admin/constance_change_list.html'

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
        """Execute the update_rnc_database management command"""
        if request.method == 'POST':
            force = request.POST.get('force', 'false') == 'true'

            try:
                # Check if RNC is enabled
                if not constance_config.DGII_RNC_ENABLED:
                    messages.warning(
                        request,
                        'DGII RNC validation is currently disabled. '
                        'Enable it in the configuration to update the database.'
                    )
                    return redirect('admin:constance_config_changelist')

                # Capture command output
                output = io.StringIO()
                call_command('update_rnc_database', force=force, stdout=output)

                # Show success message with output
                output_text = output.getvalue()
                messages.success(
                    request,
                    f'RNC database updated successfully!\n\n{output_text}'
                )

            except Exception as e:
                messages.error(
                    request,
                    f'Error updating RNC database: {str(e)}'
                )

            return redirect('admin:constance_config_changelist')

        # For GET request, show confirmation page
        context = {
            'title': 'Update RNC Database',
            'opts': self.model._meta,
            'has_permission': True,
            'site_title': self.admin_site.site_title,
            'site_header': self.admin_site.site_header,
            'rnc_enabled': constance_config.DGII_RNC_ENABLED,
            'rnc_url': constance_config.DGII_RNC_DATABASE_URL,
            'cache_timeout_days': constance_config.DGII_RNC_CACHE_TIMEOUT_DAYS,
        }
        return render(request, 'admin/constance_update_rnc.html', context)

    def changelist_view(self, request, extra_context=None):
        """Add custom context for the change list view"""
        extra_context = extra_context or {}
        extra_context['show_rnc_update_button'] = True
        extra_context['rnc_enabled'] = constance_config.DGII_RNC_ENABLED
        return super().changelist_view(request, extra_context=extra_context)
