'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { schedulesAPI } from '@/lib/api/loans';
import { LoanSchedule } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, ArrowLeft, FileText, ArrowRight } from 'lucide-react';

export default function VencimientosReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
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
      const data = await schedulesAPI.getOverdueSchedules();
      setOverdueSchedules(data || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de vencimientos.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const grouped = useMemo(() => {
    const groups = [
      { key: '0-7', label: 'Reciente · 0 a 7 días', color: 'border-emerald-200 bg-emerald-50 text-emerald-700', items: overdueSchedules.filter((s) => s.days_overdue <= 7) },
      { key: '8-30', label: 'Urgente · 8 a 30 días', color: 'border-amber-200 bg-amber-50 text-amber-700', items: overdueSchedules.filter((s) => s.days_overdue >= 8 && s.days_overdue <= 30) },
      { key: '31-60', label: 'Crítico · 31 a 60 días', color: 'border-orange-200 bg-orange-50 text-orange-700', items: overdueSchedules.filter((s) => s.days_overdue >= 31 && s.days_overdue <= 60) },
      { key: '60+', label: 'Severo · +60 días', color: 'border-red-200 bg-red-50 text-red-700', items: overdueSchedules.filter((s) => s.days_overdue > 60) },
    ];

    return groups.map((group) => ({
      ...group,
      count: group.items.length,
      balance: group.items.reduce((sum, item) => sum + Number(item.balance || 0), 0),
      items: [...group.items].sort((a, b) => b.days_overdue - a.days_overdue).slice(0, 12),
    }));
  }, [overdueSchedules]);

  if (authLoading || isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]"><Loader2 className="h-8 w-8 animate-spin text-[#163300]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] px-4 py-6 md:px-6 md:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <Link href="/collections/reports" className="mb-3 inline-flex items-center text-sm text-slate-500 hover:text-slate-900">
            <ArrowLeft className="mr-1 h-4 w-4" /> Volver a reportes
          </Link>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Reporte de vencimientos</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Vista envejecida de mora inspirada en repvenci. Sirve para priorizar la gestión por gravedad.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="bg-white" onClick={() => window.print()}><FileText className="mr-2 h-4 w-4" />Imprimir</Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/schedules/overdue')}>Abrir cola operativa</Button>
            </div>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {grouped.map((group) => (
            <Card key={group.key} className="border-[#d7e2db] shadow-none">
              <CardContent className="p-4">
                <div className={`rounded-2xl border p-4 ${group.color}`}>
                  <p className="text-xs uppercase tracking-wide">{group.label}</p>
                  <p className="mt-2 text-2xl font-semibold">{group.count}</p>
                  <p className="mt-1 text-sm">{formatCurrency(group.balance)}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Detalle por tramo</CardTitle>
            <CardDescription>Se muestra una selección priorizada por días de atraso dentro de cada grupo.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 xl:grid-cols-2">
            {grouped.map((group) => (
              <div key={group.key} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-900">{group.label}</p>
                    <p className="text-sm text-slate-500">{group.count} cuota(s) · {formatCurrency(group.balance)}</p>
                  </div>
                </div>
                <div className="space-y-3">
                  {group.items.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">Sin cuotas en este tramo.</div>
                  ) : group.items.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-900">{item.customer_name}</p>
                          <p className="text-sm text-slate-500">{item.loan_number} · cuota #{item.installment_number}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold text-slate-900">{formatCurrency(item.balance)}</p>
                          <p className="text-xs text-slate-500">{item.days_overdue} día(s)</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader><CardTitle className="text-base text-[#163300]">Cómo usar este reporte</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-700">
              <p>1. Prioriza primero el tramo de 31+ días si el saldo también es alto.</p>
              <p>2. Usa 0-7 días como prevención: llamada o WhatsApp antes de que se enfríe el caso.</p>
              <p>3. Cruza este reporte con contactos y promesas para saber dónde insistir o escalar.</p>
            </CardContent>
          </Card>
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader><CardTitle className="text-base text-[#163300]">Rutas relacionadas</CardTitle></CardHeader>
            <CardContent className="grid gap-3">
              <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/contacts')}>Ver bitácora de contacto <ArrowRight className="h-4 w-4" /></Button>
              <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reminders')}>Ver recordatorios <ArrowRight className="h-4 w-4" /></Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
