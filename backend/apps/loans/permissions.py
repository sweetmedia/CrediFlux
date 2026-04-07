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
