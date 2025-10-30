"""
Core admin configuration
Django-Celery-Beat Integration with Unfold
Following official Unfold integration guide:
https://unfoldadmin.com/docs/integrations/django-celery-beat/
"""
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

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
