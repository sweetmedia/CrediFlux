'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { schedulesAPI } from '@/lib/api/loans';
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
  Loader2,
  AlertCircle,
  Calendar,
  User,
  Phone,
  CreditCard,
  Clock,
  ArrowLeft,
  MessageCircle,
  ShieldAlert,
  Siren,
  Wallet,
  ArrowRight,
  TriangleAlert,
  CheckCircle2,
  BarChart3,
} from 'lucide-react';
import { LoanSchedule } from '@/types';

export default function OverdueSchedulesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [schedules, setSchedules] = useState<LoanSchedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadOverdueSchedules();
    }
  }, [isAuthenticated]);

  const loadOverdueSchedules = async () => {
    try {
      setIsLoading(true);
      setError('');

      const response = await schedulesAPI.getOverdueSchedules();
      const sorted = [...(response || [])].sort((a, b) => (Number(b.days_overdue) || 0) - (Number(a.days_overdue) || 0));
      setSchedules(sorted);
    } catch (err: any) {
      console.error('Error loading overdue schedules:', err);
      setError('Error al cargar los pagos vencidos');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(amount || 0);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const buildWhatsAppUrl = (schedule: LoanSchedule) => {
    const cleanPhone = schedule.customer_phone?.replace(/[^0-9]/g, '') || '';
    const message = encodeURIComponent(
      `Saludos ${schedule.customer_name}. Le contactamos para darle seguimiento a su cuota #${schedule.installment_number} del préstamo ${schedule.loan_number}, con vencimiento el ${formatDate(schedule.due_date)}. Por favor comuníquese con nosotros para coordinar el pago. ¡Gracias!`
    );
    return `https://wa.me/${cleanPhone}?text=${message}`;
  };

  const getLateFeeDue = (schedule: LoanSchedule) => {
    return Math.max(
      0,
      (Number(schedule.late_fee_amount) || 0) - (Number(schedule.late_fee_paid) || 0)
    );
  };

  const getTotalDue = (schedule: LoanSchedule) => {
    return (Number(schedule.balance) || 0) + getLateFeeDue(schedule);
  };

  const getSeverity = (days: number) => {
    if (days <= 7) {
      return {
        label: 'Reciente',
        badge: 'bg-amber-50 text-amber-700 border-amber-200',
        rowAccent: 'border-l-4 border-amber-300',
      };
    }
    if (days <= 30) {
      return {
        label: 'Urgente',
        badge: 'bg-orange-50 text-orange-700 border-orange-200',
        rowAccent: 'border-l-4 border-orange-300',
      };
    }
    if (days <= 60) {
      return {
        label: 'Crítico',
        badge: 'bg-red-50 text-red-700 border-red-200',
        rowAccent: 'border-l-4 border-red-300',
      };
    }
    return {
      label: 'Severo',
      badge: 'bg-red-100 text-red-900 border-red-300',
      rowAccent: 'border-l-4 border-red-500',
    };
  };

  const stats = useMemo(() => {
    const totalOverdue = schedules.reduce((sum, s) => sum + (Number(s.balance) || 0), 0);
    const totalLateFees = schedules.reduce((sum, s) => sum + getLateFeeDue(s), 0);
    const totalExposure = totalOverdue + totalLateFees;
    const severeCount = schedules.filter((s) => Number(s.days_overdue) > 60).length;
    const criticalCount = schedules.filter((s) => Number(s.days_overdue) > 30 && Number(s.days_overdue) <= 60).length;
    const urgentCount = schedules.filter((s) => Number(s.days_overdue) > 7 && Number(s.days_overdue) <= 30).length;
    const recentCount = schedules.filter((s) => Number(s.days_overdue) <= 7).length;

    return {
      totalOverdue,
      totalLateFees,
      totalExposure,
      scheduleCount: schedules.length,
      severeCount,
      criticalCount,
      urgentCount,
      recentCount,
    };
  }, [schedules]);

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
                Cola priorizada de morosidad
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Pagos vencidos</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Usa esta vista para decidir a quién cobrar primero, cuánto está en riesgo y cuáles casos deben moverse hoy mismo.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections')}>
                <BarChart3 className="mr-2 h-4 w-4" />
                Ver dashboard
              </Button>
              <Button variant="outline" className="bg-white" onClick={() => router.push('/collections/contacts/new')}>
                <Phone className="mr-2 h-4 w-4" />
                Registrar contacto
              </Button>
              <Button className="bg-[#163300] hover:bg-[#0f2400]" onClick={() => router.push('/payments/new')}>
                <Wallet className="mr-2 h-4 w-4" />
                Registrar pago
              </Button>
            </div>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Exposición total en atraso</p>
                  <h2 className="mt-1 text-3xl font-semibold">{formatCurrency(stats.totalExposure)}</h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    Incluye saldo vencido y mora pendiente. La idea es que aquí puedas leer el tamaño del problema antes de empezar a gestionar.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[460px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Cuotas vencidas</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.scheduleCount}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Saldo vencido</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(stats.totalOverdue)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Mora pendiente</p>
                    <p className="mt-2 text-lg font-semibold">{formatCurrency(stats.totalLateFees)}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Casos severos</p>
                    <p className="mt-2 text-2xl font-semibold">{stats.severeCount}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Recientes</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.recentCount} hasta 7 días</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Urgentes</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.urgentCount} entre 8 y 30 días</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Críticos</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.criticalCount} entre 31 y 60 días</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Severos</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{stats.severeCount} más de 60 días</p>
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

        <div className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
          <div className="space-y-6">
            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Prioridad de gestión</CardTitle>
                <CardDescription>Cómo leer esta bandeja antes de empezar a cobrar.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4">
                  <ShieldAlert className="mt-0.5 h-5 w-5 text-red-600" />
                  <div>
                    <p className="font-medium text-slate-900">Atiende primero los casos severos y críticos</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Si superan 30-60 días, el riesgo de no recuperación sube y la gestión debe ser más agresiva.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-orange-200 bg-orange-50 p-4">
                  <TriangleAlert className="mt-0.5 h-5 w-5 text-orange-600" />
                  <div>
                    <p className="font-medium text-slate-900">No dejes crecer los urgentes</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Los casos de 8 a 30 días todavía son recuperables con buena velocidad de contacto.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" />
                  <div>
                    <p className="font-medium text-slate-900">Cierra fácil donde puedas cobrar hoy</p>
                    <p className="mt-1 text-sm text-slate-600">
                      Usa el botón de pago directo para convertir rápido la gestión en recaudo.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#d7e2db] shadow-none">
              <CardHeader>
                <CardTitle className="text-base text-[#163300]">Resumen de riesgo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-600">Saldo vencido</span>
                  <span className="font-medium text-slate-900">{formatCurrency(stats.totalOverdue)}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-600">Mora pendiente</span>
                  <span className="font-medium text-orange-600">{formatCurrency(stats.totalLateFees)}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-600">Exposición total</span>
                  <span className="font-semibold text-[#163300]">{formatCurrency(stats.totalExposure)}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-600">Cuotas a trabajar</span>
                  <span className="font-medium text-slate-900">{stats.scheduleCount}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-[#d7e2db] shadow-none">
            <CardHeader>
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-base text-[#163300]">Listado priorizado</CardTitle>
                  <CardDescription>Ordenado por días de atraso, del más delicado al más reciente.</CardDescription>
                </div>
                <Button variant="outline" size="sm" className="bg-white" onClick={() => router.push('/collections')}>
                  Volver a Collections
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              {schedules.length === 0 ? (
                <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
                  <CheckCircle2 className="mb-4 h-12 w-12 text-emerald-500" />
                  <h3 className="text-lg font-medium text-slate-900">No hay pagos vencidos</h3>
                  <p className="mt-2 max-w-md text-sm text-slate-500">
                    Excelente. En este momento no hay cuotas vencidas pendientes de gestión.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50/70">
                        <TableHead>Cliente / préstamo</TableHead>
                        <TableHead>Cuota</TableHead>
                        <TableHead>Vencimiento</TableHead>
                        <TableHead>Atraso</TableHead>
                        <TableHead className="text-right">Saldo</TableHead>
                        <TableHead className="text-right">Mora</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {schedules.map((schedule) => {
                        const lateFeeDue = getLateFeeDue(schedule);
                        const totalDue = getTotalDue(schedule);
                        const severity = getSeverity(Number(schedule.days_overdue) || 0);

                        return (
                          <TableRow key={schedule.id} className={`${severity.rowAccent} hover:bg-slate-50`}>
                            <TableCell className="min-w-[240px] py-4 align-top">
                              <div className="space-y-1">
                                <Link href={`/loans/${schedule.loan}`} className="inline-flex items-center gap-2 font-medium text-[#163300] hover:underline">
                                  <User className="h-4 w-4 text-slate-400" />
                                  {schedule.customer_name}
                                </Link>
                                <p className="text-sm text-slate-500">{schedule.loan_number}</p>
                                {schedule.customer_phone && (
                                  <p className="font-mono text-xs text-slate-500">{schedule.customer_phone}</p>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-1">
                                <p className="font-medium text-slate-900">#{schedule.installment_number}</p>
                                <p className="text-xs text-slate-500">Estado: {schedule.status}</p>
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="flex items-center gap-2 text-sm text-slate-700">
                                <Calendar className="h-4 w-4 text-slate-400" />
                                {formatDate(schedule.due_date)}
                              </div>
                            </TableCell>
                            <TableCell className="align-top">
                              <div className="space-y-2">
                                <Badge variant="outline" className={severity.badge}>
                                  {severity.label}
                                </Badge>
                                <div className="flex items-center gap-2 text-sm text-slate-600">
                                  <Clock className="h-4 w-4 text-slate-400" />
                                  {schedule.days_overdue} día(s)
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="text-right align-top font-medium text-slate-900">
                              {formatCurrency(Number(schedule.balance) || 0)}
                            </TableCell>
                            <TableCell className="text-right align-top font-medium text-orange-600">
                              {formatCurrency(lateFeeDue)}
                            </TableCell>
                            <TableCell className="text-right align-top font-semibold text-slate-900">
                              {formatCurrency(totalDue)}
                            </TableCell>
                            <TableCell className="min-w-[220px] text-right align-top">
                              <div className="flex flex-col items-end gap-2">
                                <Button
                                  size="sm"
                                  className="bg-[#163300] hover:bg-[#0f2400]"
                                  onClick={() => router.push(`/payments/new?loan=${schedule.loan}&schedule=${schedule.id}`)}
                                >
                                  <CreditCard className="mr-1.5 h-4 w-4" />
                                  Registrar pago
                                </Button>

                                <div className="flex flex-wrap justify-end gap-2">
                                  {schedule.customer_phone && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="border-green-300 bg-white text-green-700 hover:bg-green-50"
                                      asChild
                                    >
                                      <a href={buildWhatsAppUrl(schedule)} target="_blank" rel="noopener noreferrer">
                                        <MessageCircle className="mr-1.5 h-4 w-4" />
                                        WhatsApp
                                      </a>
                                    </Button>
                                  )}
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="bg-white"
                                    onClick={() => router.push(`/loans/${schedule.loan}`)}
                                  >
                                    <Phone className="mr-1.5 h-4 w-4" />
                                    Ver préstamo
                                  </Button>
                                </div>
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
