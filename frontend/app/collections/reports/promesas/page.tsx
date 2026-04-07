'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI } from '@/lib/api/loans';
import { CollectionContact, PaginatedResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, ArrowRight, CalendarClock, CheckCircle2, Loader2, TriangleAlert } from 'lucide-react';

export default function PromesasReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [contacts, setContacts] = useState<CollectionContact[]>([]);
  const [promisesToday, setPromisesToday] = useState<CollectionContact[]>([]);
  const [brokenPromises, setBrokenPromises] = useState<CollectionContact[]>([]);

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
      const [contactsResponse, dueTodayResponse, brokenResponse] = await Promise.all([
        collectionsAPI.getContacts({ page: 1 }),
        collectionsAPI.getPromisesDueToday(),
        collectionsAPI.getBrokenPromises(),
      ]);

      setContacts((contactsResponse as PaginatedResponse<CollectionContact>).results || []);
      setPromisesToday(dueTodayResponse || []);
      setBrokenPromises(brokenResponse || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de promesas.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount?: number) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const promiseStats = useMemo(() => {
    const promiseContacts = contacts.filter((contact) => ['promise_to_pay', 'payment_plan'].includes(contact.outcome));
    const kept = promiseContacts.filter((contact) => contact.promise_kept === true);
    const pending = promiseContacts.filter((contact) => contact.promise_kept === null || contact.promise_kept === undefined);
    const broken = promiseContacts.filter((contact) => contact.promise_kept === false);

    return {
      promiseContacts,
      kept,
      pending,
      broken,
      keptAmount: kept.reduce((sum, item) => sum + Number(item.promise_amount || 0), 0),
      pendingAmount: pending.reduce((sum, item) => sum + Number(item.promise_amount || 0), 0),
      brokenAmount: broken.reduce((sum, item) => sum + Number(item.promise_amount || 0), 0),
    };
  }, [contacts]);

  const visibleRows = useMemo(() => {
    return [...promiseStats.promiseContacts]
      .sort((a, b) => {
        const aDate = a.promise_date ? new Date(a.promise_date).getTime() : 0;
        const bDate = b.promise_date ? new Date(b.promise_date).getTime() : 0;
        return bDate - aDate;
      })
      .slice(0, 20);
  }, [promiseStats.promiseContacts]);

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Promesas de pago</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Una de las vistas más importantes de cobranza: qué se prometió, qué sigue vivo y qué ya se rompió.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/contacts')}>Abrir bitácora</Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Promesas visibles</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{promiseStats.promiseContacts.length}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Pendientes</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{promiseStats.pending.length}</p><p className="mt-1 text-sm text-slate-500">{formatCurrency(promiseStats.pendingAmount)}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Cumplidas</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{promiseStats.kept.length}</p><p className="mt-1 text-sm text-slate-500">{formatCurrency(promiseStats.keptAmount)}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Incumplidas</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{promiseStats.broken.length}</p><p className="mt-1 text-sm text-slate-500">{formatCurrency(promiseStats.brokenAmount)}</p></CardContent></Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Promesas registradas</CardTitle>
              <CardDescription>Ordenadas por fecha prometida más reciente.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {visibleRows.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">Todavía no hay promesas visibles.</div>
              ) : visibleRows.map((item) => {
                const tone = item.promise_kept === true
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : item.promise_kept === false
                  ? 'border-red-200 bg-red-50 text-red-700'
                  : 'border-amber-200 bg-amber-50 text-amber-700';

                return (
                  <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <p className="font-medium text-slate-900">{item.customer_name}</p>
                        <p className="text-sm text-slate-500">{item.loan_number} · {item.outcome_display}</p>
                        <p className="mt-2 text-sm text-slate-600">Fecha prometida: <strong className="text-slate-900">{item.promise_date ? new Date(item.promise_date).toLocaleDateString('es-DO') : 'Sin fecha'}</strong></p>
                        <p className="mt-1 text-sm text-slate-600">Monto prometido: <strong className="text-slate-900">{formatCurrency(item.promise_amount)}</strong></p>
                      </div>
                      <div className={`rounded-full border px-3 py-1 text-xs font-medium ${tone}`}>
                        {item.promise_kept === true ? 'Cumplida' : item.promise_kept === false ? 'Incumplida' : 'Pendiente'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Promesas para hoy</CardTitle>
                <CardDescription>Compromisos que deberían convertirse en pago o en seguimiento inmediato.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {promisesToday.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No hay promesas venciendo hoy.</div>
                ) : promisesToday.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                    <p className="font-medium text-slate-900">{item.customer_name}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.loan_number} · {formatCurrency(item.promise_amount)}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Promesas incumplidas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {brokenPromises.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No hay promesas incumplidas visibles.</div>
                ) : brokenPromises.slice(0, 8).map((item) => (
                  <div key={item.id} className="rounded-2xl border border-red-200 bg-red-50 p-4">
                    <p className="font-medium text-slate-900">{item.customer_name}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.loan_number} · {formatCurrency(item.promise_amount)}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><CalendarClock className="h-4 w-4 text-[#163300]" />Uso real</div>Este reporte le dice al cobrador qué compromisos debe perseguir hoy, no mañana.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><CheckCircle2 className="h-4 w-4 text-[#163300]" />Métrica clave</div>La relación cumplidas vs incumplidas te da una lectura brutal de calidad de cartera y calidad de gestión.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><TriangleAlert className="h-4 w-4 text-[#163300]" />Siguiente salida</div><Button variant="outline" className="mt-2 w-full justify-between bg-white" onClick={() => router.push('/collections/reports/productividad')}>Abrir productividad <ArrowRight className="h-4 w-4" /></Button></CardContent></Card>
        </div>
      </div>
    </div>
  );
}
