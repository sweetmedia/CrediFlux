'use client'

import type { ReactNode } from 'react'

import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface FormFieldProps {
  name: string
  label: string
  description?: string
  error?: string
  required?: boolean
  children: ReactNode
  className?: string
}

/**
 * Label-above-input wrapper with consistent spacing, required indicator,
 * and error message placement.
 *
 * For react-hook-form integration, use the primitives in components/ui/form.tsx
 * directly. This DS component is for ad-hoc forms and controlled inputs that
 * don't want the full RHF setup.
 */
export function FormField({
  name,
  label,
  description,
  error,
  required,
  children,
  className,
}: FormFieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <Label htmlFor={name} className={cn(error && 'text-destructive')}>
        {label}
        {required && (
          <span className="ml-1 text-[var(--color-flame-500)]" aria-hidden="true">
            *
          </span>
        )}
      </Label>
      {children}
      {error ? (
        <p className="text-xs font-medium text-destructive">{error}</p>
      ) : description ? (
        <p className="text-xs text-muted-foreground">{description}</p>
      ) : null}
    </div>
  )
}
