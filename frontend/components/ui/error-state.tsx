'use client';

import * as React from 'react';
import { AlertCircle, RotateCw } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  /** Mensaje ya en español; normalmente `getApiErrorMessage(err)`. */
  message: string;
  title?: string;
  /** Si se pasa, muestra "Reintentar". Puede ser async. */
  onRetry?: () => void | Promise<void>;
  /** `inline` para banners dentro de una página; `page` para cuando la carga entera falló. */
  variant?: 'inline' | 'page';
  className?: string;
}

export function ErrorState({
  message,
  title,
  onRetry,
  variant = 'inline',
  className,
}: ErrorStateProps) {
  const [retrying, setRetrying] = React.useState(false);

  const handleRetry = async () => {
    if (!onRetry) return;
    try {
      setRetrying(true);
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  const retryButton = onRetry && (
    <Button variant="outline" size="sm" onClick={handleRetry} disabled={retrying} className="shrink-0">
      <RotateCw className={cn('mr-2 h-4 w-4', retrying && 'animate-spin')} aria-hidden />
      Reintentar
    </Button>
  );

  if (variant === 'page') {
    return (
      <div
        role="alert"
        className={cn(
          'mx-auto flex max-w-md flex-col items-center gap-3 rounded-lg border border-danger-border bg-danger-bg px-6 py-10 text-center',
          className
        )}
      >
        <AlertCircle className="h-8 w-8 text-danger-fg" aria-hidden />
        <div className="space-y-1">
          <p className="font-semibold text-fg">{title ?? 'No pudimos cargar la información'}</p>
          <p className="text-sm text-danger-fg">{message}</p>
        </div>
        {retryButton}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 rounded-lg border border-danger-border bg-danger-bg px-4 py-3',
        className
      )}
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger-fg" aria-hidden />
      <div className="min-w-0 flex-1 text-sm">
        {title && <p className="font-medium text-fg">{title}</p>}
        <p className="text-danger-fg">{message}</p>
      </div>
      {retryButton}
    </div>
  );
}
