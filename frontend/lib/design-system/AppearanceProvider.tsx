/**
 * AppearanceProvider — light / dark / system color-scheme management.
 *
 * - Persists user choice to localStorage under STORAGE_KEY.
 * - In 'system' mode, follows OS preference and reacts to changes live.
 * - Toggles the `dark` class on <html>, which Tailwind's darkMode: ['class']
 *   uses to flip CSS variables in globals.css.
 * - No flash on initial paint: see <AppearanceScript /> below — inject it
 *   in <head> from app/layout.tsx so the class is set before React mounts.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type AppearanceMode = 'light' | 'dark' | 'system';
export type ResolvedAppearance = 'light' | 'dark';

const STORAGE_KEY = 'cf-appearance';
const MODES: AppearanceMode[] = ['light', 'dark', 'system'];

interface AppearanceContextValue {
  /** What the user picked. */
  mode: AppearanceMode;
  /** What is actually painted right now (system → light|dark). */
  resolved: ResolvedAppearance;
  /** Update the mode and persist. */
  setMode: (mode: AppearanceMode) => void;
  /** Cycle light → dark → system → light. Convenient for a single-button toggle. */
  cycle: () => void;
}

const AppearanceContext = createContext<AppearanceContextValue | undefined>(
  undefined
);

function getSystemPreference(): ResolvedAppearance {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

function readStoredMode(): AppearanceMode {
  if (typeof window === 'undefined') return 'system';
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value && (MODES as string[]).includes(value)) {
      return value as AppearanceMode;
    }
  } catch {
    /* localStorage may be blocked (private mode, SSR) — ignore. */
  }
  return 'system';
}

function applyMode(resolved: ResolvedAppearance) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (resolved === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  // Hint to the UA for native form controls, scrollbars, etc.
  root.style.colorScheme = resolved;
}

export function AppearanceProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Read once on mount. We don't read during SSR — the inline script in
  // <head> sets the class for the first paint, then we hydrate to match.
  const [mode, setModeState] = useState<AppearanceMode>('system');
  const [systemPref, setSystemPref] =
    useState<ResolvedAppearance>('light');

  // Initial sync
  useEffect(() => {
    setModeState(readStoredMode());
    setSystemPref(getSystemPreference());
  }, []);

  // Watch system preference when relevant
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      setSystemPref(e.matches ? 'dark' : 'light');
    };
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  const resolved: ResolvedAppearance = useMemo(
    () => (mode === 'system' ? systemPref : mode),
    [mode, systemPref]
  );

  // Reflect the resolved mode on <html>
  useEffect(() => {
    applyMode(resolved);
  }, [resolved]);

  const setMode = useCallback((next: AppearanceMode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const cycle = useCallback(() => {
    setModeState((prev) => {
      const next: AppearanceMode =
        prev === 'light' ? 'dark' : prev === 'dark' ? 'system' : 'light';
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const value = useMemo<AppearanceContextValue>(
    () => ({ mode, resolved, setMode, cycle }),
    [mode, resolved, setMode, cycle]
  );

  return (
    <AppearanceContext.Provider value={value}>
      {children}
    </AppearanceContext.Provider>
  );
}

export function useAppearance(): AppearanceContextValue {
  const ctx = useContext(AppearanceContext);
  if (!ctx) {
    throw new Error('useAppearance must be used within an AppearanceProvider');
  }
  return ctx;
}

/**
 * AppearanceScript — render in <head> from app/layout.tsx so the correct
 * class is set on <html> BEFORE React mounts. Prevents the white flash
 * when a dark-mode user reloads.
 *
 * Kept tiny on purpose: it runs synchronously, blocking, before paint.
 */
export function AppearanceScript() {
  const code = `
(function(){
  try {
    var k='${STORAGE_KEY}';
    var m=localStorage.getItem(k);
    if(m!=='light'&&m!=='dark'&&m!=='system') m='system';
    var d=m==='dark'||(m==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);
    var r=document.documentElement;
    if(d) r.classList.add('dark'); else r.classList.remove('dark');
    r.style.colorScheme=d?'dark':'light';
  } catch(e){}
})();
`.trim();
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
