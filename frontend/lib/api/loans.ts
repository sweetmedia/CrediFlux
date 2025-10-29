import { apiClient } from './client';
import {
  Loan,
  LoanPayment,
  LoanSchedule,
  Collateral,
  PaginatedResponse,
  LoanStatistics,
} from '@/types';

export const loansAPI = {
  // Get all loans
  async getLoans(params?: {
    page?: number;
    search?: string;
    status?: string;
    loan_type?: string;
    customer?: string;
  }): Promise<PaginatedResponse<Loan>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<Loan>>(
      `/api/loans/?${queryParams.toString()}`
    );
  },

  // Get loan by ID
  async getLoan(id: string): Promise<Loan> {
    return apiClient.get<Loan>(`/api/loans/${id}/`);
  },

  // Create loan
  async createLoan(data: Partial<Loan>): Promise<Loan> {
    return apiClient.post<Loan>('/api/loans/', data);
  },

  // Update loan
  async updateLoan(id: string, data: Partial<Loan>): Promise<Loan> {
    return apiClient.put<Loan>(`/api/loans/${id}/`, data);
  },

  // Delete loan
  async deleteLoan(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/${id}/`);
  },

  // Approve loan
  async approveLoan(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/${id}/approve/`);
  },

  // Disburse loan
  async disburseLoan(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/${id}/disburse/`);
  },

  // Reject loan
  async rejectLoan(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/${id}/reject/`);
  },

  // Get loan schedule
  async getLoanSchedule(id: string): Promise<LoanSchedule[]> {
    return apiClient.get<LoanSchedule[]>(`/api/loans/${id}/schedule/`);
  },

  // Get loan payments
  async getLoanPayments(id: string): Promise<LoanPayment[]> {
    return apiClient.get<LoanPayment[]>(`/api/loans/${id}/payments/`);
  },

  // Get loan statistics
  async getStatistics(): Promise<LoanStatistics> {
    return apiClient.get<LoanStatistics>('/api/loans/statistics/');
  },
};

export const paymentsAPI = {
  // Get all payments
  async getPayments(params?: {
    page?: number;
    search?: string;
    status?: string;
    loan?: string;
    payment_method?: string;
  }): Promise<PaginatedResponse<LoanPayment>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<LoanPayment>>(
      `/api/loans/payments/?${queryParams.toString()}`
    );
  },

  // Create payment
  async createPayment(data: Partial<LoanPayment>): Promise<LoanPayment> {
    return apiClient.post<LoanPayment>('/api/loans/payments/', data);
  },

  // Get payment
  async getPayment(id: string): Promise<LoanPayment> {
    return apiClient.get<LoanPayment>(`/api/loans/payments/${id}/`);
  },

  // Reverse payment
  async reversePayment(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/payments/${id}/reverse/`);
  },
};

export const schedulesAPI = {
  // Get overdue schedules
  async getOverdueSchedules(): Promise<LoanSchedule[]> {
    return apiClient.get<LoanSchedule[]>('/api/loans/schedules/overdue/');
  },

  // Get all schedules
  async getSchedules(params?: {
    page?: number;
    loan?: string;
    status?: string;
  }): Promise<PaginatedResponse<LoanSchedule>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<LoanSchedule>>(
      `/api/loans/schedules/?${queryParams.toString()}`
    );
  },
};

export const collateralsAPI = {
  // Get all collaterals
  async getCollaterals(params?: {
    page?: number;
    loan?: string;
    collateral_type?: string;
    status?: string;
  }): Promise<PaginatedResponse<Collateral>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<Collateral>>(
      `/api/loans/collaterals/?${queryParams.toString()}`
    );
  },

  // Create collateral
  async createCollateral(data: Partial<Collateral>): Promise<Collateral> {
    return apiClient.post<Collateral>('/api/loans/collaterals/', data);
  },

  // Update collateral
  async updateCollateral(id: string, data: Partial<Collateral>): Promise<Collateral> {
    return apiClient.put<Collateral>(`/api/loans/collaterals/${id}/`, data);
  },

  // Release collateral
  async releaseCollateral(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/collaterals/${id}/release/`);
  },

  // Liquidate collateral
  async liquidateCollateral(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/collaterals/${id}/liquidate/`);
  },
};
