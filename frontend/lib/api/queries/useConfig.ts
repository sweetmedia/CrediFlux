'use client'

import { useQuery } from '@tanstack/react-query'

import { getApiUrl } from '@/lib/api/client'
import { queryKeys } from './keys'

export interface TenantConfig {
  currency: string
  currency_symbol: string
  decimal_places: number
  company_name: string
}

const defaultConfig: TenantConfig = {
  currency: 'DOP',
  currency_symbol: 'RD$',
  decimal_places: 2,
  company_name: 'CrediFlux',
}

/**
 * Cache the tenant config via React Query.
 * Longer staleTime — config rarely changes within a session.
 * Falls back to sensible defaults on error.
 */
export function useTenantConfig() {
  return useQuery<TenantConfig>({
    queryKey: queryKeys.config.all,
    queryFn: async () => {
      const response = await fetch(`${getApiUrl()}/api/config/`)
      if (!response.ok) return defaultConfig
      return (await response.json()) as TenantConfig
    },
    staleTime: 5 * 60 * 1000,
  })
}
