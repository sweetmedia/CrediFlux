from django.urls import path
from .views import AuditLogListView, AuditLogDetailView, AuditLogStatsView

app_name = 'audit'

urlpatterns = [
    path('', AuditLogListView.as_view(), name='audit-list'),
    path('stats/', AuditLogStatsView.as_view(), name='audit-stats'),
    path('<uuid:id>/', AuditLogDetailView.as_view(), name='audit-detail'),
]
