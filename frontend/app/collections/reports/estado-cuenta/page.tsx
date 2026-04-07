'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI } from '@/lib/api/loans';
import { Loan } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, ArrowLeft, Search, Download, ReceiptText } from 'lucide-react';

export default function EstadoCuentaReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [loans, setLoans] = useState<Loan[]>([]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) loadLoans();
  }, [isAuthenticated]);

  const loadLoans = async (query?: string) => {
    try {
      setIsLoading(true);
      setError('');
      const data = await loansAPI.getLoans({ page: 1, status: 'active', search: query || undefined });
      setLoans(data.results || []);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar la base para estados de cuenta.');
    } finally {
      setIsLoading(false);
    }
  };

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return loans;
    return loans.filter((loan) =>
      loan.customer_name.toLowerCase().includes(term) ||
      loan.loan_number.toLowerCase().includes(term) ||
      loan.customer_details?.customer_id?.toLowerCase().includes(term)
    );
  }, [loans, search]);

  const formatCurrency = (amount: number | string | undefined) =>
    new Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' }).format(Number(amount || 0));

  const handleDownload = async (loanId: string) => {
    try {
      setIsDownloading(loanId);
      await loansAPI.downloadBalanceReport(loanId);
    } catch (err) {
      console.error(err);
      setError('No se pudo descargar el balance de cuotas.');
    } finally {
      setIsDownloading(null);
    }
  };

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Estados de cuenta</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Punto de salida para generar estados de cuenta y balances de cuotas por préstamo.</p>
            </div>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/reports/cuotas')}>
              Ver reporte de cuotas
            </Button>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Buscar préstamo o cliente</CardTitle>
            <CardDescription>Usa nombre, número de préstamo o código de cliente para ubicar el estado de cuenta correcto.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por cliente, préstamo o código..."
                className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-[#163300]"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader>
            <CardTitle className="text-base text-[#163300]">Préstamos disponibles para estado de cuenta</CardTitle>
            <CardDescription>Primera versión: usa el PDF actual de balance de cuotas y enlaza al detalle completo del préstamo.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {filtered.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">No hay resultados con ese filtro.</div>
            ) : filtered.map((loan) => (
              <div key={loan.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <ReceiptText className="h-4 w-4 text-[#163300]" />
                      <p className="font-medium text-slate-900">{loan.customer_name}</p>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{loan.loan_number} · Cliente {loan.customer_details?.customer_id || 'N/A'}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-600">
                      <span>Balance: <strong className="text-slate-900">{formatCurrency(loan.outstanding_balance)}</strong></span>
                      <span>Total pagado: <strong className="text-slate-900">{formatCurrency(loan.total_paid)}</strong></span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" className="bg-white" onClick={() => router.push(`/loans/${loan.id}`)}>
                      Ver préstamo
                    </Button>
                    <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => handleDownload(loan.id)} disabled={isDownloading === loan.id}>
                      {isDownloading === loan.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                      Descargar balance
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-[#d7e2db] shadow-none">
          <CardHeader><CardTitle className="text-base text-[#163300]">Siguiente mejora lógica</CardTitle></CardHeader>
          <CardContent className="grid gap-3 text-sm text-slate-700 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">Agregar filtros por fecha de corte para que el estado de cuenta sea histórico.</div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">Convertir el balance PDF en una plantilla visual más fuerte, estilo Stripe invoice.</div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">Añadir envío directo por WhatsApp o email cuando el módulo de comunicaciones esté más maduro.</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
