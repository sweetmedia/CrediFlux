'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
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
  Download,
  Landmark,
  BadgeDollarSign,
  CircleDollarSign,
  FileSignature,
  Phone,
  MessageCircle,
  Mail,
} from 'lucide-react';

export default function LoanDetailPage() {
  const router = useRouter();
  const params = useParams();
  const loanId = params.id as string;
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { config } = useConfig();
  const [loan, setLoan] = useState<Loan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  // Check if user can approve/reject loans (admin, manager, loan_officer, or tenant owner)
  const canManageLoans = user && (
    user.role === 'admin' ||
    user.role === 'manager' ||
    user.role === 'loan_officer' ||
    user.is_tenant_owner ||
    user.is_superuser
  );

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

    if (!confirm('¿Estás seguro de aprobar este préstamo?')) {
      return;
    }

    try {
      setIsProcessing(true);
      setError('');
      await loansAPI.approveLoan(loan.id);
      await loadLoanDetails();
    } catch (err: any) {
      console.error('Error approving loan:', err);
      setError(err.response?.data?.error || 'Error al aprobar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDisburseLoan = async () => {
    if (!loan) return;

    if (!confirm('¿Estás seguro de desembolsar este préstamo? Esta acción marcará el préstamo como activo.')) {
      return;
    }

    try {
      setIsProcessing(true);
      setError('');
      await loansAPI.disburseLoan(loan.id);
      await loadLoanDetails();
    } catch (err: any) {
      console.error('Error disbursing loan:', err);
      setError(err.response?.data?.error || 'Error al desembolsar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectLoan = async () => {
    if (!loan) return;

    // Ask for rejection reason
    const rejectionNotes = prompt('Por favor, ingresa el motivo del rechazo:');

    if (!rejectionNotes || rejectionNotes.trim() === '') {
      setError('Se requiere especificar el motivo del rechazo');
      return;
    }

    if (!confirm(`¿Estás seguro de rechazar este préstamo?\n\nMotivo: ${rejectionNotes}`)) {
      return;
    }

    try {
      setIsProcessing(true);
      setError('');
      await loansAPI.rejectLoan(loan.id, rejectionNotes);
      await loadLoanDetails();
    } catch (err: any) {
      console.error('Error rejecting loan:', err);
      setError(err.response?.data?.error || 'Error al rechazar el préstamo');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadBalanceReport = async () => {
    if (!loan) return;

    try {
      setIsProcessing(true);
      setError('');
      await loansAPI.downloadBalanceReport(loan.id);
    } catch (err: any) {
      console.error('Error downloading report:', err);
      setError('Error al descargar el reporte');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) => {
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
    const statusConfig: Record<string, { label: string; className: string; icon: any }> = {
      pending: { label: 'Pendiente', className: 'bg-yellow-100 text-yellow-700', icon: Clock },
      approved: { label: 'Aprobado', className: 'bg-blue-100 text-blue-700', icon: CheckCircle },
      active: { label: 'Activo', className: 'bg-green-100 text-green-700', icon: TrendingUp },
      paid: { label: 'Pagado', className: 'bg-gray-100 text-gray-700', icon: CheckCircle },
      defaulted: { label: 'Moroso', className: 'bg-red-100 text-red-700', icon: AlertCircle },
      written_off: { label: 'Cancelado', className: 'bg-gray-100 text-gray-700', icon: XCircle },
      rejected: { label: 'Rechazado', className: 'bg-red-100 text-red-700', icon: XCircle },
    };

    const config = statusConfig[status] || statusConfig.pending;
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

  const paidInstallments = loan.payment_schedules?.filter((s) => s.status === 'paid').length || 0;
  const totalInstallments = loan.payment_schedules?.length || 0;
  const progressPct = totalInstallments > 0 ? Math.round((paidInstallments / totalInstallments) * 100) : 0;

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <Link href="/loans">
                <Button variant="outline" size="sm" className="bg-white">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Landmark className="h-3.5 w-3.5" />
                Expediente del préstamo
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">{loan.loan_number}</h1>
            <p className="mt-2 text-sm text-slate-600">
              {getLoanTypeLabel(loan.loan_type)} • {loan.customer_name}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {loan.contract_id && (
              <Link href={`/contracts/${loan.contract_id}`}>
                <Button variant="outline" className="bg-white">
                  <FileSignature className="mr-2 h-4 w-4" />
                  Ver contrato
                </Button>
              </Link>
            )}
            {!['paid', 'rejected', 'written_off', 'pending'].includes(loan.status) && (
              <Link href={`/payments/new?loan=${loan.id}`}>
                <Button className="bg-[#163300] hover:bg-[#0f2400]">
                  <Receipt className="mr-2 h-4 w-4" />
                  Registrar pago
                </Button>
              </Link>
            )}
            {['active', 'paid'].includes(loan.status) && (
              <Button variant="outline" onClick={handleDownloadBalanceReport} disabled={isProcessing} className="bg-white">
                {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                Balance de cuotas
              </Button>
            )}
            {loan.status === 'pending' && canManageLoans && (
              <>
                <Button variant="outline" onClick={handleRejectLoan} disabled={isProcessing} className="border-red-300 bg-white text-red-700 hover:bg-red-50">
                  {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <XCircle className="mr-2 h-4 w-4" />}
                  Rechazar
                </Button>
                <Button onClick={handleApproveLoan} disabled={isProcessing} className="bg-emerald-600 hover:bg-emerald-700">
                  {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
                  Aprobar
                </Button>
              </>
            )}
            {loan.status === 'approved' && canManageLoans && (
              <Button
                onClick={handleDisburseLoan}
                disabled={isProcessing || (loan.contract_id ? !loan.contract_is_signed : true)}
                className="bg-blue-600 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                title={loan.contract_is_signed ? 'Desembolsar préstamo' : 'El contrato debe estar firmado antes de desembolsar'}
              >
                {isProcessing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <DollarSign className="mr-2 h-4 w-4" />}
                {loan.contract_is_signed ? 'Desembolsar' : 'Esperando firma'}
              </Button>
            )}
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loan.contract_id && loan.status === 'approved' && !loan.contract_is_signed && (
          <Alert className="border-amber-200 bg-amber-50 text-amber-900">
            <AlertDescription>
              Este préstamo tiene contrato generado, pero no se puede desembolsar hasta que el cliente lo firme.
            </AlertDescription>
          </Alert>
        )}

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <div className="mb-3">{getStatusBadge(loan.status)}</div>
                  <p className="text-sm text-white/70">Relación crediticia</p>
                  <h2 className="mt-1 text-3xl font-semibold">{formatCurrency(loan.principal_amount)}</h2>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm text-white/80">
                    <span>{loan.interest_rate}% mensual</span>
                    <span>•</span>
                    <span>{loan.term_months} meses</span>
                    <span>•</span>
                    <span>{getPaymentFrequencyLabel(loan.payment_frequency)}</span>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[420px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Principal</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(loan.principal_amount)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Balance</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(loan.outstanding_balance)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Pagado</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(loan.total_paid)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Cuota</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(loan.payment_amount)}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Cliente</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{loan.customer_name}</p>
                <Link href={`/customers/${loan.customer}`} className="mt-3 inline-flex text-xs font-medium text-[#163300] hover:underline">
                  Ver perfil del cliente
                </Link>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Progreso</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{paidInstallments} de {totalInstallments || 0} cuotas pagadas</p>
                <p className="mt-1 text-xs text-slate-500">{progressPct}% completado</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Desembolso</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatDate(loan.disbursement_date)}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Vencimiento</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatDate(loan.maturity_date)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Términos del préstamo</CardTitle>
                <CardDescription>Resumen contractual y operativo del crédito.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Tipo de préstamo</p>
                    <p className="mt-1 font-medium text-slate-900">{getLoanTypeLabel(loan.loan_type)}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Tasa de interés</p>
                    <p className="mt-1 font-medium text-slate-900">{loan.interest_rate}% mensual</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Fecha de solicitud</p>
                    <p className="mt-1 font-medium text-slate-900">{formatDate(loan.application_date)}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Primer pago</p>
                    <p className="mt-1 font-medium text-slate-900">{formatDate(loan.first_payment_date)}</p>
                  </div>
                </div>
                {loan.purpose && (
                  <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Propósito</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{loan.purpose}</p>
                  </div>
                )}
                {loan.notes && (
                  <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Notas</p>
                    <p className="mt-1 text-sm leading-6 text-slate-700">{loan.notes}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {loan.payment_schedules && loan.payment_schedules.length > 0 && (
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <Calendar className="h-5 w-5" />
                    Cronograma de pagos
                  </CardTitle>
                  <CardDescription>{loan.payment_schedules.length} cuotas programadas</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                    {loan.payment_schedules.map((schedule) => (
                      <div
                        key={schedule.id}
                        className={`rounded-2xl border p-4 ${
                          schedule.status === 'paid'
                            ? 'border-green-200 bg-green-50'
                            : schedule.status === 'overdue'
                            ? 'border-red-200 bg-red-50'
                            : 'border-slate-200 bg-white'
                        }`}
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-transparent text-center">
                              <div>
                                <p className="text-[10px] uppercase text-slate-500">Cuota</p>
                                <p className="font-mono text-sm font-semibold text-slate-900">#{schedule.installment_number}</p>
                              </div>
                            </div>
                            <div>
                              <p className="font-medium text-slate-900">{formatDate(schedule.due_date)}</p>
                              <p className="text-sm text-slate-600">
                                {schedule.status === 'paid' ? 'Pagada' : schedule.status === 'overdue' ? 'Vencida' : schedule.status === 'partial' ? 'Parcial' : 'Pendiente'}
                              </p>
                            </div>
                          </div>
                          <div className="text-left sm:text-right">
                            <p className="font-semibold text-slate-900">{formatCurrency(schedule.total_amount)}</p>
                            {schedule.status !== 'paid' && schedule.balance > 0 && (
                              <p className="text-sm text-orange-600">Saldo: {formatCurrency(schedule.balance)}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {loan.recent_payments && loan.recent_payments.length > 0 && (
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <Receipt className="h-5 w-5" />
                    Pagos recientes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {loan.recent_payments.map((payment) => (
                      <div key={payment.id} className="cursor-pointer rounded-2xl border border-slate-200 bg-white p-4 transition hover:bg-slate-50" onClick={() => router.push(`/payments/${payment.id}`)}>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="font-medium text-[#163300] hover:underline">{payment.payment_number}</p>
                            <p className="text-sm text-slate-600">{formatDate(payment.payment_date)} • {payment.payment_method}</p>
                          </div>
                          <div className="text-left sm:text-right">
                            <p className="font-semibold text-emerald-700">{formatCurrency(payment.amount)}</p>
                            <p className="text-xs text-slate-500 capitalize">{payment.status}</p>
                          </div>
                        </div>
                        <div className="mt-3 grid gap-2 border-t border-slate-200 pt-3 text-xs sm:grid-cols-3">
                          <div>
                            <span className="text-slate-500">Principal</span>
                            <p className="font-medium text-slate-900">{formatCurrency(payment.principal_paid || 0)}</p>
                          </div>
                          <div>
                            <span className="text-slate-500">Interés</span>
                            <p className="font-medium text-slate-900">{formatCurrency(payment.interest_paid || 0)}</p>
                          </div>
                          <div>
                            <span className="text-slate-500">Mora</span>
                            <p className={`font-medium ${payment.late_fee_paid > 0 ? 'text-orange-600' : 'text-slate-900'}`}>{formatCurrency(payment.late_fee_paid || 0)}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                    <Link href={`/payments?loan=${loan.id}`}>
                      <Button variant="outline" className="mt-2 w-full bg-white" size="sm">
                        <Receipt className="mr-2 h-4 w-4" />
                        Ver todos los pagos
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#163300]">
                  <BadgeDollarSign className="h-5 w-5" />
                  Resumen financiero
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-600">Monto total</span>
                    <span className="font-medium text-slate-900">{formatCurrency(loan.total_amount)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-600">Interés total</span>
                    <span className="font-medium text-slate-900">{formatCurrency(loan.total_interest_paid)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-600">Cargos por mora</span>
                    <span className="font-medium text-red-600">{formatCurrency(loan.late_fees)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-600">Balance pendiente</span>
                    <span className="font-semibold text-orange-600">{formatCurrency(loan.outstanding_balance)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {totalInstallments > 0 && (
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <CircleDollarSign className="h-5 w-5" />
                    Progreso del préstamo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-600">Cuotas pagadas</span>
                      <span className="font-medium text-slate-900">{paidInstallments} / {totalInstallments}</span>
                    </div>
                    <div className="h-3 w-full rounded-full bg-slate-200">
                      <div className="h-3 rounded-full bg-gradient-to-r from-[#163300] to-[#3d6a16] transition-all" style={{ width: `${progressPct}%` }} />
                    </div>
                    <p className="text-right text-sm font-medium text-slate-700">{progressPct}% completado</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-[#163300]">
                  <User className="h-5 w-5" />
                  Cliente
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Nombre</p>
                    <p className="mt-1 font-medium text-slate-900">{loan.customer_name}</p>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <Button variant="outline" className="bg-white" size="sm" asChild>
                      <a href={`tel:${String((loan as any).customer_phone || '')}`}>
                        <Phone className="h-4 w-4" />
                      </a>
                    </Button>
                    <Button variant="outline" className="bg-white" size="sm" asChild>
                      <a href={`https://wa.me/${String((loan as any).customer_phone || '').replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer">
                        <MessageCircle className="h-4 w-4" />
                      </a>
                    </Button>
                    <Button variant="outline" className="bg-white" size="sm" asChild>
                      <a href={`mailto:${String((loan as any).customer_email || '')}`}>
                        <Mail className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                  <Link href={`/customers/${loan.customer}`}>
                    <Button variant="outline" className="w-full bg-white" size="sm">
                      Ver perfil del cliente
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {loan.collaterals && loan.collaterals.length > 0 && (
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <Shield className="h-5 w-5" />
                    Garantías
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {loan.collaterals.map((collateral) => (
                      <div key={collateral.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="font-medium capitalize text-slate-900">{collateral.collateral_type}</p>
                        <p className="mt-1 text-sm text-slate-600">{collateral.description}</p>
                        <p className="mt-2 text-sm font-medium text-slate-900">Valor: {formatCurrency(collateral.estimated_value)}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {loan.loan_officer_name && (
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="text-base text-[#163300]">Oficial de crédito</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-medium text-slate-900">{loan.loan_officer_name}</p>
                </CardContent>
              </Card>
            )}

            {loan.is_overdue && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Este préstamo tiene pagos vencidos. Conviene contactar al cliente cuanto antes.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
