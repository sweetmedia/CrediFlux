import { apiClient } from './client';

export interface AuditLog {
  id: string;
  user: number | null;
  user_email: string;
  user_name: string;
  action: string;
  action_display: string;
  model_name: string;
  object_id: string | null;
  object_repr: string;
  changes: Record<string, { old: string | null; new: string | null }>;
  ip_address: string | null;
  user_agent: string | null;
  extra_data: Record<string, unknown>;
  timestamp: string;
}

export interface AuditLogDetail extends AuditLog {
  changes_detailed: Array<{
    field: string;
    old_value: string | null;
    new_value: string | null;
  }>;
}

export interface AuditLogStats {
  total_logs: number;
  actions_by_type: Array<{ action: string; count: number }>;
  actions_by_model: Array<{ model_name: string; count: number }>;
  actions_by_user: Array<{ user_email: string; count: number }>;
  actions_by_day: Array<{ date: string; count: number }>;
}

export interface AuditLogFilters {
  user?: number;
  user_email?: string;
  action?: string;
  model_name?: string;
  object_id?: string;
  timestamp_after?: string;
  timestamp_before?: string;
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedAuditLogs {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditLog[];
}

export const auditAPI = {
  /**
   * Get list of audit logs with filtering and pagination
   */
  async getLogs(filters?: AuditLogFilters): Promise<PaginatedAuditLogs> {
    const params = new URLSearchParams();

    if (filters) {
      if (filters.user) params.append('user', filters.user.toString());
      if (filters.user_email) params.append('user_email', filters.user_email);
      if (filters.action) params.append('action', filters.action);
      if (filters.model_name) params.append('model_name', filters.model_name);
      if (filters.object_id) params.append('object_id', filters.object_id);
      if (filters.timestamp_after) params.append('timestamp_after', filters.timestamp_after);
      if (filters.timestamp_before) params.append('timestamp_before', filters.timestamp_before);
      if (filters.search) params.append('search', filters.search);
      if (filters.ordering) params.append('ordering', filters.ordering);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.page_size) params.append('page_size', filters.page_size.toString());
    }

    const queryString = params.toString();
    const url = queryString ? `/api/audit/?${queryString}` : '/api/audit/';

    return apiClient.get<PaginatedAuditLogs>(url);
  },

  /**
   * Get a single audit log entry with detailed changes
   */
  async getLog(id: string): Promise<AuditLogDetail> {
    return apiClient.get<AuditLogDetail>(`/api/audit/${id}/`);
  },

  /**
   * Get audit log statistics
   */
  async getStats(): Promise<AuditLogStats> {
    return apiClient.get<AuditLogStats>('/api/audit/stats/');
  },
};
