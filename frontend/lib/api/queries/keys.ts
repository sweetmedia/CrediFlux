/**
 * React Query key factory.
 *
 * Hierarchical keys allow targeted invalidation:
 *   queryKeys.loans.all          → invalidate all loan queries
 *   queryKeys.loans.lists()      → invalidate all loan list queries
 *   queryKeys.loans.list(params) → specific list with params
 *   queryKeys.loans.detail(id)   → specific loan detail
 *
 * Scaffolding for F2 — real consumers land in F3 when pages migrate.
 */

export const queryKeys = {
  loans: {
    all: ['loans'] as const,
    lists: () => [...queryKeys.loans.all, 'list'] as const,
    list: (params?: Record<string, unknown>) =>
      [...queryKeys.loans.lists(), params ?? {}] as const,
    details: () => [...queryKeys.loans.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.loans.details(), id] as const,
    dashboard: () => [...queryKeys.loans.all, 'dashboard'] as const,
  },
  customers: {
    all: ['customers'] as const,
    lists: () => [...queryKeys.customers.all, 'list'] as const,
    list: (params?: Record<string, unknown>) =>
      [...queryKeys.customers.lists(), params ?? {}] as const,
    details: () => [...queryKeys.customers.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.customers.details(), id] as const,
  },
  config: {
    all: ['config'] as const,
  },
  modules: {
    all: ['modules'] as const,
  },
  permissions: {
    all: ['permissions'] as const,
    user: (id: string) => [...queryKeys.permissions.all, id] as const,
  },
} as const
