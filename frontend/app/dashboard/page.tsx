'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI, paymentsAPI } from '@/lib/api/loans';
import { customersAPI } from '@/lib/api/customers';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DollarSign,
  Users,
  TrendingUp,
  AlertCircle,
  Plus,
  Loader2,
  LogOut,
  User,
  Building2,
  FileText,
  CreditCard,
  Settings,
} from 'lucide-react';
import type { LoanStatistics, Loan, LoanPayment } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const { user, tenant, isAuthenticated, isLoading: authLoading, logout } = useAuth();

  const [statistics, setStatistics] = useState<LoanStatistics | null>(null);
  const [recentLoans, setRecentLoans] = useState<Loan[]>([]);
  const [recentPayments, setRecentPayments] = useState<LoanPayment[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [error, setError] = useState<string>('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch dashboard data
  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData();
    }
  }, [isAuthenticated]);

  const fetchDashboardData = async () => {
    try {
      setIsLoadingStats(true);
      setError('');

      // Fetch all data in parallel
      const [statsData, loansData, paymentsData] = await Promise.all([
        loansAPI.getStatistics(),
        loansAPI.getLoans({ page: 1 }),
        paymentsAPI.getPayments({ page: 1 }),
      ]);

      setStatistics(statsData);
      setRecentLoans(loansData.results.slice(0, 5));
      setRecentPayments(paymentsData.results.slice(0, 5));
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError('Error al cargar los datos del dashboard');
    } finally {
      setIsLoadingStats(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
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
      active: 'bg-green-50 text-green-700',
      pending: 'bg-yellow-50 text-yellow-700',
      approved: 'bg-blue-50 text-blue-700',
      paid: 'bg-gray-50 text-gray-700',
      defaulted: 'bg-red-50 text-red-700',
      completed: 'bg-green-50 text-green-700',
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
        className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
          statusStyles[status] || 'bg-gray-50 text-gray-700'
        }`}
      >
        {statusLabels[status] || status}
      </span>
    );
  };

  // Show loading state
  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <DollarSign className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">CrediFlux</h1>
                {tenant && (
                  <p className="text-sm text-gray-600 flex items-center gap-1">
                    <Building2 className="h-3 w-3" />
                    {tenant.business_name}
                  </p>
                )}
              </div>
            </div>

            <nav className="hidden md:flex items-center space-x-6">
              <Link
                href="/dashboard"
                className="text-sm font-medium text-blue-600 border-b-2 border-blue-600 pb-1"
              >
                Dashboard
              </Link>
              <Link
                href="/loans"
                className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors"
              >
                Préstamos
              </Link>
              <Link
                href="/customers"
                className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors"
              >
                Clientes
              </Link>
              {(user?.is_tenant_owner || user?.role === 'admin') && (
                <Link
                  href="/users"
                  className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors"
                >
                  Equipo
                </Link>
              )}
              {(user?.is_tenant_owner || user?.role === 'admin') && (
                <Link
                  href="/settings"
                  className="text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors flex items-center gap-1"
                >
                  <Settings className="h-3 w-3" />
                  Configuración
                </Link>
              )}
            </nav>

            <div className="flex items-center space-x-4">
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium text-gray-900 flex items-center gap-1 justify-end">
                  <User className="h-3 w-3" />
                  {user.full_name}
                </p>
                <p className="text-xs text-gray-600 capitalize">{user.role.replace('_', ' ')}</p>
              </div>
              <Button onClick={handleLogout} variant="outline" size="sm">
                <LogOut className="h-4 w-4 mr-2" />
                Salir
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">
              ¡Bienvenido, {user.first_name}!
            </h2>
            <p className="text-gray-600 mt-1">
              Aquí está el resumen de tu cartera de préstamos
            </p>
          </div>
          <Button asChild>
            <Link href="/loans/new">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Préstamo
            </Link>
          </Button>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Stats Grid */}
        {isLoadingStats ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : statistics ? (
          <>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Préstamos</CardTitle>
                  <FileText className="h-4 w-4 text-gray-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statistics.total_loans}</div>
                  <p className="text-xs text-gray-600 mt-1">
                    {statistics.active_loans} activos
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Préstamos Activos</CardTitle>
                  <TrendingUp className="h-4 w-4 text-green-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {statistics.active_loans}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {statistics.total_loans > 0
                      ? Math.round((statistics.active_loans / statistics.total_loans) * 100)
                      : 0}
                    % del portafolio
                  </p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Saldo Pendiente</CardTitle>
                  <DollarSign className="h-4 w-4 text-blue-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(statistics.total_outstanding)}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">En préstamos activos</p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Recaudado</CardTitle>
                  <CreditCard className="h-4 w-4 text-green-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600">
                    {formatCurrency(statistics.total_collected)}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">Total de pagos</p>
                </CardContent>
              </Card>
            </div>

            {/* Additional Stats */}
            <div className="grid gap-6 md:grid-cols-3 mb-8">
              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Préstamos Pagados</CardTitle>
                  <TrendingUp className="h-4 w-4 text-gray-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{statistics.paid_loans}</div>
                  <p className="text-xs text-gray-600 mt-1">Completamente pagados</p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Préstamos Morosos</CardTitle>
                  <AlertCircle className="h-4 w-4 text-red-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600">
                    {statistics.defaulted_loans}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">Requieren atención</p>
                </CardContent>
              </Card>

              <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Desembolsado</CardTitle>
                  <DollarSign className="h-4 w-4 text-blue-600" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(statistics.total_disbursed)}
                  </div>
                  <p className="text-xs text-gray-600 mt-1">Total prestado</p>
                </CardContent>
              </Card>
            </div>
          </>
        ) : null}

        {/* Recent Activity */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Préstamos Recientes</CardTitle>
              <CardDescription>Últimas solicitudes y actualizaciones</CardDescription>
            </CardHeader>
            <CardContent>
              {recentLoans.length > 0 ? (
                <div className="space-y-4">
                  {recentLoans.map((loan) => (
                    <div key={loan.id} className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">
                          {loan.customer_name} - {loan.loan_type}
                        </p>
                        <p className="text-xs text-gray-600">{loan.loan_number}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">
                          {formatCurrency(loan.principal_amount)}
                        </p>
                        {getStatusBadge(loan.status)}
                      </div>
                    </div>
                  ))}
                  <Button className="w-full mt-4" variant="outline" asChild>
                    <Link href="/loans">Ver Todos los Préstamos</Link>
                  </Button>
                </div>
              ) : (
                <p className="text-center text-gray-600 py-8">No hay préstamos recientes</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Pagos Recientes</CardTitle>
              <CardDescription>Últimos pagos recibidos</CardDescription>
            </CardHeader>
            <CardContent>
              {recentPayments.length > 0 ? (
                <div className="space-y-4">
                  {recentPayments.map((payment) => (
                    <div key={payment.id} className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">{payment.customer_name}</p>
                        <p className="text-xs text-gray-600">
                          {formatDate(payment.payment_date)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-green-600">
                          +{formatCurrency(payment.amount)}
                        </p>
                        <p className="text-xs text-gray-600 capitalize">
                          {payment.payment_method.replace('_', ' ')}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Button className="w-full mt-4" variant="outline">
                    Ver Todos los Pagos
                  </Button>
                </div>
              ) : (
                <p className="text-center text-gray-600 py-8">No hay pagos recientes</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Acciones Rápidas</CardTitle>
            <CardDescription>Tareas y operaciones comunes</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <Button variant="outline" className="h-24 flex-col" asChild>
                <Link href="/loans/new">
                  <Plus className="h-6 w-6 mb-2" />
                  <span>Nuevo Préstamo</span>
                </Link>
              </Button>
              <Button variant="outline" className="h-24 flex-col" asChild>
                <Link href="/payments/new">
                  <DollarSign className="h-6 w-6 mb-2" />
                  <span>Registrar Pago</span>
                </Link>
              </Button>
              <Button variant="outline" className="h-24 flex-col" asChild>
                <Link href="/customers/new">
                  <Users className="h-6 w-6 mb-2" />
                  <span>Agregar Cliente</span>
                </Link>
              </Button>
              <Button variant="outline" className="h-24 flex-col" asChild>
                <Link href="/loans/overdue">
                  <AlertCircle className="h-6 w-6 mb-2" />
                  <span>Ver Morosos</span>
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
