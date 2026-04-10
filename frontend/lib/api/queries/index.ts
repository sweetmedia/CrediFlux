/**
 * React Query hooks barrel.
 *
 * Consume typed hooks for data fetching instead of calling axios directly.
 * Pages migrate to these hooks gradually in F3.
 */

export { queryKeys } from './keys'
export {
  useLoans,
  useLoan,
  useDashboardStats,
  useCreateLoan,
} from './useLoans'
export {
  useCustomers,
  useCustomer,
  useCreateCustomer,
  useUpdateCustomer,
} from './useCustomers'
export { useTenantConfig, type TenantConfig } from './useConfig'
export { useModules, type ModuleId } from './useModules'
export { usePermissions } from './usePermissions'
