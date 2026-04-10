'use client'

import { cn } from '@/lib/utils'
import { useConfig } from '@/lib/contexts/ConfigContext'

interface MoneyProps {
  amount: number | string | null | undefined
  currency?: string
  decimals?: number
  className?: string
  /** Show explicit +/- sign. Default false. */
  showSign?: boolean
  /** Green for positive, red for negative. Default false. */
  colorize?: boolean
}

/**
 * Formatted currency display.
 *
 * Uses Intl.NumberFormat with the tenant's currency from ConfigContext,
 * falling back to DOP. Always renders in a monospace tabular-nums font
 * so columns of numbers align cleanly.
 */
export function Money({
  amount,
  currency,
  decimals,
  className,
  showSign = false,
  colorize = false,
}: MoneyProps) {
  const { config } = useConfig()
  const ccy = currency ?? config.currency ?? 'DOP'
  const digits = decimals ?? config.decimal_places ?? 2

  const numeric = typeof amount === 'string' ? parseFloat(amount) : amount ?? 0
  const isNegative = numeric < 0

  const formatter = new Intl.NumberFormat('es-DO', {
    style: 'currency',
    currency: ccy,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: showSign ? 'always' : 'auto',
  })

  return (
    <span
      className={cn(
        'cf-mono-number',
        colorize && isNegative && 'text-[var(--color-danger)]',
        colorize && !isNegative && numeric > 0 && 'text-[var(--color-success)]',
        className
      )}
    >
      {formatter.format(numeric)}
    </span>
  )
}
