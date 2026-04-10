'use client'

import type { ReactNode } from 'react'

import { usePermissions } from '@/lib/api/queries'

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

interface PermissionGateProps {
  action: Action
  resource: Resource
  fallback?: ReactNode
  children: ReactNode
}

/**
 * Conditionally render children only when the current user has permission.
 *
 * Wraps the usePermissions() hook declaratively. Renders nothing by default
 * when permission is denied — pass `fallback` to show a specific "no access"
 * UI instead.
 */
export function PermissionGate({
  action,
  resource,
  fallback = null,
  children,
}: PermissionGateProps) {
  const { can } = usePermissions()
  if (!can(action, resource)) return <>{fallback}</>
  return <>{children}</>
}
