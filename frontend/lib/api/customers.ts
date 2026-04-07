import { apiClient } from './client';
import { Customer, PaginatedResponse, Loan, CustomerStatistics } from '@/types';

export const customersAPI = {
  // Get all customers
  async getCustomers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    employment_status?: string;
  }): Promise<PaginatedResponse<Customer>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<Customer>>(
      `/api/loans/customers/?${queryParams.toString()}`
    );
  },

  // Get customer by ID
  async getCustomer(id: string): Promise<Customer> {
    return apiClient.get<Customer>(`/api/loans/customers/${id}/`);
  },

  // Create customer
  async createCustomer(data: Partial<Customer>): Promise<Customer> {
    return apiClient.post<Customer>('/api/loans/customers/', data);
  },

  // Update customer
  async updateCustomer(id: string, data: Partial<Customer>): Promise<Customer> {
    return apiClient.put<Customer>(`/api/loans/customers/${id}/`, data);
  },

  // Delete customer
  async deleteCustomer(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/customers/${id}/`);
  },

  // Get customer's loans
  async getCustomerLoans(id: string): Promise<Loan[]> {
    return apiClient.get<Loan[]>(`/api/loans/customers/${id}/loans/`);
  },

  // Get customer statistics
  async getCustomerStatistics(id: string): Promise<CustomerStatistics> {
    return apiClient.get<CustomerStatistics>(`/api/loans/customers/${id}/statistics/`);
  },
};
