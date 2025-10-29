"""
URL configuration for Tenant API endpoints
"""
from django.urls import path
from .views import TenantRegistrationView, TenantHealthCheckView, TenantLoginView

app_name = 'tenants'

urlpatterns = [
    # Public endpoints
    path('register/', TenantRegistrationView.as_view(), name='register'),
    path('login/', TenantLoginView.as_view(), name='login'),
    path('health/', TenantHealthCheckView.as_view(), name='health'),
]
