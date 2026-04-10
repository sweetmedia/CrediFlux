'use client'

import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

import { cn } from '@/lib/utils'

type DateTimeFormat = 'short' | 'long' | 'relative' | 'datetime'

interface DateTimeProps {
  date: string | Date | null | undefined
  format?: DateTimeFormat
  className?: string
}

const formatMap: Record<Exclude<DateTimeFormat, 'relative'>, string> = {
  short: 'dd MMM yyyy',
  long: "dd 'de' MMMM 'de' yyyy",
  datetime: "dd MMM yyyy, HH:mm",
}

/**
 * Formatted date/time display.
 *
 * Uses es-DO locale by default. F2 hardcodes Spanish — M5 will switch
 * the locale based on user.preferred_language.
 */
export function DateTime({
  date,
  format: formatKey = 'short',
  className,
}: DateTimeProps) {
  if (!date) return <span className={cn('text-muted-foreground', className)}>—</span>

  const d = typeof date === 'string' ? parseISO(date) : date

  let output: string
  if (formatKey === 'relative') {
    output = formatDistanceToNow(d, { locale: es, addSuffix: true })
  } else {
    output = format(d, formatMap[formatKey], { locale: es })
  }

  return <span className={className}>{output}</span>
}
