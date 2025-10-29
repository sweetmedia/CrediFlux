import { apiClient } from './client';
import { PaginatedResponse } from '@/types';

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone?: string;
  role: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title?: string;
  department?: string;
  is_active: boolean;
  is_tenant_owner: boolean;
  is_staff: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface CreateUserData {
  email: string;
  username?: string;
  first_name: string;
  last_name: string;
  phone?: string;
  password: string;
  role?: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title?: string;
  department?: string;
}

export interface UpdateUserData {
  first_name?: string;
  last_name?: string;
  phone?: string;
  role?: 'admin' | 'manager' | 'loan_officer' | 'accountant' | 'cashier' | 'viewer';
  job_title?: string;
  department?: string;
  is_active?: boolean;
}

export const usersAPI = {
  // Get all team members
  async getTeamMembers(params?: {
    page?: number;
    search?: string;
    role?: string;
    is_active?: boolean;
  }): Promise<PaginatedResponse<User>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          queryParams.append(key, String(value));
        }
      });
    }
    return apiClient.get<PaginatedResponse<User>>(
      `/api/users/team/?${queryParams.toString()}`
    );
  },

  // Get team member by ID
  async getTeamMember(id: string): Promise<User> {
    return apiClient.get<User>(`/api/users/team/${id}/`);
  },

  // Create new team member
  async createTeamMember(data: CreateUserData): Promise<User> {
    return apiClient.post<User>('/api/users/team/create/', data);
  },

  // Update team member
  async updateTeamMember(id: string, data: UpdateUserData): Promise<User> {
    return apiClient.put<User>(`/api/users/team/${id}/`, data);
  },

  // Deactivate team member
  async deleteTeamMember(id: string): Promise<void> {
    return apiClient.delete(`/api/users/team/${id}/`);
  },

  // Get current user profile
  async getProfile(): Promise<User> {
    return apiClient.get<User>('/api/users/profile/');
  },

  // Update current user profile
  async updateProfile(data: Partial<User>): Promise<User> {
    return apiClient.put<User>('/api/users/profile/update/', data);
  },

  // Change password
  async changePassword(data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }): Promise<void> {
    return apiClient.post('/api/users/profile/change-password/', data);
  },
};
