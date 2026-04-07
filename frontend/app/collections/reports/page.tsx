'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI, collectionsAPI, schedulesAPI } from '@/lib/api/loans';
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
  ArrowLeft,
  FileText,
  AlertCircle,
  BarChart3,
  Siren,
  Wallet,
  Bell,
  Phone,
  ShieldAlert,
  CalendarClock,
  Landmark,
  Users,
  ArrowRight,
  CheckCircle2,
  Receipt,
  FolderKanban,
} from 'lucide-react';

interface LoanStats {
  total_loans: number;
  active_loans: number;
  overdue_loans: number;
  defaulted_loans: number;
  total_outstanding: number;
  total_collected: number;
}

export default function CollectionReportsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [loanStats, setLoanStats] = useState<LoanStats>({
    total_loans: 0,
    active_loans: 0,
    overdue_loans: 0,
    defaulted_loans: 0,
    total_outstanding: 0,
    total_collected: 0,
  });
  const [reminders, setReminders] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [overdueSchedules, setOverdueSchedules] = useState<any[]>([]);
  const [legacyReportHints, setLegacyReportHints] = useState<string[]>([
    'Reporte de cobros',
    'Carta de cobros',
    'Estado de cuenta',
    'Vencimientos',
    'Cuotas',
    'Pagos e ingresos',
    'Cierre de caja',
    'Estado bancario',
    'Clientes',
  ]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadReportData();
    }
  }, [isAuthenticated]);

  const loadReportData = async () => {
    try {
      setIsLoading(true);
      setError('');

      const [stats, remindersData, contactsData, overdueData, promisesToday, brokenPromises, escalation] = await Promise.all([
        loansAPI.getStatistics(),
        collectionsAPI.getReminders({ page: 1 }),
        collectionsAPI.getContacts({ page: 1 }),
        schedulesAPI.getOverdueSchedules(),
        collectionsAPI.getPromisesDueToday(),
        collectionsAPI.getBrokenPromises(),
        collectionsAPI.getRequiringEscalation(),
      ]);

      setLoanStats(stats as LoanStats);
      setReminders(remindersData.results || []);
      setContacts(contactsData.results || []);
      setOverdueSchedules(overdueData || []);

      setLegacyReportHints((prev) => {
        const dynamic = [
          promisesToday.length ? 'Promesas de pago del día' : '',
          brokenPromises.length ? 'Promesas incumplidas' : '',
          escalation.length ? 'Casos escalados' : '',
        ].filter(Boolean);
        return Array.from(new Set([...prev, ...dynamic]));
      });
    } catch (err: any) {
      console.error('Error loading collection reports data:', err);
      setError('Error al cargar los reportes de cobranza');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(Number(amount || 0));
  };

  const computed = useMemo(() => {
    const pendingReminders = reminders.filter((r) => r.status === 'pending').length;
    const sentReminders = reminders.filter((r) => r.status === 'sent').length;
    const failedReminders = reminders.filter((r) => r.status === 'failed').length;
    const promises = contacts.filter((c) => ['promise_to_pay', 'payment_plan'].includes(c.outcome)).length;
    const brokenPromises = contacts.filter((c) => c.promise_kept === false).length;
    const escalatedContacts = contacts.filter((c) => c.requires_escalation).length;
    const lateFeesPending = overdueSchedules.reduce((sum, schedule) => {
      const due = (Number(schedule.late_fee_amount) || 0) - (Number(schedule.late_fee_paid) || 0);
      return sum + Math.max(due, 0);
    }, 0);
    const overdueExposure = overdueSchedules.reduce((sum, schedule) => sum + (Number(schedule.balance) || 0), 0);
    const recoveryRateBase = loanStats.total_collected + loanStats.total_outstanding;
    const recoveryRate = recoveryRateBase > 0
      ? ((loanStats.total_collected / recoveryRateBase) * 100).toFixed(1)
      : '0.0';
    const overdueRate = loanStats.active_loans > 0
      ? ((loanStats.overdue_loans / loanStats.active_loans) * 100).toFixed(1)
      : '0.0';

    return {
      pendingReminders,
      sentReminders,
      failedReminders,
      promises,
      brokenPromises,
      escalatedContacts,
      lateFeesPending,
      overdueExposure,
      recoveryRate,
      overdueRate,
    };
  }, [reminders, contacts, overdueSchedules, loanStats]);

  const reportFamilies = useMemo(() => [
    {
      title: 'Cartera y cobranza',
      description: 'Inspirado en PRE_REPCOB, PRE_CAR_COB y reportes de vencimiento del sistema legacy.',
      icon: Siren,
      reports: [
        'Reporte general de cobros',
        'Cartera en atraso por rango de días',
        'Clientes con mayor exposición',
        'Carta / gestión de cobro por cliente',
      ],
      action: () => router.push('/collections/reports/cartera'),
      actionLabel: 'Abrir reporte',
    },
    {
      title: 'Estados de cuenta y cuotas',
      description: 'Tomado de estcue, rep_cua y variantes de cuotas/cuadre del legado.',
      icon: Receipt,
      reports: [
        'Estado de cuenta por cliente',
        'Balance de cuotas por préstamo',
        'Cuotas vencidas y próximas',
        'Promesas de pago por vencer',
      ],
      action: () => router.push('/collections/reports/estado-cuenta'),
      actionLabel: 'Abrir reporte',
    },
    {
      title: 'Pagos, caja y banco',
      description: 'Basado en reppag2, CIERCAJA y rep_ban como referencia operativa.',
      icon: Landmark,
      reports: [
        'Reporte de pagos / ingresos',
        'Cierre diario de caja',
        'Movimientos por banco o método',
        'Cobros por cobrador / cajero',
      ],
      action: () => router.push('/payments'),
      actionLabel: 'Ver pagos',
    },
    {
      title: 'Clientes y seguimiento',
      description: 'Inspirado en repcli / repclit / repclivz y la bitácora de contactos.',
      icon: Users,
      reports: [
        'Clientes activos / morosos / inactivos',
        'Historial de contacto de cobranza',
        'Promesas cumplidas vs incumplidas',
        'Casos escalados',
      ],
      action: () => router.push('/collections/contacts'),
      actionLabel: 'Ver contactos',
    },
  ], [router]);

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
                <FolderKanban className="h-3.5 w-3.5" />
                Biblioteca operativa de reportes
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Reportes de cobranza</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Aquí no solo vemos KPIs. Aquí definimos qué reportes necesita de verdad CrediFlux para operar cartera, mora, pagos, caja y seguimiento.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => window.print()}>
                <FileText className="mr-2 h-4 w-4" />
                Imprimir vista
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/collections')}>
                <ArrowRight className="mr-2 h-4 w-4" />
                Volver al módulo
              </Button>
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Lectura rápida de la cartera</p>
                  <h2 className="mt-1 text-3xl font-semibold">{formatCurrency(loanStats.total_outstanding)}</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    Balance pendiente actual. Esta es la base sobre la que deben construirse los reportes generales de cobranza y cartera.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[460px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Recuperación</p>
                    <p className="mt-2 text-2xl font-semibold">{computed.recoveryRate}%</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Mora</p>
                    <p className="mt-2 text-2xl font-semibold">{computed.overdueRate}%</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Exposición vencida</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(computed.overdueExposure)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Mora pendiente</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(computed.lateFeesPending)}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Recordatorios</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{computed.pendingReminders} pendientes · {computed.sentReminders} enviados</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Promesas</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{computed.promises} registradas · {computed.brokenPromises} incumplidas</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Escalación</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{computed.escalatedContacts} caso(s) visibles</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Usuario</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{user?.email || 'N/A'}</p>
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

        <div className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Familias de reportes a implementar</CardTitle>
                <CardDescription>
                  Agrupación propuesta para los reportes generales de CrediFlux, tomando inspiración directa del sistema legacy.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                {reportFamilies.map((family) => {
                  const Icon = family.icon;
                  return (
                    <div key={family.title} className="rounded-2xl border border-slate-200 bg-white p-5">
                      <div className="mb-3 flex items-center gap-3">
                        <div className="rounded-xl border border-[#d7e2db] bg-[#f6f8f7] p-2.5 text-[#163300]">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{family.title}</p>
                          <p className="text-sm text-slate-500">{family.description}</p>
                        </div>
                      </div>
                      <ul className="space-y-2 text-sm text-slate-700">
                        {family.reports.map((item) => (
                          <li key={item} className="flex items-start gap-2">
                            <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                      <div className="mt-4">
                        <Button variant="outline" className="bg-white" onClick={family.action}>
                          {family.actionLabel}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">KPIs operativos del módulo</CardTitle>
                <CardDescription>Lo que hoy sí podemos leer directamente del sistema actual.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-2 text-slate-500">
                      <Wallet className="h-4 w-4" />
                      <span className="text-sm">Total cobrado</span>
                    </div>
                    <p className="mt-3 text-xl font-semibold text-slate-900">{formatCurrency(loanStats.total_collected)}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-2 text-slate-500">
                      <Siren className="h-4 w-4" />
                      <span className="text-sm">Préstamos morosos</span>
                    </div>
                    <p className="mt-3 text-xl font-semibold text-slate-900">{loanStats.overdue_loans}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-2 text-slate-500">
                      <Bell className="h-4 w-4" />
                      <span className="text-sm">Recordatorios fallidos</span>
                    </div>
                    <p className="mt-3 text-xl font-semibold text-slate-900">{computed.failedReminders}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-2 text-slate-500">
                      <Phone className="h-4 w-4" />
                      <span className="text-sm">Contactos registrados</span>
                    </div>
                    <p className="mt-3 text-xl font-semibold text-slate-900">{contacts.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Lo que ya detecté en Seane</CardTitle>
                <CardDescription>
                  Primer inventario de pistas del sistema legacy que conviene traducir a CrediFlux.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {legacyReportHints.map((item) => (
                  <div key={item} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <BarChart3 className="mt-0.5 h-4 w-4 text-[#163300]" />
                    <p className="text-sm text-slate-700">{item}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Prioridad sugerida</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-slate-700">
                <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4">
                  <Siren className="mt-0.5 h-4 w-4 text-red-600" />
                  <p><strong>Alta:</strong> cartera en atraso, vencimientos, estado de cuenta, pagos e ingresos.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                  <CalendarClock className="mt-0.5 h-4 w-4 text-amber-600" />
                  <p><strong>Media:</strong> promesas de pago, productividad de cobradores, clientes contactados vs no localizados.</p>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <ShieldAlert className="mt-0.5 h-4 w-4 text-slate-600" />
                  <p><strong>Post-MVP:</strong> cierres avanzados, comparativas históricas, scoreboards operativos más complejos.</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Rutas rápidas</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reports/cartera')}>
                  Abrir cartera y cobros
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reports/vencimientos')}>
                  Abrir vencimientos
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reports/estado-cuenta')}>
                  Abrir estados de cuenta
                  <ArrowRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" className="justify-between bg-white" onClick={() => router.push('/collections/reports/cuotas')}>
                  Abrir cuotas
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
