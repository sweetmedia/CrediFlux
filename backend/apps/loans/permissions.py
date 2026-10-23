"""
Custom permissions for loan operations
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class CanApproveLoan(permissions.BasePermission):
    """
    Permission to approve/reject loans.
    Only users with roles: admin, manager, or loan_officer can approve/reject loans.
    """

    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers always have permission
        if request.user.is_superuser:
            return True

        # Tenant owners always have permission
        if request.user.is_tenant_owner:
            return True

        # Check user role
        allowed_roles = ['admin', 'manager', 'loan_officer']
        if request.user.role not in allowed_roles:
            # Raise detailed permission denied error
            raise PermissionDenied({
                'detail': f'Solo administradores, gerentes y oficiales de préstamos pueden aprobar/rechazar préstamos. Tu rol actual es: {request.user.get_role_display()}',
                'required_permission': 'CanApproveLoan',
                'required_roles': allowed_roles,
                'current_role': request.user.role,
            })

        return True


class CanManageLoans(permissions.BasePermission):
    """
    Permission to manage loans (create, edit, delete).
    Only users with roles: admin, manager, or loan_officer can manage loans.
    """

    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Read-only permissions are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Superusers always have permission
        if request.user.is_superuser:
            return True

        # Tenant owners always have permission
        if request.user.is_tenant_owner:
            return True

        # Check user role for create/update/delete
        allowed_roles = ['admin', 'manager', 'loan_officer']
        if request.user.role not in allowed_roles:
            # Raise detailed permission denied error
            raise PermissionDenied({
                'detail': f'Solo administradores, gerentes y oficiales de préstamos pueden gestionar préstamos. Tu rol actual es: {request.user.get_role_display()}',
                'required_permission': 'CanManageLoans',
                'required_roles': allowed_roles,
                'current_role': request.user.role,
            })

        return True


class CanRegisterPayments(permissions.BasePermission):
    """
    Registrar pagos: roles que cobran (caja, cobranza, oficiales y gerencia).
    Lectura para cualquier usuario autenticado. Contabilidad y consulta no cobran.
    """

    allowed_roles = ['admin', 'manager', 'loan_officer', 'collector', 'collection_supervisor', 'cashier']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_superuser or request.user.is_tenant_owner:
            return True

        if request.user.role not in self.allowed_roles:
            raise PermissionDenied({
                'detail': f'Tu rol ({request.user.get_role_display()}) no puede registrar pagos.',
                'required_permission': 'CanRegisterPayments',
                'required_roles': self.allowed_roles,
                'current_role': request.user.role,
            })

        return True


class CanManageCollections(permissions.BasePermission):
    """
    Gestión de cobranza (teléfonos, correos, recordatorios y contactos de cobro).
    Lectura para cualquier usuario autenticado; escritura para gerencia, oficiales y cobranza.
    """

    allowed_roles = ['admin', 'manager', 'loan_officer', 'collector', 'collection_supervisor']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.user.is_superuser or request.user.is_tenant_owner:
            return True

        if request.user.role not in self.allowed_roles:
            raise PermissionDenied({
                'detail': f'Tu rol ({request.user.get_role_display()}) no puede gestionar la cobranza.',
                'required_permission': 'CanManageCollections',
                'required_roles': self.allowed_roles,
                'current_role': request.user.role,
            })

        return True
