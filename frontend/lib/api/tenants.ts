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
  logo?: string;
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

  /**
   * Upload tenant logo
   */
  uploadLogo: async (file: File): Promise<TenantUpdateResponse> => {
    const formData = new FormData();
    formData.append('logo', file);

    const token = localStorage.getItem('access_token');
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    console.log('Uploading to:', `${apiUrl}/api/tenants/settings/`);
    console.log('File:', file.name, file.size, file.type);
    console.log('Token exists:', !!token);

    try {
      const response = await fetch(`${apiUrl}/api/tenants/settings/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      console.log('Response status:', response.status, response.statusText);

      if (!response.ok) {
        let error;
        try {
          error = await response.json();
          console.log('Error response:', error);
        } catch (e) {
          // If response is not JSON, use status text
          const text = await response.text();
          console.log('Error response (text):', text);
          error = { detail: response.statusText || 'Error desconocido' };
        }

        const err = new Error('Upload failed');
        (err as any).response = {
          data: error,
          status: response.status,
          statusText: response.statusText
        };
        throw err;
      }

      const result = await response.json();
      console.log('Upload success:', result);
      return result;
    } catch (error: any) {
      console.error('Upload error:', error);
      // Re-throw with better error information
      if (error.response) {
        throw error;
      }
      // Network error or other issues
      throw new Error(`Error de red: ${error.message || 'No se pudo conectar con el servidor'}`);
    }
  },

  /**
   * Remove tenant logo
   */
  removeLogo: async (): Promise<TenantUpdateResponse> => {
    return apiClient.patch<TenantUpdateResponse>('/api/tenants/settings/', { logo: null });
  },
};
