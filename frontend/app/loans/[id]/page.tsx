'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI } from '@/lib/api/loans';
import { Loan } from '@/types';
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
  User,
  DollarSign,
  Calendar,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  AlertCircle,
  CreditCard,
  Receipt,
  Shield,
  Edit,
  Trash2,
} from 'lucide-react';

export default function LoanDetailPage() {
  const router = useRouter();
  const params = useParams();
  const loanId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [loan, setLoan] = useState<Loan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load loan details
  useEffect(() => {
    if (isAuthenticated && loanId) {
      loadLoanDetails();
    }
  }, [isAuthenticated, loanId]);

  const loadLoanDetails = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await loansAPI.getLoan(loanId);
      setLoan(data);
    } catch (err: any) {
      console.error('Error loading loan:', err);
      setError('Error al cargar los detalles del préstamo');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApproveLoan = async () => {
    if (!loan) return;
    try {
      setIsProcessing(true);
      await loansAPI.approveLoan(loan.id);
      await loadLoanDetails();
    } catch (err) {
      console.error('Error approving loan:', err);
      setError('Error al aprobar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDisburseLoan = async () => {
    if (!loan) return;
    try {
      setIsProcessing(true);
      await loansAPI.disburseLoan(loan.id);
      await loadLoanDetails();
    } catch (err) {
      console.error('Error disbursing loan:', err);
      setError('Error al desembolsar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectLoan = async () => {
    if (!loan || !confirm('¿Estás seguro de rechazar este préstamo?')) return;
    try {
      setIsProcessing(true);
      await loansAPI.rejectLoan(loan.id);
      await loadLoanDetails();
    } catch (err) {
      console.error('Error rejecting loan:', err);
      setError('Error al rechazar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) => {
    if (amount === undefined || amount === null) return '$0.00';
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numAmount)) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
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
    const statusConfig: Record<string, { label: string; className: string; icon: any }> = {
      draft: { label: 'Borrador', className: 'bg-gray-100 text-gray-700', icon: FileText },
      pending: { label: 'Pendiente', className: 'bg-yellow-100 text-yellow-700', icon: Clock },
      approved: { label: 'Aprobado', className: 'bg-blue-100 text-blue-700', icon: CheckCircle },
      active: { label: 'Activo', className: 'bg-green-100 text-green-700', icon: TrendingUp },
      paid: { label: 'Pagado', className: 'bg-gray-100 text-gray-700', icon: CheckCircle },
      defaulted: { label: 'Moroso', className: 'bg-red-100 text-red-700', icon: AlertCircle },
      written_off: { label: 'Cancelado', className: 'bg-gray-100 text-gray-700', icon: XCircle },
      rejected: { label: 'Rechazado', className: 'bg-red-100 text-red-700', icon: XCircle },
    };

    const config = statusConfig[status] || statusConfig.draft;
    const Icon = config.icon;

    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${config.className}`}>
        <Icon className="h-4 w-4" />
        {config.label}
      </div>
    );
  };

  const getLoanTypeLabel = (type: string) => {
    const types: Record<string, string> = {
      personal: 'Personal',
      auto: 'Automóvil',
      mortgage: 'Hipotecario',
      business: 'Empresarial',
      student: 'Estudiantil',
      payday: 'Día de Pago',
    };
    return types[type] || type;
  };

  const getPaymentFrequencyLabel = (frequency: string) => {
    const frequencies: Record<string, string> = {
      daily: 'Diario',
      weekly: 'Semanal',
      biweekly: 'Quincenal',
      monthly: 'Mensual',
      quarterly: 'Trimestral',
    };
    return frequencies[frequency] || frequency;
  };

  // Show loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!loan) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
        <div className="container mx-auto max-w-7xl">
          <Alert variant="destructive">
            <AlertDescription>No se encontró el préstamo</AlertDescription>
          </Alert>
          <div className="mt-4">
            <Link href="/loans">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver a Préstamos
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/loans">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <h1 className="text-3xl font-bold text-gray-900">
                {loan.loan_number}
              </h1>
              {getStatusBadge(loan.status)}
            </div>
            <p className="text-gray-600 ml-12">
              {getLoanTypeLabel(loan.loan_type)} - {loan.customer_name}
            </p>
          </div>
          <div className="flex gap-2">
            {loan.status === 'pending' && (
              <>
                <Button
                  variant="outline"
                  onClick={handleRejectLoan}
                  disabled={isProcessing}
                >
                  {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}
                  Rechazar
                </Button>
                <Button
                  onClick={handleApproveLoan}
                  disabled={isProcessing}
                >
                  {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                  Aprobar
                </Button>
              </>
            )}
            {loan.status === 'approved' && (
              <Button
                onClick={handleDisburseLoan}
                disabled={isProcessing}
              >
                {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <DollarSign className="mr-2 h-4 w-4" />}
                Desembolsar
              </Button>
            )}
            {!['paid', 'rejected', 'written_off', 'draft', 'pending'].includes(loan.status) && (
              <Link href={`/payments/new?loan=${loan.id}`}>
                <Button>
                  <Receipt className="mr-2 h-4 w-4" />
                  Registrar Pago
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Monto Principal</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {formatCurrency(loan.principal_amount)}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Balance Pendiente</p>
                  <p className="text-2xl font-bold text-orange-600">
                    {formatCurrency(loan.outstanding_balance)}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Pagado</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(loan.total_paid)}
                  </p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Pago Mensual</p>
                  <p className="text-2xl font-bold">
                    {formatCurrency(loan.payment_amount)}
                  </p>
                </div>
                <Calendar className="h-8 w-8 text-gray-600" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Loan Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-600" />
                  Detalles del Préstamo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Tipo de Préstamo</p>
                    <p className="font-medium">{getLoanTypeLabel(loan.loan_type)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Tasa de Interés</p>
                    <p className="font-medium">{loan.interest_rate}% anual</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Plazo</p>
                    <p className="font-medium">{loan.term_months} meses</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Frecuencia de Pago</p>
                    <p className="font-medium">{getPaymentFrequencyLabel(loan.payment_frequency)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Fecha de Solicitud</p>
                    <p className="font-medium">{formatDate(loan.application_date)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Fecha de Desembolso</p>
                    <p className="font-medium">{formatDate(loan.disbursement_date)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Primer Pago</p>
                    <p className="font-medium">{formatDate(loan.first_payment_date)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Fecha de Vencimiento</p>
                    <p className="font-medium">{formatDate(loan.maturity_date)}</p>
                  </div>
                </div>

                {loan.purpose && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm text-gray-600 mb-1">Propósito</p>
                    <p className="font-medium">{loan.purpose}</p>
                  </div>
                )}

                {loan.notes && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-sm text-gray-600 mb-1">Notas</p>
                    <p className="text-sm">{loan.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Payment Schedule */}
            {loan.payment_schedules && loan.payment_schedules.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-blue-600" />
                    Cronograma de Pagos
                  </CardTitle>
                  <CardDescription>
                    {loan.payment_schedules.length} cuotas programadas
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {loan.payment_schedules.map((schedule) => (
                      <div
                        key={schedule.id}
                        className={`flex items-center justify-between p-3 rounded-lg border ${
                          schedule.status === 'paid'
                            ? 'bg-green-50 border-green-200'
                            : schedule.status === 'overdue'
                            ? 'bg-red-50 border-red-200'
                            : 'bg-white border-gray-200'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="text-center">
                            <p className="text-xs text-gray-600">Cuota</p>
                            <p className="font-bold text-lg">#{schedule.installment_number}</p>
                          </div>
                          <div>
                            <p className="font-medium">{formatDate(schedule.due_date)}</p>
                            <p className="text-sm text-gray-600">
                              {schedule.status === 'paid' ? 'Pagada' :
                               schedule.status === 'overdue' ? 'Vencida' :
                               schedule.status === 'partial' ? 'Parcial' : 'Pendiente'}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-bold">{formatCurrency(schedule.total_amount)}</p>
                          {schedule.status !== 'paid' && schedule.balance > 0 && (
                            <p className="text-sm text-orange-600">
                              Saldo: {formatCurrency(schedule.balance)}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Recent Payments */}
            {loan.recent_payments && loan.recent_payments.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Receipt className="h-5 w-5 text-blue-600" />
                    Pagos Recientes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {loan.recent_payments.map((payment) => (
                      <div
                        key={payment.id}
                        className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                        onClick={() => router.push(`/payments/${payment.id}`)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <p className="font-medium text-blue-600 hover:underline">{payment.payment_number}</p>
                            <p className="text-sm text-gray-600">
                              {formatDate(payment.payment_date)} - {payment.payment_method}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-green-600">
                              {formatCurrency(payment.amount)}
                            </p>
                            <p className="text-xs text-gray-600 capitalize">
                              {payment.status}
                            </p>
                          </div>
                        </div>

                        {/* Payment Breakdown */}
                        <div className="flex gap-3 text-xs pt-2 border-t border-gray-200">
                          <div className="flex items-center gap-1">
                            <span className="text-gray-600">Principal:</span>
                            <span className="font-semibold text-gray-900">
                              {formatCurrency(payment.principal_paid || 0)}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-gray-600">Interés:</span>
                            <span className="font-semibold text-gray-900">
                              {formatCurrency(payment.interest_paid || 0)}
                            </span>
                          </div>
                          {payment.late_fee_paid > 0 && (
                            <div className="flex items-center gap-1">
                              <span className="text-gray-600">Mora:</span>
                              <span className="font-semibold text-orange-600">
                                {formatCurrency(payment.late_fee_paid)}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    {/* View All Payments Button */}
                    <Link href={`/payments?loan=${loan.id}`}>
                      <Button variant="outline" className="w-full mt-2" size="sm">
                        <Receipt className="mr-2 h-4 w-4" />
                        Ver Todos los Pagos
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Customer & Additional Info */}
          <div className="space-y-6">
            {/* Customer Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-blue-600" />
                  Cliente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-gray-600">Nombre</p>
                    <p className="font-medium">{loan.customer_name}</p>
                  </div>
                  <Link href={`/customers/${loan.customer}`}>
                    <Button variant="outline" className="w-full" size="sm">
                      Ver Perfil del Cliente
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Financial Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-blue-600" />
                  Resumen Financiero
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Monto Total</span>
                    <span className="font-medium">{formatCurrency(loan.total_amount)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Interés Total</span>
                    <span className="font-medium">{formatCurrency(loan.total_interest_paid)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Cargos por Mora</span>
                    <span className="font-medium text-red-600">{formatCurrency(loan.late_fees)}</span>
                  </div>
                  <div className="pt-3 border-t flex justify-between">
                    <span className="font-medium">Balance Pendiente</span>
                    <span className="font-bold text-orange-600">
                      {formatCurrency(loan.outstanding_balance)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Collaterals */}
            {loan.collaterals && loan.collaterals.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-600" />
                    Garantías
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {loan.collaterals.map((collateral) => (
                      <div key={collateral.id} className="p-3 bg-gray-50 rounded-lg">
                        <p className="font-medium capitalize">{collateral.collateral_type}</p>
                        <p className="text-sm text-gray-600">{collateral.description}</p>
                        <p className="text-sm font-medium mt-1">
                          Valor: {formatCurrency(collateral.estimated_value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Officer Info */}
            {loan.loan_officer_name && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="h-5 w-5 text-blue-600" />
                    Oficial de Crédito
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium">{loan.loan_officer_name}</p>
                </CardContent>
              </Card>
            )}

            {/* Overdue Warning */}
            {loan.is_overdue && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Este préstamo tiene pagos vencidos. Por favor, contacte al cliente.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
