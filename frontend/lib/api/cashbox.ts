/**
 * Cash Management API client
 */
import { apiClient } from './client';

export interface CashRegister {
  id: string;
  name: string;
  code: string;
  location: string;
  is_active: boolean;
  default_cashier: string | null;
  default_cashier_name: string;
}

export interface CashSession {
  id: string;
  register: string;
  register_name: string;
  cashier: string;
  cashier_name: string;
  opened_at: string;
  opening_balance: number;
  opening_notes: string;
  closed_at: string | null;
  closing_balance: number | null;
  expected_balance: number | null;
  difference: number | null;
  closing_notes: string;
  status: string;
  status_display: string;
  total_inflows: number;
  total_outflows: number;
}

export interface CashMovement {
  id: string;
  session: string;
  movement_type: 'inflow' | 'outflow';
  type_display: string;
  category: string;
  category_display: string;
  amount: number;
  description: string;
  reference: string;
  customer_name: string;
  recorded_by_name: string;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  register: string;
  status: string;
  opened_at: string;
  closed_at: string | null;
  opening_balance: number;
  total_inflows: number;
  total_outflows: number;
  expected_balance: number;
  closing_balance: number | null;
  difference: number | null;
  inflows_by_category: { category: string; total: number }[];
  outflows_by_category: { category: string; total: number }[];
  movement_count: number;
}

export const cashboxAPI = {
  // Registers
  async getRegisters(): Promise<CashRegister[]> {
    const data = await apiClient.get<any>('/api/cashbox/registers/');
    return Array.isArray(data) ? data : data.results || [];
  },

  async createRegister(data: Partial<CashRegister>): Promise<CashRegister> {
    return apiClient.post<CashRegister>('/api/cashbox/registers/', data);
  },

  // Sessions
  async getSessions(params?: { register?: string; status?: string }): Promise<CashSession[]> {
    const qp = new URLSearchParams();
    if (params?.register) qp.append('register', params.register);
    if (params?.status) qp.append('status', params.status);
    const data = await apiClient.get<any>(`/api/cashbox/sessions/?${qp.toString()}`);
    return Array.isArray(data) ? data : data.results || [];
  },

  async getActiveSessions(): Promise<CashSession[]> {
    return apiClient.get<CashSession[]>('/api/cashbox/sessions/active/');
  },

  async openSession(data: { register: string; opening_balance: number; opening_notes?: string }): Promise<CashSession> {
    return apiClient.post<CashSession>('/api/cashbox/sessions/open/', data);
  },

  async closeSession(sessionId: string, data: { closing_balance: number; closing_notes?: string }): Promise<CashSession> {
    return apiClient.post<CashSession>(`/api/cashbox/sessions/${sessionId}/close/`, data);
  },

  async getSessionSummary(sessionId: string): Promise<SessionSummary> {
    return apiClient.get<SessionSummary>(`/api/cashbox/sessions/${sessionId}/summary/`);
  },

  async getSessionMovements(sessionId: string): Promise<CashMovement[]> {
    return apiClient.get<CashMovement[]>(`/api/cashbox/sessions/${sessionId}/movements/`);
  },

  // Movements
  async createMovement(data: any): Promise<CashMovement> {
    return apiClient.post<CashMovement>('/api/cashbox/movements/', data);
  },

  async getMovements(params?: { session?: string; movement_type?: string; category?: string }): Promise<CashMovement[]> {
    const qp = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => { if (v) qp.append(k, v); });
    }
    const data = await apiClient.get<any>(`/api/cashbox/movements/?${qp.toString()}`);
    return Array.isArray(data) ? data : data.results || [];
  },
};
