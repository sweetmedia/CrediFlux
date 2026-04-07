'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { schedulesAPI } from '@/lib/api/loans';
import { LoanSchedule } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, ArrowLeft, CalendarRange, ArrowRight } from 'lucide-react';

export default function CuotasReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [pendingSchedules, setPendingSchedules] = useState<LoanSchedule[]>([]);
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
      const [pendingData, overdueData] = await Promise.all([
        schedulesAPI.getSchedules({ page: 1, status: 'pending' }),
        schedulesAPI.getOverdueSchedules(),
      ]);
      setPendingSchedules(pendingData.results || []);
      setOverdueSchedules(overdueData || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de cuotas.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const formatDate = (value?: string) => {
    if (!value) return 'N/A';
    return new Date(value).toLocaleDateString('es-DO', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const metrics = useMemo(() => {
    const upcoming = [...pendingSchedules]
      .sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime())
      .slice(0, 12);
    const overdue = [...overdueSchedules]
      .sort((a, b) => b.days_overdue - a.days_overdue)
      .slice(0, 12);

    return {
      pendingCount: pendingSchedules.length,
      pendingBalance: pendingSchedules.reduce((sum, item) => sum + Number(item.balance || item.total_amount || 0), 0),
      overdueCount: overdueSchedules.length,
      overdueBalance: overdueSchedules.reduce((sum, item) => sum + Number(item.balance || 0), 0),
      upcoming,
      overdue,
    };
  }, [pendingSchedules, overdueSchedules]);

  if (authLoading || isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]"><Loader2 className="h-8 w-8 animate-spin text-[#163300]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] px-4 py-6 md:px-6 md:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <Link href="/collections/reports" className="mb-3 inline-flex items-center text-sm text-slate-500 hover:text-slate-900"><ArrowLeft className="mr-1 h-4 w-4" />Volver a reportes</Link>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Reporte de cuotas</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Lectura rápida de cuotas pendientes y vencidas, útil para balance por préstamo y control operativo.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/reports/estado-cuenta')}>Ir a estados de cuenta</Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border-[#d7e2db] shadow-none">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-wide text-slate-500">Cuotas pendientes</p>
              <p className="mt-2 text-3xl font-semibold text-[#163300]">{metrics.pendingCount}</p>
              <p className="mt-1 text-sm text-slate-600">Balance proyectado: {formatCurrency(metrics.pendingBalance)}</p>
            </CardContent>
          </Card>
          <Card className="border-[#d7e2db] shadow-none">
            <CardContent className="p-5">
              <p className="text-xs uppercase tracking-wide text-slate-500">Cuotas vencidas</p>
              <p className="mt-2 text-3xl font-semibold text-[#163300]">{metrics.overdueCount}</p>
              <p className="mt-1 text-sm text-slate-600">Balance vencido: {formatCurrency(metrics.overdueBalance)}</p>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Próximas cuotas</CardTitle>
              <CardDescription>Base de seguimiento preventivo antes de caer en mora.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {metrics.upcoming.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No hay cuotas pendientes disponibles.</div>
              ) : metrics.upcoming.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-slate-900">{item.customer_name}</p>
                      <p className="text-sm text-slate-500">{item.loan_number} · cuota #{item.installment_number}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-900">{formatCurrency(item.total_amount)}</p>
                      <p className="text-xs text-slate-500">vence {formatDate(item.due_date)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Cuotas vencidas críticas</CardTitle>
              <CardDescription>Lo que más rápido debe convertirse en gestión o pago.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {metrics.overdue.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No hay cuotas vencidas.</div>
              ) : metrics.overdue.map((item) => (
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
        </div>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Siguiente paso natural</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700"><CalendarRange className="mb-2 h-4 w-4 text-[#163300]" />Usa próximas cuotas para recordatorios preventivos y promesas antes del vencimiento.</div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">Combina cuotas vencidas con el reporte de vencimientos para priorizar por gravedad.</div>
            <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reports/vencimientos')}>Abrir vencimientos <ArrowRight className="h-4 w-4" /></Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
