'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI } from '@/lib/api/loans';
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
  Filter,
  DollarSign,
  User,
  Calendar,
  FileText,
  ChevronLeft,
  ChevronRight,
  Eye,
  AlertCircle,
} from 'lucide-react';

export default function LoansListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [loans, setLoans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loanTypeFilter, setLoanTypeFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load loans only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadLoans();
    }
  }, [isAuthenticated, currentPage, searchTerm, statusFilter, loanTypeFilter]);

  const loadLoans = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
      };

      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (loanTypeFilter) params.loan_type = loanTypeFilter;

      const response = await loansAPI.getLoans(params);
      setLoans(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading loans:', err);
      setError('Error al cargar los préstamos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Reset to first page on search
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  const handleLoanTypeFilter = (value: string) => {
    setLoanTypeFilter(value);
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setStatusFilter('');
    setLoanTypeFilter('');
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
    const statusStyles: Record<string, string> = {
      active: 'bg-green-50 text-green-700 border-green-200',
      pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      approved: 'bg-blue-50 text-blue-700 border-blue-200',
      paid: 'bg-gray-50 text-gray-700 border-gray-200',
      defaulted: 'bg-red-50 text-red-700 border-red-200',
      completed: 'bg-green-50 text-green-700 border-green-200',
    };

    const statusLabels: Record<string, string> = {
      active: 'Activo',
      pending: 'Pendiente',
      approved: 'Aprobado',
      paid: 'Pagado',
      defaulted: 'Moroso',
      completed: 'Completado',
    };

    return (
      <span
        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium border ${
          statusStyles[status] || 'bg-gray-50 text-gray-700 border-gray-200'
        }`}
      >
        {statusLabels[status] || status}
      </span>
    );
  };

  const getLoanTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      personal: 'Personal',
      auto: 'Automóvil',
      mortgage: 'Hipotecario',
      business: 'Empresarial',
      other: 'Otro',
    };
    return labels[type] || type;
  };

  const totalPages = Math.ceil(totalCount / 10); // Assuming 10 items per page

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
              <FileText className="h-8 w-8 text-blue-600" />
              Préstamos
            </h1>
            <p className="text-gray-600 mt-1">
              Gestiona y consulta todos los préstamos del sistema
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard">
              <Button variant="outline">Volver al Dashboard</Button>
            </Link>
            <Link href="/loans/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Préstamo
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters Card */}
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Búsqueda y Filtros
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="mr-2 h-4 w-4" />
                {showFilters ? 'Ocultar' : 'Mostrar'} Filtros
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Search */}
              <div className="space-y-2">
                <Label htmlFor="search">Buscar</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="search"
                    placeholder="Buscar por número de préstamo, cliente..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              {/* Advanced Filters */}
              {showFilters && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t">
                  <div className="space-y-2">
                    <Label htmlFor="status">Estado</Label>
                    <Select
                      id="status"
                      value={statusFilter}
                      onChange={(e) => handleStatusFilter(e.target.value)}
                    >
                      <option value="">Todos los estados</option>
                      <option value="pending">Pendiente</option>
                      <option value="approved">Aprobado</option>
                      <option value="active">Activo</option>
                      <option value="paid">Pagado</option>
                      <option value="defaulted">Moroso</option>
                      <option value="completed">Completado</option>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="loan_type">Tipo de Préstamo</Label>
                    <Select
                      id="loan_type"
                      value={loanTypeFilter}
                      onChange={(e) => handleLoanTypeFilter(e.target.value)}
                    >
                      <option value="">Todos los tipos</option>
                      <option value="personal">Personal</option>
                      <option value="auto">Automóvil</option>
                      <option value="mortgage">Hipotecario</option>
                      <option value="business">Empresarial</option>
                      <option value="other">Otro</option>
                    </Select>
                  </div>

                  <div className="flex items-end">
                    <Button variant="outline" onClick={clearFilters} className="w-full">
                      Limpiar Filtros
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Préstamos</p>
                  <p className="text-2xl font-bold">{totalCount}</p>
                </div>
                <FileText className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Activos</p>
                  <p className="text-2xl font-bold text-green-600">
                    {loans.filter((l) => l.status === 'active').length}
                  </p>
                </div>
                <DollarSign className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Morosos</p>
                  <p className="text-2xl font-bold text-red-600">
                    {loans.filter((l) => l.days_overdue > 0).length}
                  </p>
                </div>
                <AlertCircle className="h-8 w-8 text-red-600" />
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
                <FileText className="h-8 w-8 text-gray-400" />
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

        {/* Loans List */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando préstamos...</p>
          </div>
        ) : loans.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-gray-100 p-6">
                  <FileText className="h-12 w-12 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">No se encontraron préstamos</h3>
                <p className="text-gray-600">
                  {searchTerm || statusFilter || loanTypeFilter
                    ? 'Intenta ajustar los filtros de búsqueda'
                    : 'Comienza creando tu primer préstamo'}
                </p>
                <Link href="/loans/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Crear Primer Préstamo
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {loans.map((loan) => (
              <Card
                key={loan.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/loans/${loan.id}`)}
              >
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    {/* Left Section - Main Info */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                              <User className="h-5 w-5 text-gray-600" />
                              {loan.customer_name}
                            </h3>
                            {loan.days_overdue > 0 && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-100 text-red-700 text-xs font-medium">
                                <AlertCircle className="h-3 w-3" />
                                {loan.days_overdue}d mora
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-600">
                            <span className="flex items-center gap-1">
                              <FileText className="h-4 w-4" />
                              {loan.loan_number}
                            </span>
                            <span className="flex items-center gap-1">
                              <Calendar className="h-4 w-4" />
                              {formatDate(loan.disbursement_date)}
                            </span>
                            <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                              {getLoanTypeLabel(loan.loan_type)}
                            </span>
                          </div>
                        </div>
                        {getStatusBadge(loan.status)}
                      </div>

                      {/* Financial Info */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-gray-600">Monto Original</p>
                          <p className="text-sm font-semibold">
                            {formatCurrency(loan.principal_amount)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Total Pagado</p>
                          <p className="text-sm font-semibold text-green-600">
                            {formatCurrency(loan.total_paid || 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Balance Pendiente</p>
                          <p className="text-sm font-semibold text-blue-600">
                            {formatCurrency(loan.outstanding_balance)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">Tasa de Interés</p>
                          <p className="text-sm font-semibold">{loan.interest_rate}%</p>
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
                          router.push(`/loans/${loan.id}`);
                        }}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ver Detalles
                      </Button>
                      {loan.status === 'active' && (
                        <Button
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/payments/new?loan=${loan.id}`);
                          }}
                        >
                          <DollarSign className="mr-2 h-4 w-4" />
                          Pagar
                        </Button>
                      )}
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
                      {Math.min(currentPage * 10, totalCount)} de {totalCount} préstamos
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
