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
  is_archived: boolean;
  archived_at?: string;
  archived_by?: string;
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
  async signCustomer(id: string, signatureData?: string | File): Promise<{ message: string }> {
    // If signatureData is a string (base64), send as JSON
    if (typeof signatureData === 'string') {
      return apiClient.post<{ message: string }>(
        `/api/loans/contracts/${id}/sign_customer/`,
        { signature_data: signatureData }
      );
    }

    // If signatureData is a File, send as FormData
    const formData = new FormData();
    if (signatureData) {
      formData.append('signature', signatureData);
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
  async signOfficer(id: string, signatureData?: string | File): Promise<{ message: string }> {
    // If signatureData is a string (base64), send as JSON
    if (typeof signatureData === 'string') {
      return apiClient.post<{ message: string }>(
        `/api/loans/contracts/${id}/sign_officer/`,
        { signature_data: signatureData }
      );
    }

    // If signatureData is a File, send as FormData
    const formData = new FormData();
    if (signatureData) {
      formData.append('signature', signatureData);
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

  // Archive contract (only for cancelled contracts)
  async archive(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/contracts/${id}/archive/`, {});
  },

  // Unarchive contract
  async unarchive(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/contracts/${id}/unarchive/`, {});
  },

  // Send contract for signature via email
  async sendForSignature(id: string, email: string, days_valid?: number): Promise<{
    message: string;
    token_id: string;
    expires_at: string;
  }> {
    return apiClient.post(`/api/loans/contracts/${id}/send_for_signature/`, {
      email,
      days_valid: days_valid || 7,
    });
  },

  // Get PDF download URL
  getPdfDownloadUrl(id: string): string {
    return `/api/loans/contracts/${id}/download_pdf/`;
  },

  // Get PDF view URL
  getPdfViewUrl(id: string): string {
    return `/api/loans/contracts/${id}/view_pdf/`;
  },
};

// Public contract signature API (no authentication required)
export const publicContractAPI = {
  // Get contract details by token
  async getContractByToken(token: string): Promise<{
    contract: Contract;
    token_permissions: {
      can_sign_as_customer: boolean;
      can_sign_as_officer: boolean;
    };
    expires_at: string;
  }> {
    const response = await fetch(`/api/loans/public/contracts/${token}/`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch contract');
    }
    return response.json();
  },

  // Sign contract with token
  async signWithToken(token: string, signature_data: string): Promise<{
    message: string;
    signed_as: string;
    contract_status: string;
    is_fully_signed: boolean;
  }> {
    const response = await fetch(`/api/loans/public/contracts/${token}/sign/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ signature_data }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to sign contract');
    }
    return response.json();
  },
};
