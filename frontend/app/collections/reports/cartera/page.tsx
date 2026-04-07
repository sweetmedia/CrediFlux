'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI, schedulesAPI } from '@/lib/api/loans';
import { Loan, LoanSchedule } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, ArrowLeft, ArrowRight, Wallet, TriangleAlert, BadgeDollarSign, FileText } from 'lucide-react';

interface LoanStats {
  total_loans: number;
  active_loans: number;
  overdue_loans: number;
  defaulted_loans: number;
  total_outstanding: number;
  total_collected: number;
}

export default function CarteraReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<LoanStats | null>(null);
  const [activeLoans, setActiveLoans] = useState<Loan[]>([]);
  const [overdueSchedules, setOverdueSchedules] = useState<LoanSchedule[]>([]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadData();
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError('');
      const [statsData, loansData, overdueData] = await Promise.all([
        loansAPI.getStatistics(),
        loansAPI.getLoans({ page: 1, status: 'active' }),
        schedulesAPI.getOverdueSchedules(),
      ]);
      setStats(statsData as LoanStats);
      setActiveLoans(loansData.results || []);
      setOverdueSchedules(overdueData || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de cartera.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const metrics = useMemo(() => {
    const overdueExposure = overdueSchedules.reduce((sum, item) => sum + Number(item.balance || 0), 0);
    const lateFees = overdueSchedules.reduce((sum, item) => {
      const due = Number(item.late_fee_amount || 0) - Number(item.late_fee_paid || 0);
      return sum + Math.max(due, 0);
    }, 0);
    const buckets = {
      recien: overdueSchedules.filter((s) => s.days_overdue <= 7),
      alerta: overdueSchedules.filter((s) => s.days_overdue >= 8 && s.days_overdue <= 30),
      critica: overdueSchedules.filter((s) => s.days_overdue >= 31 && s.days_overdue <= 60),
      severa: overdueSchedules.filter((s) => s.days_overdue > 60),
    };

    return {
      overdueExposure,
      lateFees,
      buckets: [
        { label: '0-7 días', count: buckets.recien.length, balance: buckets.recien.reduce((s, i) => s + Number(i.balance || 0), 0), tone: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
        { label: '8-30 días', count: buckets.alerta.length, balance: buckets.alerta.reduce((s, i) => s + Number(i.balance || 0), 0), tone: 'text-amber-700 bg-amber-50 border-amber-200' },
        { label: '31-60 días', count: buckets.critica.length, balance: buckets.critica.reduce((s, i) => s + Number(i.balance || 0), 0), tone: 'text-orange-700 bg-orange-50 border-orange-200' },
        { label: '+60 días', count: buckets.severa.length, balance: buckets.severa.reduce((s, i) => s + Number(i.balance || 0), 0), tone: 'text-red-700 bg-red-50 border-red-200' },
      ],
      topExposure: [...activeLoans]
        .sort((a, b) => Number(b.outstanding_balance || 0) - Number(a.outstanding_balance || 0))
        .slice(0, 8),
      topOverdue: [...overdueSchedules]
        .sort((a, b) => Number(b.balance || 0) - Number(a.balance || 0))
        .slice(0, 8),
    };
  }, [activeLoans, overdueSchedules]);

  if (authLoading || isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]"><Loader2 className="h-8 w-8 animate-spin text-[#163300]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] px-4 py-6 md:px-6 md:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <Link href="/collections/reports" className="mb-3 inline-flex items-center text-sm text-slate-500 hover:text-slate-900">
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a reportes
          </Link>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Reporte de cartera y cobros</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Versión operativa inspirada en PRE_REPCOB y PRE_CAR_COB. Resume exposición, atraso y casos prioritarios.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="bg-white" onClick={() => window.print()}>
                <FileText className="mr-2 h-4 w-4" /> Imprimir
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/schedules/overdue')}>
                Ver morosidad
              </Button>
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="grid gap-4 lg:grid-cols-4">
                <div>
                  <p className="text-sm text-white/70">Balance pendiente</p>
                  <p className="mt-2 text-3xl font-semibold">{formatCurrency(stats?.total_outstanding)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Exposición vencida</p>
                  <p className="mt-2 text-2xl font-semibold">{formatCurrency(metrics.overdueExposure)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Mora acumulada</p>
                  <p className="mt-2 text-2xl font-semibold">{formatCurrency(metrics.lateFees)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Préstamos activos / morosos</p>
                  <p className="mt-2 text-2xl font-semibold">{stats?.active_loans || 0} / {stats?.overdue_loans || 0}</p>
                </div>
              </div>
            </div>
            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              {metrics.buckets.map((bucket) => (
                <div key={bucket.label} className={`rounded-2xl border p-4 ${bucket.tone}`}>
                  <p className="text-xs uppercase tracking-wide">{bucket.label}</p>
                  <p className="mt-2 text-2xl font-semibold">{bucket.count}</p>
                  <p className="mt-1 text-sm">{formatCurrency(bucket.balance)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Préstamos con mayor exposición</CardTitle>
              <CardDescription>Base para seguimiento gerencial de cartera activa.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {metrics.topExposure.map((loan) => (
                <div key={loan.id} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4">
                  <div>
                    <p className="font-medium text-slate-900">{loan.customer_name}</p>
                    <p className="text-sm text-slate-500">{loan.loan_number}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-900">{formatCurrency(loan.outstanding_balance)}</p>
                    <Button variant="outline" className="mt-2 h-8 bg-white" onClick={() => router.push(`/loans/${loan.id}`)}>Ver préstamo</Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Casos vencidos prioritarios</CardTitle>
                <CardDescription>Los atrasos de mayor saldo para salir primero.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {metrics.topOverdue.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-slate-900">{item.customer_name}</p>
                        <p className="text-sm text-slate-500">{item.loan_number} · cuota #{item.installment_number}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-slate-900">{formatCurrency(item.balance)}</p>
                        <p className="text-xs text-red-600">{item.days_overdue} días</p>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Siguiente salida útil</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><Wallet className="mt-0.5 h-4 w-4 text-[#163300]" /><p>Usa este reporte para lectura ejecutiva de cartera total.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><TriangleAlert className="mt-0.5 h-4 w-4 text-[#ff7503]" /><p>Si necesitas envejecimiento detallado por cuota, baja al reporte de vencimientos.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><BadgeDollarSign className="mt-0.5 h-4 w-4 text-emerald-600" /><p>Para soporte al cliente o impresión individual, usa estado de cuenta por préstamo.</p></div>
                <Button variant="outline" className="w-full justify-between bg-white" onClick={() => router.push('/collections/reports/vencimientos')}>Abrir reporte de vencimientos <ArrowRight className="h-4 w-4" /></Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
