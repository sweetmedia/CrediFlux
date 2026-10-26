from django.contrib import admin
from apps.core.admin_mixins import TenantHistoryMixin, TenantUserFKMixin
from .models import CashRegister, CashSession, CashMovement, DenominationCount


@admin.register(CashRegister)
class CashRegisterAdmin(TenantHistoryMixin, TenantUserFKMixin, admin.ModelAdmin):
    list_display = ['name', 'code', 'location', 'is_active']
    list_filter = ['is_active']


@admin.register(CashSession)
class CashSessionAdmin(TenantHistoryMixin, TenantUserFKMixin, admin.ModelAdmin):
    list_display = ['register', 'cashier', 'opened_at', 'closed_at', 'status', 'opening_balance']
    list_filter = ['status', 'register']
    date_hierarchy = 'opened_at'


@admin.register(CashMovement)
class CashMovementAdmin(TenantHistoryMixin, TenantUserFKMixin, admin.ModelAdmin):
    list_display = ['session', 'movement_type', 'category', 'amount', 'description', 'created_at']
    list_filter = ['movement_type', 'category']
    search_fields = ['description', 'customer_name']


@admin.register(DenominationCount)
class DenominationCountAdmin(TenantHistoryMixin, admin.ModelAdmin):
    list_display = ['session', 'count_type', 'total']
    list_filter = ['count_type']
