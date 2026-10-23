"""
Permisos del módulo de comunicaciones.
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class CanSendMessages(permissions.BasePermission):
    """
    Enviar mensajes a clientes: gerencia, oficiales y cobranza.
    El dueño del tenant y el superusuario siempre pasan.
    """

    allowed_roles = ['admin', 'manager', 'loan_officer', 'collector', 'collection_supervisor']

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_tenant_owner:
            return True

        if user.role not in self.allowed_roles:
            raise PermissionDenied({
                'detail': f'Tu rol no puede enviar mensajes a clientes. Tu rol actual es: {user.get_role_display()}',
                'required_permission': 'CanSendMessages',
                'required_roles': self.allowed_roles,
                'current_role': user.role,
            })

        return True
