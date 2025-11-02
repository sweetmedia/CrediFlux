'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI } from '@/lib/api/loans';
import { Loan } from '@/types';
import LoanApprovalDialog from '@/components/loans/LoanApprovalDialog';
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
  Filter,
  DollarSign,
  FileText,
  AlertCircle,
  CheckCircle,
  TrendingUp,
} from 'lucide-react';

export default function LoansListPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [loans, setLoans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [statistics, setStatistics] = useState({
    total_loans: 0,
    active_loans: 0,
    pending_loans: 0,
    paid_loans: 0,
    defaulted_loans: 0,
    overdue_loans: 0,
  });

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loanTypeFilter, setLoanTypeFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Approval dialog state
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);

  // Check if user can approve loans
  const canApproveLoan = user && (
    user.is_superuser ||
    user.is_tenant_owner ||
    ['admin', 'manager', 'loan_officer'].includes(user.role)
  );

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
      loadStatistics();
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

  const loadStatistics = async () => {
    try {
      const stats = await loansAPI.getStatistics();
      setStatistics(stats);
    } catch (err: any) {
      console.error('Error loading statistics:', err);
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

  const handleOpenApprovalDialog = (loan: Loan) => {
    setSelectedLoan(loan);
    setApprovalDialogOpen(true);
  };

  const handleApprove = async (notes?: string) => {
    if (!selectedLoan) return;

    try {
      await loansAPI.approveLoan(selectedLoan.id, notes);
      await loadLoans();
      setApprovalDialogOpen(false);
      setSelectedLoan(null);
    } catch (err: any) {
      console.error('Error approving loan:', err);
      throw err;
    }
  };

  const handleReject = async (notes: string) => {
    if (!selectedLoan) return;

    try {
      await loansAPI.rejectLoan(selectedLoan.id, notes);
      await loadLoans();
      setApprovalDialogOpen(false);
      setSelectedLoan(null);
    } catch (err: any) {
      console.error('Error rejecting loan:', err);
      throw err;
    }
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
      active: 'bg-green-100 text-green-700',
      pending: 'bg-yellow-100 text-yellow-700',
      approved: 'bg-blue-100 text-blue-700',
      paid: 'bg-slate-100 text-slate-700',
      defaulted: 'bg-red-100 text-red-700',
      rejected: 'bg-red-100 text-red-700',
      completed: 'bg-green-100 text-green-700',
    };

    const statusLabels: Record<string, string> = {
      active: 'Activo',
      pending: 'Pendiente',
      approved: 'Aprobado',
      paid: 'Pagado',
      defaulted: 'Moroso',
      rejected: 'Rechazado',
      completed: 'Completado',
    };

    return (
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusStyles[status] || 'bg-slate-100 text-slate-700'}`}>
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

  const totalPages = Math.ceil(totalCount / 20);

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
            <h1 className="text-2xl font-bold text-slate-900">Gestión de Préstamos</h1>
            <p className="text-sm text-slate-600 mt-1">
              Administra y monitorea todos los préstamos del sistema
            </p>
          </div>
          <Link href="/loans/new">
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Préstamo
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
                <FileText className="h-6 w-6 text-blue-600" />
              </div>
              <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                <TrendingUp className="h-3 w-3" />
                +8.2%
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Total Préstamos</p>
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
            <p className="text-sm text-slate-600 mb-1">Activos</p>
            <p className="text-2xl font-bold text-slate-900">{statistics.active_loans}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-yellow-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Pendientes</p>
            <p className="text-2xl font-bold text-slate-900">{statistics.pending_loans}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Morosos</p>
            <p className="text-2xl font-bold text-slate-900">{statistics.overdue_loans}</p>
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
                  placeholder="Buscar por número de préstamo, cliente..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {showFilters && (
              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-200">
                <div className="space-y-2">
                  <Label htmlFor="status" className="text-sm font-medium text-slate-700">Estado</Label>
                  <Select
                    id="status"
                    value={statusFilter}
                    onChange={(e) => handleStatusFilter(e.target.value)}
                  >
                    <option value="">Todos los estados</option>
                    <option value="pending">Pendiente</option>
                    <option value="approved">Aprobado</option>
                    <option value="rejected">Rechazado</option>
                    <option value="active">Activo</option>
                    <option value="paid">Pagado</option>
                    <option value="defaulted">Moroso</option>
                    <option value="completed">Completado</option>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="loan_type" className="text-sm font-medium text-slate-700">Tipo de Préstamo</Label>
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

      {/* Error */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loans Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-slate-600">Cargando préstamos...</p>
        </div>
      ) : loans.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-slate-100 p-6">
                <FileText className="h-12 w-12 text-slate-400" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">No se encontraron préstamos</h3>
              <p className="text-slate-600">
                {searchTerm || statusFilter || loanTypeFilter
                  ? 'Intenta ajustar los filtros de búsqueda'
                  : 'Comienza creando tu primer préstamo'}
              </p>
              <Link href="/loans/new">
                <Button className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="mr-2 h-4 w-4" />
                  Crear Primer Préstamo
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
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Cliente</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Préstamo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Monto</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pagado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Balance</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Estado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loans.map((loan) => (
                  <tr key={loan.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => router.push(`/loans/${loan.id}`)}>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{loan.customer_name}</p>
                        <p className="text-xs text-slate-500">{formatDate(loan.disbursement_date)}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{loan.loan_number}</p>
                        <p className="text-xs text-slate-500">{getLoanTypeLabel(loan.loan_type)}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-medium text-slate-900">{formatCurrency(loan.principal_amount)}</p>
                      <p className="text-xs text-slate-500">{loan.interest_rate}% interés</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-medium text-green-600">{formatCurrency(loan.total_paid || 0)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-blue-600">{formatCurrency(loan.outstanding_balance)}</p>
                        {loan.days_overdue > 0 && (
                          <p className="text-xs text-red-600 font-medium">{loan.days_overdue}d mora</p>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(loan.status)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        {loan.status === 'pending' && canApproveLoan && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenApprovalDialog(loan);
                            }}
                          >
                            Gestionar
                          </Button>
                        )}
                        {loan.status === 'active' && (
                          <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/payments/new?loan=${loan.id}`);
                            }}
                          >
                            <DollarSign className="mr-1 h-3 w-3" />
                            Pagar
                          </Button>
                        )}
                      </div>
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
                    Mostrando {(currentPage - 1) * 20 + 1} a {Math.min(currentPage * 20, totalCount)} de {totalCount} préstamos
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

      {/* Loan Approval/Rejection Dialog */}
      <LoanApprovalDialog
        loan={selectedLoan}
        open={approvalDialogOpen}
        onOpenChange={setApprovalDialogOpen}
        onApprove={handleApprove}
        onReject={handleReject}
      />
    </div>
  );
}
