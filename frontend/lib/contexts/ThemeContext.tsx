'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeVersion, ThemeConfig, getTheme } from '../config/themes';
import { getApiUrl } from '../api/client';

interface ThemeContextType {
  theme: ThemeConfig;
  themeVersion: ThemeVersion;
  isLoading: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeVersion, setThemeVersion] = useState<ThemeVersion>('v1');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch theme configuration from backend
    const fetchTheme = async () => {
      try {
        const apiUrl = getApiUrl();
        const response = await fetch(`${apiUrl}/api/ui-theme/`);

        if (response.ok) {
          const data = await response.json();
          const version = data.theme as ThemeVersion;

          if (version === 'v1' || version === 'v2') {
            setThemeVersion(version);

            // Apply theme to document
            applyTheme(version);
          }
        }
      } catch (error) {
        console.error('Error fetching theme:', error);
        // Fallback to v1 on error
        setThemeVersion('v1');
        applyTheme('v1');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTheme();
  }, []);

  const applyTheme = (version: ThemeVersion) => {
    const theme = getTheme(version);

    // Set CSS custom properties for colors
    const root = document.documentElement;

    // Primary colors
    Object.entries(theme.colors.primary).forEach(([key, value]) => {
      root.style.setProperty(`--color-primary-${key}`, value);
    });

    // Secondary colors
    Object.entries(theme.colors.secondary).forEach(([key, value]) => {
      root.style.setProperty(`--color-secondary-${key}`, value);
    });

    // Fonts
    root.style.setProperty('--font-heading', theme.fonts.heading);
    root.style.setProperty('--font-body', theme.fonts.body);

    // Add theme class to body
    document.body.classList.remove('theme-v1', 'theme-v2');
    document.body.classList.add(`theme-${version}`);

    // Load Inter Tight font if using v2
    if (version === 'v2') {
      loadInterTightFont();
    }
  };

  const loadInterTightFont = () => {
    // Check if font is already loaded
    if (document.querySelector('#inter-tight-font')) {
      return;
    }

    // Create link element for Google Fonts
    const link = document.createElement('link');
    link.id = 'inter-tight-font';
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&display=swap';
    document.head.appendChild(link);
  };

  const theme = getTheme(themeVersion);

  return (
    <ThemeContext.Provider value={{ theme, themeVersion, isLoading }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
