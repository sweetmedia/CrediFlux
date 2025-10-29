'use client';

import { useState } from 'react';
import { Loan } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';

interface LoanApprovalDialogProps {
  loan: Loan | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApprove: (notes?: string) => Promise<void>;
  onReject: (notes: string) => Promise<void>;
}

export default function LoanApprovalDialog({
  loan,
  open,
  onOpenChange,
  onApprove,
  onReject,
}: LoanApprovalDialogProps) {
  const [action, setAction] = useState<'approve' | 'reject' | null>(null);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');

  const handleSubmit = async () => {
    if (action === 'reject' && !notes.trim()) {
      setError('Se requiere una nota para rechazar el préstamo');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');

      if (action === 'approve') {
        await onApprove(notes || undefined);
      } else if (action === 'reject') {
        await onReject(notes);
      }

      // Reset form
      setNotes('');
      setAction(null);
      onOpenChange(false);
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Ocurrió un error');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!loan) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {action === 'approve' ? 'Aprobar Préstamo' : action === 'reject' ? 'Rechazar Préstamo' : 'Gestionar Préstamo'}
          </DialogTitle>
          <DialogDescription>
            {loan.loan_number} - {loan.customer_name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Loan Information */}
          <div className="bg-gray-50 p-4 rounded-md space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Monto:</span>
              <span className="text-sm font-semibold">${loan.principal_amount.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Tipo:</span>
              <span className="text-sm capitalize">{loan.loan_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Plazo:</span>
              <span className="text-sm">{loan.term_months} meses</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Tasa:</span>
              <span className="text-sm">{loan.interest_rate}% anual</span>
            </div>
          </div>

          {!action && (
            <div className="flex gap-3">
              <Button
                className="flex-1"
                variant="default"
                onClick={() => setAction('approve')}
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Aprobar
              </Button>
              <Button
                className="flex-1"
                variant="destructive"
                onClick={() => setAction('reject')}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Rechazar
              </Button>
            </div>
          )}

          {action && (
            <>
              <div className="space-y-2">
                <Label htmlFor="notes">
                  {action === 'approve' ? 'Notas (Opcional)' : 'Motivo del Rechazo *'}
                </Label>
                <Textarea
                  id="notes"
                  placeholder={
                    action === 'approve'
                      ? 'Agregue notas sobre la aprobación...'
                      : 'Explique el motivo del rechazo...'
                  }
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  disabled={isSubmitting}
                />
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </>
          )}
        </div>

        {action && (
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setAction(null);
                setNotes('');
                setError('');
              }}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              variant={action === 'approve' ? 'default' : 'destructive'}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  {action === 'approve' ? 'Aprobar Préstamo' : 'Rechazar Préstamo'}
                </>
              )}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
