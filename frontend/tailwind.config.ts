import type { Config } from "tailwindcss"
import animate from "tailwindcss-animate"

/**
 * V2 token-driven Tailwind config.
 *
 * Two utility namespaces coexist during the V1 → V2 migration:
 *
 *   V2 (preferred, semantic): bg-bg, bg-surface, text-fg, text-fg-muted,
 *                             border-border (same name, V2 token), bg-accent,
 *                             text-success-fg, bg-danger-bg, etc.
 *
 *   V1 (legacy):              bg-background, bg-card, text-foreground,
 *                             bg-primary, bg-destructive, bg-muted, ...
 *
 * Delete a V1 entry once every page that used it has been rebuilt.
 */

/** Helper: turn an HSL triplet token into an hsl() w/ optional alpha */
const hsl = (token: string) => `hsl(var(${token}) / <alpha-value>)`

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      // ----------------------------------------------------------
      // Fonts
      // ----------------------------------------------------------
      fontFamily: {
        display: ['var(--font-display)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },

      // ----------------------------------------------------------
      // Type scale (V2)
      // ----------------------------------------------------------
      fontSize: {
        'display-xl': ['48px', { lineHeight: '56px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'display-lg': ['36px', { lineHeight: '44px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-xl': ['28px', { lineHeight: '36px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-lg': ['22px', { lineHeight: '30px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'heading-md': ['18px', { lineHeight: '26px', fontWeight: '600' }],
        'heading-sm': ['15px', { lineHeight: '22px', fontWeight: '600' }],
        'body-lg':    ['16px', { lineHeight: '24px' }],
        'body':       ['15px', { lineHeight: '22px' }],
        'body-sm':    ['13px', { lineHeight: '20px' }],
        'label':      ['13px', { lineHeight: '18px', fontWeight: '500' }],
        'caption':    ['12px', { lineHeight: '16px' }],
        'mono':       ['14px', { lineHeight: '22px', fontWeight: '500' }],
        'mono-sm':    ['12px', { lineHeight: '18px', fontWeight: '500' }],
      },

      // ----------------------------------------------------------
      // Colors — V2 semantic + V1 legacy
      // ----------------------------------------------------------
      colors: {
        // V2 semantic tokens ----------------------------------
        bg:               hsl('--color-bg'),
        surface: {
          DEFAULT:        hsl('--color-surface'),
          raised:         hsl('--color-surface-raised'),
          sunken:         hsl('--color-surface-sunken'),
          hover:          hsl('--color-surface-hover'),
          active:         hsl('--color-surface-active'),
        },
        fg: {
          DEFAULT:        hsl('--color-fg'),
          muted:          hsl('--color-fg-muted'),
          subtle:         hsl('--color-fg-subtle'),
          'on-accent':    hsl('--color-fg-on-accent'),
          'on-status':    hsl('--color-fg-on-status'),
        },

        // V2 'border' overlaps with V1 'border' utility name —
        // we redefine it to point at the V2 token. V1 used the
        // same CSS variable shape (--border), so legacy pages
        // that wrote `border-border` still resolve correctly,
        // because we keep --border alive in globals.css :root.
        border: hsl('--color-border'),

        'border-strong': hsl('--color-border-strong'),
        'border-subtle': hsl('--color-border-subtle'),

        accent: {
          DEFAULT:        hsl('--color-accent'),
          hover:          hsl('--color-accent-hover'),
          active:         hsl('--color-accent-active'),
          muted:          hsl('--color-accent-muted'),
          // V1 compat: accent-foreground
          foreground:     hsl('--accent-foreground'),
          fg:             hsl('--color-accent-fg'),
        },

        success: {
          bg:             hsl('--color-success-bg'),
          fg:             hsl('--color-success-fg'),
          border:         hsl('--color-success-border'),
          solid:          hsl('--color-success-solid'),
        },
        warn: {
          bg:             hsl('--color-warn-bg'),
          fg:             hsl('--color-warn-fg'),
          border:         hsl('--color-warn-border'),
          solid:          hsl('--color-warn-solid'),
        },
        danger: {
          bg:             hsl('--color-danger-bg'),
          fg:             hsl('--color-danger-fg'),
          border:         hsl('--color-danger-border'),
          solid:          hsl('--color-danger-solid'),
        },
        info: {
          bg:             hsl('--color-info-bg'),
          fg:             hsl('--color-info-fg'),
          border:         hsl('--color-info-border'),
          solid:          hsl('--color-info-solid'),
        },

        // Brand palette (same values as branding/tokens.css and the F3 prototypes).
        // sun is never text or a hover fill — focus/active marks only.
        forest: { 50: '#f0f7eb', 100: '#dcecd0', 500: '#4d8630', 700: '#2d5a10', 900: '#163300', 950: '#0a1a00' },
        sage: { 50: '#f3f6f1', 100: '#e4ebe0', 200: '#c8d4be', 300: '#a8b89c', 400: '#8a9d7a', 500: '#738566', 600: '#5c6d4d', 700: '#4a5a3d' },
        sun: { 500: '#ffe026' },
        flame: { 50: '#fff4eb', 500: '#ff7503', 600: '#cc5e02' },
        cream: '#faf8f2',
        tenant: 'var(--color-tenant-primary, #163300)',

        focus:            hsl('--color-focus-ring'),
        overlay:          hsl('--color-overlay'),

        // V1 legacy tokens (kept so V1 pages keep rendering) ----
        input:            hsl('--input'),
        ring:             hsl('--ring'),
        background:       hsl('--background'),
        foreground:       hsl('--foreground'),
        primary: {
          DEFAULT:        hsl('--primary'),
          foreground:     hsl('--primary-foreground'),
        },
        secondary: {
          DEFAULT:        hsl('--secondary'),
          foreground:     hsl('--secondary-foreground'),
        },
        destructive: {
          DEFAULT:        hsl('--destructive'),
          foreground:     hsl('--destructive-foreground'),
        },
        muted: {
          DEFAULT:        hsl('--muted'),
          foreground:     hsl('--muted-foreground'),
        },
        popover: {
          DEFAULT:        hsl('--popover'),
          foreground:     hsl('--popover-foreground'),
        },
        card: {
          DEFAULT:        hsl('--card'),
          foreground:     hsl('--card-foreground'),
        },
      },

      // ----------------------------------------------------------
      // Spacing — Tailwind's default 4px scale already matches our
      // V2 spacing tokens (p-0.5 = 2px, p-1.5 = 6px, ...). The
      // --space-* CSS variables in globals.css are kept for any
      // code that wants to reference them by name from inline CSS.
      // ----------------------------------------------------------

      // ----------------------------------------------------------
      // Radii
      // ----------------------------------------------------------
      borderRadius: {
        // V2
        none: 'var(--radius-none)',
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl':'var(--radius-2xl)',
        full: 'var(--radius-full)',
      },

      // ----------------------------------------------------------
      // Elevation
      // ----------------------------------------------------------
      boxShadow: {
        'elevation-0':       'var(--elevation-0)',
        'elevation-1':       'var(--elevation-1)',
        'elevation-2':       'var(--elevation-2)',
        'elevation-3':       'var(--elevation-3)',
        'elevation-overlay': 'var(--elevation-overlay)',
      },

      // ----------------------------------------------------------
      // Motion
      // ----------------------------------------------------------
      transitionDuration: {
        instant: 'var(--duration-instant)',
        fast:    'var(--duration-fast)',
        base:    'var(--duration-base)',
        slow:    'var(--duration-slow)',
        slower:  'var(--duration-slower)',
      },
      transitionTimingFunction: {
        standard: 'var(--ease-standard)',
        // ('in', 'out', 'in-out' shadow Tailwind defaults — intentional)
        in:       'var(--ease-in)',
        out:      'var(--ease-out)',
        'in-out': 'var(--ease-in-out)',
        spring:   'var(--ease-spring)',
      },

      // ----------------------------------------------------------
      // Z-index scale
      // ----------------------------------------------------------
      zIndex: {
        base:     'var(--z-base)',
        dropdown: 'var(--z-dropdown)',
        sticky:   'var(--z-sticky)',
        overlay:  'var(--z-overlay)',
        modal:    'var(--z-modal)',
        popover:  'var(--z-popover)',
        toast:    'var(--z-toast)',
        tooltip:  'var(--z-tooltip)',
      },

      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [animate],
} satisfies Config

export default config
