import { apiClient } from './client';

export interface ContractTemplate {
  id: string;
  name: string;
  description: string;
  content: string;
  is_active: boolean;
  is_default: boolean;
  loan_types: string[];
  header_image?: string;
  footer_text: string;
  created_by?: string;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
}

export interface Contract {
  id: string;
  contract_number: string;
  loan: string;
  loan_number: string;
  customer_name: string;
  template?: string;
  template_name?: string;
  content: string;
  pdf_file?: string;
  status: 'draft' | 'pending_signature' | 'signed' | 'active' | 'completed' | 'cancelled';
  customer_signed_at?: string;
  customer_signature?: string;
  officer_signed_at?: string;
  officer_signature?: string;
  witness_name?: string;
  witness_id?: string;
  witness_signature?: string;
  witness_signed_at?: string;
  special_terms: string;
  notes: string;
  generated_by?: string;
  generated_by_name?: string;
  generated_at: string;
  updated_at: string;
  is_fully_signed: boolean;
}

export interface ContractVariable {
  variable: string;
  description: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const contractTemplatesAPI = {
  // Get all contract templates
  async getTemplates(params?: {
    page?: number;
    search?: string;
    is_active?: boolean;
    is_default?: boolean;
  }): Promise<PaginatedResponse<ContractTemplate>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiClient.get<PaginatedResponse<ContractTemplate>>(
      `/api/loans/contract-templates/?${queryParams.toString()}`
    );
  },

  // Get template by ID
  async getTemplate(id: string): Promise<ContractTemplate> {
    return apiClient.get<ContractTemplate>(`/api/loans/contract-templates/${id}/`);
  },

  // Create template
  async createTemplate(data: Partial<ContractTemplate>): Promise<ContractTemplate> {
    return apiClient.post<ContractTemplate>('/api/loans/contract-templates/', data);
  },

  // Update template
  async updateTemplate(id: string, data: Partial<ContractTemplate>): Promise<ContractTemplate> {
    return apiClient.put<ContractTemplate>(`/api/loans/contract-templates/${id}/`, data);
  },

  // Delete template
  async deleteTemplate(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/contract-templates/${id}/`);
  },

  // Set template as default
  async setDefault(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/contract-templates/${id}/set_default/`, {});
  },

  // Duplicate template
  async duplicate(id: string): Promise<ContractTemplate> {
    return apiClient.post<ContractTemplate>(`/api/loans/contract-templates/${id}/duplicate/`, {});
  },

  // Get available variables
  async getVariables(): Promise<{ variables: ContractVariable[] }> {
    return apiClient.get<{ variables: ContractVariable[] }>('/api/loans/contract-templates/variables/');
  },
};

export const contractsAPI = {
  // Get all contracts
  async getContracts(params?: {
    page?: number;
    search?: string;
    status?: string;
    loan?: string;
  }): Promise<PaginatedResponse<Contract>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiClient.get<PaginatedResponse<Contract>>(
      `/api/loans/contracts/?${queryParams.toString()}`
    );
  },

  // Get contract by ID
  async getContract(id: string): Promise<Contract> {
    return apiClient.get<Contract>(`/api/loans/contracts/${id}/`);
  },

  // Create contract
  async createContract(data: {
    loan: string;
    template?: string;
    special_terms?: string;
    notes?: string;
  }): Promise<Contract> {
    return apiClient.post<Contract>('/api/loans/contracts/', data);
  },

  // Update contract
  async updateContract(id: string, data: Partial<Contract>): Promise<Contract> {
    return apiClient.put<Contract>(`/api/loans/contracts/${id}/`, data);
  },

  // Delete contract
  async deleteContract(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/contracts/${id}/`);
  },

  // Regenerate contract content from template
  async regenerate(id: string): Promise<Contract> {
    return apiClient.post<Contract>(`/api/loans/contracts/${id}/regenerate/`, {});
  },

  // Sign as customer
  async signCustomer(id: string, signature?: File): Promise<{ message: string }> {
    const formData = new FormData();
    if (signature) {
      formData.append('signature', signature);
    }
    return apiClient.post<{ message: string }>(
      `/api/loans/contracts/${id}/sign_customer/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  // Sign as officer
  async signOfficer(id: string, signature?: File): Promise<{ message: string }> {
    const formData = new FormData();
    if (signature) {
      formData.append('signature', signature);
    }
    return apiClient.post<{ message: string }>(
      `/api/loans/contracts/${id}/sign_officer/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  // Activate contract
  async activate(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/contracts/${id}/activate/`, {});
  },

  // Cancel contract
  async cancel(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/contracts/${id}/cancel/`, {});
  },
};
