"""
URL Configuration for the Billing app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DigitalCertificateViewSet,
    FiscalSequenceViewSet,
    InvoiceViewSet,
    ECFSubmissionViewSet,
    DGIIReportViewSet,
)

router = DefaultRouter()
router.register(r'certificates', DigitalCertificateViewSet, basename='certificate')
router.register(r'sequences', FiscalSequenceViewSet, basename='sequence')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'submissions', ECFSubmissionViewSet, basename='submission')
router.register(r'dgii-reports', DGIIReportViewSet, basename='dgii-report')

app_name = 'billing'

urlpatterns = [
    path('', include(router.urls)),
]
