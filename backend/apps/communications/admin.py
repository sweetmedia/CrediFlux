from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Email, WhatsAppMessage, Task


@admin.register(Email)
class EmailAdmin(ModelAdmin):
    list_display = ['subject', 'from_email', 'to_email', 'direction', 'status', 'created_at']
    list_filter = ['direction', 'status', 'created_at']
    search_fields = ['subject', 'from_email', 'to_email', 'body_text']
    readonly_fields = ['message_id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(ModelAdmin):
    list_display = ['wa_message_id', 'from_phone', 'to_phone', 'direction', 'status', 'message_type', 'created_at']
    list_filter = ['direction', 'status', 'message_type', 'created_at']
    search_fields = ['wa_message_id', 'from_phone', 'to_phone', 'content']
    readonly_fields = ['wa_message_id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ['title', 'status', 'priority', 'assignee', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'assignee', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_by', 'created_at', 'updated_at']
    ordering = ['position', '-created_at']
    list_editable = ['status', 'priority']

    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Estado', {
            'fields': ('status', 'priority', 'position')
        }),
        ('Asignación', {
            'fields': ('assignee', 'due_date', 'tags')
        }),
        ('Metadatos', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
