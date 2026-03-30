'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI } from '@/lib/api/loans';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Plus,
  Loader2,
  ArrowUpRight,
  Wallet,
  Target,
  Calendar,
  Banknote,
  Clock,
  CheckCircle2,
  Activity,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { DashboardStatistics, Loan } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();

  const [dashboardStats, setDashboardStats] = useState<DashboardStatistics | null>(null);
  const [recentLoans, setRecentLoans] = useState<Loan[]>([]);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData();
    }
  }, [isAuthenticated]);

  const fetchDashboardData = async () => {
    try {
      setIsLoadingStats(true);
      setError('');

      const [statsData, loansData] = await Promise.all([
        loansAPI.getDashboardStatistics(),
        loansAPI.getLoans({ page: 1 }),
      ]);

      setDashboardStats(statsData);
      setRecentLoans(loansData.results.slice(0, 5));
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError('Error al cargar los datos del dashboard');
    } finally {
      setIsLoadingStats(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatCompactCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `${config.currency_symbol}${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${config.currency_symbol}${(amount / 1000).toFixed(1)}K`;
    }
    return formatCurrency(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
    });
  };

  // Merge monthly_disbursements + monthly_collections into unified chart data
  const buildChartData = (stats: DashboardStatistics) => {
    const months: Record<string, { month: string; desembolsado: number; recaudado: number }> = {};

    stats.charts.monthly_disbursements.forEach(({ month, amount }) => {
      if (!months[month]) months[month] = { month, desembolsado: 0, recaudado: 0 };
      months[month].desembolsado = amount;
    });

    stats.charts.monthly_collections.forEach(({ month, amount }) => {
      if (!months[month]) months[month] = { month, desembolsado: 0, recaudado: 0 };
      months[month].recaudado = amount;
    });

    return Object.values(months).sort((a, b) => a.month.localeCompare(b.month));
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const recoveryRate = dashboardStats
    ? dashboardStats.summary.total_loans > 0
      ? Math.round((dashboardStats.summary.paid_loans / dashboardStats.summary.total_loans) * 100)
      : 0
    : 0;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200">
        <div className="px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-slate-900">Dashboard Ejecutivo</h1>
                <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded-full">
                  En Vivo
                </span>
              </div>
              <p className="text-sm text-slate-500 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                {new Date().toLocaleDateString('es-ES', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            <Button asChild className="bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-600/30">
              <Link href="/loans/new">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Préstamo
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="p-8">
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoadingStats ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : dashboardStats ? (
          <>
            {/* Row 1: 5 KPI Cards */}
            <div className="grid grid-cols-5 gap-4 mb-8">
              {/* Valor de Cartera */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-blue-100 flex items-center justify-center">
                      <Wallet className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                      Activa
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Valor de Cartera</p>
                  <p className="text-xl font-bold text-slate-900">
                    {formatCompactCurrency(dashboardStats.financial.total_outstanding)}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {dashboardStats.summary.active_loans} préstamos activos
                  </p>
                </CardContent>
              </Card>

              {/* Total Desembolsado */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                      <Banknote className="h-5 w-5 text-indigo-600" />
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Total Desembolsado</p>
                  <p className="text-xl font-bold text-slate-900">
                    {formatCompactCurrency(dashboardStats.financial.total_disbursed)}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {dashboardStats.summary.total_loans} préstamos totales
                  </p>
                </CardContent>
              </Card>

              {/* Total Recaudado */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-green-100 flex items-center justify-center">
                      <DollarSign className="h-5 w-5 text-green-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                      Cobrado
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Total Recaudado</p>
                  <p className="text-xl font-bold text-slate-900">
                    {formatCompactCurrency(dashboardStats.financial.total_collected)}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {dashboardStats.summary.recent_payments_7d} pagos últimos 7d
                  </p>
                </CardContent>
              </Card>

              {/* Mora - RED */}
              <Card className="border-red-200 shadow-sm bg-red-50">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-red-100 flex items-center justify-center">
                      <AlertCircle className="h-5 w-5 text-red-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-red-600">
                      <TrendingDown className="h-3 w-3" />
                      Alerta
                    </div>
                  </div>
                  <p className="text-xs font-medium text-red-700 mb-1">En Mora</p>
                  <p className="text-xl font-bold text-red-900">
                    {dashboardStats.summary.defaulted_loans}
                  </p>
                  <p className="text-xs text-red-700 mt-1">
                    {dashboardStats.summary.overdue_schedules} cuotas vencidas
                  </p>
                </CardContent>
              </Card>

              {/* Tasa de Recuperación */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center">
                      <Target className="h-5 w-5 text-purple-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                    </div>
                  </div>
                  <p className="text-xs font-medium text-slate-500 mb-1">Tasa de Recuperación</p>
                  <p className="text-xl font-bold text-slate-900">{recoveryRate}%</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {dashboardStats.summary.paid_loans} préstamos pagados
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Row 2: Charts */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              {/* Area Chart - monthly performance */}
              <Card className="col-span-2 border-slate-200 shadow-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base font-bold text-slate-900">
                        Rendimiento Mensual
                      </CardTitle>
                      <CardDescription>Desembolsos vs Recaudación</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/loans">
                        Ver Reporte
                        <ArrowUpRight className="ml-2 h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={buildChartData(dashboardStats)}>
                      <defs>
                        <linearGradient id="gradDesembolsado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gradRecaudado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis dataKey="month" stroke="#64748B" fontSize={12} />
                      <YAxis
                        stroke="#64748B"
                        fontSize={11}
                        tickFormatter={(v) => formatCompactCurrency(v)}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #E2E8F0',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                        }}
                        formatter={(value) => [formatCompactCurrency(Number(value)), '']}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="desembolsado"
                        stroke="#3B82F6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#gradDesembolsado)"
                        name="Desembolsado"
                      />
                      <Area
                        type="monotone"
                        dataKey="recaudado"
                        stroke="#10B981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#gradRecaudado)"
                        name="Recaudado"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Portfolio quality - status distribution */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-base font-bold text-slate-900">
                    Distribución de Cartera
                  </CardTitle>
                  <CardDescription>Por estado de préstamo</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {dashboardStats.charts.status_distribution.map((item) => {
                      const total = dashboardStats.charts.status_distribution.reduce(
                        (sum, s) => sum + s.value,
                        0
                      );
                      const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
                      return (
                        <div key={item.name}>
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-sm font-medium text-slate-700">{item.name}</span>
                            <span className="text-sm font-bold text-slate-900">
                              {item.value}{' '}
                              <span className="text-xs font-normal text-slate-500">({pct}%)</span>
                            </span>
                          </div>
                          <div className="w-full bg-slate-200 rounded-full h-2">
                            <div
                              className="h-2 rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: item.color }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    {dashboardStats.charts.status_distribution.length === 0 && (
                      <p className="text-sm text-slate-500 text-center py-4">Sin datos</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Row 3: Quick Actions */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              {/* Overdue schedules */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-amber-500" />
                    <CardTitle className="text-base font-bold text-slate-900">
                      Cuotas Vencidas
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="text-4xl font-bold text-amber-600">
                      {dashboardStats.summary.overdue_schedules}
                    </div>
                    <div className="text-sm text-slate-600">cuotas pendientes de cobro</div>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    {dashboardStats.summary.defaulted_loans} préstamos en mora actualmente
                  </p>
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href="/collections">
                      Gestionar Cobros
                      <ArrowUpRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              {/* Pending loans */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-blue-500" />
                    <CardTitle className="text-base font-bold text-slate-900">
                      Pendientes de Aprobación
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 mb-4">
                    <div className="text-4xl font-bold text-blue-600">
                      {dashboardStats.summary.pending_loans}
                    </div>
                    <div className="text-sm text-slate-600">solicitudes esperando revisión</div>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    Requieren aprobación del oficial de crédito
                  </p>
                  <Button variant="outline" size="sm" className="w-full" asChild>
                    <Link href="/loans?status=pending">
                      Revisar Solicitudes
                      <ArrowUpRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              {/* Recent activity */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-green-500" />
                    <CardTitle className="text-base font-bold text-slate-900">
                      Actividad Reciente
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <Banknote className="h-4 w-4 text-blue-600" />
                        <span className="text-sm font-medium text-slate-700">Nuevos Préstamos</span>
                      </div>
                      <span className="text-lg font-bold text-blue-700">
                        {dashboardStats.summary.recent_loans_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-green-600" />
                        <span className="text-sm font-medium text-slate-700">Pagos Recibidos</span>
                      </div>
                      <span className="text-lg font-bold text-green-700">
                        {dashboardStats.summary.recent_payments_7d}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 text-center">Últimos 7 días</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Row 4: Recent Loans Table */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold text-slate-900">
                      Préstamos Recientes
                    </CardTitle>
                    <CardDescription>Últimas solicitudes y desembolsos</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/loans">
                      Ver Todos
                      <ArrowUpRight className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Cliente / Préstamo
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Monto
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                          Fecha
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentLoans.map((loan) => (
                        <tr
                          key={loan.id}
                          className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                        >
                          <td className="py-3 px-4">
                            <div>
                              <p className="text-sm font-semibold text-slate-900">
                                {loan.customer_name}
                              </p>
                              <p className="text-xs text-slate-500">{loan.loan_number}</p>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-slate-600">
                              {loan.loan_type === 'personal'
                                ? 'Personal'
                                : loan.loan_type === 'auto'
                                ? 'Auto'
                                : loan.loan_type === 'mortgage'
                                ? 'Hipoteca'
                                : loan.loan_type === 'business'
                                ? 'Negocio'
                                : loan.loan_type === 'student'
                                ? 'Estudiantil'
                                : loan.loan_type === 'payday'
                                ? 'Nómina'
                                : loan.loan_type}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm font-bold text-slate-900">
                              {formatCurrency(loan.principal_amount)}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                                loan.status === 'active'
                                  ? 'bg-green-100 text-green-700'
                                  : loan.status === 'pending'
                                  ? 'bg-amber-100 text-amber-700'
                                  : loan.status === 'defaulted'
                                  ? 'bg-red-100 text-red-700'
                                  : loan.status === 'paid'
                                  ? 'bg-blue-100 text-blue-700'
                                  : loan.status === 'approved'
                                  ? 'bg-teal-100 text-teal-700'
                                  : 'bg-slate-100 text-slate-600'
                              }`}
                            >
                              {loan.status === 'active'
                                ? 'Activo'
                                : loan.status === 'pending'
                                ? 'Pendiente'
                                : loan.status === 'defaulted'
                                ? 'Mora'
                                : loan.status === 'paid'
                                ? 'Pagado'
                                : loan.status === 'approved'
                                ? 'Aprobado'
                                : loan.status === 'rejected'
                                ? 'Rechazado'
                                : loan.status === 'written_off'
                                ? 'Castigado'
                                : loan.status}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-slate-500">
                              {formatDate(loan.created_at)}
                            </span>
                          </td>
                        </tr>
                      ))}
                      {recentLoans.length === 0 && (
                        <tr>
                          <td colSpan={5} className="py-8 text-center text-sm text-slate-500">
                            No hay préstamos registrados
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}
