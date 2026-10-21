'use client';

/**
 * AppearanceToggle — single-button cycler: light → dark → system → light.
 *
 * Renders the icon for the *current user choice* (not the resolved mode),
 * so the user can tell at a glance whether they've explicitly picked a
 * mode or are following the OS.
 */

import * as React from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';
import { useAppearance, type AppearanceMode } from './AppearanceProvider';

const ICONS: Record<AppearanceMode, React.ComponentType<{ className?: string }>> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

const LABELS: Record<AppearanceMode, string> = {
  light: 'Tema claro (clic para cambiar a oscuro)',
  dark: 'Tema oscuro (clic para seguir el sistema)',
  system: 'Tema del sistema (clic para cambiar a claro)',
};

export interface AppearanceToggleProps {
  className?: string;
}

export function AppearanceToggle({ className }: AppearanceToggleProps) {
  const { mode, cycle } = useAppearance();
  const Icon = ICONS[mode];

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={LABELS[mode]}
      title={LABELS[mode]}
      className={
        'inline-flex h-9 w-9 items-center justify-center rounded-md ' +
        'text-fg-muted hover:text-fg hover:bg-surface-hover ' +
        'transition-colors duration-fast ease-standard ' +
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ' +
        (className ?? '')
      }
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
