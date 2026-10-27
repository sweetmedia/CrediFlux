/**
 * ThemeSwitch — claro / oscuro / sistema en tres segmentos (D3: topbar de la
 * app; D8: en móvil va dentro del menú de usuario). Radios con flechas, como
 * el `cf-theme-switch` del canvas.
 */

import * as React from 'react';
import { Monitor, Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppearance, type AppearanceMode } from './AppearanceProvider';

const OPCIONES: { mode: AppearanceMode; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { mode: 'light', label: 'Claro', Icon: Sun },
  { mode: 'dark', label: 'Oscuro', Icon: Moon },
  { mode: 'system', label: 'Sistema', Icon: Monitor },
];

export interface ThemeSwitchProps {
  className?: string;
}

export function ThemeSwitch({ className }: ThemeSwitchProps) {
  const { mode, setMode } = useAppearance();
  const refs = React.useRef<(HTMLButtonElement | null)[]>([]);

  const mover = (desde: number, paso: number) => {
    const i = (desde + paso + OPCIONES.length) % OPCIONES.length;
    setMode(OPCIONES[i].mode);
    refs.current[i]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label="Tema"
      className={cn('inline-flex gap-px rounded-lg border border-sage-200 bg-sage-50 p-0.5', className)}
    >
      {OPCIONES.map(({ mode: m, label, Icon }, i) => {
        const activo = m === mode;
        return (
          <button
            key={m}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={activo}
            aria-label={label}
            title={label}
            tabIndex={activo ? 0 : -1}
            onClick={() => setMode(m)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                e.preventDefault();
                mover(i, 1);
              } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                e.preventDefault();
                mover(i, -1);
              }
            }}
            className={cn(
              'grid h-6 w-7 place-items-center rounded-md border border-transparent text-sage-500',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-400',
              activo && 'border-sage-200 bg-white text-forest-900',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
          </button>
        );
      })}
    </div>
  );
}
