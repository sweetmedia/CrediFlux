'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI } from '@/lib/api/loans';
import { CollectionContact, CollectionReminder, PaginatedResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Bell, Loader2, PhoneCall, Search, ShieldAlert, Target } from 'lucide-react';

export default function ProductividadReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [contacts, setContacts] = useState<CollectionContact[]>([]);
  const [collectorContacts, setCollectorContacts] = useState<CollectionContact[]>([]);
  const [reminders, setReminders] = useState<CollectionReminder[]>([]);
  const [collectorSearch, setCollectorSearch] = useState('');

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
      const [contactsResponse, byCollectorResponse, remindersResponse] = await Promise.all([
        collectionsAPI.getContacts({ page: 1 }),
        collectionsAPI.getContactsByCollector(),
        collectionsAPI.getReminders({ page: 1 }),
      ]);

      setContacts((contactsResponse as PaginatedResponse<CollectionContact>).results || []);
      setCollectorContacts(byCollectorResponse || []);
      setReminders((remindersResponse as PaginatedResponse<CollectionReminder>).results || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de productividad.');
    } finally {
      setIsLoading(false);
    }
  };

  const grouped = useMemo(() => {
    const map = new Map<string, { name: string; total: number; promises: number; escalations: number; answered: number; effectiveness: number }>();

    collectorContacts.forEach((contact) => {
      const key = contact.contacted_by || 'unknown';
      const current = map.get(key) || {
        name: contact.contacted_by_name || 'Sin asignar',
        total: 0,
        promises: 0,
        escalations: 0,
        answered: 0,
        effectiveness: 0,
      };

      current.total += 1;
      if (['promise_to_pay', 'payment_plan'].includes(contact.outcome)) current.promises += 1;
      if (contact.requires_escalation) current.escalations += 1;
      if (contact.outcome === 'answered') current.answered += 1;
      map.set(key, current);
    });

    return [...map.values()]
      .map((collector) => ({
        ...collector,
        effectiveness: collector.total > 0 ? Math.round(((collector.promises + collector.answered) / collector.total) * 100) : 0,
      }))
      .filter((collector) => collector.name.toLowerCase().includes(collectorSearch.trim().toLowerCase()))
      .sort((a, b) => b.total - a.total);
  }, [collectorContacts, collectorSearch]);

  const reminderStats = useMemo(() => {
    return {
      pending: reminders.filter((item) => item.status === 'pending').length,
      sent: reminders.filter((item) => item.status === 'sent').length,
      failed: reminders.filter((item) => item.status === 'failed').length,
    };
  }, [reminders]);

  const operationalStats = useMemo(() => {
    return {
      totalContacts: contacts.length,
      promises: contacts.filter((item) => ['promise_to_pay', 'payment_plan'].includes(item.outcome)).length,
      escalations: contacts.filter((item) => item.requires_escalation).length,
      noAnswer: contacts.filter((item) => item.outcome === 'no_answer').length,
    };
  }, [contacts]);

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Productividad de cobranza</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Primera lectura del esfuerzo operativo: contactos hechos, promesas generadas, escalaciones y soporte de recordatorios.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections')}>Volver al módulo</Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Contactos visibles</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{operationalStats.totalContacts}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Promesas generadas</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{operationalStats.promises}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Escalaciones</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{operationalStats.escalations}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Sin respuesta</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{operationalStats.noAnswer}</p></CardContent></Card>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Actividad por cobrador</CardTitle>
              <CardDescription>Si el endpoint agrupa global, aquí te deja una base inmediata para comparar trabajo visible por persona.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={collectorSearch}
                  onChange={(e) => setCollectorSearch(e.target.value)}
                  placeholder="Buscar cobrador..."
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-[#163300]"
                />
              </div>
              {grouped.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">Todavía no hay datos suficientes por cobrador.</div>
              ) : grouped.map((collector) => (
                <div key={collector.name} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{collector.name}</p>
                      <p className="mt-1 text-sm text-slate-500">Contactos visibles: {collector.total}</p>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[420px] lg:grid-cols-4">
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">Promesas: <strong>{collector.promises}</strong></div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">Respondió: <strong>{collector.answered}</strong></div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">Escaló: <strong>{collector.escalations}</strong></div>
                      <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">Efectividad: <strong>{collector.effectiveness}%</strong></div>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Soporte de recordatorios</CardTitle>
                <CardDescription>La productividad no solo es llamar; también importa cuánto respaldo automatizado hay detrás.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="text-sm font-medium text-slate-900">Pendientes</span><span className="text-lg font-semibold text-slate-900">{reminderStats.pending}</span></div>
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="text-sm font-medium text-slate-900">Enviados</span><span className="text-lg font-semibold text-slate-900">{reminderStats.sent}</span></div>
                <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="text-sm font-medium text-slate-900">Fallidos</span><span className="text-lg font-semibold text-slate-900">{reminderStats.failed}</span></div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader><CardTitle className="text-base text-[#163300]">Cómo usar esta vista</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><PhoneCall className="mt-0.5 h-4 w-4 text-[#163300]" /><p>Sirve para ver quién realmente está moviendo gestión, no solo quién tiene casos asignados.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><Target className="mt-0.5 h-4 w-4 text-[#163300]" /><p>Promesas y respuestas son mejores señales que el volumen bruto. Por eso agregué una lectura simple de efectividad.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><ShieldAlert className="mt-0.5 h-4 w-4 text-[#163300]" /><p>Si alguien genera muchas escalaciones y pocas promesas, hay fricción operativa o calidad débil de cartera.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><Bell className="mt-0.5 h-4 w-4 text-[#163300]" /><p>Recordatorios pendientes altos con poca actividad humana = cola acumulándose.</p></div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
