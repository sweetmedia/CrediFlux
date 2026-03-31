"""URL Configuration for the Cashbox app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CashRegisterViewSet,
    CashSessionViewSet,
    CashMovementViewSet,
    DenominationCountViewSet,
)

router = DefaultRouter()
router.register(r'registers', CashRegisterViewSet, basename='register')
router.register(r'sessions', CashSessionViewSet, basename='session')
router.register(r'movements', CashMovementViewSet, basename='movement')
router.register(r'denominations', DenominationCountViewSet, basename='denomination')

app_name = 'cashbox'

urlpatterns = [
    path('', include(router.urls)),
]
