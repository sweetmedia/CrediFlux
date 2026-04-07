'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  Plus,
  Send,
  XCircle,
  Clock,
  CheckCircle,
  AlertCircle,
  Mail,
  MessageSquare,
  Phone,
  Bell,
  Calendar,
  User,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ArrowRight,
  Siren,
  Filter,
  CalendarClock,
  TriangleAlert,
  Ban,
} from 'lucide-react';
import { CollectionReminder } from '@/types';

export default function RemindersListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [reminders, setReminders] = useState<CollectionReminder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const [statusFilter, setStatusFilter] = useState('all');
  const [channelFilter, setChannelFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadReminders();
    }
  }, [isAuthenticated, currentPage, statusFilter, channelFilter, typeFilter]);

  const loadReminders = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = { page: currentPage };
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      if (channelFilter && channelFilter !== 'all') params.channel = channelFilter;
      if (typeFilter && typeFilter !== 'all') params.reminder_type = typeFilter;

      const response = await collectionsAPI.getReminders(params);
      setReminders(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading reminders:', err);
      setError('Error al cargar recordatorios');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendReminder = async (id: string) => {
    try {
      await collectionsAPI.sendReminder(id);
      loadReminders();
    } catch (err: any) {
      console.error('Error sending reminder:', err);
      setError('Error al enviar recordatorio');
    }
  };

  const handleCancelReminder = async (id: string) => {
    if (!confirm('¿Está seguro de cancelar este recordatorio?')) return;

    try {
      await collectionsAPI.cancelReminder(id);
      loadReminders();
    } catch (err: any) {
      console.error('Error canceling reminder:', err);
      setError('Error al cancelar recordatorio');
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: { icon: Clock, color: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Pendiente' },
      sent: { icon: CheckCircle, color: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Enviado' },
      failed: { icon: XCircle, color: 'bg-red-50 text-red-700 border-red-200', label: 'Fallido' },
      cancelled: { icon: Ban, color: 'bg-slate-50 text-slate-700 border-slate-200', label: 'Cancelado' },
    };
    const config = variants[status] || variants.pending;
    const Icon = config.icon;
    return (
      <Badge variant="outline" className={config.color}>
        <Icon className="mr-1 h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getChannelIcon = (channel: string) => {
    const icons: Record<string, any> = {
      email: Mail,
      sms: MessageSquare,
      whatsapp: MessageSquare,
      call: Phone,
    };
    const Icon = icons[channel] || Bell;
    return <Icon className="h-4 w-4" />;
  };

  const totalPages = Math.ceil(totalCount / 25);

  const stats = useMemo(() => {
    const pending = reminders.filter((r) => r.status === 'pending').length;
    const sent = reminders.filter((r) => r.status === 'sent').length;
    const failed = reminders.filter((r) => r.status === 'failed').length;
    const cancelled = reminders.filter((r) => r.status === 'cancelled').length;
    return { pending, sent, failed, cancelled };
  }, [reminders]);

  if (authLoading || isLoading) {
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
            href="/collections"
            className="mb-3 inline-flex items-center text-sm text-slate-500 transition-colors hover:text-slate-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Volver a Collections
          </Link>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Siren className="h-3.5 w-3.5" />
                Centro de salidas programadas
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Recordatorios de cobranza</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Gestiona recordatorios pendientes, confirma qué salió bien y detecta rápido lo que falló o ya perdió vigencia.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections')}>
                <Bell className="mr-2 h-4 w-4" />
                Dashboard
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/reminders/new')}>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo recordatorio
              </Button>
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Bandeja actual</p>
                  <h2 className="mt-1 text-3xl font-semibold">{totalCount} recordatorio(s)</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    Esta vista debe decirte qué necesita salir ahora, qué ya fue enviado y qué requiere intervención manual.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[440px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Pendientes</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.pending}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Enviados</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.sent}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Fallidos</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.failed}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Cancelados</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.cancelled}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Carga pendiente</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.pending} por disparar</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Entregas correctas</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.sent} enviadas</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Errores operativos</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.failed} fallidas</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Total visible</p>
                <p className="mt-2 text-sm font-medium text-slate-900">Página {currentPage} de {Math.max(totalPages, 1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base text-[#163300]">
                  <Filter className="h-4 w-4" />
                  Filtros
                </CardTitle>
                <CardDescription>Recorta la bandeja por estado, canal o tipo.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-1">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Estado</label>
                    <Select value={statusFilter} onValueChange={(value) => { setCurrentPage(1); setStatusFilter(value); }}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Todos los estados" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="pending">Pendiente</SelectItem>
                        <SelectItem value="sent">Enviado</SelectItem>
                        <SelectItem value="failed">Fallido</SelectItem>
                        <SelectItem value="cancelled">Cancelado</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Canal</label>
                    <Select value={channelFilter} onValueChange={(value) => { setCurrentPage(1); setChannelFilter(value); }}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Todos los canales" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="email">Email</SelectItem>
                        <SelectItem value="sms">SMS</SelectItem>
                        <SelectItem value="whatsapp">WhatsApp</SelectItem>
                        <SelectItem value="call">Llamada</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Tipo</label>
                    <Select value={typeFilter} onValueChange={(value) => { setCurrentPage(1); setTypeFilter(value); }}>
                      <SelectTrigger className="bg-white">
                        <SelectValue placeholder="Todos los tipos" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="upcoming_3">Próximo (3 días)</SelectItem>
                        <SelectItem value="upcoming_1">Próximo (1 día)</SelectItem>
                        <SelectItem value="due_today">Vence hoy</SelectItem>
                        <SelectItem value="overdue_1">Atrasado 1 día</SelectItem>
                        <SelectItem value="overdue_3">Atrasado 3 días</SelectItem>
                        <SelectItem value="overdue_7">Atrasado 7 días</SelectItem>
                        <SelectItem value="overdue_15">Atrasado 15 días</SelectItem>
                        <SelectItem value="overdue_30">Atrasado 30 días</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Lectura rápida</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                  <CalendarClock className="mt-0.5 h-5 w-5 text-amber-600" />
                  <div>
                    <p className="font-medium text-slate-900">Pendientes primero</p>
                    <p className="mt-1 text-sm text-slate-600">Lo que está pendiente es lo que todavía puede empujar recaudo hoy.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4">
                  <TriangleAlert className="mt-0.5 h-5 w-5 text-red-600" />
                  <div>
                    <p className="font-medium text-slate-900">Los fallidos no se ignoran</p>
                    <p className="mt-1 text-sm text-slate-600">Un recordatorio fallido normalmente necesita revisión de canal, datos o contacto manual.</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <Bell className="mt-0.5 h-5 w-5 text-slate-600" />
                  <div>
                    <p className="font-medium text-slate-900">Esta vista es operativa</p>
                    <p className="mt-1 text-sm text-slate-600">Debe ayudarte a decidir qué sale ya, qué se cancela y qué requiere seguimiento humano.</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-base text-[#163300]">Lista de recordatorios</CardTitle>
                  <CardDescription>{totalCount} recordatorio(s) encontrado(s)</CardDescription>
                </div>
                <Button variant="outline" size="sm" className="bg-white" onClick={() => router.push('/collections/reminders/new')}>
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {reminders.length === 0 ? (
                <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
                  <Bell className="mb-4 h-12 w-12 text-slate-400" />
                  <h3 className="text-lg font-medium text-slate-900">No hay recordatorios</h3>
                  <p className="mt-2 mb-4 max-w-md text-sm text-slate-500">
                    Ajusta los filtros o crea un nuevo recordatorio para comenzar.
                  </p>
                  <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections/reminders/new')}>
                    <Plus className="mr-2 h-4 w-4" />
                    Nuevo recordatorio
                  </Button>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-slate-50/70">
                          <TableHead>Cliente</TableHead>
                          <TableHead>Préstamo</TableHead>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Canal</TableHead>
                          <TableHead>Programado</TableHead>
                          <TableHead>Estado</TableHead>
                          <TableHead>Enviado</TableHead>
                          <TableHead className="text-right">Acciones</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {reminders.map((reminder) => (
                          <TableRow key={reminder.id} className="hover:bg-slate-50">
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 font-medium text-slate-900">
                                <User className="h-4 w-4 text-slate-400" />
                                {reminder.customer_name}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <Link href={`/loans/${reminder.loan}`} className="text-[#163300] hover:underline">
                                #{reminder.loan_number}
                              </Link>
                            </TableCell>
                            <TableCell className="align-top">
                              <Badge variant="outline" className="bg-white">
                                {reminder.reminder_type_display}
                              </Badge>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 text-sm text-slate-700">
                                {getChannelIcon(reminder.channel)}
                                {reminder.channel_display}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 text-sm text-slate-700">
                                <Calendar className="h-4 w-4 text-slate-400" />
                                {formatDateTime(reminder.scheduled_for)}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">{getStatusBadge(reminder.status)}</TableCell>
                            <TableCell className="align-top text-sm text-slate-600">
                              {reminder.sent_at ? formatDateTime(reminder.sent_at) : '-'}
                            </TableCell>
                            <TableCell className="text-right align-top">
                              <div className="flex items-center justify-end gap-2">
                                {reminder.status === 'pending' && (
                                  <>
                                    <Button
                                      size="sm"
                                      className="bg-[#163300] hover:bg-[#0f2400]"
                                      onClick={() => handleSendReminder(reminder.id)}
                                    >
                                      <Send className="mr-1 h-4 w-4" />
                                      Enviar
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="bg-white"
                                      onClick={() => handleCancelReminder(reminder.id)}
                                    >
                                      <XCircle className="h-4 w-4" />
                                    </Button>
                                  </>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {totalPages > 1 && (
                    <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
                      <p className="text-sm text-slate-600">
                        Página {currentPage} de {totalPages}
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="bg-white"
                          disabled={currentPage === 1}
                          onClick={() => setCurrentPage(currentPage - 1)}
                        >
                          <ChevronLeft className="mr-1 h-4 w-4" />
                          Anterior
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="bg-white"
                          disabled={currentPage === totalPages}
                          onClick={() => setCurrentPage(currentPage + 1)}
                        >
                          Siguiente
                          <ChevronRight className="ml-1 h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
