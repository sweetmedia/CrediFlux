"""
Admin configuration for the Billing app.
Uses Django Unfold for a modern admin experience.
"""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    DigitalCertificate, FiscalSequence, Invoice, InvoiceItem, ECFSubmission
)


class InvoiceItemInline(TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['line_number', 'description', 'quantity', 'unit_price', 'itbis_rate', 'itbis_amount', 'total']
    readonly_fields = ['itbis_amount', 'total']


class ECFSubmissionInline(TabularInline):
    model = ECFSubmission
    extra = 0
    fields = ['action', 'environment', 'trackid', 'response_status', 'http_status_code', 'submitted_at']
    readonly_fields = ['action', 'environment', 'trackid', 'response_status', 'http_status_code', 'submitted_at']
    can_delete = False


@admin.register(DigitalCertificate)
class DigitalCertificateAdmin(ModelAdmin):
    list_display = ['name', 'issuer', 'valid_from', 'valid_until', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'issuer', 'serial_number']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FiscalSequence)
class FiscalSequenceAdmin(ModelAdmin):
    list_display = ['ecf_type', 'prefix', 'range_from', 'range_to', 'current_number', 'available_count', 'expiration_date', 'is_active']
    list_filter = ['ecf_type', 'is_active']
    search_fields = ['prefix', 'authorization_number']
    readonly_fields = ['created_at', 'updated_at']

    def available_count(self, obj):
        return obj.available_count
    available_count.short_description = 'Disponibles'


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ['encf_number', 'ecf_type', 'comprador_razon_social', 'total', 'status', 'issue_date', 'dgii_status']
    list_filter = ['status', 'ecf_type', 'issue_date']
    search_fields = ['encf_number', 'comprador_razon_social', 'comprador_rnc', 'dgii_trackid']
    readonly_fields = [
        'created_at', 'updated_at', 'created_by',
        'dgii_trackid', 'dgii_status', 'dgii_response', 'dgii_submitted_at',
        'xml_content', 'signed_xml',
    ]
    date_hierarchy = 'issue_date'
    inlines = [InvoiceItemInline, ECFSubmissionInline]

    fieldsets = (
        ('Identificación Fiscal', {
            'fields': ('ecf_type', 'encf_number', 'fiscal_sequence', 'security_code', 'status')
        }),
        ('Vinculación', {
            'fields': ('customer', 'loan', 'payment', 'reference_invoice')
        }),
        ('Emisor', {
            'fields': ('emisor_rnc', 'emisor_razon_social')
        }),
        ('Comprador', {
            'fields': ('comprador_rnc', 'comprador_razon_social')
        }),
        ('Fechas y Pago', {
            'fields': ('issue_date', 'due_date', 'payment_method')
        }),
        ('Totales', {
            'fields': ('subtotal', 'total_itbis', 'total_discount', 'total')
        }),
        ('DGII', {
            'fields': ('dgii_trackid', 'dgii_status', 'dgii_response', 'dgii_submitted_at'),
            'classes': ('collapse',)
        }),
        ('XML', {
            'fields': ('xml_content', 'signed_xml', 'certificate'),
            'classes': ('collapse',)
        }),
        ('Notas', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ECFSubmission)
class ECFSubmissionAdmin(ModelAdmin):
    list_display = ['invoice', 'action', 'environment', 'trackid', 'response_status', 'http_status_code', 'submitted_at']
    list_filter = ['action', 'environment', 'response_status']
    search_fields = ['trackid', 'invoice__encf_number']
    readonly_fields = ['submitted_at', 'request_xml', 'response_body']
