'use client';

import * as React from 'react';
import * as AlertDialogPrimitive from '@radix-ui/react-alert-dialog';
import { Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { buttonVariants } from '@/components/ui/button';
import { Money } from '@/components/ui/money';

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: React.ReactNode;
  /** Monto afectado por la acción; se muestra en mono tabular vía <Money>. */
  amount?: number | string | null;
  /** Cliente afectado por la acción. */
  customer?: string | null;
  confirmLabel: string;
  cancelLabel?: string;
  variant?: 'default' | 'destructive';
  /**
   * Puede ser async: el diálogo queda abierto y bloqueado mientras corre. Si devuelve
   * `false`, el diálogo sigue abierto (p. ej. para mostrar un error y reintentar).
   */
  onConfirm: () => void | boolean | Promise<void | boolean>;
  confirmDisabled?: boolean;
  /** Contenido extra entre el resumen y los botones (p. ej. un motivo). */
  children?: React.ReactNode;
}

/**
 * Confirmación para acciones irreversibles. Reemplaza al confirm() nativo:
 * muestra qué se hace, a quién y por cuánto antes de ejecutar.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  amount,
  customer,
  confirmLabel,
  cancelLabel = 'Cancelar',
  variant = 'default',
  onConfirm,
  confirmDisabled,
  children,
}: ConfirmDialogProps) {
  const [pending, setPending] = React.useState(false);
  const hasSummary = amount !== undefined && amount !== null || !!customer;

  const handleConfirm = async (e: React.MouseEvent) => {
    // Radix cierra al hacer clic en Action; lo cerramos nosotros al terminar.
    e.preventDefault();
    try {
      setPending(true);
      const result = await onConfirm();
      if (result !== false) onOpenChange(false);
    } finally {
      setPending(false);
    }
  };

  return (
    <AlertDialogPrimitive.Root open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <AlertDialogPrimitive.Portal>
        <AlertDialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:duration-200 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:duration-150" />
        <AlertDialogPrimitive.Content
          className="fixed left-[50%] top-[50%] z-50 grid w-[calc(100%-2rem)] max-w-md translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border border-border bg-surface p-6 shadow-lg ease-out data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-[0.97] data-[state=open]:duration-200 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-[0.97] data-[state=closed]:duration-150"
        >
          <div className="space-y-2">
            <AlertDialogPrimitive.Title className="text-lg font-semibold leading-tight tracking-tight text-fg">
              {title}
            </AlertDialogPrimitive.Title>
            {description ? (
              <AlertDialogPrimitive.Description className="text-sm text-fg-muted">
                {description}
              </AlertDialogPrimitive.Description>
            ) : (
              <AlertDialogPrimitive.Description className="sr-only">{title}</AlertDialogPrimitive.Description>
            )}
          </div>

          {hasSummary && (
            <dl className="grid gap-2 rounded-md border border-border bg-surface-sunken px-4 py-3 text-sm">
              {customer && (
                <div className="flex items-baseline justify-between gap-4">
                  <dt className="text-fg-muted">Cliente</dt>
                  <dd className="text-right font-medium text-fg">{customer}</dd>
                </div>
              )}
              {amount !== undefined && amount !== null && (
                <div className="flex items-baseline justify-between gap-4">
                  <dt className="text-fg-muted">Monto</dt>
                  <dd className="text-right text-base text-fg">
                    <Money value={amount} />
                  </dd>
                </div>
              )}
            </dl>
          )}

          {children}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <AlertDialogPrimitive.Cancel
              disabled={pending}
              className={cn(buttonVariants({ variant: 'outline' }))}
            >
              {cancelLabel}
            </AlertDialogPrimitive.Cancel>
            <AlertDialogPrimitive.Action
              onClick={handleConfirm}
              disabled={pending || confirmDisabled}
              className={cn(buttonVariants({ variant: variant === 'destructive' ? 'destructive' : 'default' }))}
            >
              {pending && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
              {confirmLabel}
            </AlertDialogPrimitive.Action>
          </div>
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Portal>
    </AlertDialogPrimitive.Root>
  );
}

type ConfirmOptions = Omit<ConfirmDialogProps, 'open' | 'onOpenChange' | 'onConfirm' | 'children'>;

/**
 * Versión imperativa para reemplazar `if (!confirm(...)) return;` sin
 * reestructurar el handler:
 *
 *   const [confirm, confirmDialog] = useConfirm();
 *   if (!(await confirm({ title, confirmLabel, variant: 'destructive' }))) return;
 *   ...
 *   return <>{confirmDialog}...</>;
 */
export function useConfirm(): [(options: ConfirmOptions) => Promise<boolean>, React.ReactNode] {
  const [options, setOptions] = React.useState<ConfirmOptions | null>(null);
  const [open, setOpen] = React.useState(false);
  const resolver = React.useRef<((value: boolean) => void) | null>(null);

  const confirm = React.useCallback((opts: ConfirmOptions) => {
    resolver.current?.(false);
    setOptions(opts);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const settle = (value: boolean) => {
    resolver.current?.(value);
    resolver.current = null;
  };

  const element = options ? (
    <ConfirmDialog
      {...options}
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) settle(false);
      }}
      onConfirm={() => settle(true)}
    />
  ) : null;

  return [confirm, element];
}
