'use client'

import type { ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface AsyncBoundaryProps {
  isLoading: boolean
  error?: Error | string | null | unknown
  skeleton?: ReactNode
  errorFallback?: ReactNode
  retry?: () => void
  children: ReactNode
  className?: string
}

/**
 * Replaces the repetitive `if (isLoading) return <X />; if (error) return <Y />`
 * pattern with a declarative boundary.
 */
export function AsyncBoundary({
  isLoading,
  error,
  skeleton,
  errorFallback,
  retry,
  children,
  className,
}: AsyncBoundaryProps) {
  if (isLoading) {
    return (
      <div className={className}>
        {skeleton ?? <DefaultSkeleton />}
      </div>
    )
  }

  if (error) {
    return (
      <div className={className}>
        {errorFallback ?? <DefaultError error={error} retry={retry} />}
      </div>
    )
  }

  return <>{children}</>
}

function DefaultSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-32 w-full" />
    </div>
  )
}

function DefaultError({ error, retry }: { error: unknown; retry?: () => void }) {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : 'Ocurrió un error inesperado.'

  return (
    <Alert variant="destructive" className={cn('items-start gap-2')}>
      <AlertCircle className="h-4 w-4" />
      <div className="flex-1">
        <AlertTitle>No se pudo cargar</AlertTitle>
        <AlertDescription className="mt-1">{message}</AlertDescription>
        {retry && (
          <Button
            size="sm"
            variant="outline"
            onClick={retry}
            className="mt-3"
          >
            <RefreshCw className="mr-2 h-3 w-3" />
            Reintentar
          </Button>
        )}
      </div>
    </Alert>
  )
}
