/**
 * Theme Configuration for CrediFlux
 *
 * This file defines the two theme versions available:
 * - v1: Blue/Purple theme (original)
 * - v2: Green theme with Inter Tight font (new style guide)
 */

export type ThemeVersion = 'v1' | 'v2';

export interface ThemeConfig {
  version: ThemeVersion;
  name: string;
  colors: {
    primary: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    secondary: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
  };
  fonts: {
    heading: string;
    body: string;
  };
}

export const themes: Record<ThemeVersion, ThemeConfig> = {
  v1: {
    version: 'v1',
    name: 'CrediFlux v1',
    colors: {
      primary: {
        50: '#f0f9ff',
        100: '#e0f2fe',
        200: '#bae6fd',
        300: '#7dd3fc',
        400: '#38bdf8',
        500: '#0ea5e9',
        600: '#0284c7',
        700: '#0369a1',
        800: '#075985',
        900: '#0c4a6e',
      },
      secondary: {
        50: '#faf5ff',
        100: '#f3e8ff',
        200: '#e9d5ff',
        300: '#d8b4fe',
        400: '#c084fc',
        500: '#a855f7',
        600: '#9333ea',
        700: '#7e22ce',
        800: '#6b21a8',
        900: '#581c87',
      },
    },
    fonts: {
      heading: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      body: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
  },
  v2: {
    version: 'v2',
    name: 'CrediFlux v2',
    colors: {
      primary: {
        0: '#f1f8f4',   // Lightest green
        25: '#c8e6c9',  // Light green
        50: '#a5d6a7',  // Light-medium green
        100: '#81c784', // Medium-light green
        200: '#66bb6a', // Medium green
        300: '#4caf50', // Base green (main primary)
        400: '#43a047', // Medium-dark green
        500: '#388e3c', // Dark green
        600: '#2e7d32', // Darker green
        700: '#1b5e20', // Very dark green
        800: '#1b5e20', // Extra dark green
        900: '#0d3c15', // Darkest green
      },
      secondary: {
        0: '#e8f5e9',   // Lightest grey-green
        25: '#c5cac8',  // Light grey
        50: '#9fa39f',  // Medium-light grey
        100: '#7a7f7a', // Medium grey
        200: '#636a63', // Medium-dark grey
        300: '#4d524d', // Dark grey
        400: '#3e433e', // Darker grey
        500: '#2f342f', // Very dark grey
        600: '#212421', // Extra dark grey
        700: '#1a1d1a', // Almost black
        800: '#141614', // Very dark
        900: '#0f110f', // Darkest
      },
    },
    fonts: {
      heading: '"Inter Tight", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      body: '"Inter Tight", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
  },
};

export function getTheme(version: ThemeVersion): ThemeConfig {
  return themes[version] || themes.v1;
}
