"""
Core admin configuration for dynamic settings (Constance)
"""
from django.contrib import admin
from django.utils.html import format_html
from constance import config
from constance.admin import ConstanceAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import display


class CustomConstanceAdmin(ConstanceAdmin):
    """
    Custom Constance admin with Unfold styling and best practices
    """
    # Unfold specific settings
    change_form_template = 'unfold/admin/constance/change_form.html'

    class Media:
        css = {
            'all': ('unfold/css/styles.css',)
        }
        js = ('unfold/js/scripts.js',)

    def changelist_view(self, request, extra_context=None):
        """
        Override changelist_view to use Unfold styling
        """
        extra_context = extra_context or {}
        extra_context['title'] = 'Application Settings'
        extra_context['subtitle'] = 'Configure dynamic application settings'
        extra_context['site_title'] = 'CrediFlux Admin'
        extra_context['site_header'] = 'Application Settings'

        return super().changelist_view(request, extra_context)

    def has_module_permission(self, request):
        """Only show for superusers"""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Only allow view for superusers"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Only allow change for superusers"""
        return request.user.is_superuser


# Unregister the default Constance admin
try:
    from constance.admin import Config
    admin.site.unregister([Config])
except:
    pass

# Register our custom admin
try:
    from constance.admin import Config
    admin.site.register([Config], CustomConstanceAdmin)
except:
    pass
