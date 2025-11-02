'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI, paymentsAPI } from '@/lib/api/loans';
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
  BarChart3,
  Calendar,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { LoanStatistics, Loan, LoanPayment } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();

  const [statistics, setStatistics] = useState<LoanStatistics | null>(null);
  const [recentLoans, setRecentLoans] = useState<Loan[]>([]);
  const [recentPayments, setRecentPayments] = useState<LoanPayment[]>([]);
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

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
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

  // Mock data for executive dashboard
  const monthlyPerformance = [
    { month: 'Ene', desembolsado: 850000, recaudado: 720000, objetivo: 800000 },
    { month: 'Feb', desembolsado: 920000, recaudado: 780000, objetivo: 850000 },
    { month: 'Mar', desembolsado: 880000, recaudado: 810000, objetivo: 850000 },
    { month: 'Abr', desembolsado: 1050000, recaudado: 890000, objetivo: 900000 },
    { month: 'May', desembolsado: 980000, recaudado: 920000, objetivo: 900000 },
    { month: 'Jun', desembolsado: 1120000, recaudado: 980000, objetivo: 950000 },
  ];

  const portfolioQuality = [
    { category: 'Al día', value: 65, color: '#10B981' },
    { category: '1-30 días', value: 20, color: '#F59E0B' },
    { category: '31-60 días', value: 10, color: '#EF4444' },
    { category: '+60 días', value: 5, color: '#991B1B' },
  ];

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Executive Header */}
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
                  day: 'numeric'
                })}
              </p>
            </div>
            <Button className="bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-600/30">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Préstamo
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
        ) : statistics ? (
          <>
            {/* KPI Grid */}
            <div className="grid grid-cols-4 gap-6 mb-8">
              {/* Portfolio Value */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
                      <Wallet className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                      +12.5%
                    </div>
                  </div>
                  <p className="text-sm font-medium text-slate-600 mb-1">
                    Valor de Cartera
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {formatCompactCurrency(statistics.total_outstanding)}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    {statistics.active_loans} préstamos activos
                  </p>
                </CardContent>
              </Card>

              {/* Collections */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="h-12 w-12 rounded-xl bg-green-100 flex items-center justify-center">
                      <DollarSign className="h-6 w-6 text-green-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                      +8.3%
                    </div>
                  </div>
                  <p className="text-sm font-medium text-slate-600 mb-1">
                    Recaudación
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {formatCompactCurrency(statistics.total_collected)}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    vs mes anterior
                  </p>
                </CardContent>
              </Card>

              {/* Recovery Rate */}
              <Card className="border-slate-200 shadow-sm">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="h-12 w-12 rounded-xl bg-purple-100 flex items-center justify-center">
                      <Target className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-green-600">
                      <TrendingUp className="h-3 w-3" />
                      +2.1%
                    </div>
                  </div>
                  <p className="text-sm font-medium text-slate-600 mb-1">
                    Tasa de Recuperación
                  </p>
                  <p className="text-2xl font-bold text-slate-900">
                    {statistics.total_loans > 0
                      ? Math.round((statistics.paid_loans / statistics.total_loans) * 100)
                      : 0}%
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    {statistics.paid_loans} préstamos pagados
                  </p>
                </CardContent>
              </Card>

              {/* At Risk */}
              <Card className="border-red-200 shadow-sm bg-red-50">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="h-12 w-12 rounded-xl bg-red-100 flex items-center justify-center">
                      <AlertCircle className="h-6 w-6 text-red-600" />
                    </div>
                    <div className="flex items-center gap-1 text-xs font-medium text-red-600">
                      <TrendingDown className="h-3 w-3" />
                      Atención
                    </div>
                  </div>
                  <p className="text-sm font-medium text-red-900 mb-1">
                    En Riesgo
                  </p>
                  <p className="text-2xl font-bold text-red-900">
                    {statistics.defaulted_loans}
                  </p>
                  <p className="text-xs text-red-700 mt-2">
                    préstamos en mora
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-3 gap-6 mb-8">
              {/* Performance Chart */}
              <Card className="col-span-2 border-slate-200 shadow-sm">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg font-bold text-slate-900">
                        Rendimiento Mensual
                      </CardTitle>
                      <CardDescription>
                        Desembolsos vs Recaudación
                      </CardDescription>
                    </div>
                    <Button variant="outline" size="sm">
                      Ver Reporte
                      <ArrowUpRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={monthlyPerformance}>
                      <defs>
                        <linearGradient id="desembolsado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="recaudado" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis dataKey="month" stroke="#64748B" fontSize={12} />
                      <YAxis stroke="#64748B" fontSize={12} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'white',
                          border: '1px solid #E2E8F0',
                          borderRadius: '8px',
                          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                        }}
                        formatter={(value) => formatCompactCurrency(Number(value))}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="desembolsado"
                        stroke="#3B82F6"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#desembolsado)"
                        name="Desembolsado"
                      />
                      <Area
                        type="monotone"
                        dataKey="recaudado"
                        stroke="#10B981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#recaudado)"
                        name="Recaudado"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Portfolio Quality */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-lg font-bold text-slate-900">
                    Calidad de Cartera
                  </CardTitle>
                  <CardDescription>
                    Distribución por antigüedad
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {portfolioQuality.map((item) => (
                      <div key={item.category}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-slate-700">
                            {item.category}
                          </span>
                          <span className="text-sm font-bold text-slate-900">
                            {item.value}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-2">
                          <div
                            className="h-2 rounded-full transition-all duration-500"
                            style={{
                              width: `${item.value}%`,
                              backgroundColor: item.color
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity Table */}
            <Card className="border-slate-200 shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg font-bold text-slate-900">
                      Actividad Reciente
                    </CardTitle>
                    <CardDescription>
                      Últimas transacciones y préstamos
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/loans">Ver Préstamos</Link>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                      <Link href="/payments">Ver Pagos</Link>
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Cliente
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Monto
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Fecha
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentLoans.slice(0, 5).map((loan) => (
                        <tr key={loan.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                          <td className="py-3 px-4">
                            <div>
                              <p className="text-sm font-medium text-slate-900">
                                {loan.customer_name}
                              </p>
                              <p className="text-xs text-slate-500">
                                {loan.loan_number}
                              </p>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-slate-600 capitalize">
                              {loan.loan_type}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm font-semibold text-slate-900">
                              {formatCurrency(loan.principal_amount)}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className={`
                              inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                              ${loan.status === 'active' ? 'bg-green-100 text-green-700' :
                                loan.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                loan.status === 'defaulted' ? 'bg-red-100 text-red-700' :
                                'bg-slate-100 text-slate-700'}
                            `}>
                              {loan.status === 'active' ? 'Activo' :
                               loan.status === 'pending' ? 'Pendiente' :
                               loan.status === 'defaulted' ? 'Mora' : loan.status}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-slate-600">
                              {formatDate(loan.created_at)}
                            </span>
                          </td>
                        </tr>
                      ))}
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
