'use client'

import type { LucideIcon } from 'lucide-react'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { Money } from './Money'

type StatFormat = 'currency' | 'number' | 'percentage' | 'text'

interface StatTrend {
  value: number
  label: string
  direction: 'up' | 'down' | 'neutral'
}

interface StatCardProps {
  title: string
  value: string | number
  icon?: LucideIcon
  trend?: StatTrend
  format?: StatFormat
  currency?: string
  isLoading?: boolean
  className?: string
}

/**
 * Single metric card for dashboards.
 *
 * Renders value in tabular-num mono for clean alignment. When format is
 * `currency`, delegates to <Money/> so the display inherits the tenant's
 * currency formatting rules.
 */
export function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  format = 'number',
  currency,
  isLoading = false,
  className,
}: StatCardProps) {
  return (
    <Card className={cn('cf-surface-card', className)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="cf-section-title">{title}</p>
            <div className="mt-2">
              {isLoading ? (
                <Skeleton className="h-8 w-32" />
              ) : format === 'currency' && typeof value === 'number' ? (
                <Money amount={value} currency={currency} className="text-2xl font-bold" />
              ) : (
                <span className="cf-mono-number text-2xl font-bold text-foreground">
                  {formatValue(value, format)}
                </span>
              )}
            </div>
            {trend && !isLoading && <TrendIndicator trend={trend} />}
          </div>
          {Icon && (
            <div className="rounded-lg bg-[var(--color-forest-50)] p-2.5">
              <Icon
                className="h-5 w-5 text-[var(--color-forest-700)]"
                strokeWidth={1.75}
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function formatValue(value: string | number, format: StatFormat): string {
  if (format === 'percentage' && typeof value === 'number') {
    return `${value.toFixed(1)}%`
  }
  if (format === 'number' && typeof value === 'number') {
    return new Intl.NumberFormat('es-DO').format(value)
  }
  return String(value)
}

function TrendIndicator({ trend }: { trend: StatTrend }) {
  const Icon =
    trend.direction === 'up' ? TrendingUp : trend.direction === 'down' ? TrendingDown : Minus
  const colorClass =
    trend.direction === 'up'
      ? 'text-[var(--color-success)]'
      : trend.direction === 'down'
        ? 'text-[var(--color-danger)]'
        : 'text-muted-foreground'

  return (
    <div className={cn('mt-2 flex items-center gap-1 text-xs', colorClass)}>
      <Icon className="h-3.5 w-3.5" />
      <span className="font-medium">{trend.value > 0 ? '+' : ''}{trend.value}%</span>
      <span className="text-muted-foreground">{trend.label}</span>
    </div>
  )
}
