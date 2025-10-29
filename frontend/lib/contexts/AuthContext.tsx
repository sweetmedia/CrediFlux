'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI } from '@/lib/api/auth';
import { User, Tenant, LoginCredentials, TenantLoginResponse } from '@/types';

interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<TenantLoginResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  refreshTenant: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Initialize auth state from localStorage
  const initializeAuth = useCallback(async () => {
    try {
      setIsLoading(true);

      // Check if we have a token
      if (!authAPI.isAuthenticated()) {
        setUser(null);
        setTenant(null);
        setIsLoading(false);
        return;
      }

      // Load user and tenant from localStorage first (for instant UI)
      const storedUser = authAPI.getStoredUser();
      const storedTenant = authAPI.getStoredTenant();

      if (storedUser && storedTenant) {
        setUser(storedUser);
        setTenant(storedTenant);
      }

      // Then fetch fresh data from API
      try {
        const freshUser = await authAPI.getProfile();
        setUser(freshUser);

        // Update localStorage with fresh data
        if (typeof window !== 'undefined') {
          localStorage.setItem('user', JSON.stringify(freshUser));
        }
      } catch (error) {
        // If API call fails, logout
        console.error('Failed to fetch user profile:', error);
        await handleLogout();
      }
    } catch (error) {
      console.error('Error initializing auth:', error);
      setUser(null);
      setTenant(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  const handleLogin = async (credentials: LoginCredentials): Promise<TenantLoginResponse> => {
    try {
      const response = await authAPI.login(credentials);

      setUser(response.user);
      setTenant(response.tenant);

      return response;
    } catch (error) {
      throw error;
    }
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      setUser(null);
      setTenant(null);
      router.push('/login');
    }
  };

  const refreshUser = async () => {
    try {
      const freshUser = await authAPI.getProfile();
      setUser(freshUser);

      // Update localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('user', JSON.stringify(freshUser));
      }
    } catch (error) {
      console.error('Failed to refresh user:', error);
      throw error;
    }
  };

  const refreshTenant = async () => {
    try {
      // Import tenantsAPI dynamically to avoid circular dependency
      const { tenantsAPI } = await import('@/lib/api/tenants');
      const freshTenant = await tenantsAPI.getSettings();
      setTenant(freshTenant);

      // Update localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('tenant', JSON.stringify(freshTenant));
      }
    } catch (error) {
      console.error('Failed to refresh tenant:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    tenant,
    isAuthenticated: !!user,
    isLoading,
    login: handleLogin,
    logout: handleLogout,
    refreshUser,
    refreshTenant,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
