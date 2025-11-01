"""
Core app URLs
"""
from django.urls import path
from .views import HealthCheckView, validate_rnc_view, rnc_database_status, get_ui_theme, get_tenant_config

app_name = 'core'

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('validate-rnc/', validate_rnc_view, name='validate-rnc'),
    path('rnc-database-status/', rnc_database_status, name='rnc-database-status'),
    path('ui-theme/', get_ui_theme, name='ui-theme'),
    path('config/', get_tenant_config, name='tenant-config'),
]
