"""
Admin de los modelos de `djangosdk` (app de tenant de terceros).

`djangosdk` registra sus admins sin el historial acotado al tenant del host: se vuelven a
registrar con `TenantHistoryMixin` delante. Este módulo carga después de `djangosdk` (orden de
INSTALLED_APPS).
"""
from django.contrib import admin
from djangosdk.models.conversation import Conversation
from djangosdk.models.message import Message

from apps.core.admin_mixins import scope_history_to_tenant

scope_history_to_tenant(admin.site, Conversation, Message)
