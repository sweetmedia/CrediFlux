'use client'

import { useModules, type ModuleId } from '@/lib/api/queries'

/**
 * Returns true when the tenant has the given module active.
 *
 * Defaults to `true` while the modules query is loading so the sidebar
 * doesn't flash groups on and off during initial hydration.
 */
export function useModule(moduleId: ModuleId): boolean {
  const { data, isLoading } = useModules()
  if (isLoading || !data) return true
  return data.modules.includes(moduleId)
}
