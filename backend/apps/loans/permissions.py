"""
Custom permissions for loan operations
"""
from rest_framework import permissions


class CanApproveLoan(permissions.BasePermission):
    """
    Permission to approve/reject loans.
    Only users with roles: admin, manager, or loan_officer can approve/reject loans.
    """
    message = "Solo administradores, gerentes y oficiales de préstamos pueden aprobar/rechazar préstamos."

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
        return request.user.role in allowed_roles


class CanManageLoans(permissions.BasePermission):
    """
    Permission to manage loans (create, edit, delete).
    Only users with roles: admin, manager, or loan_officer can manage loans.
    """
    message = "Solo administradores, gerentes y oficiales de préstamos pueden gestionar préstamos."

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
        return request.user.role in allowed_roles
