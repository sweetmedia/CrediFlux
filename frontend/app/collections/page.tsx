'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { schedulesAPI, collectionsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  AlertCircle,
  TrendingUp,
  Bell,
  Users,
  Phone,
  Mail,
  MessageSquare,
  Clock,
  Target,
  CheckCircle,
  XCircle,
  Landmark,
  ArrowRight,
  ShieldAlert,
  CalendarClock,
  Siren,
  Wallet,
} from 'lucide-react';

interface DashboardStats {
  overdueSchedules: number;
  totalOverdue: number;
  totalLateFees: number;
  pendingReminders: number;
  promisesToday: number;
  brokenPromises: number;
  escalationRequired: number;
}

export default function CollectionsDashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { config } = useConfig();
  const [stats, setStats] = useState<DashboardStats>({
    overdueSchedules: 0,
    totalOverdue: 0,
    totalLateFees: 0,
    pendingReminders: 0,
    promisesToday: 0,
    brokenPromises: 0,
    escalationRequired: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [recentContacts, setRecentContacts] = useState<any[]>([]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated]);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError('');

      const [
        overdueResponse,
        pendingRemindersResponse,
        promisesResponse,
        brokenPromisesResponse,
        escalationResponse,
        recentContactsResponse,
      ] = await Promise.all([
        schedulesAPI.getOverdueSchedules(),
        collectionsAPI.getPendingReminders(),
        collectionsAPI.getPromisesDueToday(),
        collectionsAPI.getBrokenPromises(),
        collectionsAPI.getRequiringEscalation(),
        collectionsAPI.getContactsByCollector({ user_id: user?.id }),
      ]);

      const totalOverdue = overdueResponse.reduce((sum, s) => sum + (Number(s.balance) || 0), 0);
      const totalLateFees = overdueResponse.reduce((sum, s) => {
        const lateFeeDue = (Number(s.late_fee_amount) || 0) - (Number(s.late_fee_paid) || 0);
        return sum + Math.max(lateFeeDue, 0);
      }, 0);

      setStats({
        overdueSchedules: overdueResponse.length,
        totalOverdue,
        totalLateFees,
        pendingReminders: pendingRemindersResponse.length,
        promisesToday: promisesResponse.length,
        brokenPromises: brokenPromisesResponse.length,
        escalationRequired: escalationResponse.length,
      });

      setRecentContacts((recentContactsResponse || []).slice(0, 6));
    } catch (err: any) {
      console.error('Error loading dashboard data:', err);
      setError('Error al cargar datos del dashboard de cobranza');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const urgentActions = useMemo(() => {
    return [
      {
        id: 'escalation',
        title: 'Casos para escalar',
        subtitle: `${stats.escalationRequired} caso(s) requieren supervisor`,
        count: stats.escalationRequired,
        icon: ShieldAlert,
        tone: 'red',
        action: () => router.push('/collections/contacts'),
      },
      {
        id: 'broken-promises',
        title: 'Promesas incumplidas',
        subtitle: `${stats.brokenPromises} compromiso(s) no cumplido(s)`,
        count: stats.brokenPromises,
        icon: XCircle,
        tone: 'orange',
        action: () => router.push('/collections/contacts'),
      },
      {
        id: 'today-promises',
        title: 'Promesas para hoy',
        subtitle: `${stats.promisesToday} compromiso(s) con vencimiento hoy`,
        count: stats.promisesToday,
        icon: CalendarClock,
        tone: 'green',
        action: () => router.push('/collections/contacts'),
      },
      {
        id: 'reminders',
        title: 'Recordatorios pendientes',
        subtitle: `${stats.pendingReminders} pendiente(s) por enviar`,
        count: stats.pendingReminders,
        icon: Bell,
        tone: 'slate',
        action: () => router.push('/collections/reminders'),
      },
    ].filter((item) => item.count > 0);
  }, [stats, router]);

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f8f7]">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Landmark className="h-3.5 w-3.5" />
                Torre de control de cobranza
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Collections</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Vista operativa para priorizar morosidad, promesas de pago, recordatorios y casos que necesitan intervención.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" className="bg-white" onClick={() => router.push('/collections/contacts')}>
              <Phone className="mr-2 h-4 w-4" />
              Registrar contacto
            </Button>
            <Button variant="outline" className="bg-white" onClick={() => router.push('/collections/reminders')}>
              <Bell className="mr-2 h-4 w-4" />
              Recordatorios
            </Button>
            <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/schedules/overdue')}>
              <Siren className="mr-2 h-4 w-4" />
              Ver vencidos
            </Button>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Exposición total en seguimiento</p>
                  <h2 className="mt-1 text-3xl font-semibold">{formatCurrency(stats.totalOverdue)}</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    Aquí deberías ver rápido dónde está el riesgo, qué cobranzas se pueden cerrar hoy y qué casos requieren gestión más dura.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[420px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Cuotas vencidas</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.overdueSchedules}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Mora acumulada</p>
                    <p className="mt-2 text-2xl font-semibold">{formatCurrency(stats.totalLateFees)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Promesas hoy</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.promisesToday}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Escalación</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.escalationRequired}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Pendiente de recuperar</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatCurrency(stats.totalOverdue)}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Carga de recordatorios</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.pendingReminders} pendientes</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Promesas rotas</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.brokenPromises} caso(s)</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Actividad del cobrador</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{recentContacts.length} contacto(s) recientes</p>
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

        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Prioridades del día</CardTitle>
                <CardDescription>
                  Casos que conviene atacar primero antes de pasar a gestión rutinaria.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {urgentActions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
                    <CheckCircle className="mb-3 h-10 w-10 text-emerald-500" />
                    <p className="font-medium text-slate-900">Sin alertas críticas por ahora</p>
                    <p className="mt-1 text-sm text-slate-600">La operación está estable. Puedes enfocarte en seguimiento normal y preventivo.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {urgentActions.map((item) => {
                      const Icon = item.icon;
                      const toneClasses: Record<string, string> = {
                        red: 'border-red-200 bg-red-50 text-red-700',
                        orange: 'border-orange-200 bg-orange-50 text-orange-700',
                        green: 'border-emerald-200 bg-emerald-50 text-emerald-700',
                        slate: 'border-slate-200 bg-slate-50 text-slate-700',
                      };

                      return (
                        <div key={item.id} className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4">
                          <div className="flex min-w-0 items-start gap-3">
                            <div className={`rounded-xl border p-2.5 ${toneClasses[item.tone]}`}>
                              <Icon className="h-5 w-5" />
                            </div>
                            <div>
                              <p className="font-medium text-slate-900">{item.title}</p>
                              <p className="mt-1 text-sm text-slate-600">{item.subtitle}</p>
                            </div>
                          </div>
                          <Button variant="outline" size="sm" className="bg-white" onClick={item.action}>
                            Ver
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Acciones rápidas</CardTitle>
                <CardDescription>Atajos útiles para el equipo de cobranza.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Button variant="outline" className="justify-start bg-white" onClick={() => router.push('/schedules/overdue')}>
                    <AlertCircle className="mr-2 h-4 w-4" />
                    Ver pagos vencidos
                  </Button>
                  <Button variant="outline" className="justify-start bg-white" onClick={() => router.push('/payments/new')}>
                    <Wallet className="mr-2 h-4 w-4" />
                    Registrar pago
                  </Button>
                  <Button variant="outline" className="justify-start bg-white" onClick={() => router.push('/collections/contacts/new')}>
                    <Phone className="mr-2 h-4 w-4" />
                    Registrar contacto
                  </Button>
                  <Button variant="outline" className="justify-start bg-white" onClick={() => router.push('/collections/reminders')}>
                    <Bell className="mr-2 h-4 w-4" />
                    Gestionar recordatorios
                  </Button>
                  <Button variant="outline" className="justify-start bg-white sm:col-span-2" onClick={() => router.push('/collections/reports')}>
                    <Target className="mr-2 h-4 w-4" />
                    Ver reportes de cobranza
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <CardTitle className="text-base text-[#163300]">Actividad reciente</CardTitle>
                    <CardDescription>
                      Últimos contactos de cobranza registrados por el equipo.
                    </CardDescription>
                  </div>
                  <Button variant="outline" size="sm" className="bg-white" onClick={() => router.push('/collections/contacts')}>
                    Ver todos
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {recentContacts.length === 0 ? (
                  <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
                    <Users className="mb-3 h-10 w-10 text-slate-400" />
                    <p className="font-medium text-slate-900">No hay actividad reciente</p>
                    <p className="mt-1 text-sm text-slate-600">Todavía no se han registrado contactos de cobranza.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[760px]">
                      <thead className="bg-slate-50/70">
                        <tr className="border-b border-slate-200">
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Cliente</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Canal</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Resultado</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Fecha</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentContacts.map((contact) => {
                          const isPhone = contact.contact_type === 'phone_call';
                          const isEmail = contact.contact_type === 'email';
                          const isWhatsapp = contact.contact_type === 'whatsapp';

                          return (
                            <tr key={contact.id} className="border-b border-slate-100 transition-colors hover:bg-slate-50">
                              <td className="px-4 py-4 align-top">
                                <p className="font-medium text-slate-900">{contact.customer_name}</p>
                              </td>
                              <td className="px-4 py-4 align-top">
                                <div className="flex items-center gap-2 text-sm text-slate-900">
                                  {isPhone && <Phone className="h-4 w-4 text-[#163300]" />}
                                  {isEmail && <Mail className="h-4 w-4 text-[#738566]" />}
                                  {isWhatsapp && <MessageSquare className="h-4 w-4 text-green-600" />}
                                  <span>{contact.contact_type_display}</span>
                                </div>
                              </td>
                              <td className="px-4 py-4 align-top">
                                <p className="text-sm text-slate-600">{contact.outcome_display}</p>
                              </td>
                              <td className="px-4 py-4 align-top">
                                <p className="text-sm text-slate-600">{formatDateTime(contact.contact_date)}</p>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="grid gap-6 md:grid-cols-2">
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-[#163300]">
                    <TrendingUp className="h-5 w-5" />
                    Lectura del riesgo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Mora acumulada</span>
                      <span className="font-medium text-slate-900">{formatCurrency(stats.totalLateFees)}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Compromisos hoy</span>
                      <span className="font-medium text-slate-900">{stats.promisesToday}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Promesas rotas</span>
                      <span className="font-medium text-orange-600">{stats.brokenPromises}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Escalación requerida</span>
                      <span className="font-semibold text-red-600">{stats.escalationRequired}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-[#163300]">
                    <Clock className="h-5 w-5" />
                    Guía operativa
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm text-slate-700">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="mt-0.5 h-4 w-4 text-red-500" />
                      <p>Ataca primero casos con escalación o promesas incumplidas.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Bell className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>No dejes recordatorios pendientes si el contacto puede salir hoy.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Phone className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>Registra cada interacción para no perder contexto del cliente.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Target className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>Usa esta vista para decidir prioridades, no solo para ver números.</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
