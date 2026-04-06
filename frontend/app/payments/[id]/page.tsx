'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { paymentsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ArrowLeft,
  Receipt,
  DollarSign,
  CreditCard,
  FileText,
  User,
  AlertCircle,
  CheckCircle,
  XCircle,
  RotateCcw,
  Printer,
  Download,
  Landmark,
  Wallet,
  BadgeDollarSign,
  CircleDollarSign,
} from 'lucide-react';

export default function PaymentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const paymentId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [payment, setPayment] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load payment details
  useEffect(() => {
    if (isAuthenticated && paymentId) {
      loadPayment();
    }
  }, [isAuthenticated, paymentId]);

  const loadPayment = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await paymentsAPI.getPayment(paymentId);
      setPayment(data);
    } catch (err: any) {
      console.error('Error loading payment:', err);
      setError('Error al cargar el pago');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReversePayment = async () => {
    if (!confirm('¿Estás seguro de que deseas revertir este pago? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      setIsProcessing(true);
      setError('');
      await paymentsAPI.reversePayment(paymentId);
      await loadPayment(); // Reload payment details
    } catch (err: any) {
      console.error('Error reversing payment:', err);
      setError(err.response?.data?.error || 'Error al revertir el pago');
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePrintReceipt = () => {
    window.print();
  };

  const handleDownloadReceipt = () => {
    // Open the receipt PDF in a new tab for download
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || '';
    window.open(`${baseUrl}/api/loans/payments/${paymentId}/receipt-pdf/`, '_blank');
  };

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return `${config.currency_symbol}0.00`;
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numAmount)) return `${config.currency_symbol}0.00`;
    return `${config.currency_symbol}${numAmount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      completed: {
        label: 'Completado',
        icon: CheckCircle,
        className: 'bg-green-100 text-green-800 border-green-200',
      },
      pending: {
        label: 'Pendiente',
        icon: AlertCircle,
        className: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      },
      failed: {
        label: 'Fallido',
        icon: XCircle,
        className: 'bg-red-100 text-red-800 border-red-200',
      },
      reversed: {
        label: 'Revertido',
        icon: RotateCcw,
        className: 'bg-gray-100 text-gray-800 border-gray-200',
      },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border ${config.className}`}>
        <Icon className="h-4 w-4" />
        <span className="font-semibold">{config.label}</span>
      </div>
    );
  };

  const getPaymentMethodLabel = (method: string) => {
    const methods: Record<string, string> = {
      cash: 'Efectivo',
      check: 'Cheque',
      bank_transfer: 'Transferencia bancaria',
      card: 'Tarjeta',
      mobile_payment: 'Pago móvil',
    };
    return methods[method] || method;
  };

  const getLoanStatusLabel = (status: string | undefined) => {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      approved: 'Aprobado',
      active: 'Activo',
      paid: 'Pagado',
      defaulted: 'En mora',
      written_off: 'Castigado',
      rejected: 'Rechazado',
    };
    return labels[status || ''] || 'Activo';
  };

  const getLoanStatusClassName = (status: string | undefined) => {
    const styles: Record<string, string> = {
      pending: 'bg-amber-50 text-amber-700 border-amber-200',
      approved: 'bg-sky-50 text-sky-700 border-sky-200',
      active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      paid: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      defaulted: 'bg-orange-50 text-orange-700 border-orange-200',
      written_off: 'bg-rose-50 text-rose-700 border-rose-200',
      rejected: 'bg-zinc-100 text-zinc-700 border-zinc-200',
    };
    return styles[status || ''] || styles.active;
  };

  const principalPaid = Number(payment?.principal_paid || 0);
  const interestPaid = Number(payment?.interest_paid || 0);
  const lateFeePaid = Number(payment?.late_fee_paid || 0);
  const loanOutstandingBalance = Number(payment?.loan_outstanding_balance || 0);
  const loanPrincipalAmount = Number(payment?.loan_principal_amount || 0);

  const paymentExplanation =
    interestPaid > 0 || lateFeePaid > 0
      ? 'Este pago no se aplicó 100% al capital. Primero se cubren interés y mora; el resto reduce el principal del préstamo.'
      : 'Este pago se aplicó completamente al principal del préstamo.';

  // Show loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !payment) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
        <div className="container mx-auto max-w-4xl">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <div className="mt-4">
            <Link href="/payments">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver a Pagos
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!payment) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 print:bg-white md:p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between print:hidden">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
              <Receipt className="h-3.5 w-3.5" />
              Recibo de pago
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">
              Detalle del pago
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Revisa cómo se distribuyó este pago entre capital, interés y mora, y qué impacto tuvo sobre el préstamo.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link href="/payments">
              <Button variant="outline" className="bg-white">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver a pagos
              </Button>
            </Link>
            <Button variant="outline" onClick={handleDownloadReceipt} className="bg-white">
              <Download className="mr-2 h-4 w-4" />
              Descargar PDF
            </Button>
            <Button variant="outline" onClick={handlePrintReceipt} className="bg-white">
              <Printer className="mr-2 h-4 w-4" />
              Imprimir
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="print:hidden">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Card className="overflow-hidden border-[#d7e2db] shadow-sm">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#264f06] to-[#3c6a12] px-6 py-5 text-white">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-sm font-medium text-white/75">Pago registrado</p>
                  <h2 className="mt-1 text-2xl font-semibold">{payment.payment_number}</h2>
                  <p className="mt-2 text-sm text-white/75">Fecha de pago: {formatDate(payment.payment_date)}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  {getStatusBadge(payment.status)}
                  <div className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium ${getLoanStatusClassName(payment.loan_status)}`}>
                    Préstamo {getLoanStatusLabel(payment.loan_status)}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 border-b border-[#d7e2db] bg-white px-6 py-6 md:grid-cols-3">
              <div className="rounded-2xl border border-[#d7e2db] bg-[#fbfcfb] p-5">
                <p className="text-sm text-slate-500">Monto recibido</p>
                <p className="mt-2 text-3xl font-semibold text-[#163300]">{formatCurrency(payment.amount)}</p>
                <p className="mt-2 text-xs text-slate-500">Monto total registrado en el recibo.</p>
              </div>
              <div className="rounded-2xl border border-[#d7e2db] bg-[#fbfcfb] p-5">
                <p className="text-sm text-slate-500">Aplicado a capital</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900">{formatCurrency(payment.principal_paid)}</p>
                <p className="mt-2 text-xs text-slate-500">Esto es lo que realmente reduce el balance del préstamo.</p>
              </div>
              <div className="rounded-2xl border border-[#d7e2db] bg-[#fbfcfb] p-5">
                <p className="text-sm text-slate-500">Balance pendiente del préstamo</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900">{formatCurrency(payment.loan_outstanding_balance)}</p>
                <p className="mt-2 text-xs text-slate-500">Balance restante después de aplicar este pago.</p>
              </div>
            </div>

            <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="space-y-6">
                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center gap-2 text-[#163300]">
                      <BadgeDollarSign className="h-5 w-5" />
                      Desglose del pago
                    </CardTitle>
                    <CardDescription>
                      Prioridad de aplicación: mora → interés → capital.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between rounded-xl border border-[#edf1ee] px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-900">Capital pagado</p>
                        <p className="text-xs text-slate-500">Reduce el balance del préstamo</p>
                      </div>
                      <p className="text-lg font-semibold text-slate-900">{formatCurrency(payment.principal_paid)}</p>
                    </div>

                    <div className="flex items-center justify-between rounded-xl border border-[#edf1ee] px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-900">Interés pagado</p>
                        <p className="text-xs text-slate-500">Parte financiera del pago</p>
                      </div>
                      <p className="text-lg font-semibold text-slate-900">{formatCurrency(payment.interest_paid)}</p>
                    </div>

                    <div className="flex items-center justify-between rounded-xl border border-[#edf1ee] px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-900">Mora pagada</p>
                        <p className="text-xs text-slate-500">
                          {lateFeePaid > 0 ? 'Se cubrieron cargos por atraso en este pago.' : 'No se aplicó monto a mora en este pago.'}
                        </p>
                      </div>
                      <p className={`text-lg font-semibold ${lateFeePaid > 0 ? 'text-[#FF7503]' : 'text-slate-400'}`}>
                        {formatCurrency(payment.late_fee_paid || 0)}
                      </p>
                    </div>

                    <div className="rounded-2xl border border-[#d9e6dc] bg-[#f7faf8] p-4">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="mt-0.5 h-4 w-4 text-[#738566]" />
                        <div>
                          <p className="font-medium text-slate-900">Cómo interpretar este pago</p>
                          <p className="mt-1 text-sm leading-6 text-slate-600">{paymentExplanation}</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {payment.notes && (
                  <Card className="border-[#d7e2db] shadow-none">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-[#163300]">
                        <FileText className="h-5 w-5" />
                        Notas del pago
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{payment.notes}</p>
                    </CardContent>
                  </Card>
                )}
              </div>

              <div className="space-y-6">
                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center gap-2 text-[#163300]">
                      <Landmark className="h-5 w-5" />
                      Impacto sobre el préstamo
                    </CardTitle>
                    <CardDescription>
                      Resumen para entender por qué el préstamo sigue activo o quedó pagado.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-xl border border-[#edf1ee] px-4 py-3">
                      <p className="text-xs uppercase tracking-wide text-slate-500">Préstamo</p>
                      <Link href={`/loans/${payment.loan}`} className="mt-1 inline-block text-base font-semibold text-[#163300] hover:underline">
                        {payment.loan_number}
                      </Link>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="rounded-xl border border-[#edf1ee] px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Cliente</p>
                        <p className="mt-1 font-medium text-slate-900">{payment.customer_name}</p>
                      </div>
                      <div className="rounded-xl border border-[#edf1ee] px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Método</p>
                        <p className="mt-1 font-medium text-slate-900">{getPaymentMethodLabel(payment.payment_method)}</p>
                      </div>
                    </div>

                    {payment.reference_number && (
                      <div className="rounded-xl border border-[#edf1ee] px-4 py-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Referencia</p>
                        <p className="mt-1 font-medium text-slate-900">{payment.reference_number}</p>
                      </div>
                    )}

                    <div className="space-y-3 rounded-2xl border border-[#d9e6dc] bg-[#f7faf8] p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <Wallet className="h-4 w-4 text-[#738566]" />
                          Principal original
                        </div>
                        <span className="font-semibold text-slate-900">{formatCurrency(loanPrincipalAmount)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                          <CircleDollarSign className="h-4 w-4 text-[#738566]" />
                          Capital aplicado en este pago
                        </div>
                        <span className="font-semibold text-slate-900">{formatCurrency(principalPaid)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 border-t border-[#d9e6dc] pt-3">
                        <div className="text-sm font-medium text-slate-700">Balance restante</div>
                        <span className={`text-lg font-semibold ${loanOutstandingBalance <= 0 ? 'text-emerald-700' : 'text-slate-900'}`}>
                          {formatCurrency(payment.loan_outstanding_balance)}
                        </span>
                      </div>
                    </div>

                    <Alert className="border-[#e7efe9] bg-[#fbfcfb]">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        {loanOutstandingBalance <= 0
                          ? 'Este pago dejó el préstamo sin balance pendiente. Debe reflejarse como pagado.'
                          : 'El préstamo todavía tiene balance pendiente. Aunque el pago sea grande, solo la parte aplicada a capital reduce el saldo.'}
                      </AlertDescription>
                    </Alert>
                  </CardContent>
                </Card>

                {payment.status === 'completed' && (
                  <Card className="border-[#d7e2db] shadow-none print:hidden">
                    <CardHeader>
                      <CardTitle className="text-[#163300]">Acciones</CardTitle>
                      <CardDescription>
                        Herramientas rápidas para revisar o corregir este pago.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex flex-wrap gap-3">
                        <Link href={`/loans/${payment.loan}`}>
                          <Button variant="outline" className="bg-white">
                            <FileText className="mr-2 h-4 w-4" />
                            Ver préstamo
                          </Button>
                        </Link>

                        <Button
                          variant="destructive"
                          onClick={handleReversePayment}
                          disabled={isProcessing}
                        >
                          {isProcessing ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Procesando...
                            </>
                          ) : (
                            <>
                              <RotateCcw className="mr-2 h-4 w-4" />
                              Revertir pago
                            </>
                          )}
                        </Button>
                      </div>

                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <strong>Advertencia:</strong> revertir un pago actualizará los balances del préstamo y no se puede deshacer.
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="hidden border-t pt-8 text-center text-sm text-gray-600 print:block">
          <p>Impreso el {new Date().toLocaleDateString('es-ES')}</p>
          <p className="mt-2">CrediFlux - Sistema de Gestión de Préstamos</p>
        </div>
      </div>
    </div>
  );
}
