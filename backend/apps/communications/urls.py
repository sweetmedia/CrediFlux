"""
URL configuration for Communications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet
from .views_whatsapp import WhatsAppConversationViewSet

app_name = 'communications'

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'whatsapp/conversations', WhatsAppConversationViewSet, basename='whatsapp-conversation')

urlpatterns = [
    path('', include(router.urls)),
]
