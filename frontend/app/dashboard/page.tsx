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
import { StatusBadge } from '@/components/ui/status-badge';
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
    return `RD$ ${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatCompactCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `RD$ ${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `RD$ ${(amount / 1000).toFixed(1)}K`;
    }
    return formatCurrency(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
    });
  };

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
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
      </div>
    );
  }

  const recoveryRate = dashboardStats
    ? dashboardStats.summary.total_loans > 0
      ? Math.round((dashboardStats.summary.paid_loans / dashboardStats.summary.total_loans) * 100)
      : 0
    : 0;

  const getLoanTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      personal: 'Personal', auto: 'Auto', mortgage: 'Hipoteca',
      business: 'Negocio', student: 'Estudiantil', payday: 'Nómina',
    };
    return labels[type] ?? type;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Page header */}
      <div className="bg-card border-b border-border">
        <div className="px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-foreground">Dashboard Ejecutivo</h1>
              <p className="text-sm text-muted-foreground mt-0.5 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                {new Date().toLocaleDateString('es-ES', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            <Button asChild size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-md shadow-none">
              <Link href="/loans/new">
                <Plus className="mr-1.5 h-3.5 w-3.5" />
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
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-7 w-7 animate-spin text-primary" />
          </div>
        ) : dashboardStats ? (
          <>
            {/* KPI Row */}
            <div className="grid grid-cols-5 gap-4 mb-6">
              {/* Cartera Activa */}
              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <p className="text-xs font-medium text-muted-foreground mb-3">Cartera Activa</p>
                  <p className="text-2xl font-semibold text-foreground leading-none mb-2">
                    {formatCompactCurrency(dashboardStats.financial.total_outstanding)}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-green-600">
                    <TrendingUp className="h-3 w-3" />
                    <span>{dashboardStats.summary.active_loans} activos</span>
                  </div>
                </CardContent>
              </Card>

              {/* Desembolsado */}
              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <p className="text-xs font-medium text-muted-foreground mb-3">Total Desembolsado</p>
                  <p className="text-2xl font-semibold text-foreground leading-none mb-2">
                    {formatCompactCurrency(dashboardStats.financial.total_disbursed)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {dashboardStats.summary.total_loans} préstamos totales
                  </p>
                </CardContent>
              </Card>

              {/* Recaudado */}
              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <p className="text-xs font-medium text-muted-foreground mb-3">Total Recaudado</p>
                  <p className="text-2xl font-semibold text-foreground leading-none mb-2">
                    {formatCompactCurrency(dashboardStats.financial.total_collected)}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-green-600">
                    <TrendingUp className="h-3 w-3" />
                    <span>{dashboardStats.summary.recent_payments_7d} pagos (7d)</span>
                  </div>
                </CardContent>
              </Card>

              {/* Mora */}
              <Card className="border-red-200 shadow-none bg-red-50/50">
                <CardContent className="p-5">
                  <p className="text-xs font-medium text-red-600/80 mb-3">En Mora</p>
                  <p className="text-2xl font-semibold text-red-700 leading-none mb-2">
                    {dashboardStats.summary.defaulted_loans}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-red-500">
                    <AlertCircle className="h-3 w-3" />
                    <span>{dashboardStats.summary.overdue_schedules} cuotas vencidas</span>
                  </div>
                </CardContent>
              </Card>

              {/* Tasa de Recuperación */}
              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <p className="text-xs font-medium text-muted-foreground mb-3">Tasa de Recuperación</p>
                  <p className="text-2xl font-semibold text-foreground leading-none mb-2">{recoveryRate}%</p>
                  <p className="text-xs text-muted-foreground">
                    {dashboardStats.summary.paid_loans} préstamos pagados
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-3 gap-5 mb-6">
              {/* Area Chart */}
              <Card className="col-span-2 border-border shadow-none">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm font-semibold text-foreground">Rendimiento Mensual</CardTitle>
                      <CardDescription className="text-xs">Desembolsos vs Recaudación</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" asChild className="h-7 text-xs border-border shadow-none">
                      <Link href="/loans">
                        Ver Reporte
                        <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                      </Link>
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={240}>
                    <AreaChart data={buildChartData(dashboardStats)} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="gradDesembolsado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#163300" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#163300" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="gradRecaudado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#30B130" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#30B130" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ee" vertical={false} />
                      <XAxis dataKey="month" stroke="#697386" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis
                        stroke="#697386"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => formatCompactCurrency(v)}
                        width={70}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #e3e8ee',
                          borderRadius: '6px',
                          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                          fontSize: 12,
                        }}
                        formatter={(value) => [formatCompactCurrency(Number(value)), '']}
                      />
                      <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                      <Area
                        type="monotone"
                        dataKey="desembolsado"
                        stroke="#163300"
                        strokeWidth={1.5}
                        fillOpacity={1}
                        fill="url(#gradDesembolsado)"
                        name="Desembolsado"
                        dot={false}
                      />
                      <Area
                        type="monotone"
                        dataKey="recaudado"
                        stroke="#30B130"
                        strokeWidth={1.5}
                        fillOpacity={1}
                        fill="url(#gradRecaudado)"
                        name="Recaudado"
                        dot={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Portfolio Distribution */}
              <Card className="border-border shadow-none">
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-semibold text-foreground">Distribución de Cartera</CardTitle>
                  <CardDescription className="text-xs">Por estado de préstamo</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3.5">
                    {dashboardStats.charts.status_distribution.map((item) => {
                      const total = dashboardStats.charts.status_distribution.reduce(
                        (sum, s) => sum + s.value, 0
                      );
                      const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
                      return (
                        <div key={item.name}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-foreground">{item.name}</span>
                            <span className="text-xs font-semibold text-foreground">
                              {item.value} <span className="font-normal text-muted-foreground">({pct}%)</span>
                            </span>
                          </div>
                          <div className="w-full bg-secondary rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${pct}%`, backgroundColor: item.color }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    {dashboardStats.charts.status_distribution.length === 0 && (
                      <p className="text-xs text-muted-foreground text-center py-4">Sin datos</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-3 gap-5 mb-6">
              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="h-4 w-4 text-amber-500" />
                    <p className="text-sm font-semibold text-foreground">Cuotas Vencidas</p>
                  </div>
                  <p className="text-3xl font-semibold text-amber-600 mb-1">
                    {dashboardStats.summary.overdue_schedules}
                  </p>
                  <p className="text-xs text-muted-foreground mb-4">
                    {dashboardStats.summary.defaulted_loans} préstamos en mora
                  </p>
                  <Button variant="outline" size="sm" className="w-full text-xs h-8 border-border shadow-none" asChild>
                    <Link href="/collections">
                      Gestionar Cobros
                      <ArrowUpRight className="ml-1.5 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    <p className="text-sm font-semibold text-foreground">Pendientes de Aprobación</p>
                  </div>
                  <p className="text-3xl font-semibold text-primary mb-1">
                    {dashboardStats.summary.pending_loans}
                  </p>
                  <p className="text-xs text-muted-foreground mb-4">
                    Solicitudes esperando revisión
                  </p>
                  <Button variant="outline" size="sm" className="w-full text-xs h-8 border-border shadow-none" asChild>
                    <Link href="/loans?status=pending">
                      Revisar Solicitudes
                      <ArrowUpRight className="ml-1.5 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-border shadow-none">
                <CardContent className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity className="h-4 w-4 text-green-500" />
                    <p className="text-sm font-semibold text-foreground">Actividad Reciente</p>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between py-2 px-3 bg-[#e8eddf] rounded-md">
                      <div className="flex items-center gap-2">
                        <Banknote className="h-3.5 w-3.5 text-[#163300]" />
                        <span className="text-xs text-foreground">Nuevos Préstamos</span>
                      </div>
                      <span className="text-sm font-semibold text-[#163300]">
                        {dashboardStats.summary.recent_loans_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-2 px-3 bg-green-50 rounded-md">
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-3.5 w-3.5 text-green-500" />
                        <span className="text-xs text-foreground">Pagos Recibidos</span>
                      </div>
                      <span className="text-sm font-semibold text-green-700">
                        {dashboardStats.summary.recent_payments_7d}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground text-center">Últimos 7 días</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Loans Table */}
            <Card className="border-border shadow-none">
              <CardHeader className="pb-0">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold text-foreground">Préstamos Recientes</CardTitle>
                    <CardDescription className="text-xs">Últimas solicitudes y desembolsos</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" asChild className="h-7 text-xs border-border shadow-none">
                    <Link href="/loans">
                      Ver Todos
                      <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="px-0 pb-0">
                <table className="w-full">
                  <thead>
                    <tr className="border-y border-border">
                      <th className="text-left py-2.5 px-6 text-xs font-medium text-muted-foreground">Cliente / Préstamo</th>
                      <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Tipo</th>
                      <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Monto</th>
                      <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Estado</th>
                      <th className="text-left py-2.5 px-4 text-xs font-medium text-muted-foreground">Fecha</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentLoans.map((loan) => (
                      <tr
                        key={loan.id}
                        className="border-b border-border last:border-0 hover:bg-muted/40 transition-colors cursor-pointer"
                        onClick={() => router.push(`/loans/${loan.id}`)}
                      >
                        <td className="py-3 px-6">
                          <p className="text-sm font-medium text-foreground">{loan.customer_name}</p>
                          <p className="text-xs text-muted-foreground">{loan.loan_number}</p>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-sm text-muted-foreground">{getLoanTypeLabel(loan.loan_type)}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-sm font-medium text-foreground">
                            {formatCurrency(loan.principal_amount)}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={loan.status} />
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-sm text-muted-foreground">{formatDate(loan.created_at)}</span>
                        </td>
                      </tr>
                    ))}
                    {recentLoans.length === 0 && (
                      <tr>
                        <td colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                          No hay préstamos registrados
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </div>
  );
}
