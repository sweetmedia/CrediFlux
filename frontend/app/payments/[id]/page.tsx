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
  Calendar,
  CreditCard,
  FileText,
  User,
  AlertCircle,
  CheckCircle,
  XCircle,
  RotateCcw,
  Printer,
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

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '$0.00';
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numAmount)) return '$0.00';
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(numAmount);
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
      bank_transfer: 'Transferencia Bancaria',
      card: 'Tarjeta',
      mobile_payment: 'Pago Móvil',
    };
    return methods[method] || method;
  };

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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8 print:bg-white">
      <div className="container mx-auto max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between print:hidden">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <Receipt className="h-8 w-8 text-blue-600" />
              Detalle del Pago
            </h1>
            <p className="text-gray-600 mt-1">
              Información completa del pago {payment.payment_number}
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/loans">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver
              </Button>
            </Link>
            <Button variant="outline" onClick={handlePrintReceipt}>
              <Printer className="mr-2 h-4 w-4" />
              Imprimir
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6 print:hidden">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Payment Header Card */}
        <Card className="mb-6">
          <CardHeader className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <CardTitle className="text-2xl mb-2">
                  {payment.payment_number}
                </CardTitle>
                <CardDescription className="text-blue-100">
                  {formatDate(payment.payment_date)}
                </CardDescription>
              </div>
              <div className="text-right">
                {getStatusBadge(payment.status)}
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6">
            {/* Amount Display */}
            <div className="text-center mb-6">
              <p className="text-sm text-gray-600 mb-2">Monto Total</p>
              <p className="text-5xl font-bold text-blue-600">
                {formatCurrency(payment.amount)}
              </p>
            </div>

            {/* Payment Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-6 border-t">
              <div className="flex items-center gap-3">
                <CreditCard className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-600">Método de Pago</p>
                  <p className="font-semibold">{getPaymentMethodLabel(payment.payment_method)}</p>
                </div>
              </div>

              {payment.reference_number && (
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-xs text-gray-600">Número de Referencia</p>
                    <p className="font-semibold">{payment.reference_number}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <User className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-600">Cliente</p>
                  <p className="font-semibold">{payment.customer_name}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-xs text-gray-600">Préstamo</p>
                  <Link href={`/loans/${payment.loan}`}>
                    <p className="font-semibold text-blue-600 hover:underline cursor-pointer">
                      {payment.loan_number}
                    </p>
                  </Link>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Payment Breakdown */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Desglose del Pago
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center pb-3 border-b">
                <span className="text-gray-600">Capital Pagado</span>
                <span className="font-semibold text-lg">
                  {formatCurrency(payment.principal_paid)}
                </span>
              </div>

              <div className="flex justify-between items-center pb-3 border-b">
                <span className="text-gray-600">Interés Pagado</span>
                <span className="font-semibold text-lg">
                  {formatCurrency(payment.interest_paid)}
                </span>
              </div>

              <div className="flex justify-between items-center pb-3 border-b">
                <div>
                  <span className="text-gray-600">Mora Pagada</span>
                  {payment.late_fee_paid > 0 ? (
                    <p className="text-xs text-green-600 mt-1">
                      ✓ Cargos por atraso cubiertos en este pago
                    </p>
                  ) : (
                    <p className="text-xs text-gray-500 mt-1">
                      No se aplicó a mora en este pago
                    </p>
                  )}
                </div>
                <span className={`font-semibold text-lg ${payment.late_fee_paid > 0 ? 'text-orange-600' : 'text-gray-400'}`}>
                  {formatCurrency(payment.late_fee_paid || 0)}
                </span>
              </div>

              <div className="flex justify-between items-center pt-3 bg-blue-50 p-4 rounded-lg">
                <span className="font-semibold text-gray-900">Total</span>
                <span className="font-bold text-2xl text-blue-600">
                  {formatCurrency(payment.amount)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notes */}
        {payment.notes && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Notas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 whitespace-pre-wrap">{payment.notes}</p>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        {payment.status === 'completed' && (
          <Card className="print:hidden">
            <CardHeader>
              <CardTitle>Acciones</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                <Link href={`/loans/${payment.loan}`}>
                  <Button variant="outline">
                    <FileText className="mr-2 h-4 w-4" />
                    Ver Préstamo
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
                      Revertir Pago
                    </>
                  )}
                </Button>
              </div>

              <Alert className="mt-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Advertencia:</strong> Revertir un pago actualizará los balances del
                  préstamo y no se puede deshacer. Use esta función con precaución.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}

        {/* Print Footer */}
        <div className="hidden print:block mt-8 pt-8 border-t text-center text-sm text-gray-600">
          <p>Impreso el {new Date().toLocaleDateString('es-ES')}</p>
          <p className="mt-2">CrediFlux - Sistema de Gestión de Préstamos</p>
        </div>
      </div>
    </div>
  );
}
