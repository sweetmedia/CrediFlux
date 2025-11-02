'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
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
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  AlertCircle,
  TrendingUp,
  DollarSign,
  Calendar,
  Bell,
  Users,
  Phone,
  Mail,
  MessageSquare,
  Clock,
  Target,
  CheckCircle,
  XCircle,
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
      const totalLateFees = overdueResponse.reduce(
        (sum, s) => {
          const lateFeeDue = (Number(s.late_fee_amount) || 0) - (Number(s.late_fee_paid) || 0);
          return sum + lateFeeDue;
        },
        0
      );

      setStats({
        overdueSchedules: overdueResponse.length,
        totalOverdue,
        totalLateFees,
        pendingReminders: pendingRemindersResponse.length,
        promisesToday: promisesResponse.length,
        brokenPromises: brokenPromisesResponse.length,
        escalationRequired: escalationResponse.length,
      });

      setRecentContacts(recentContactsResponse.slice(0, 5));
    } catch (err: any) {
      console.error('Error loading dashboard data:', err);
      setError('Error al cargar datos del dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
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

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard de Cobranza</h1>
            <p className="text-sm text-slate-600 mt-1">
              Resumen de actividades y métricas de cobranza
            </p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Pagos Vencidos</p>
            <p className="text-2xl font-bold text-slate-900">{stats.overdueSchedules}</p>
            <p className="text-xs text-slate-500 mt-2">{formatCurrency(stats.totalOverdue)} vencido</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-orange-100 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-orange-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Mora Acumulada</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(stats.totalLateFees)}</p>
            <p className="text-xs text-slate-500 mt-2">Cargos por atraso</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-blue-100 flex items-center justify-center">
                <Bell className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Recordatorios</p>
            <p className="text-2xl font-bold text-slate-900">{stats.pendingReminders}</p>
            <p className="text-xs text-slate-500 mt-2">Pendientes por enviar</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-green-100 flex items-center justify-center">
                <Calendar className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Promesas Hoy</p>
            <p className="text-2xl font-bold text-slate-900">{stats.promisesToday}</p>
            <p className="text-xs text-slate-500 mt-2">Compromisos de pago</p>
          </CardContent>
        </Card>
      </div>

      {/* Action Items & Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        {/* Urgent Actions */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-slate-900">Acciones Urgentes</CardTitle>
            <CardDescription>Requieren atención inmediata</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.escalationRequired > 0 && (
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <div>
                    <p className="font-medium text-sm text-slate-900">Escalamiento Requerido</p>
                    <p className="text-xs text-slate-600">
                      {stats.escalationRequired} caso(s) necesitan supervisor
                    </p>
                  </div>
                </div>
                <Button size="sm" variant="outline">Ver</Button>
              </div>
            )}

            {stats.brokenPromises > 0 && (
              <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                <div className="flex items-center gap-3">
                  <XCircle className="h-5 w-5 text-orange-600" />
                  <div>
                    <p className="font-medium text-sm text-slate-900">Promesas Incumplidas</p>
                    <p className="text-xs text-slate-600">
                      {stats.brokenPromises} promesa(s) no cumplida(s)
                    </p>
                  </div>
                </div>
                <Button size="sm" variant="outline">Ver</Button>
              </div>
            )}

            {stats.overdueSchedules > 10 && (
              <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-yellow-600" />
                  <div>
                    <p className="font-medium text-sm text-slate-900">Alto Volumen Vencido</p>
                    <p className="text-xs text-slate-600">
                      {stats.overdueSchedules} pagos requieren seguimiento
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => router.push('/schedules/overdue')}
                >
                  Ver
                </Button>
              </div>
            )}

            {stats.escalationRequired === 0 && stats.brokenPromises === 0 && stats.overdueSchedules <= 10 && (
              <div className="flex items-center justify-center py-8 text-center">
                <div>
                  <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                  <p className="text-sm text-slate-600">No hay acciones urgentes</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-slate-900">Acciones Rápidas</CardTitle>
            <CardDescription>Acceso directo a funciones comunes</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => router.push('/schedules/overdue')}
            >
              <AlertCircle className="h-4 w-4 mr-2" />
              Ver Pagos Vencidos
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => router.push('/payments/new')}
            >
              <DollarSign className="h-4 w-4 mr-2" />
              Registrar Pago
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => router.push('/collections/contacts/new')}
            >
              <Phone className="h-4 w-4 mr-2" />
              Registrar Contacto
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => router.push('/collections/reminders')}
            >
              <Bell className="h-4 w-4 mr-2" />
              Gestionar Recordatorios
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => router.push('/collections/reports')}
            >
              <Target className="h-4 w-4 mr-2" />
              Ver Reportes
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity Table */}
      <Card className="border-slate-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg font-bold text-slate-900">Actividad Reciente</CardTitle>
          <CardDescription>Últimos contactos de cobranza</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {recentContacts.length === 0 ? (
            <div className="text-center py-12">
              <Users className="h-12 w-12 text-slate-400 mx-auto mb-2" />
              <p className="text-sm text-slate-600">No hay contactos registrados aún</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Cliente</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Tipo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Resultado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {recentContacts.map((contact) => (
                  <tr key={contact.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4">
                      <p className="font-medium text-slate-900">{contact.customer_name}</p>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        {contact.contact_type === 'phone_call' && <Phone className="h-4 w-4 text-blue-600" />}
                        {contact.contact_type === 'email' && <Mail className="h-4 w-4 text-purple-600" />}
                        {contact.contact_type === 'whatsapp' && <MessageSquare className="h-4 w-4 text-green-600" />}
                        <span className="text-sm text-slate-900">{contact.contact_type_display}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm text-slate-600">{contact.outcome_display}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm text-slate-600">{formatDateTime(contact.contact_date)}</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
