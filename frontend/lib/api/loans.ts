import { apiClient } from './client';
import {
  Loan,
  LoanPayment,
  LoanSchedule,
  Collateral,
  PaginatedResponse,
  LoanStatistics,
  CollectionReminder,
  CollectionReminderCreate,
  CollectionContact,
  CollectionContactCreate,
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
  async approveLoan(id: string, notes?: string): Promise<{ message: string; loan: Loan }> {
    return apiClient.post<{ message: string; loan: Loan }>(`/api/loans/${id}/approve/`, { notes });
  },

  // Disburse loan
  async disburseLoan(id: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(`/api/loans/${id}/disburse/`);
  },

  // Reject loan
  async rejectLoan(id: string, notes: string): Promise<{ message: string; loan: Loan }> {
    return apiClient.post<{ message: string; loan: Loan }>(`/api/loans/${id}/reject/`, { notes });
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

  // Download Balance de Cuotas PDF report
  async downloadBalanceReport(id: string): Promise<void> {
    const { getApiUrl } = await import('./client');
    const API_URL = getApiUrl();
    const token = localStorage.getItem('access_token');

    const response = await fetch(`${API_URL}/api/loans/${id}/balance_report/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Error al descargar el reporte');
    }

    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `balance_cuotas_${id}.pdf`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
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

  // Confirm payment
  async confirmPayment(id: string): Promise<{ message: string; payment: LoanPayment }> {
    return apiClient.post<{ message: string; payment: LoanPayment }>(
      `/api/loans/payments/${id}/confirm/`
    );
  },

  // Cancel payment
  async cancelPayment(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/payments/${id}/cancel/`);
  },

  // Reverse payment
  async reversePayment(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/payments/${id}/reverse/`);
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

export const collectionsAPI = {
  // Reminders
  async getReminders(params?: {
    page?: number;
    status?: string;
    reminder_type?: string;
    channel?: string;
    loan?: string;
    customer?: string;
  }): Promise<PaginatedResponse<CollectionReminder>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<PaginatedResponse<CollectionReminder>>(
      `/api/loans/collection-reminders/?${queryParams.toString()}`
    );
  },

  async getReminder(id: string): Promise<CollectionReminder> {
    return apiClient.get<CollectionReminder>(`/api/loans/collection-reminders/${id}/`);
  },

  async createReminder(data: CollectionReminderCreate): Promise<CollectionReminder> {
    return apiClient.post<CollectionReminder>('/api/loans/collection-reminders/', data);
  },

  async updateReminder(id: string, data: Partial<CollectionReminderCreate>): Promise<CollectionReminder> {
    return apiClient.put<CollectionReminder>(`/api/loans/collection-reminders/${id}/`, data);
  },

  async deleteReminder(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/collection-reminders/${id}/`);
  },

  async sendReminder(id: string): Promise<{ message: string; reminder: CollectionReminder }> {
    return apiClient.post<{ message: string; reminder: CollectionReminder }>(
      `/api/loans/collection-reminders/${id}/send/`
    );
  },

  async cancelReminder(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/api/loans/collection-reminders/${id}/cancel/`);
  },

  async getPendingReminders(): Promise<CollectionReminder[]> {
    return apiClient.get<CollectionReminder[]>('/api/loans/collection-reminders/pending/');
  },

  async getScheduledToday(): Promise<CollectionReminder[]> {
    return apiClient.get<CollectionReminder[]>('/api/loans/collection-reminders/scheduled_today/');
  },

  // Contacts
  async getContacts(params?: {
    page?: number;
    contact_type?: string;
    outcome?: string;
    loan?: string;
    customer?: string;
    requires_escalation?: boolean;
    promise_kept?: boolean;
  }): Promise<PaginatedResponse<CollectionContact>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiClient.get<PaginatedResponse<CollectionContact>>(
      `/api/loans/collection-contacts/?${queryParams.toString()}`
    );
  },

  async getContact(id: string): Promise<CollectionContact> {
    return apiClient.get<CollectionContact>(`/api/loans/collection-contacts/${id}/`);
  },

  async createContact(data: CollectionContactCreate): Promise<CollectionContact> {
    return apiClient.post<CollectionContact>('/api/loans/collection-contacts/', data);
  },

  async updateContact(id: string, data: Partial<CollectionContactCreate>): Promise<CollectionContact> {
    return apiClient.put<CollectionContact>(`/api/loans/collection-contacts/${id}/`, data);
  },

  async deleteContact(id: string): Promise<void> {
    return apiClient.delete(`/api/loans/collection-contacts/${id}/`);
  },

  async markPromiseKept(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/api/loans/collection-contacts/${id}/mark_promise_kept/`
    );
  },

  async markPromiseBroken(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/api/loans/collection-contacts/${id}/mark_promise_broken/`
    );
  },

  async escalateContact(id: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/api/loans/collection-contacts/${id}/escalate/`
    );
  },

  async getRequiringEscalation(): Promise<CollectionContact[]> {
    return apiClient.get<CollectionContact[]>(
      '/api/loans/collection-contacts/requiring_escalation/'
    );
  },

  async getPromisesDueToday(): Promise<CollectionContact[]> {
    return apiClient.get<CollectionContact[]>('/api/loans/collection-contacts/promises_due_today/');
  },

  async getBrokenPromises(): Promise<CollectionContact[]> {
    return apiClient.get<CollectionContact[]>('/api/loans/collection-contacts/broken_promises/');
  },

  async getContactsByCollector(params?: {
    user_id?: string;
    start_date?: string;
    end_date?: string;
  }): Promise<CollectionContact[]> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, String(value));
      });
    }
    return apiClient.get<CollectionContact[]>(
      `/api/loans/collection-contacts/by_collector/?${queryParams.toString()}`
    );
  },
};
