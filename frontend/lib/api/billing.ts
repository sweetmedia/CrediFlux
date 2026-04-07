import { apiClient } from './client';
import {
  Invoice,
  InvoiceCreate,
  FiscalSequence,
  DigitalCertificate,
  ECFSubmission,
} from '@/types/billing';
import { PaginatedResponse } from '@/types';

export const billingAPI = {
  // ============================================================
  // Invoices
  // ============================================================

  async getInvoices(params?: {
    page?: number;
    search?: string;
    status?: string;
    ecf_type?: string;
    ordering?: string;
  }): Promise<PaginatedResponse<Invoice>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<Invoice>>(
      `/api/billing/invoices/?${queryParams.toString()}`
    );
  },

  async getInvoice(id: string): Promise<Invoice> {
    return apiClient.get<Invoice>(`/api/billing/invoices/${id}/`);
  },

  async createInvoice(data: InvoiceCreate): Promise<Invoice> {
    return apiClient.post<Invoice>('/api/billing/invoices/', data);
  },

  async updateInvoice(id: string, data: Partial<InvoiceCreate>): Promise<Invoice> {
    return apiClient.patch<Invoice>(`/api/billing/invoices/${id}/`, data);
  },

  async deleteInvoice(id: string): Promise<void> {
    return apiClient.delete(`/api/billing/invoices/${id}/`);
  },

  // Generate e-CF XML
  async generateECF(id: string): Promise<Invoice> {
    return apiClient.post<Invoice>(`/api/billing/invoices/${id}/generate-ecf/`);
  },

  // Sign e-CF
  async signECF(id: string, certificateId?: string): Promise<Invoice> {
    return apiClient.post<Invoice>(`/api/billing/invoices/${id}/sign/`, {
      certificate_id: certificateId,
    });
  },

  // Submit to DGII
  async submitToDGII(id: string, environment?: string): Promise<{
    message: string;
    trackid: string;
    invoice: Invoice;
  }> {
    return apiClient.post(`/api/billing/invoices/${id}/submit-dgii/`, {
      environment: environment || 'testecf',
    });
  },

  // Check DGII status
  async checkDGIIStatus(id: string, environment?: string): Promise<{
    dgii_status: string;
    dgii_response: any;
    invoice: Invoice;
  }> {
    const params = environment ? `?environment=${environment}` : '';
    return apiClient.get(`/api/billing/invoices/${id}/dgii-status/${params}`);
  },

  // Get invoice submissions history
  async getInvoiceSubmissions(id: string): Promise<ECFSubmission[]> {
    return apiClient.get<ECFSubmission[]>(`/api/billing/invoices/${id}/submissions/`);
  },

  // ============================================================
  // Fiscal Sequences
  // ============================================================

  async getSequences(params?: {
    page?: number;
    ecf_type?: string;
    is_active?: boolean;
  }): Promise<PaginatedResponse<FiscalSequence>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<FiscalSequence>>(
      `/api/billing/sequences/?${queryParams.toString()}`
    );
  },

  async getSequence(id: string): Promise<FiscalSequence> {
    return apiClient.get<FiscalSequence>(`/api/billing/sequences/${id}/`);
  },

  async createSequence(data: Partial<FiscalSequence>): Promise<FiscalSequence> {
    return apiClient.post<FiscalSequence>('/api/billing/sequences/', data);
  },

  async updateSequence(id: string, data: Partial<FiscalSequence>): Promise<FiscalSequence> {
    return apiClient.patch<FiscalSequence>(`/api/billing/sequences/${id}/`, data);
  },

  // ============================================================
  // Digital Certificates
  // ============================================================

  async getCertificates(): Promise<PaginatedResponse<DigitalCertificate>> {
    return apiClient.get<PaginatedResponse<DigitalCertificate>>(
      '/api/billing/certificates/'
    );
  },

  async getCertificate(id: string): Promise<DigitalCertificate> {
    return apiClient.get<DigitalCertificate>(`/api/billing/certificates/${id}/`);
  },

  async uploadCertificate(formData: FormData): Promise<DigitalCertificate> {
    return apiClient.post<DigitalCertificate>('/api/billing/certificates/', formData);
  },

  async deleteCertificate(id: string): Promise<void> {
    return apiClient.delete(`/api/billing/certificates/${id}/`);
  },

  // ============================================================
  // Submissions (read-only)
  // ============================================================

  async getSubmissions(params?: {
    page?: number;
    action?: string;
    environment?: string;
  }): Promise<PaginatedResponse<ECFSubmission>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<ECFSubmission>>(
      `/api/billing/submissions/?${queryParams.toString()}`
    );
  },
};
