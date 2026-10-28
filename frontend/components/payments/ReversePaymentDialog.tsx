import axios from 'axios';
import { useEffect, useState } from 'react';

import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { getApiErrorMessage } from '@/lib/api/client';
import { paymentsAPI, type ReverseAuthorizer } from '@/lib/api/loans';

interface ReversePaymentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  paymentId: string;
  customer?: string | null;
  amount?: number | string | null;
  /** Tras un reverso correcto (el diálogo ya se cierra solo). */
  onReversed: () => void | Promise<void>;
}

/** Primer mensaje de un campo de error de DRF (`{"code": ["..."]}`). */
function fieldMessage(data: unknown, field: string): string | null {
  if (!data || typeof data !== 'object') return null;
  const value = (data as Record<string, unknown>)[field];
  if (Array.isArray(value) && value.length) return String(value[0]);
  if (typeof value === 'string' && value) return value;
  return null;
}

/**
 * El cuerpo de error del reverso: `code` (intentos que quedan), `authorizer_id` o `detail`
 * (bloqueo 429, permiso). `getApiErrorMessage` ignora el campo `code`, por eso se leen aquí.
 */
function reverseErrorMessage(err: unknown): string {
  const data = (err as { response?: { data?: unknown } } | null)?.response?.data;
  const campo = fieldMessage(data, 'code') || fieldMessage(data, 'authorizer_id');
  if (campo) return campo;
  // `detail` (429, 403): getApiErrorMessage lo lee y traduce en un error de axios.
  if (!axios.isAxiosError(err) && fieldMessage(data, 'detail')) return fieldMessage(data, 'detail')!;
  return getApiErrorMessage(err, 'Error al revertir el pago');
}

/**
 * Diálogo mínimo para revertir un pago (Task 14): motivo, autorizador (dueño o administrador
 * con 2FA) y su código de 6 dígitos. El diseño final llega en F3.
 */
export function ReversePaymentDialog({
  open,
  onOpenChange,
  paymentId,
  customer,
  amount,
  onReversed,
}: ReversePaymentDialogProps) {
  const [reason, setReason] = useState('');
  const [authorizerId, setAuthorizerId] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [authorizers, setAuthorizers] = useState<ReverseAuthorizer[] | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setAuthorizers(null);
    paymentsAPI
      .getReverseAuthorizers()
      .then((list) => {
        if (!active) return;
        setAuthorizers(list);
        if (list.length === 1) setAuthorizerId(String(list[0].id));
      })
      .catch((err) => {
        if (!active) return;
        setAuthorizers([]);
        setError(getApiErrorMessage(err, 'No se pudieron cargar los autorizadores'));
      });
    return () => {
      active = false;
    };
  }, [open]);

  const reset = () => {
    setReason('');
    setAuthorizerId('');
    setCode('');
    setError('');
  };

  const handleConfirm = async () => {
    setError('');
    try {
      await paymentsAPI.reversePayment(paymentId, reason.trim(), Number(authorizerId), code);
    } catch (err) {
      setError(reverseErrorMessage(err));
      setCode('');
      return false; // el diálogo sigue abierto para reintentar
    }
    reset();
    await onReversed();
  };

  const ready = !!reason.trim() && !!authorizerId && /^\d{6}$/.test(code);
  const sinAutorizadores = authorizers !== null && authorizers.length === 0;

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) reset();
      }}
      title="¿Revertir este pago?"
      description="El pago se anulará y el balance del préstamo se recalculará. Lo autoriza el dueño o un administrador con su código de verificación."
      customer={customer}
      amount={amount}
      confirmLabel="Revertir pago"
      variant="destructive"
      confirmDisabled={!ready}
      onConfirm={handleConfirm}
    >
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="reverse-reason">
            Motivo del reverso <span className="font-normal text-fg-muted">(obligatorio)</span>
          </Label>
          <Textarea
            id="reverse-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Ej.: pago registrado en el préstamo equivocado"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="reverse-authorizer">Autoriza</Label>
          <NativeSelect
            id="reverse-authorizer"
            value={authorizerId}
            onChange={(e) => setAuthorizerId(e.target.value)}
            disabled={!authorizers || sinAutorizadores}
          >
            <option value="">
              {authorizers === null ? 'Cargando…' : 'Elige quién autoriza'}
            </option>
            {(authorizers || []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.full_name} · {a.role_label}
              </option>
            ))}
          </NativeSelect>
          {sinAutorizadores && !error && (
            <p className="text-sm text-fg-muted">
              Nadie puede autorizar todavía: el dueño o un administrador debe activar la verificación en dos pasos.
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="reverse-code">Código de verificación del autorizador</Label>
          <Input
            id="reverse-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            className="font-mono tracking-widest"
            aria-describedby={error ? 'reverse-error' : undefined}
          />
        </div>

        {error && (
          <p id="reverse-error" role="alert" className="text-sm text-danger-fg">
            {error}
          </p>
        )}
      </div>
    </ConfirmDialog>
  );
}
