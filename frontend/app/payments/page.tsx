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
  DollarSign,
  CheckCircle,
  TrendingUp,
  Filter,
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

  // Filters and pagination
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
        ordering: ordering,
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
      maximumFractionDigits: 2
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
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusStyles[status] || 'bg-slate-100 text-slate-700'}`}>
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
      mobile_payment: 'Pago Móvil',
    };
    return methods[method] || method;
  };

  const totalPages = Math.ceil(totalCount / 10);

  const totalAmount = payments.reduce((sum, payment) => sum + (parseFloat(payment.amount) || 0), 0);
  const completedPayments = payments.filter((p) => p.status === 'completed').length;

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Gestión de Pagos</h1>
            <p className="text-sm text-slate-600 mt-1">
              {loanFilter ? 'Pagos del préstamo seleccionado' : 'Administra y monitorea todos los pagos registrados'}
            </p>
          </div>
          <Link href="/payments/new">
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus className="mr-2 h-4 w-4" />
              Registrar Pago
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
                <Receipt className="h-6 w-6 text-blue-600" />
              </div>
              <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                <TrendingUp className="h-3 w-3" />
                +12%
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Total Pagos</p>
            <p className="text-2xl font-bold text-slate-900">{totalCount}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Completados</p>
            <p className="text-2xl font-bold text-slate-900">{completedPayments}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-purple-100 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Monto Total</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(totalAmount)}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-slate-100 flex items-center justify-center">
                <Receipt className="h-6 w-6 text-slate-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Página</p>
            <p className="text-2xl font-bold text-slate-900">
              {currentPage} / {totalPages || 1}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6 border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-200">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-slate-900">Filtros</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="mr-2 h-4 w-4" />
              {showFilters ? 'Ocultar' : 'Mostrar'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="search" className="text-sm font-medium text-slate-700">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="search"
                  placeholder="Número de pago, referencia..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {showFilters && (
              <div className="grid grid-cols-4 gap-4 pt-4 border-t border-slate-200">
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
                  <Label htmlFor="payment_method" className="text-sm font-medium text-slate-700">Método de Pago</Label>
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
                    <option value="mobile_payment">Pago Móvil</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="ordering" className="text-sm font-medium text-slate-700">Ordenar por</Label>
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
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Payments Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-slate-600">Cargando pagos...</p>
        </div>
      ) : payments.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-slate-100 p-6">
                <Receipt className="h-12 w-12 text-slate-400" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">
                No se encontraron pagos
              </h3>
              <p className="text-slate-600">
                {searchTerm || statusFilter || paymentMethodFilter
                  ? 'Intenta ajustar tus filtros'
                  : 'Comienza registrando tu primer pago'}
              </p>
              <Link href="/payments/new">
                <Button className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="mr-2 h-4 w-4" />
                  Registrar Primer Pago
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pago</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Cliente/Préstamo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Método</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Monto</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Desglose</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Estado</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => router.push(`/payments/${payment.id}`)}>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{payment.payment_number}</p>
                        <p className="text-xs text-slate-500">{formatDate(payment.payment_date)}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{payment.customer_name}</p>
                        <p className="text-xs text-blue-600">{payment.loan_number}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-sm text-slate-900">{getPaymentMethodLabel(payment.payment_method)}</p>
                        {payment.reference_number && (
                          <p className="text-xs text-slate-500">Ref: {payment.reference_number}</p>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-bold text-blue-600 text-lg">{formatCurrency(payment.amount)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-600">Principal:</span>
                          <span className="font-medium text-slate-900">{formatCurrency(payment.principal_paid || 0)}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-600">Interés:</span>
                          <span className="font-medium text-slate-900">{formatCurrency(payment.interest_paid || 0)}</span>
                        </div>
                        {payment.late_fee_paid > 0 && (
                          <div className="flex items-center justify-between">
                            <span className="text-slate-600">Mora:</span>
                            <span className="font-medium text-orange-600">{formatCurrency(payment.late_fee_paid)}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(payment.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="border-t border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-slate-600">
                    Mostrando {(currentPage - 1) * 10 + 1} a {Math.min(currentPage * 10, totalCount)} de {totalCount} pagos
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
