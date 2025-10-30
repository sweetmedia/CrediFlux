"""
Core app URLs
"""
from django.urls import path
from .views import HealthCheckView, validate_rnc_view, rnc_database_status

app_name = 'core'

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('validate-rnc/', validate_rnc_view, name='validate-rnc'),
    path('rnc-database-status/', rnc_database_status, name='rnc-database-status'),
]
