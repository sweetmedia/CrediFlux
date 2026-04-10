'use client'

import { useMemo } from 'react'

import { useAuth } from '@/lib/contexts/AuthContext'

type Action = 'view' | 'create' | 'edit' | 'delete' | 'approve'
type Resource =
  | 'loan'
  | 'customer'
  | 'payment'
  | 'contract'
  | 'billing'
  | 'user'
  | 'audit'
  | 'settings'
  | 'report'

/**
 * Derive the permission checker from the authenticated user's role.
 *
 * This is the F2 scaffold — a role-based ACL. When the backend adds
 * fine-grained permission records (F5 hardening), this hook swaps to
 * reading them from /api/auth/me without changing consumer code.
 */
export function usePermissions() {
  const { user } = useAuth()

  return useMemo(() => {
    const role = user?.role
    const isOwner = user?.is_tenant_owner ?? false

    const can = (action: Action, resource: Resource): boolean => {
      if (!user) return false
      // Tenant owners and admins can do anything within their tenant.
      if (isOwner || role === 'admin') return true

      // Role matrix — conservative defaults.
      switch (role) {
        case 'manager':
          return resource !== 'settings' && resource !== 'audit'
        case 'loan_officer':
          return (
            (resource === 'loan' || resource === 'customer') &&
            action !== 'delete'
          )
        case 'collector':
        case 'collection_supervisor':
          return (
            resource === 'customer' ||
            (resource === 'payment' && action !== 'delete') ||
            (resource === 'loan' && action === 'view')
          )
        case 'accountant':
          return (
            resource === 'billing' ||
            resource === 'payment' ||
            (resource === 'report' && action === 'view')
          )
        case 'cashier':
          return resource === 'payment' && action !== 'delete'
        case 'viewer':
          return action === 'view'
        default:
          return false
      }
    }

    return { can, role, isOwner }
  }, [user])
}
