"""
URLs for loans app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, CustomerDocumentViewSet, LoanViewSet, LoanPaymentViewSet,
    LoanScheduleViewSet, CollateralViewSet, CollectionReminderViewSet, CollectionContactViewSet,
    ContractTemplateViewSet, ContractViewSet
)

app_name = 'loans'

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'customer-documents', CustomerDocumentViewSet, basename='customer-document')
router.register(r'payments', LoanPaymentViewSet, basename='payment')
router.register(r'schedules', LoanScheduleViewSet, basename='schedule')
router.register(r'collaterals', CollateralViewSet, basename='collateral')
router.register(r'collection-reminders', CollectionReminderViewSet, basename='collection-reminder')
router.register(r'collection-contacts', CollectionContactViewSet, basename='collection-contact')
router.register(r'contract-templates', ContractTemplateViewSet, basename='contract-template')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'', LoanViewSet, basename='loan')  # Root viewset must be last

urlpatterns = [
    path('', include(router.urls)),
]
