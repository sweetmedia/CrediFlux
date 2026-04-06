'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Plus,
  Search,
  Receipt,
  CheckCircle,
  Filter,
  Landmark,
  ArrowRight,
  Clock3,
  Wallet,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export default function PaymentsListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loanFilter = searchParams.get('loan');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [payments, setPayments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [paymentMethodFilter, setPaymentMethodFilter] = useState('');
  const [ordering, setOrdering] = useState('-payment_date');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadPayments();
    }
  }, [isAuthenticated, currentPage, searchTerm, statusFilter, paymentMethodFilter, loanFilter, ordering]);

  const loadPayments = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
        ordering,
      };

      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (paymentMethodFilter) params.payment_method = paymentMethodFilter;
      if (loanFilter) params.loan = loanFilter;

      const response = await paymentsAPI.getPayments(params);
      setPayments(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading payments:', err);
      setError('Error al cargar los pagos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  const handlePaymentMethodFilter = (value: string) => {
    setPaymentMethodFilter(value);
    setCurrentPage(1);
  };

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, string> = {
      completed: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      failed: 'bg-red-100 text-red-700',
      reversed: 'bg-slate-100 text-slate-700',
    };

    const statusLabels: Record<string, string> = {
      completed: 'Completado',
      pending: 'Pendiente',
      failed: 'Fallido',
      reversed: 'Revertido',
    };

    return (
      <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyles[status] || 'bg-slate-100 text-slate-700'}`}>
        {statusLabels[status] || status}
      </span>
    );
  };

  const getPaymentMethodLabel = (method: string) => {
    const methods: Record<string, string> = {
      cash: 'Efectivo',
      check: 'Cheque',
      bank_transfer: 'Transferencia',
      card: 'Tarjeta',
      mobile_payment: 'Pago móvil',
    };
    return methods[method] || method;
  };

  const totalPages = Math.ceil(totalCount / 10);
  const totalAmount = payments.reduce((sum, payment) => sum + (parseFloat(payment.amount) || 0), 0);
  const completedPayments = payments.filter((p) => p.status === 'completed').length;
  const pendingPayments = payments.filter((p) => p.status === 'pending').length;

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Landmark className="h-3.5 w-3.5" />
                Operación de caja y cobranzas
              </div>
              {loanFilter && (
                <div className="inline-flex items-center rounded-full bg-[#e8eddf] px-3 py-1 text-xs font-medium text-[#163300]">
                  Filtrado por préstamo
                </div>
              )}
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Pagos</h1>
            <p className="mt-2 text-sm text-slate-600">
              {loanFilter
                ? 'Seguimiento de pagos vinculados al préstamo seleccionado.'
                : 'Vista operativa para registrar, filtrar y revisar pagos sin perder contexto financiero.'}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="bg-white"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="mr-2 h-4 w-4" />
              {showFilters ? 'Ocultar filtros' : 'Mostrar filtros'}
              {showFilters ? <ChevronUp className="ml-2 h-4 w-4" /> : <ChevronDown className="ml-2 h-4 w-4" />}
            </Button>
            <Link href="/payments/new">
              <Button className="bg-[#163300] hover:bg-[#0f2400]">
                <Plus className="mr-2 h-4 w-4" />
                Registrar pago
              </Button>
            </Link>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Recaudo visible</p>
                  <h2 className="mt-1 text-3xl font-semibold">{formatCurrency(totalAmount)}</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/75">
                    Este panel prioriza lectura rápida: cuánto entró, qué falta validar y qué pagos merecen seguimiento inmediato.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[420px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Registros</p>
                    <p className="mt-2 text-2xl font-semibold">{totalCount}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Completados</p>
                    <p className="mt-2 text-2xl font-semibold">{completedPayments}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Pendientes</p>
                    <p className="mt-2 text-2xl font-semibold">{pendingPayments}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Página</p>
                    <p className="mt-2 text-2xl font-semibold">{currentPage} / {totalPages || 1}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Monto visible</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatCurrency(totalAmount)}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Método dominante</p>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {paymentMethodFilter ? getPaymentMethodLabel(paymentMethodFilter) : 'Todos los métodos'}
                </p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Estado aplicado</p>
                <div className="mt-2 text-sm font-medium text-slate-900">{statusFilter ? getStatusBadge(statusFilter) : 'Todos los estados'}</div>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Orden actual</p>
                <p className="mt-2 text-sm font-medium text-slate-900">
                  {ordering === '-payment_date'
                    ? 'Más recientes primero'
                    : ordering === 'payment_date'
                    ? 'Más antiguos primero'
                    : ordering === '-amount'
                    ? 'Mayor monto primero'
                    : 'Menor monto primero'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader className="pb-4">
            <CardTitle className="text-base text-[#163300]">Búsqueda y filtros</CardTitle>
            <CardDescription>
              Encuentra pagos por número, referencia, estado, método o prioridad de revisión.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr_auto]">
              <div className="space-y-2">
                <Label htmlFor="search" className="text-sm font-medium text-slate-700">Buscar</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="search"
                    placeholder="Número de pago, referencia o cliente..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="border-slate-200 bg-white pl-10 shadow-none"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="ordering" className="text-sm font-medium text-slate-700">Ordenar</Label>
                  <Select
                    id="ordering"
                    value={ordering}
                    onChange={(e) => setOrdering(e.target.value)}
                  >
                    <option value="-payment_date">Más recientes primero</option>
                    <option value="payment_date">Más antiguos primero</option>
                    <option value="-amount">Mayor monto primero</option>
                    <option value="amount">Menor monto primero</option>
                  </Select>
                </div>

                <div className="flex items-end">
                  <div className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    {totalCount} registro{totalCount === 1 ? '' : 's'} encontrados
                  </div>
                </div>
              </div>
            </div>

            {showFilters && (
              <div className="mt-4 grid gap-4 border-t border-slate-200 pt-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="status" className="text-sm font-medium text-slate-700">Estado</Label>
                  <Select
                    id="status"
                    value={statusFilter}
                    onChange={(e) => handleStatusFilter(e.target.value)}
                  >
                    <option value="">Todos los estados</option>
                    <option value="completed">Completado</option>
                    <option value="pending">Pendiente</option>
                    <option value="failed">Fallido</option>
                    <option value="reversed">Revertido</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="payment_method" className="text-sm font-medium text-slate-700">Método de pago</Label>
                  <Select
                    id="payment_method"
                    value={paymentMethodFilter}
                    onChange={(e) => handlePaymentMethodFilter(e.target.value)}
                  >
                    <option value="">Todos los métodos</option>
                    <option value="cash">Efectivo</option>
                    <option value="check">Cheque</option>
                    <option value="bank_transfer">Transferencia</option>
                    <option value="card">Tarjeta</option>
                    <option value="mobile_payment">Pago móvil</option>
                  </Select>
                </div>

                <div className="flex items-end">
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full bg-white"
                    onClick={() => {
                      setSearchTerm('');
                      setStatusFilter('');
                      setPaymentMethodFilter('');
                      setOrdering('-payment_date');
                      setCurrentPage(1);
                    }}
                  >
                    Limpiar filtros
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="mb-4 h-10 w-10 animate-spin text-[#163300]" />
            <p className="text-sm text-slate-600">Cargando pagos...</p>
          </div>
        ) : payments.length === 0 ? (
          <Card className="border-[#d7e2db] shadow-none">
            <CardContent className="py-16">
              <div className="mx-auto flex max-w-md flex-col items-center gap-4 text-center">
                <div className="rounded-full bg-slate-100 p-6">
                  <Receipt className="h-12 w-12 text-slate-400" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900">No se encontraron pagos</h3>
                <p className="text-sm text-slate-600">
                  {searchTerm || statusFilter || paymentMethodFilter
                    ? 'Prueba ajustando los filtros o ampliando la búsqueda.'
                    : 'Todavía no hay pagos registrados. Empieza con el primero.'}
                </p>
                <Link href="/payments/new">
                  <Button className="bg-[#163300] hover:bg-[#0f2400]">
                    <Plus className="mr-2 h-4 w-4" />
                    Registrar primer pago
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader className="border-b border-slate-200 pb-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <CardTitle className="text-base text-[#163300]">Listado operativo</CardTitle>
                  <CardDescription>
                    Haz clic en cualquier fila para ver el detalle completo del pago.
                  </CardDescription>
                </div>
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600">
                  <Wallet className="h-3.5 w-3.5" />
                  {Math.min(currentPage * 10, totalCount)} de {totalCount} visibles
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1020px]">
                  <thead className="bg-slate-50/70">
                    <tr className="border-b border-slate-200">
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Pago</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cliente / préstamo</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Método</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Monto</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Aplicación</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Estado</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((payment) => (
                      <tr
                        key={payment.id}
                        className="cursor-pointer border-b border-slate-100 transition-colors hover:bg-slate-50"
                        onClick={() => router.push(`/payments/${payment.id}`)}
                      >
                        <td className="px-4 py-4 align-top">
                          <div>
                            <p className="font-medium text-slate-900">{payment.payment_number}</p>
                            <p className="mt-1 text-xs text-slate-500">{formatDate(payment.payment_date)}</p>
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top">
                          <div>
                            <p className="font-medium text-slate-900">{payment.customer_name}</p>
                            <p className="mt-1 text-xs font-medium text-[#163300]">{payment.loan_number}</p>
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top">
                          <div>
                            <p className="text-sm text-slate-900">{getPaymentMethodLabel(payment.payment_method)}</p>
                            {payment.reference_number ? (
                              <p className="mt-1 text-xs text-slate-500">Ref: {payment.reference_number}</p>
                            ) : (
                              <p className="mt-1 text-xs text-slate-400">Sin referencia</p>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top">
                          <p className="text-lg font-semibold text-[#163300]">{formatCurrency(payment.amount)}</p>
                        </td>
                        <td className="px-4 py-4 align-top">
                          <div className="space-y-1 text-xs">
                            <div className="flex items-center justify-between gap-4">
                              <span className="text-slate-500">Principal</span>
                              <span className="font-medium text-slate-900">{formatCurrency(payment.principal_paid || 0)}</span>
                            </div>
                            <div className="flex items-center justify-between gap-4">
                              <span className="text-slate-500">Interés</span>
                              <span className="font-medium text-slate-900">{formatCurrency(payment.interest_paid || 0)}</span>
                            </div>
                            <div className="flex items-center justify-between gap-4">
                              <span className="text-slate-500">Mora</span>
                              <span className={`font-medium ${payment.late_fee_paid > 0 ? 'text-orange-600' : 'text-slate-900'}`}>
                                {formatCurrency(payment.late_fee_paid || 0)}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 align-top">
                          {getStatusBadge(payment.status)}
                        </td>
                        <td className="px-4 py-4 text-right align-top">
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-sm font-medium text-[#163300] hover:underline"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/payments/${payment.id}`);
                            }}
                          >
                            Ver
                            <ArrowRight className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {totalPages > 1 && (
                <div className="flex flex-col gap-3 border-t border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm text-slate-600">
                    Mostrando {(currentPage - 1) * 10 + 1} a {Math.min(currentPage * 10, totalCount)} de {totalCount} pagos
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-white"
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-white"
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {pendingPayments > 0 && !isLoading && payments.length > 0 && (
          <Card className="border-[#d7e2db] shadow-none">
            <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-amber-100 p-2.5 text-amber-700">
                  <Clock3 className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">Hay pagos pendientes de validación</p>
                  <p className="text-sm text-slate-600">
                    En esta página tienes {pendingPayments} pago{pendingPayments === 1 ? '' : 's'} en estado pendiente.
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                className="bg-white"
                onClick={() => {
                  setShowFilters(true);
                  setStatusFilter('pending');
                  setCurrentPage(1);
                }}
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Ver pendientes
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
