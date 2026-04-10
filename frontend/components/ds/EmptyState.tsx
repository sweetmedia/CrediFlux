'use client'

import type { LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface EmptyStateAction {
  label: string
  onClick: () => void
  variant?: 'default' | 'outline'
}

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: EmptyStateAction
  secondaryAction?: EmptyStateAction
  className?: string
}

/**
 * Blank-slate placeholder.
 *
 * Follows DESIGN_SYSTEM.md §8: 48px icon in sage-400, heading in display
 * font, single line of helper text, up to two action buttons.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 py-12 px-6 text-center',
        className
      )}
    >
      <div className="rounded-full bg-[var(--color-sage-50)] p-4">
        <Icon className="h-8 w-8 text-[var(--color-sage-400)]" strokeWidth={1.5} />
      </div>
      <h3 className="cf-font-display text-lg font-medium text-foreground">
        {title}
      </h3>
      {description && (
        <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {(action || secondaryAction) && (
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
          {action && (
            <Button variant={action.variant ?? 'default'} onClick={action.onClick}>
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant={secondaryAction.variant ?? 'outline'}
              onClick={secondaryAction.onClick}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
