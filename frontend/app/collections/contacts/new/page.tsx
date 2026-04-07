'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI, loansAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Loader2,
  ArrowLeft,
  Phone,
  Plus,
  Search,
  Landmark,
  User,
  CalendarClock,
  MessageSquare,
  CheckCircle2,
  Wallet,
  ArrowRight,
  ShieldAlert,
  Clock3,
} from 'lucide-react';

const CONTACT_TYPE_OPTIONS = [
  { value: 'phone_call', label: 'Llamada telefónica' },
  { value: 'sms', label: 'SMS' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'Email' },
  { value: 'home_visit', label: 'Visita domicilio' },
  { value: 'office_visit', label: 'Visita oficina' },
  { value: 'meeting', label: 'Reunión acordada' },
];

const OUTCOME_OPTIONS = [
  { value: 'answered', label: 'Cliente contestó / atendió' },
  { value: 'no_answer', label: 'No contestó' },
  { value: 'wrong_number', label: 'Número equivocado' },
  { value: 'promise_to_pay', label: 'Promesa de pago' },
  { value: 'payment_plan', label: 'Plan de pagos acordado' },
  { value: 'partial_payment', label: 'Pago parcial recibido' },
  { value: 'full_payment', label: 'Pago completo recibido' },
  { value: 'dispute', label: 'Cliente disputa la deuda' },
  { value: 'hardship', label: 'Dificultad económica' },
  { value: 'refused_to_pay', label: 'Se niega a pagar' },
  { value: 'not_reachable', label: 'No localizable' },
];

export default function NewCollectionContactPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [isSaving, setIsSaving] = useState(false);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loanSearch, setLoanSearch] = useState('');
  const [loanResults, setLoanResults] = useState<any[]>([]);
  const [selectedLoan, setSelectedLoan] = useState<any>(null);
  const [contactDate, setContactDate] = useState(() => new Date().toISOString().slice(0, 16));
  const [contactType, setContactType] = useState('phone_call');
  const [outcome, setOutcome] = useState('answered');
  const [promiseDate, setPromiseDate] = useState('');
  const [promiseAmount, setPromiseAmount] = useState('');
  const [nextContactDate, setNextContactDate] = useState('');
  const [requiresEscalation, setRequiresEscalation] = useState(false);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    const run = async () => {
      if (selectedLoan || loanSearch.trim().length < 2) {
        if (!selectedLoan) setLoanResults([]);
        return;
      }

      try {
        setLoadingSearch(true);
        const response = await loansAPI.getLoans({ search: loanSearch.trim(), status: 'active' });
        setLoanResults(response.results || []);
      } catch (err) {
        console.error('Error searching loans:', err);
      } finally {
        setLoadingSearch(false);
      }
    };

    const timer = setTimeout(run, 250);
    return () => clearTimeout(timer);
  }, [loanSearch, selectedLoan]);

  const requiresPromise = useMemo(
    () => ['promise_to_pay', 'payment_plan'].includes(outcome),
    [outcome]
  );

  const selectedOutcomeLabel = useMemo(
    () => OUTCOME_OPTIONS.find((item) => item.value === outcome)?.label || 'Resultado',
    [outcome]
  );

  const selectedContactTypeLabel = useMemo(
    () => CONTACT_TYPE_OPTIONS.find((item) => item.value === contactType)?.label || 'Contacto',
    [contactType]
  );

  useEffect(() => {
    if (!requiresPromise) {
      setPromiseDate('');
      setPromiseAmount('');
    }
  }, [requiresPromise]);

  const formatCurrency = (amount: number | string | undefined | null) => {
    const value = Number(amount || 0);
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(value);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!selectedLoan) {
      toast.error('Selecciona un préstamo antes de registrar el contacto.');
      return;
    }

    if (!contactDate) {
      toast.error('Indica la fecha y hora del contacto.');
      return;
    }

    if (!notes.trim()) {
      toast.error('Agrega las notas del contacto.');
      return;
    }

    if (requiresPromise) {
      if (!promiseDate) {
        toast.error('La promesa requiere una fecha comprometida.');
        return;
      }
      if (!promiseAmount || Number(promiseAmount) <= 0) {
        toast.error('La promesa requiere un monto válido.');
        return;
      }
    }

    try {
      setIsSaving(true);

      await collectionsAPI.createContact({
        loan: selectedLoan.id,
        customer: selectedLoan.customer,
        contact_date: contactDate,
        contact_type: contactType as any,
        outcome: outcome as any,
        promise_date: requiresPromise ? promiseDate : undefined,
        promise_amount: requiresPromise ? Number(promiseAmount) : undefined,
        notes: notes.trim(),
        next_contact_date: nextContactDate || undefined,
        requires_escalation: requiresEscalation,
      });

      toast.success('Contacto de cobranza registrado.');
      setTimeout(() => router.push('/collections/contacts'), 700);
    } catch (err: any) {
      console.error('Error creating collection contact:', err);
      const msg = err?.response?.data?.detail || err?.detail || 'Error al registrar el contacto.';
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] px-4 py-6 md:px-6 md:py-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div>
          <Link
            href="/collections/contacts"
            className="mb-3 inline-flex items-center text-sm text-slate-500 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a Contactos
          </Link>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Phone className="h-3.5 w-3.5" />
                Registrar gestión de cobro
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Nuevo contacto</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Registra la interacción con el cliente, el resultado de la gestión y el siguiente paso para que la cobranza tenga continuidad real.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections/contacts')}>
                <Phone className="mr-2 h-4 w-4" />
                Ver bitácora
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={handleSubmit} disabled={isSaving}>
                {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
                Registrar contacto
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Detalles del contacto</CardTitle>
              <CardDescription>
                Define el canal, el resultado y deja contexto suficiente para que el próximo seguimiento no empiece desde cero.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="loan-search">Buscar préstamo / cliente</Label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="loan-search"
                      type="text"
                      placeholder="Número de préstamo, nombre o cédula del cliente..."
                      value={selectedLoan ? `${selectedLoan.loan_number} - ${selectedLoan.customer_name}` : loanSearch}
                      onChange={(e) => {
                        if (selectedLoan) return;
                        setLoanSearch(e.target.value);
                      }}
                      disabled={!!selectedLoan}
                      className="pl-9"
                    />
                  </div>

                  {!selectedLoan && loanSearch.trim().length >= 2 && (
                    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                      {loadingSearch ? (
                        <div className="flex items-center gap-2 px-4 py-4 text-sm text-slate-500">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Buscando préstamos...
                        </div>
                      ) : loanResults.length === 0 ? (
                        <div className="px-4 py-4 text-sm text-slate-500">No se encontraron préstamos activos.</div>
                      ) : (
                        loanResults.map((loan) => (
                          <button
                            key={loan.id}
                            type="button"
                            className="flex w-full items-start justify-between border-b border-slate-100 px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-slate-50"
                            onClick={() => {
                              setSelectedLoan(loan);
                              setLoanSearch('');
                              setLoanResults([]);
                            }}
                          >
                            <div>
                              <p className="font-medium text-slate-900">#{loan.loan_number}</p>
                              <p className="mt-1 text-sm text-slate-600">{loan.customer_name}</p>
                            </div>
                            <div className="text-right text-sm text-slate-500">
                              <p>Balance</p>
                              <p className="font-medium text-slate-900">{formatCurrency(loan.outstanding_balance)}</p>
                            </div>
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {selectedLoan && (
                  <div className="rounded-2xl border border-[#d7e2db] bg-[#fbfcfb] p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-slate-500">Caso seleccionado</p>
                        <p className="mt-1 font-semibold text-slate-900">#{selectedLoan.loan_number}</p>
                        <p className="mt-1 text-sm text-slate-600">{selectedLoan.customer_name}</p>
                        <p className="mt-2 font-mono text-sm text-slate-500">{formatCurrency(selectedLoan.outstanding_balance)}</p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="bg-white"
                        onClick={() => {
                          setSelectedLoan(null);
                          setLoanSearch('');
                        }}
                      >
                        Cambiar
                      </Button>
                    </div>
                  </div>
                )}

                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="contact-date">Fecha y hora del contacto</Label>
                    <Input
                      id="contact-date"
                      type="datetime-local"
                      value={contactDate}
                      onChange={(e) => setContactDate(e.target.value)}
                      className="bg-white"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="next-contact-date">Próximo contacto</Label>
                    <Input
                      id="next-contact-date"
                      type="date"
                      value={nextContactDate}
                      onChange={(e) => setNextContactDate(e.target.value)}
                      className="bg-white"
                    />
                  </div>
                </div>

                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="contact-type">Canal</Label>
                    <Select value={contactType} onValueChange={setContactType}>
                      <SelectTrigger id="contact-type" className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CONTACT_TYPE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="outcome">Resultado</Label>
                    <Select value={outcome} onValueChange={setOutcome}>
                      <SelectTrigger id="outcome" className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {OUTCOME_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {requiresPromise && (
                  <div className="grid gap-6 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="promise-date">Fecha comprometida</Label>
                      <Input
                        id="promise-date"
                        type="date"
                        value={promiseDate}
                        onChange={(e) => setPromiseDate(e.target.value)}
                        className="bg-white"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="promise-amount">Monto prometido</Label>
                      <Input
                        id="promise-amount"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="0.00"
                        value={promiseAmount}
                        onChange={(e) => setPromiseAmount(e.target.value)}
                        className="bg-white"
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="notes">Notas del contacto</Label>
                  <Textarea
                    id="notes"
                    rows={7}
                    placeholder="Qué dijo el cliente, objeciones, acuerdos, contexto y siguiente paso..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="bg-white"
                  />
                </div>

                <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4">
                  <input
                    type="checkbox"
                    checked={requiresEscalation}
                    onChange={(e) => setRequiresEscalation(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-[#163300] focus:ring-[#163300]"
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-900">Requiere escalación</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Activa esto si el caso necesita supervisor, negociación distinta o seguimiento más fuerte.
                    </p>
                  </div>
                </label>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Button type="submit" className="bg-[#163300] hover:bg-[#0f2400]" disabled={isSaving}>
                    {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}
                    Registrar contacto
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="bg-white"
                    onClick={() => router.push('/collections/contacts')}
                    disabled={isSaving}
                  >
                    Cancelar
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <div className="space-y-6">
            <Card className="overflow-hidden border-[#d7e2db] shadow-none">
              <CardContent className="p-0">
                <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
                  <p className="text-sm text-white/70">Resumen de la gestión</p>
                  <h2 className="mt-1 text-2xl font-semibold">{selectedOutcomeLabel}</h2>
                  <p className="mt-3 text-sm text-white/80">
                    Antes de guardar, valida si este registro deja claro qué pasó y qué debe ocurrir después.
                  </p>
                </div>

                <div className="space-y-3 bg-white px-6 py-5">
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                      <User className="h-3.5 w-3.5" />
                      Cliente
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-900">
                      {selectedLoan?.customer_name || 'Selecciona un caso'}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                      <Landmark className="h-3.5 w-3.5" />
                      Préstamo
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-900">
                      {selectedLoan ? `#${selectedLoan.loan_number}` : 'Pendiente'}
                    </p>
                    <p className="mt-1 text-sm text-slate-600">
                      Balance: {formatCurrency(selectedLoan?.outstanding_balance)}
                    </p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                    <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                        <MessageSquare className="h-3.5 w-3.5" />
                        Canal
                      </div>
                      <p className="mt-2 text-sm font-medium text-slate-900">{selectedContactTypeLabel}</p>
                    </div>
                    <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                        <CalendarClock className="h-3.5 w-3.5" />
                        Próximo paso
                      </div>
                      <p className="mt-2 text-sm font-medium text-slate-900">{nextContactDate || 'No definido'}</p>
                    </div>
                  </div>

                  {requiresPromise && (
                    <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-blue-700">
                        <Wallet className="h-3.5 w-3.5" />
                        Promesa registrada
                      </div>
                      <p className="mt-2 text-sm font-medium text-slate-900">Fecha: {promiseDate || 'Pendiente'}</p>
                      <p className="mt-1 text-sm text-slate-700">Monto: {formatCurrency(promiseAmount)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Guía rápida</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                  <p>Si hubo una promesa, registra fecha y monto. Si no, el dato queda demasiado flojo para seguimiento real.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <Clock3 className="mt-0.5 h-4 w-4 text-slate-500" />
                  <p>Define próximo contacto cuando el caso no quedó cerrado. Eso evita perseguir clientes “a memoria”.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <ShieldAlert className="mt-0.5 h-4 w-4 text-red-500" />
                  <p>Escala si el cliente se niega, disputa la deuda o el caso ya pide una jugada distinta.</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Siguiente paso natural</CardTitle>
                <CardDescription>Después de guardar, normalmente sigues con la bitácora o con el cobro.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/contacts')}>
                  Ver bitácora de contactos
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/payments/new')}>
                  Ir a registrar pago
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
