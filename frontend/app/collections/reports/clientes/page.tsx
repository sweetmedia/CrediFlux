'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { customersAPI } from '@/lib/api/customers';
import { collectionsAPI } from '@/lib/api/loans';
import { Customer, CollectionContact, PaginatedResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, ArrowRight, Loader2, Search, ShieldAlert, Users, Wallet } from 'lucide-react';

export default function ClientesReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [contacts, setContacts] = useState<CollectionContact[]>([]);
  const [escalated, setEscalated] = useState<CollectionContact[]>([]);

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
      const [customersResponse, contactsResponse, escalatedResponse] = await Promise.all([
        customersAPI.getCustomers({ page: 1, page_size: 100 }),
        collectionsAPI.getContacts({ page: 1 }),
        collectionsAPI.getRequiringEscalation(),
      ]);

      setCustomers((customersResponse as PaginatedResponse<Customer>).results || []);
      setContacts((contactsResponse as PaginatedResponse<CollectionContact>).results || []);
      setEscalated(escalatedResponse || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de clientes.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const filteredCustomers = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return customers;
    return customers.filter((customer) =>
      customer.full_name.toLowerCase().includes(term) ||
      customer.customer_id.toLowerCase().includes(term) ||
      customer.id_number.toLowerCase().includes(term)
    );
  }, [customers, search]);

  const customerRows = useMemo(() => {
    return filteredCustomers
      .map((customer) => {
        const relatedContacts = contacts.filter((contact) => contact.customer === customer.id);
        const lastContact = [...relatedContacts].sort(
          (a, b) => new Date(b.contact_date).getTime() - new Date(a.contact_date).getTime()
        )[0];
        const hasEscalation = escalated.some((contact) => contact.customer === customer.id);

        return {
          customer,
          relatedContacts,
          lastContact,
          hasEscalation,
        };
      })
      .sort((a, b) => {
        const aPriority = a.hasEscalation ? 1 : 0;
        const bPriority = b.hasEscalation ? 1 : 0;
        if (aPriority !== bPriority) return bPriority - aPriority;
        return b.customer.active_loans - a.customer.active_loans;
      })
      .slice(0, 20);
  }, [filteredCustomers, contacts, escalated]);

  const summary = useMemo(() => {
    const withLoans = customers.filter((customer) => customer.total_loans > 0).length;
    const activePortfolioCustomers = customers.filter((customer) => customer.active_loans > 0).length;
    const blacklisted = customers.filter((customer) => customer.status === 'blacklisted').length;

    return {
      withLoans,
      activePortfolioCustomers,
      blacklisted,
    };
  }, [customers]);

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Clientes y seguimiento</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Lectura operativa inspirada en reportes de clientes del legacy, aterrizada a cartera, actividad y señales de riesgo.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/customers')}>Abrir clientes</Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Total clientes</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{customers.length}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Con préstamos</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{summary.withLoans}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Con cartera activa</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{summary.activePortfolioCustomers}</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Escalados visibles</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{escalated.length}</p></CardContent></Card>
        </div>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Buscar cliente</CardTitle>
            <CardDescription>Filtra por nombre, código o cédula para enfocar la revisión.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar cliente o cédula..."
                className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-[#163300]"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Clientes priorizados</CardTitle>
            <CardDescription>Suben primero los casos escalados y luego los clientes con mayor cartera activa.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {customerRows.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">No hay clientes para mostrar con ese filtro.</div>
            ) : customerRows.map(({ customer, relatedContacts, lastContact, hasEscalation }) => (
              <div key={customer.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-[#163300]" />
                      <p className="font-medium text-slate-900">{customer.full_name}</p>
                      {hasEscalation ? <span className="rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">Escalado</span> : null}
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{customer.customer_id} · {customer.id_number}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
                      <span>Préstamos: <strong className="text-slate-900">{customer.total_loans}</strong></span>
                      <span>Activos: <strong className="text-slate-900">{customer.active_loans}</strong></span>
                      <span>Status: <strong className="text-slate-900 capitalize">{customer.status}</strong></span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
                      <span>Contactos visibles: <strong className="text-slate-900">{relatedContacts.length}</strong></span>
                      <span>Último contacto: <strong className="text-slate-900">{lastContact ? new Date(lastContact.contact_date).toLocaleDateString('es-DO') : 'Sin gestión'}</strong></span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-slate-500">Ingreso mensual</p>
                    <p className="text-lg font-semibold text-slate-900">{formatCurrency(customer.monthly_income)}</p>
                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                      <Button variant="outline" className="bg-white" onClick={() => router.push(`/customers/${customer.id}`)}>Ver cliente</Button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><Wallet className="h-4 w-4 text-[#163300]" />Lectura útil</div>Esta vista sirve para saber a quién mirar primero cuando combinas cartera, historial y señales de escalación.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><ShieldAlert className="h-4 w-4 text-[#163300]" />Post-MVP obvio</div>Más adelante conviene cruzar clientes con antigüedad de mora, score interno y tasa de promesas incumplidas.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><ArrowRight className="h-4 w-4 text-[#163300]" />Siguiente salida</div><Button variant="outline" className="mt-2 w-full justify-between bg-white" onClick={() => router.push('/collections/reports/promesas')}>Abrir promesas <ArrowRight className="h-4 w-4" /></Button></CardContent></Card>
        </div>
      </div>
    </div>
  );
}
