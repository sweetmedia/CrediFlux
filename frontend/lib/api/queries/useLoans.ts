'use client'

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'

import { loansAPI } from '@/lib/api/loans'
import type { Loan, PaginatedResponse, DashboardStatistics } from '@/types'
import { queryKeys } from './keys'

interface UseLoansOptions {
  page?: number
  search?: string
  status?: string
  loan_type?: string
  customer?: string
  enabled?: boolean
}

/** List loans with optional filters. Paginated. */
export function useLoans(options: UseLoansOptions = {}) {
  const { enabled = true, ...params } = options
  return useQuery<PaginatedResponse<Loan>>({
    queryKey: queryKeys.loans.list(params),
    queryFn: () => loansAPI.getLoans(params),
    enabled,
    staleTime: 60 * 1000,
  })
}

/** Single loan detail. */
export function useLoan(
  id: string,
  options?: Omit<UseQueryOptions<Loan>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Loan>({
    queryKey: queryKeys.loans.detail(id),
    queryFn: () => loansAPI.getLoan(id),
    enabled: !!id,
    staleTime: 60 * 1000,
    ...options,
  })
}

/** Dashboard KPIs. Cached longer since it aggregates across many rows. */
export function useDashboardStats() {
  return useQuery<DashboardStatistics>({
    queryKey: queryKeys.loans.dashboard(),
    queryFn: () => loansAPI.getDashboardStatistics(),
    staleTime: 2 * 60 * 1000,
  })
}

/** Create a new loan. Invalidates all loan lists on success. */
export function useCreateLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Loan>) => loansAPI.createLoan(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.loans.lists() })
      qc.invalidateQueries({ queryKey: queryKeys.loans.dashboard() })
    },
  })
}
