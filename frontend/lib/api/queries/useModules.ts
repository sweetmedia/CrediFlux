'use client'

import { useQuery } from '@tanstack/react-query'

import { getApiUrl } from '@/lib/api/client'
import { queryKeys } from './keys'

export type ModuleId =
  | 'loans'
  | 'billing'
  | 'collections'
  | 'contracts'
  | 'communications'
  | 'ai'
  | 'calculator'
  | 'cashbox'

interface ModulesResponse {
  modules: ModuleId[]
}

/**
 * The tenant's active modules.
 *
 * Drives sidebar group filtering in the AppShell (M4) — groups with a
 * `module` field only render when that module is in the response.
 *
 * Until the backend exposes a real /api/modules/ endpoint, this returns
 * the full set so nothing gets hidden by mistake. Moving the server side
 * happens in F6.
 */
export function useModules() {
  return useQuery<ModulesResponse>({
    queryKey: queryKeys.modules.all,
    queryFn: async () => {
      try {
        const response = await fetch(`${getApiUrl()}/api/modules/`)
        if (response.ok) return (await response.json()) as ModulesResponse
      } catch {
        // fall through to default
      }
      // Default: all modules enabled until backend exposes the real endpoint.
      return {
        modules: [
          'loans',
          'billing',
          'collections',
          'contracts',
          'communications',
          'ai',
          'calculator',
          'cashbox',
        ],
      }
    },
    staleTime: 10 * 60 * 1000,
  })
}
