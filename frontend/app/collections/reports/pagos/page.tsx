'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { paymentsAPI } from '@/lib/api/loans';
import { LoanPayment, PaginatedResponse } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, ArrowRight, CreditCard, Download, Landmark, Loader2, ReceiptText, Search, Wallet } from 'lucide-react';

export default function PagosReportPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [latestPayments, setLatestPayments] = useState<LoanPayment[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'completed' | 'pending' | 'reversed' | 'failed'>('all');
  const [paymentSearch, setPaymentSearch] = useState('');
  const [completedCount, setCompletedCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [reversedCount, setReversedCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [cashCount, setCashCount] = useState(0);
  const [transferCount, setTransferCount] = useState(0);
  const [cardCount, setCardCount] = useState(0);
  const [mobileCount, setMobileCount] = useState(0);

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
      const [latest, completed, pending, reversed, failed, cash, transfer, card, mobile] = await Promise.all([
        paymentsAPI.getPayments({ page: 1, status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, status: 'completed' }),
        paymentsAPI.getPayments({ page: 1, status: 'pending' }),
        paymentsAPI.getPayments({ page: 1, status: 'reversed' }),
        paymentsAPI.getPayments({ page: 1, status: 'failed' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'cash' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'bank_transfer' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'card' }),
        paymentsAPI.getPayments({ page: 1, payment_method: 'mobile_payment' }),
      ]);

      setLatestPayments((latest as PaginatedResponse<LoanPayment>).results || []);
      setCompletedCount((completed as PaginatedResponse<LoanPayment>).count || 0);
      setPendingCount((pending as PaginatedResponse<LoanPayment>).count || 0);
      setReversedCount((reversed as PaginatedResponse<LoanPayment>).count || 0);
      setFailedCount((failed as PaginatedResponse<LoanPayment>).count || 0);
      setCashCount((cash as PaginatedResponse<LoanPayment>).count || 0);
      setTransferCount((transfer as PaginatedResponse<LoanPayment>).count || 0);
      setCardCount((card as PaginatedResponse<LoanPayment>).count || 0);
      setMobileCount((mobile as PaginatedResponse<LoanPayment>).count || 0);
    } catch (err) {
      console.error(err);
      setError('No se pudo cargar el reporte de pagos.');
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
    const filteredPayments = latestPayments.filter((item) => {
      const matchesStatus = statusFilter === 'all' ? true : item.status === statusFilter;
      const term = paymentSearch.trim().toLowerCase();
      const matchesSearch = !term
        ? true
        : item.customer_name.toLowerCase().includes(term) || item.loan_number.toLowerCase().includes(term) || item.payment_number.toLowerCase().includes(term);
      return matchesStatus && matchesSearch;
    });

    const visibleCollected = filteredPayments.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const visiblePrincipal = filteredPayments.reduce((sum, item) => sum + Number(item.principal_paid || 0), 0);
    const visibleInterest = filteredPayments.reduce((sum, item) => sum + Number(item.interest_paid || 0), 0);
    const visibleLateFees = filteredPayments.reduce((sum, item) => sum + Number(item.late_fee_paid || 0), 0);

    return {
      filteredPayments,
      visibleCollected,
      visiblePrincipal,
      visibleInterest,
      visibleLateFees,
      topPayments: [...filteredPayments].sort((a, b) => Number(b.amount || 0) - Number(a.amount || 0)).slice(0, 8),
    };
  }, [latestPayments, paymentSearch, statusFilter]);

  const methodRows = [
    { label: 'Efectivo', count: cashCount },
    { label: 'Transferencia', count: transferCount },
    { label: 'Tarjeta', count: cardCount },
    { label: 'Pago móvil', count: mobileCount },
  ];

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
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Reporte de pagos e ingresos</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">Primera versión inspirada en reppag2. Resume recaudo reciente, aplicación del dinero y mezcla de métodos.</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="bg-white" onClick={() => window.print()}><Download className="mr-2 h-4 w-4" />Imprimir</Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/payments')}>Abrir pagos</Button>
            </div>
          </div>
        </div>

        {error ? <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="grid gap-4 lg:grid-cols-4">
                <div>
                  <p className="text-sm text-white/70">Recaudo visible</p>
                  <p className="mt-2 text-3xl font-semibold">{formatCurrency(metrics.visibleCollected)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Aplicado a principal</p>
                  <p className="mt-2 text-2xl font-semibold">{formatCurrency(metrics.visiblePrincipal)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Aplicado a interés</p>
                  <p className="mt-2 text-2xl font-semibold">{formatCurrency(metrics.visibleInterest)}</p>
                </div>
                <div>
                  <p className="text-sm text-white/70">Aplicado a mora</p>
                  <p className="mt-2 text-2xl font-semibold">{formatCurrency(metrics.visibleLateFees)}</p>
                </div>
              </div>
            </div>
            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Completados</p><p className="mt-2 text-2xl font-semibold text-slate-900">{completedCount}</p></div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Pendientes</p><p className="mt-2 text-2xl font-semibold text-slate-900">{pendingCount}</p></div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Revertidos</p><p className="mt-2 text-2xl font-semibold text-slate-900">{reversedCount}</p></div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4"><p className="text-xs uppercase tracking-wide text-slate-500">Fallidos</p><p className="mt-2 text-2xl font-semibold text-slate-900">{failedCount}</p></div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Pagos recientes con mayor impacto</CardTitle>
              <CardDescription>Lectura operativa de ingresos recientes. Transparente: se basa en los últimos registros disponibles.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <input
                    value={paymentSearch}
                    onChange={(e) => setPaymentSearch(e.target.value)}
                    placeholder="Buscar por cliente, préstamo o recibo..."
                    className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-[#163300]"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { value: 'all', label: 'Todos' },
                    { value: 'completed', label: 'Completados' },
                    { value: 'pending', label: 'Pendientes' },
                    { value: 'reversed', label: 'Revertidos' },
                    { value: 'failed', label: 'Fallidos' },
                  ].map((option) => (
                    <Button
                      key={option.value}
                      type="button"
                      variant={statusFilter === option.value ? 'default' : 'outline'}
                      className={statusFilter === option.value ? 'bg-[#163300] hover:bg-[#0f2400]' : 'bg-white'}
                      onClick={() => setStatusFilter(option.value as typeof statusFilter)}
                    >
                      {option.label}
                    </Button>
                  ))}
                </div>
              </div>
              {metrics.topPayments.map((payment) => (
                <div key={payment.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{payment.customer_name}</p>
                      <p className="text-sm text-slate-500">{payment.payment_number} · {payment.loan_number} · {formatDate(payment.payment_date)}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-900">{formatCurrency(payment.amount)}</p>
                      <Button variant="outline" className="mt-2 h-8 bg-white" onClick={() => router.push(`/payments/${payment.id}`)}>Ver detalle</Button>
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Mezcla por método</CardTitle>
                <CardDescription>Equivale a una lectura simple de caja/banco según cómo entra el dinero.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {methodRows.map((row) => (
                  <div key={row.label} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-3"><CreditCard className="h-4 w-4 text-[#163300]" /><span className="text-sm font-medium text-slate-900">{row.label}</span></div>
                    <span className="text-lg font-semibold text-slate-900">{row.count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader><CardTitle className="text-base text-[#163300]">Cómo leer este reporte</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><Wallet className="mt-0.5 h-4 w-4 text-[#163300]" /><p><strong>Ingresos:</strong> mide el dinero que ya entró en pagos recientes.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><ReceiptText className="mt-0.5 h-4 w-4 text-emerald-600" /><p><strong>Aplicación:</strong> deja claro cuánto redujo capital, cuánto fue interés y cuánto cubrió mora.</p></div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><Landmark className="mt-0.5 h-4 w-4 text-amber-600" /><p><strong>Métodos:</strong> ayuda a separar lo que parece más caja vs más banca.</p></div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700"><strong className="text-slate-900">Refinamiento MVP:</strong> ya puedes filtrar visualmente por estado y buscar pagos clave sin salir del reporte.</div>
                <Button variant="outline" className="w-full justify-between bg-white" onClick={() => router.push('/collections/reports/caja-banco')}>Abrir caja y banco <ArrowRight className="h-4 w-4" /></Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
