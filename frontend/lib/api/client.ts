import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * Get API URL based on current browser hostname
 * Supports multi-tenant subdomain routing
 *
 * @returns The API base URL for the current tenant
 */
export function getApiUrl(): string {
  // Server-side: use env variable
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  // Client-side: detect subdomain from browser
  const hostname = window.location.hostname;
  const port = ':8000'; // Backend always on port 8000

  // If accessing via subdomain (e.g., democompany.localhost, caproinsa.localhost)
  // use the same subdomain for API calls
  if (hostname.includes('.localhost')) {
    return `http://${hostname}${port}`;
  }

  // Default to localhost:8000 for regular localhost access
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

// Log initial configuration
if (typeof window !== 'undefined') {
  console.log('🔧 API Client Configuration:');
  console.log('  - Hostname:', window.location.hostname);
  console.log('  - NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);
  console.log('  - API_URL (dynamic):', getApiUrl());
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Calculate baseURL dynamically for each request
        config.baseURL = getApiUrl();

        // Get token from localStorage
        if (typeof window !== 'undefined') {
          const token = localStorage.getItem('access_token');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // If error is 403 (Forbidden) - redirect to access denied page
        if (error.response?.status === 403) {
          const errorData = error.response.data as any;
          const reason = errorData?.detail || errorData?.error || 'No tienes permisos para acceder a este recurso.';
          const permission = errorData?.required_permission;

          // Get current URL for return
          const currentUrl = typeof window !== 'undefined' ? window.location.pathname : '/dashboard';

          // Build access denied URL with params
          const params = new URLSearchParams({
            reason,
            returnUrl: currentUrl,
          });

          if (permission) {
            params.append('permission', permission);
          }

          // Redirect to access denied page
          if (typeof window !== 'undefined') {
            window.location.href = `/access-denied?${params.toString()}`;
          }

          return Promise.reject(error);
        }

        // If error is 401 and we haven't retried yet
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // Try to refresh token
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              const response = await axios.post(`${getApiUrl()}/api/auth/token/refresh/`, {
                refresh: refreshToken,
              });

              const { access } = response.data;
              localStorage.setItem('access_token', access);

              // Retry original request
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${access}`;
              }
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, logout user
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
}

export const apiClient = new APIClient();
