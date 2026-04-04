from django.urls import path
from . import views

app_name = 'ai'

urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('agents/', views.AgentsListView.as_view(), name='agents-list'),
]
