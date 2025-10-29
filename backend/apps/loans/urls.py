"""
URLs for loans app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, LoanViewSet, LoanPaymentViewSet,
    LoanScheduleViewSet, CollateralViewSet
)

app_name = 'loans'

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'', LoanViewSet, basename='loan')
router.register(r'payments', LoanPaymentViewSet, basename='payment')
router.register(r'schedules', LoanScheduleViewSet, basename='schedule')
router.register(r'collaterals', CollateralViewSet, basename='collateral')

urlpatterns = [
    path('', include(router.urls)),
]
