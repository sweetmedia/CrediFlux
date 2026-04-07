'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { paymentsAPI } from '@/lib/api/loans';
import { LoanPayment, PaginatedResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, ArrowRight, Building2, CircleDollarSign, Landmark, Loader2, Wallet } from 'lucide-react';

export default function CajaBancoReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [cashPayments, setCashPayments] = useState<LoanPayment[]>([]);
  const [bankTransfers, setBankTransfers] = useState<LoanPayment[]>([]);
  const [checks, setChecks] = useState<LoanPayment[]>([]);
  const [cards, setCards] = useState<LoanPayment[]>([]);
  const [mobile, setMobile] = useState<LoanPayment[]>([]);

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
      const [cash, transfer, check, card, mobileData] = await Promise.all([
        paymentsAPI.getPayments({ page: 1, payment_method: 'cash', status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'bank_transfer', status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'check', status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'card', status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'mobile_payment', status: 'completed' }),
      ]);

      setCashPayments((cash as PaginatedResponse<LoanPayment>).results || []);
      setBankTransfers((transfer as PaginatedResponse<LoanPayment>).results || []);
      setChecks((check as PaginatedResponse<LoanPayment>).results || []);
      setCards((card as PaginatedResponse<LoanPayment>).results || []);
      setMobile((mobileData as PaginatedResponse<LoanPayment>).results || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de caja y banco.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const methodBlocks = useMemo(() => {
    const make = (label: string, items: LoanPayment[], tone: string) => ({
      label,
      items,
      tone,
      count: items.length,
      total: items.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    });

    return [
      make('Caja · Efectivo', cashPayments, 'border-emerald-200 bg-emerald-50 text-emerald-700'),
      make('Banco · Transferencias', bankTransfers, 'border-sky-200 bg-sky-50 text-sky-700'),
      make('Banco · Cheques', checks, 'border-amber-200 bg-amber-50 text-amber-700'),
      make('Canal digital · Tarjetas', cards, 'border-violet-200 bg-violet-50 text-violet-700'),
      make('Canal digital · Pago móvil', mobile, 'border-fuchsia-200 bg-fuchsia-50 text-fuchsia-700'),
    ];
  }, [cashPayments, bankTransfers, checks, cards, mobile]);

  const cashVisible = cashPayments.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const bankVisible = [...bankTransfers, ...checks].reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const digitalVisible = [...cards, ...mobile].reduce((sum, item) => sum + Number(item.amount || 0), 0);

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Caja y banco</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Lectura inspirada en cierre de caja y reportes bancarios del legacy. Separa por cómo entró el dinero.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/payments')}>Ver operación de pagos</Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-3">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Caja visible</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{formatCurrency(cashVisible)}</p><p className="mt-1 text-sm text-slate-600">Pagos completados en efectivo</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Banco visible</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{formatCurrency(bankVisible)}</p><p className="mt-1 text-sm text-slate-600">Transferencias y cheques</p></CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-5"><p className="text-xs uppercase tracking-wide text-slate-500">Digital visible</p><p className="mt-2 text-3xl font-semibold text-[#163300]">{formatCurrency(digitalVisible)}</p><p className="mt-1 text-sm text-slate-600">Tarjetas y pagos móviles</p></CardContent></Card>
        </div>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Separación operativa por canal</CardTitle>
            <CardDescription>No pretende ser contabilidad final; es una lectura clara de por dónde está entrando el recaudo visible.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 xl:grid-cols-2">
            {methodBlocks.map((block) => (
              <div key={block.label} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className={`mb-4 rounded-2xl border p-4 ${block.tone}`}>
                  <p className="text-xs uppercase tracking-wide">{block.label}</p>
                  <p className="mt-2 text-2xl font-semibold">{block.count}</p>
                  <p className="mt-1 text-sm">{formatCurrency(block.total)}</p>
                </div>
                <div className="space-y-3">
                  {block.items.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">Sin registros visibles en este canal.</div>
                  ) : block.items.slice(0, 5).map((payment) => (
                    <div key={payment.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-medium text-slate-900">{payment.customer_name}</p>
                          <p className="text-sm text-slate-500">{payment.payment_number} · {payment.loan_number}</p>
                        </div>
                        <p className="font-semibold text-slate-900">{formatCurrency(payment.amount)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><Wallet className="h-4 w-4 text-[#163300]" />Caja</div>Sirve para leer entradas en efectivo y preparar una futura versión formal de cierre diario.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><Building2 className="h-4 w-4 text-[#163300]" />Banco</div>Sirve como base para futuros reportes de depósitos, cheques y conciliación por referencia.</CardContent></Card>
          <Card className="border-[#d7e2db] shadow-none"><CardContent className="p-4 text-sm text-slate-700"><div className="mb-2 flex items-center gap-2 font-medium text-slate-900"><CircleDollarSign className="h-4 w-4 text-[#163300]" />Siguiente paso</div><Button variant="outline" className="mt-2 w-full justify-between bg-white" onClick={() => router.push('/collections/reports/pagos')}>Abrir pagos e ingresos <ArrowRight className="h-4 w-4" /></Button></CardContent></Card>
        </div>
      </div>
    </div>
  );
}
