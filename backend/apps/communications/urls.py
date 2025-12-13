"""
URL configuration for Communications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet

app_name = 'communications'

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
]
