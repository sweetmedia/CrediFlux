'use client';

import * as React from 'react';

import { cn } from '@/lib/utils';
import { Label } from '@/components/ui/label';

interface FieldProps {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: string | null;
  required?: boolean;
  /** id del control; si se omite se usa el `id` del hijo o uno generado. */
  id?: string;
  className?: string;
  /**
   * Un único control (Input, MoneyInput, Textarea, NativeSelect...), o una
   * función que recibe las props de accesibilidad cuando el control va
   * envuelto (p. ej. dentro de un `Controller` de react-hook-form).
   */
  children: React.ReactElement<Record<string, unknown>> | ((control: FieldControlProps) => React.ReactNode);
}

export interface FieldControlProps {
  id: string;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
  'aria-required'?: boolean;
}

/**
 * Etiqueta + control + ayuda + error, con la accesibilidad conectada:
 * `htmlFor`/`id`, `aria-invalid`, `aria-describedby` y `aria-required`.
 */
export function Field({ label, hint, error, required, id, className, children }: FieldProps) {
  const generatedId = React.useId();
  const childProps = typeof children === 'function' ? {} : children.props;
  const controlId = id ?? (childProps.id as string | undefined) ?? generatedId;
  const hintId = hint ? `${controlId}-hint` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const describedBy =
    [childProps['aria-describedby'] as string | undefined, hintId, errorId].filter(Boolean).join(' ') ||
    undefined;

  const controlProps: FieldControlProps = {
    id: controlId,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy,
    'aria-required': required || undefined,
  };
  const control =
    typeof children === 'function' ? children(controlProps) : React.cloneElement(children, { ...controlProps });

  return (
    <div className={cn('space-y-2', className)}>
      <Label htmlFor={controlId}>
        {label}
        {required && <span className="ml-1 font-normal text-fg-muted">(obligatorio)</span>}
      </Label>
      {control}
      {hint && (
        <p id={hintId} className="text-xs text-fg-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-danger-fg">
          {error}
        </p>
      )}
    </div>
  );
}
