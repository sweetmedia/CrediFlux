import { apiClient } from './client';
import {
  LoginCredentials,
  TenantLoginResponse,
  TenantRegistrationData,
  EmailVerificationRequest,
  EmailVerificationConfirm,
  PasswordResetRequest,
  PasswordResetConfirm,
  ProfileUpdateData,
  PasswordChangeData,
  TeamMember,
  TeamMemberCreate,
  TeamMemberUpdate,
  User,
} from '@/types';

export const authAPI = {
  // ============================================================================
  // TENANT REGISTRATION & LOGIN
  // ============================================================================

  /**
   * Register a new tenant (company)
   */
  async registerTenant(data: TenantRegistrationData): Promise<any> {
    return apiClient.post('/api/tenants/register/', data);
  },

  /**
   * Login for tenant users
   */
  async login(credentials: LoginCredentials): Promise<TenantLoginResponse> {
    const response = await apiClient.post<TenantLoginResponse>(
      '/api/tenants/login/',
      credentials
    );

    // Save tokens and user/tenant info
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      localStorage.setItem('tenant', JSON.stringify(response.tenant));
    }

    return response;
  },

  /**
   * Logout user (blacklist refresh token)
   */
  async logout(): Promise<void> {
    if (typeof window !== 'undefined') {
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          await apiClient.post('/api/users/auth/logout/', {
            refresh_token: refreshToken,
          });
        } catch (error) {
          console.error('Error during logout:', error);
        }
      }

      // Clear all auth data
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant');
    }
  },

  // ============================================================================
  // EMAIL VERIFICATION
  // ============================================================================

  /**
   * Send email verification link
   */
  async sendEmailVerification(data: EmailVerificationRequest): Promise<any> {
    return apiClient.post('/api/users/auth/verify-email/send/', data);
  },

  /**
   * Confirm email verification
   */
  async confirmEmailVerification(data: EmailVerificationConfirm): Promise<any> {
    return apiClient.post('/api/users/auth/verify-email/confirm/', data);
  },

  // ============================================================================
  // PASSWORD RESET
  // ============================================================================

  /**
   * Request password reset link
   */
  async requestPasswordReset(data: PasswordResetRequest): Promise<any> {
    return apiClient.post('/api/users/auth/password-reset/request/', data);
  },

  /**
   * Confirm password reset with new password
   */
  async confirmPasswordReset(data: PasswordResetConfirm): Promise<any> {
    return apiClient.post('/api/users/auth/password-reset/confirm/', data);
  },

  // ============================================================================
  // PROFILE MANAGEMENT
  // ============================================================================

  /**
   * Get current user profile
   */
  async getProfile(): Promise<User> {
    return apiClient.get<User>('/api/users/profile/');
  },

  /**
   * Update current user profile
   */
  async updateProfile(data: ProfileUpdateData): Promise<User> {
    // If there's an avatar file, use FormData
    if (data.avatar instanceof File) {
      const formData = new FormData();
      Object.entries(data).forEach(([key, value]) => {
        if (value !== null && value !== undefined) {
          formData.append(key, value);
        }
      });

      return apiClient.patch<User>('/api/users/profile/update/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    }

    return apiClient.patch<User>('/api/users/profile/update/', data);
  },

  /**
   * Change password (requires current password)
   */
  async changePassword(data: PasswordChangeData): Promise<any> {
    return apiClient.post('/api/users/profile/change-password/', data);
  },

  // ============================================================================
  // TEAM MANAGEMENT
  // ============================================================================

  /**
   * List all team members
   */
  async getTeamMembers(): Promise<TeamMember[]> {
    return apiClient.get<TeamMember[]>('/api/users/team/');
  },

  /**
   * Get specific team member details
   */
  async getTeamMember(id: number): Promise<TeamMember> {
    return apiClient.get<TeamMember>(`/api/users/team/${id}/`);
  },

  /**
   * Create new team member (staff user)
   */
  async createTeamMember(data: TeamMemberCreate): Promise<TeamMember> {
    return apiClient.post<TeamMember>('/api/users/team/create/', data);
  },

  /**
   * Update team member
   */
  async updateTeamMember(id: number, data: TeamMemberUpdate): Promise<TeamMember> {
    return apiClient.patch<TeamMember>(`/api/users/team/${id}/`, data);
  },

  /**
   * Delete (deactivate) team member
   */
  async deleteTeamMember(id: number): Promise<any> {
    return apiClient.delete(`/api/users/team/${id}/`);
  },

  // ============================================================================
  // TOKEN MANAGEMENT
  // ============================================================================

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<{ access: string; refresh: string }> {
    return apiClient.post<{ access: string; refresh: string }>(
      '/api/auth/token/refresh/',
      { refresh: refreshToken }
    );
  },

  /**
   * Get stored user data from localStorage
   */
  getStoredUser(): User | null {
    if (typeof window === 'undefined') return null;

    const userStr = localStorage.getItem('user');
    if (!userStr) return null;

    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  },

  /**
   * Get stored tenant data from localStorage
   */
  getStoredTenant(): any | null {
    if (typeof window === 'undefined') return null;

    const tenantStr = localStorage.getItem('tenant');
    if (!tenantStr) return null;

    try {
      return JSON.parse(tenantStr);
    } catch {
      return null;
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;

    const accessToken = localStorage.getItem('access_token');
    return !!accessToken;
  },
};
