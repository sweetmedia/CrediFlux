'use client'

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from '@tanstack/react-query'

import { customersAPI } from '@/lib/api/customers'
import type { Customer, PaginatedResponse } from '@/types'
import { queryKeys } from './keys'

interface UseCustomersOptions {
  page?: number
  page_size?: number
  search?: string
  status?: string
  employment_status?: string
  enabled?: boolean
}

/** List customers with optional filters. Paginated. */
export function useCustomers(options: UseCustomersOptions = {}) {
  const { enabled = true, ...params } = options
  return useQuery<PaginatedResponse<Customer>>({
    queryKey: queryKeys.customers.list(params),
    queryFn: () => customersAPI.getCustomers(params),
    enabled,
    staleTime: 60 * 1000,
  })
}

/** Single customer detail. */
export function useCustomer(
  id: string,
  options?: Omit<UseQueryOptions<Customer>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Customer>({
    queryKey: queryKeys.customers.detail(id),
    queryFn: () => customersAPI.getCustomer(id),
    enabled: !!id,
    staleTime: 60 * 1000,
    ...options,
  })
}

/** Create a new customer. Invalidates all customer lists on success. */
export function useCreateCustomer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Customer>) => customersAPI.createCustomer(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.customers.lists() })
    },
  })
}

/** Update an existing customer. Invalidates both list and detail queries. */
export function useUpdateCustomer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Customer> }) =>
      customersAPI.updateCustomer(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: queryKeys.customers.lists() })
      qc.invalidateQueries({ queryKey: queryKeys.customers.detail(id) })
    },
  })
}
