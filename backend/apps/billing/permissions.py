"""
Permisos de facturación electrónica (e-CF).
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class CanManageBilling(permissions.BasePermission):
    """
    Gestionar facturación fiscal: certificados, secuencias e-NCF, facturas y
    proveedor e-CF. Solo administradores y contadores (dueño y superusuario
    siempre pasan).

    La lectura (GET/HEAD/OPTIONS) queda abierta a cualquier usuario autenticado,
    salvo las acciones que hablan con la DGII o el proveedor e-CF, que exigen el
    rol aunque sean GET.
    """

    allowed_roles = ('admin', 'accountant')
    dgii_actions = (
        'generate_ecf', 'sign_ecf', 'submit_to_dgii', 'check_dgii_status',
        'submit_invoice', 'query_invoice',
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if (request.method in permissions.SAFE_METHODS
                and getattr(view, 'action', None) not in self.dgii_actions):
            return True

        if user.is_superuser or getattr(user, 'is_tenant_owner', False):
            return True

        if getattr(user, 'role', None) not in self.allowed_roles:
            raise PermissionDenied({
                'detail': 'Solo administradores y contadores pueden gestionar la facturación '
                          f'electrónica. Tu rol actual es: {user.get_role_display()}',
                'required_permission': 'CanManageBilling',
                'required_roles': list(self.allowed_roles),
                'current_role': user.role,
            })

        return True
