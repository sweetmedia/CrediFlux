/**
 * Customer Documents API
 */
import { apiClient } from './client';
import {
  CustomerDocument,
  CustomerDocumentCreate,
  PaginatedResponse,
} from '@/types';

export const documentsAPI = {
  /**
   * Get all documents
   */
  async getDocuments(params?: {
    page?: number;
    customer?: string;
    document_type?: string;
    verification_status?: string;
    is_primary?: boolean;
    search?: string;
  }): Promise<PaginatedResponse<CustomerDocument>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiClient.get<PaginatedResponse<CustomerDocument>>(
      `/api/loans/customer-documents/?${queryParams.toString()}`
    );
  },

  /**
   * Get document by ID
   */
  async getDocument(id: string): Promise<CustomerDocument> {
    return apiClient.get<CustomerDocument>(`/api/loans/customer-documents/${id}/`);
  },

  /**
   * Upload new document
   */
  async uploadDocument(data: CustomerDocumentCreate): Promise<CustomerDocument> {
    const formData = new FormData();

    // Append all fields to FormData
    formData.append('customer', data.customer);
    formData.append('document_type', data.document_type);
    formData.append('title', data.title);

    if (data.description) {
      formData.append('description', data.description);
    }

    formData.append('document_file', data.document_file);

    if (data.issue_date) {
      formData.append('issue_date', data.issue_date);
    }

    if (data.expiry_date) {
      formData.append('expiry_date', data.expiry_date);
    }

    if (data.notes) {
      formData.append('notes', data.notes);
    }

    if (data.is_primary !== undefined) {
      formData.append('is_primary', String(data.is_primary));
    }

    return apiClient.post<CustomerDocument>(
      '/api/loans/customer-documents/',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  /**
   * Update document (excluding file)
   */
  async updateDocument(
    id: string,
    data: Partial<Omit<CustomerDocumentCreate, 'document_file'>>
  ): Promise<CustomerDocument> {
    return apiClient.patch<CustomerDocument>(
      `/api/loans/customer-documents/${id}/`,
      data
    );
  },

  /**
   * Delete document
   */
  async deleteDocument(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/customer-documents/${id}/`);
  },

  /**
   * Verify document
   */
  async verifyDocument(id: string): Promise<{ message: string; document: CustomerDocument }> {
    return apiClient.post<{ message: string; document: CustomerDocument }>(
      `/api/loans/customer-documents/${id}/verify/`,
      {}
    );
  },

  /**
   * Reject document
   */
  async rejectDocument(
    id: string,
    reason: string
  ): Promise<{ message: string; document: CustomerDocument }> {
    return apiClient.post<{ message: string; document: CustomerDocument }>(
      `/api/loans/customer-documents/${id}/reject/`,
      { reason }
    );
  },

  /**
   * Mark document as primary
   */
  async markAsPrimary(
    id: string
  ): Promise<{ message: string; document: CustomerDocument }> {
    return apiClient.post<{ message: string; document: CustomerDocument }>(
      `/api/loans/customer-documents/${id}/mark_primary/`,
      {}
    );
  },

  /**
   * Get expired documents
   */
  async getExpiredDocuments(): Promise<CustomerDocument[]> {
    return apiClient.get<CustomerDocument[]>(
      '/api/loans/customer-documents/expired/'
    );
  },

  /**
   * Get pending verification documents
   */
  async getPendingVerification(): Promise<CustomerDocument[]> {
    return apiClient.get<CustomerDocument[]>(
      '/api/loans/customer-documents/pending_verification/'
    );
  },

  /**
   * Get customer's documents
   */
  async getCustomerDocuments(customerId: string): Promise<CustomerDocument[]> {
    const response = await this.getDocuments({ customer: customerId });
    return response.results;
  },
};
