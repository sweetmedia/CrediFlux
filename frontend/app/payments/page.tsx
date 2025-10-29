'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
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
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Plus,
  Search,
  Receipt,
  DollarSign,
  Calendar,
  CreditCard,
  User,
  ChevronLeft,
  ChevronRight,
  Eye,
  CheckCircle,
  XCircle,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';

export default function PaymentsListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loanFilter = searchParams.get('loan');
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [payments, setPayments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [paymentMethodFilter, setPaymentMethodFilter] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load payments only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadPayments();
    }
  }, [isAuthenticated, currentPage, searchTerm, statusFilter, paymentMethodFilter, loanFilter]);

  const loadPayments = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
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
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      completed: {
        label: 'Completado',
        icon: CheckCircle,
        className: 'bg-green-100 text-green-700',
      },
      pending: {
        label: 'Pendiente',
        icon: AlertCircle,
        className: 'bg-yellow-100 text-yellow-700',
      },
      failed: {
        label: 'Fallido',
        icon: XCircle,
        className: 'bg-red-100 text-red-700',
      },
      reversed: {
        label: 'Revertido',
        icon: RotateCcw,
        className: 'bg-gray-100 text-gray-700',
      },
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${config.className}`}>
        <Icon className="h-3 w-3" />
        <span className="font-semibold">{config.label}</span>
      </div>
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

  // Calculate statistics
  const totalAmount = payments.reduce((sum, payment) => sum + (payment.amount || 0), 0);
  const completedPayments = payments.filter((p) => p.status === 'completed').length;

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <Receipt className="h-8 w-8 text-blue-600" />
              Pagos
              {loanFilter && (
                <span className="text-sm font-normal bg-blue-100 text-blue-700 px-3 py-1 rounded-full">
                  Filtrado por préstamo
                </span>
              )}
            </h1>
            <p className="text-gray-600 mt-1">
              {loanFilter
                ? 'Pagos del préstamo seleccionado'
                : 'Gestiona y consulta todos los pagos registrados'}
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard">
              <Button variant="outline">Volver al Dashboard</Button>
            </Link>
            <Link href="/payments/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Registrar Pago
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Filtros de Búsqueda
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="search">Buscar</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="search"
                    placeholder="Número de pago, referencia..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">Estado</Label>
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
                <Label htmlFor="payment_method">Método de Pago</Label>
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
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Pagos</p>
                  <p className="text-2xl font-bold">{totalCount}</p>
                </div>
                <Receipt className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Completados</p>
                  <p className="text-2xl font-bold text-green-600">{completedPayments}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Monto Total</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {formatCurrency(totalAmount)}
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
                  <p className="text-sm text-gray-600">Página</p>
                  <p className="text-2xl font-bold">
                    {currentPage} / {totalPages || 1}
                  </p>
                </div>
                <Receipt className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Payments List */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando pagos...</p>
          </div>
        ) : payments.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-gray-100 p-6">
                  <Receipt className="h-12 w-12 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  No se encontraron pagos
                </h3>
                <p className="text-gray-600">
                  {searchTerm || statusFilter || paymentMethodFilter
                    ? 'Intenta ajustar tus filtros'
                    : 'Comienza registrando tu primer pago'}
                </p>
                <Link href="/payments/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Registrar Primer Pago
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {payments.map((payment) => (
              <Card
                key={payment.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/payments/${payment.id}`)}
              >
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    {/* Left Section - Main Info */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">
                              {payment.payment_number}
                            </h3>
                            {getStatusBadge(payment.status)}
                          </div>

                          {/* Payment Info */}
                          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-3">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-4 w-4" />
                              {formatDate(payment.payment_date)}
                            </span>
                            <span className="flex items-center gap-1">
                              <CreditCard className="h-4 w-4" />
                              {getPaymentMethodLabel(payment.payment_method)}
                            </span>
                            {payment.reference_number && (
                              <span className="flex items-center gap-1">
                                <span className="font-semibold">Ref:</span>
                                {payment.reference_number}
                              </span>
                            )}
                          </div>

                          {/* Loan and Customer Info */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-gray-400" />
                              <div>
                                <p className="text-xs text-gray-600">Cliente</p>
                                <p className="text-sm font-medium">{payment.customer_name}</p>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <Receipt className="h-4 w-4 text-gray-400" />
                              <div>
                                <p className="text-xs text-gray-600">Préstamo</p>
                                <p className="text-sm font-medium text-blue-600">
                                  {payment.loan_number}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Amount Display */}
                      <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Monto del Pago</span>
                          <span className="text-2xl font-bold text-blue-600">
                            {formatCurrency(payment.amount)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Right Section - Actions */}
                    <div className="flex lg:flex-col gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/payments/${payment.id}`);
                        }}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ver Detalles
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      Mostrando {(currentPage - 1) * 10 + 1} a{' '}
                      {Math.min(currentPage * 10, totalCount)} de {totalCount} pagos
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage + 1)}
                        disabled={currentPage === totalPages}
                      >
                        Siguiente
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
