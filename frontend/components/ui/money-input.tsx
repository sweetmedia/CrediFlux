'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';

const DISPLAY_LOCALE = 'es-DO';

/** "1,234.5" → "1234.5". Deja solo dígitos y un punto decimal. */
export function parseMoneyInput(text: string, decimals = 2): string {
  const cleaned = text.replace(/[^\d.]/g, '');
  const [int = '', ...rest] = cleaned.split('.');
  if (rest.length === 0) return int;
  return `${int}.${rest.join('').slice(0, decimals)}`;
}

function formatForDisplay(raw: string, decimals: number): string {
  if (raw === '' || raw === '.') return '';
  const n = Number(raw);
  if (Number.isNaN(n)) return raw;
  return n.toLocaleString(DISPLAY_LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export interface MoneyInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'type' | 'inputMode' | 'defaultValue'> {
  /** Valor numérico sin formato, p. ej. "1234.50". Vacío = sin valor. */
  value: string | number | null | undefined;
  onValueChange: (raw: string) => void;
  /** Símbolo de moneda que se muestra dentro del campo. */
  currencySymbol?: string;
  decimals?: number;
}

/**
 * Campo de monto: teclado decimal en móvil, mono tabular, y separador de miles
 * al salir del campo. Entrega siempre el valor crudo ("1234.5") a onValueChange.
 */
export const MoneyInput = React.forwardRef<HTMLInputElement, MoneyInputProps>(
  ({ value, onValueChange, currencySymbol, decimals = 2, className, onFocus, onBlur, ...props }, ref) => {
    const raw = value === null || value === undefined ? '' : String(value);
    const [focused, setFocused] = React.useState(false);
    const [draft, setDraft] = React.useState(raw);

    // Mientras se edita mostramos lo que el usuario escribe; si el valor cambia
    // desde fuera (p. ej. al elegir un préstamo) lo reflejamos.
    React.useEffect(() => {
      if (!focused) setDraft(raw);
    }, [raw, focused]);

    const display = focused ? draft : formatForDisplay(raw, decimals);

    return (
      <div className="relative">
        {currencySymbol && (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-3 flex items-center font-mono text-sm text-fg-muted"
          >
            {currencySymbol}
          </span>
        )}
        <Input
          ref={ref}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={display}
          onFocus={(e) => {
            setFocused(true);
            setDraft(raw);
            onFocus?.(e);
          }}
          onChange={(e) => {
            const next = parseMoneyInput(e.target.value, decimals);
            setDraft(next);
            onValueChange(next);
          }}
          onBlur={(e) => {
            setFocused(false);
            if (raw.endsWith('.')) onValueChange(raw.slice(0, -1));
            onBlur?.(e);
          }}
          className={cn('font-mono tabular-nums', currencySymbol && 'pl-12', className)}
          {...props}
        />
      </div>
    );
  }
);
MoneyInput.displayName = 'MoneyInput';
