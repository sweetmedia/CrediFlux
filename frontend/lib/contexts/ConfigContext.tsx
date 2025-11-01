'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface TenantConfig {
  currency: string;
  currency_symbol: string;
  decimal_places: number;
  company_name: string;
}

interface ConfigContextType {
  config: TenantConfig;
  isLoading: boolean;
}

const defaultConfig: TenantConfig = {
  currency: 'USD',
  currency_symbol: '$',
  decimal_places: 2,
  company_name: 'CrediFlux',
};

const ConfigContext = createContext<ConfigContextType>({
  config: defaultConfig,
  isLoading: true,
});

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<TenantConfig>(defaultConfig);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/config/`);

        if (response.ok) {
          const data = await response.json();
          setConfig(data);
        }
      } catch (error) {
        console.error('Error fetching tenant config:', error);
        // Keep default config on error
      } finally {
        setIsLoading(false);
      }
    };

    fetchConfig();
  }, []);

  return (
    <ConfigContext.Provider value={{ config, isLoading }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}
