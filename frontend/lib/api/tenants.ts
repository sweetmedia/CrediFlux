import { apiClient } from './client';

export interface Tenant {
  id: number;
  name: string;
  schema_name: string;
  business_name: string;
  tax_id?: string;
  email: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  is_active: boolean;
  max_users: number;
  subscription_plan: 'basic' | 'professional' | 'enterprise';
  primary_color?: string;
  created_on: string;
  updated_on: string;
}

export interface TenantUpdateData {
  business_name?: string;
  tax_id?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  postal_code?: string;
  primary_color?: string;
}

export interface TenantUpdateResponse {
  message: string;
  tenant: Tenant;
}

export const tenantsAPI = {
  /**
   * Get current tenant settings
   */
  getSettings: async (): Promise<Tenant> => {
    return apiClient.get<Tenant>('/api/tenants/settings/');
  },

  /**
   * Update tenant settings
   */
  updateSettings: async (data: TenantUpdateData): Promise<TenantUpdateResponse> => {
    return apiClient.patch<TenantUpdateResponse>('/api/tenants/settings/', data);
  },
};
