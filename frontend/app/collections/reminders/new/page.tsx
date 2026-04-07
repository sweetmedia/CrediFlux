'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
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
import { toast } from 'sonner';
import {
  Loader2,
  ArrowLeft,
  Save,
  Search,
  Bell,
  CalendarClock,
  MessageSquare,
  User,
  Landmark,
  CheckCircle2,
  Clock,
  Mail,
  Phone,
  Wallet,
  FileText,
  ArrowRight,
} from 'lucide-react';
import { Loan } from '@/types';

const REMINDER_TYPE_OPTIONS = [
  { value: 'upcoming_3', label: 'Próximo (3 días)' },
  { value: 'upcoming_1', label: 'Próximo (1 día)' },
  { value: 'due_today', label: 'Vence hoy' },
  { value: 'overdue_1', label: 'Atrasado 1 día' },
  { value: 'overdue_3', label: 'Atrasado 3 días' },
  { value: 'overdue_7', label: 'Atrasado 7 días' },
  { value: 'overdue_15', label: 'Atrasado 15 días' },
  { value: 'overdue_30', label: 'Atrasado 30 días' },
];

const CHANNEL_OPTIONS = [
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'sms', label: 'SMS', icon: MessageSquare },
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageSquare },
  { value: 'call', label: 'Llamada', icon: Phone },
];

export default function NewReminderPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [loans, setLoans] = useState<Loan[]>([]);
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [reminderType, setReminderType] = useState('due_today');
  const [channel, setChannel] = useState('email');
  const [scheduledFor, setScheduledFor] = useState('');
  const [messageContent, setMessageContent] = useState('');
  const [loadingSearch, setLoadingSearch] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!scheduledFor) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(9, 0, 0, 0);
      setScheduledFor(tomorrow.toISOString().slice(0, 16));
    }
  }, [scheduledFor]);

  useEffect(() => {
    if (!selectedLoan) {
      setLoans([]);
      return;
    }
    generateDefaultMessage(selectedLoan, reminderType);
  }, [selectedLoan, reminderType, channel]);

  useEffect(() => {
    const run = async () => {
      if (searchTerm.trim().length < 2 || selectedLoan) {
        if (!selectedLoan) setLoans([]);
        return;
      }

      try {
        setLoadingSearch(true);
        const response = await loansAPI.getLoans({ search: searchTerm.trim(), status: 'active' });
        setLoans(response.results || []);
      } catch (err) {
        console.error('Error searching loans:', err);
      } finally {
        setLoadingSearch(false);
      }
    };

    const timer = setTimeout(run, 250);
    return () => clearTimeout(timer);
  }, [searchTerm, selectedLoan]);

  const generateDefaultMessage = (loan: Loan, type: string) => {
    const customerName = loan.customer_name;
    const loanNumber = loan.loan_number;
    const balance = new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(Number(loan.outstanding_balance || 0));

    const messages: Record<string, string> = {
      upcoming_3: `Estimado/a ${customerName}, le recordamos que su pago del préstamo ${loanNumber} vence en 3 días. Monto pendiente: ${balance}.`,
      upcoming_1: `Estimado/a ${customerName}, le recordamos que su pago del préstamo ${loanNumber} vence mañana. Monto pendiente: ${balance}.`,
      due_today: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} vence hoy. Por favor realice su pago a tiempo. Monto: ${balance}.`,
      overdue_1: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 1 día de atraso. Por favor comuníquese con nosotros. Monto adeudado: ${balance}.`,
      overdue_3: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 3 días de atraso. Es importante que regularice su situación. Monto adeudado: ${balance}.`,
      overdue_7: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 7 días de atraso. Por favor contacte a nuestro departamento de cobranza. Monto adeudado: ${balance}.`,
      overdue_15: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 15 días de atraso. Necesitamos urgente comunicación de su parte. Monto adeudado: ${balance}.`,
      overdue_30: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 30 días de atraso. Su cuenta está en riesgo. Por favor contacte inmediatamente. Monto adeudado: ${balance}.`,
    };

    setMessageContent(messages[type] || messages.due_today);
  };

  const formatCurrency = (amount: number | string | undefined | null) => {
    const value = Number(amount || 0);
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(value);
  };

  const selectedReminderType = useMemo(
    () => REMINDER_TYPE_OPTIONS.find((item) => item.value === reminderType)?.label || 'Vence hoy',
    [reminderType]
  );

  const selectedChannel = useMemo(
    () => CHANNEL_OPTIONS.find((item) => item.value === channel),
    [channel]
  );

  const messageLengthTone = useMemo(() => {
    if (messageContent.length < 80) return 'text-amber-600';
    if (messageContent.length > 280) return 'text-slate-500';
    return 'text-emerald-600';
  }, [messageContent.length]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!selectedLoan) {
      toast.error('Selecciona un préstamo antes de continuar.');
      return;
    }

    if (!scheduledFor) {
      toast.error('Selecciona fecha y hora para el recordatorio.');
      return;
    }

    if (!messageContent.trim()) {
      toast.error('Escribe el mensaje del recordatorio.');
      return;
    }

    try {
      setIsLoading(true);
      const schedules = selectedLoan.payment_schedules || [];
      const pendingSchedule = schedules.find((s: any) => ['pending', 'partial', 'overdue'].includes(s.status));

      await collectionsAPI.createReminder({
        loan_schedule: pendingSchedule?.id || '',
        loan: selectedLoan.id,
        customer: selectedLoan.customer,
        reminder_type: reminderType as any,
        channel: channel as any,
        scheduled_for: scheduledFor,
        message_content: messageContent.trim(),
      });

      toast.success('Recordatorio creado exitosamente.');
      setTimeout(() => {
        router.push('/collections/reminders');
      }, 800);
    } catch (err: any) {
      console.error('Error creating reminder:', err);
      const errorMsg =
        err?.response?.data?.detail ||
        err?.detail ||
        'Error al crear el recordatorio.';
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
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
            href="/collections/reminders"
            className="mb-3 inline-flex items-center text-sm text-slate-500 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a Recordatorios
          </Link>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Bell className="h-3.5 w-3.5" />
                Programar salida de cobranza
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Nuevo recordatorio</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Programa un contacto preventivo o de mora con el contexto correcto del préstamo, el canal adecuado y un mensaje listo para salir.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections/reminders')}>
                <FileText className="mr-2 h-4 w-4" />
                Ver lista
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={handleSubmit} disabled={isLoading}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                Crear recordatorio
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <CardTitle className="text-base text-[#163300]">Configuración del recordatorio</CardTitle>
              <CardDescription>
                Completa los datos principales y ajusta el mensaje antes de programarlo.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="loan-search">Buscar préstamo</Label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <Input
                      id="loan-search"
                      type="text"
                      placeholder="Número de préstamo, nombre o cédula del cliente..."
                      value={selectedLoan ? `${selectedLoan.loan_number} - ${selectedLoan.customer_name}` : searchTerm}
                      onChange={(e) => {
                        if (selectedLoan) return;
                        setSearchTerm(e.target.value);
                      }}
                      disabled={!!selectedLoan}
                      className="pl-9"
                    />
                  </div>

                  {!selectedLoan && searchTerm.trim().length >= 2 && (
                    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                      {loadingSearch ? (
                        <div className="flex items-center gap-2 px-4 py-4 text-sm text-slate-500">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Buscando préstamos...
                        </div>
                      ) : loans.length === 0 ? (
                        <div className="px-4 py-4 text-sm text-slate-500">No se encontraron préstamos activos.</div>
                      ) : (
                        loans.map((loan) => (
                          <button
                            key={loan.id}
                            type="button"
                            className="flex w-full items-start justify-between border-b border-slate-100 px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-slate-50"
                            onClick={() => {
                              setSelectedLoan(loan);
                              setSearchTerm('');
                              setLoans([]);
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
                        <p className="text-xs uppercase tracking-wide text-slate-500">Préstamo seleccionado</p>
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
                          setSearchTerm('');
                          setMessageContent('');
                        }}
                      >
                        Cambiar
                      </Button>
                    </div>
                  </div>
                )}

                <div className="grid gap-6 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="reminder-type">Tipo de recordatorio</Label>
                    <Select value={reminderType} onValueChange={setReminderType}>
                      <SelectTrigger id="reminder-type" className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {REMINDER_TYPE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="channel">Canal de comunicación</Label>
                    <Select value={channel} onValueChange={setChannel}>
                      <SelectTrigger id="channel" className="bg-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CHANNEL_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="scheduled-for">Fecha y hora programada</Label>
                  <Input
                    id="scheduled-for"
                    type="datetime-local"
                    value={scheduledFor}
                    onChange={(e) => setScheduledFor(e.target.value)}
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor="message">Mensaje</Label>
                    <span className={`text-xs font-medium ${messageLengthTone}`}>
                      {messageContent.length} caracteres
                    </span>
                  </div>
                  <Textarea
                    id="message"
                    rows={7}
                    placeholder="Escribe el mensaje del recordatorio..."
                    value={messageContent}
                    onChange={(e) => setMessageContent(e.target.value)}
                    className="bg-white"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <Button type="submit" className="bg-[#163300] hover:bg-[#0f2400]" disabled={isLoading}>
                    {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                    Crear recordatorio
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="bg-white"
                    onClick={() => router.push('/collections/reminders')}
                    disabled={isLoading}
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
                  <p className="text-sm text-white/70">Resumen de la salida</p>
                  <h2 className="mt-1 text-2xl font-semibold">{selectedReminderType}</h2>
                  <p className="mt-3 text-sm text-white/80">
                    Confirma el tono, el canal y el momento correcto antes de programar el contacto.
                  </p>
                </div>

                <div className="space-y-3 bg-white px-6 py-5">
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                      <User className="h-3.5 w-3.5" />
                      Cliente
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-900">
                      {selectedLoan?.customer_name || 'Selecciona un préstamo'}
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
                      <p className="mt-2 text-sm font-medium text-slate-900">{selectedChannel?.label || 'Email'}</p>
                    </div>
                    <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
                        <CalendarClock className="h-3.5 w-3.5" />
                        Programado
                      </div>
                      <p className="mt-2 text-sm font-medium text-slate-900">{scheduledFor || 'Pendiente'}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Guía rápida</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <Clock className="mt-0.5 h-4 w-4 text-slate-500" />
                  <p>Programa temprano los recordatorios preventivos y reserva los de mora para horario de mayor respuesta.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                  <p>El mensaje sugerido ya trae contexto base, pero conviene personalizarlo si el caso lo amerita.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <Wallet className="mt-0.5 h-4 w-4 text-[#163300]" />
                  <p>Si el cliente ya está listo para pagar, te conviene registrar el cobro en lugar de dejar solo el recordatorio.</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Siguiente paso natural</CardTitle>
                <CardDescription>Después de programar el recordatorio, normalmente sigues con monitoreo o gestión directa.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reminders')}>
                  Ver bandeja de recordatorios
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/schedules/overdue')}>
                  Ir a pagos vencidos
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
