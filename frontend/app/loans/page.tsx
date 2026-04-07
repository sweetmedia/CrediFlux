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
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { StatusBadge } from '@/components/ui/status-badge';
import {
  Loader2,
  Plus,
  Search,
  DollarSign,
  FileText,
  AlertCircle,
  CheckCircle,
  TrendingUp,
  X,
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

  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loanTypeFilter, setLoanTypeFilter] = useState('');

  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);

  const canApproveLoan = user && (
    user.is_superuser ||
    user.is_tenant_owner ||
    ['admin', 'manager', 'loan_officer'].includes(user.role)
  );

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

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
      const params: any = { page: currentPage };
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
    return `RD$ ${amount.toLocaleString('en-US', {
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
  const hasFilters = searchTerm || statusFilter || loanTypeFilter;

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Gestión de Préstamos</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Administra y monitorea todos los préstamos del sistema
          </p>
        </div>
        <Link href="/loans/new">
          <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-md shadow-none">
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Nuevo Préstamo
          </Button>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card className="border-border shadow-none">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-9 w-9 rounded-lg bg-[#e8eddf] flex items-center justify-center">
                <FileText className="h-4.5 w-4.5 text-primary" style={{ height: 18, width: 18 }} />
              </div>
              <div className="flex items-center gap-1 text-xs text-green-600">
                <TrendingUp className="h-3 w-3" />
                +8.2%
              </div>
            </div>
            <p className="text-xs text-muted-foreground mb-1">Total Préstamos</p>
            <p className="text-2xl font-semibold text-foreground">{totalCount}</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-none">
          <CardContent className="p-5">
            <div className="h-9 w-9 rounded-lg bg-green-50 flex items-center justify-center mb-3">
              <CheckCircle className="h-4.5 w-4.5 text-green-600" style={{ height: 18, width: 18 }} />
            </div>
            <p className="text-xs text-muted-foreground mb-1">Activos</p>
            <p className="text-2xl font-semibold text-foreground">{statistics.active_loans}</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-none">
          <CardContent className="p-5">
            <div className="h-9 w-9 rounded-lg bg-yellow-50 flex items-center justify-center mb-3">
              <AlertCircle className="h-4.5 w-4.5 text-yellow-600" style={{ height: 18, width: 18 }} />
            </div>
            <p className="text-xs text-muted-foreground mb-1">Pendientes</p>
            <p className="text-2xl font-semibold text-foreground">{statistics.pending_loans}</p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-none">
          <CardContent className="p-5">
            <div className="h-9 w-9 rounded-lg bg-red-50 flex items-center justify-center mb-3">
              <AlertCircle className="h-4.5 w-4.5 text-red-600" style={{ height: 18, width: 18 }} />
            </div>
            <p className="text-xs text-muted-foreground mb-1">Morosos</p>
            <p className="text-2xl font-semibold text-foreground">{statistics.overdue_loans}</p>
          </CardContent>
        </Card>
      </div>

      {/* Inline Filter Bar */}
      <div className="flex items-center gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Buscar por número o cliente..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-9 h-8 text-sm border-border bg-card shadow-none"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => handleStatusFilter(e.target.value)}
          className="h-8 text-sm border-border bg-card shadow-none w-40"
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
        <Select
          value={loanTypeFilter}
          onChange={(e) => handleLoanTypeFilter(e.target.value)}
          className="h-8 text-sm border-border bg-card shadow-none w-40"
        >
          <option value="">Todos los tipos</option>
          <option value="personal">Personal</option>
          <option value="auto">Automóvil</option>
          <option value="mortgage">Hipotecario</option>
          <option value="business">Empresarial</option>
          <option value="other">Otro</option>
        </Select>
        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="h-8 text-xs text-muted-foreground hover:text-foreground px-2"
          >
            <X className="h-3.5 w-3.5 mr-1" />
            Limpiar
          </Button>
        )}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-5">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loans Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="h-7 w-7 animate-spin text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Cargando préstamos...</p>
        </div>
      ) : loans.length === 0 ? (
        <Card className="border-border shadow-none">
          <CardContent className="text-center py-14">
            <div className="flex flex-col items-center gap-3">
              <div className="rounded-full bg-muted p-5">
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-base font-semibold text-foreground">No se encontraron préstamos</h3>
              <p className="text-sm text-muted-foreground">
                {hasFilters
                  ? 'Intenta ajustar los filtros de búsqueda'
                  : 'Comienza creando tu primer préstamo'}
              </p>
              <Link href="/loans/new">
                <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-none mt-1">
                  <Plus className="mr-1.5 h-3.5 w-3.5" />
                  Crear Primer Préstamo
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-border shadow-none">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2.5 px-5 text-xs font-medium text-muted-foreground">Cliente</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Préstamo</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Monto</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Pagado</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Balance</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Estado</th>
                  <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loans.map((loan) => (
                  <tr
                    key={loan.id}
                    className="border-b border-border last:border-0 hover:bg-muted/40 transition-colors cursor-pointer"
                    onClick={() => router.push(`/loans/${loan.id}`)}
                  >
                    <td className="py-3 px-5">
                      <p className="text-sm font-medium text-foreground">{loan.customer_name}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(loan.disbursement_date)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm font-medium text-foreground">{loan.loan_number}</p>
                      <p className="text-xs text-muted-foreground">{getLoanTypeLabel(loan.loan_type)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm font-medium text-foreground">{formatCurrency(loan.principal_amount)}</p>
                      <p className="text-xs text-muted-foreground">{loan.interest_rate}% interés</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm font-medium text-green-600">{formatCurrency(loan.total_paid || 0)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm font-medium text-foreground">{formatCurrency(loan.outstanding_balance)}</p>
                      {loan.days_overdue > 0 && (
                        <p className="text-xs text-red-500 font-medium">{loan.days_overdue}d mora</p>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={loan.status} />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                        {loan.status === 'pending' && canApproveLoan && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-border shadow-none"
                            onClick={() => handleOpenApprovalDialog(loan)}
                          >
                            Gestionar
                          </Button>
                        )}
                        {loan.status === 'active' && (
                          <Button
                            size="sm"
                            className="h-7 text-xs bg-primary hover:bg-primary/90 text-primary-foreground shadow-none"
                            onClick={() => router.push(`/payments/new?loan=${loan.id}`)}
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
              <div className="border-t border-border px-5 py-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    Mostrando {(currentPage - 1) * 20 + 1}–{Math.min(currentPage * 20, totalCount)} de {totalCount} préstamos
                  </p>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs border-border shadow-none"
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Anterior
                    </Button>
                    <span className="px-3 text-xs text-muted-foreground">
                      {currentPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs border-border shadow-none"
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
