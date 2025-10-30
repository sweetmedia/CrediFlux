'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
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
  TrendingDown,
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
  ArrowRight,
  ArrowLeft,
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

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load dashboard data
  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated]);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Load all data in parallel
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

      // Calculate overdue stats
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
    return new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(amount);
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

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/loans"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Volver a Préstamos
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard de Cobranza</h1>
        <p className="text-muted-foreground mt-2">
          Resumen de actividades y métricas de cobranza
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Main Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pagos Vencidos</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {stats.overdueSchedules}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatCurrency(stats.totalOverdue)} vencido
            </p>
            <Button
              variant="link"
              size="sm"
              className="p-0 h-auto mt-2 text-red-600"
              onClick={() => router.push('/schedules/overdue')}
            >
              Ver detalles <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-orange-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mora Acumulada</CardTitle>
            <TrendingUp className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(stats.totalLateFees)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Cargos por atraso
            </p>
            <Button
              variant="link"
              size="sm"
              className="p-0 h-auto mt-2 text-orange-600"
              onClick={() => router.push('/schedules/overdue')}
            >
              Ver detalles <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recordatorios Pendientes</CardTitle>
            <Bell className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {stats.pendingReminders}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Por enviar
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Promesas Hoy</CardTitle>
            <Calendar className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {stats.promisesToday}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Compromisos de pago
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Action Items & Alerts */}
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        {/* Urgent Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Acciones Urgentes</CardTitle>
            <CardDescription>
              Requieren atención inmediata
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.escalationRequired > 0 && (
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  <div>
                    <p className="font-medium text-sm">Escalamiento Requerido</p>
                    <p className="text-xs text-muted-foreground">
                      {stats.escalationRequired} caso(s) necesitan supervisor
                    </p>
                  </div>
                </div>
                <Button size="sm" variant="outline">
                  Ver
                </Button>
              </div>
            )}

            {stats.brokenPromises > 0 && (
              <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                <div className="flex items-center gap-3">
                  <XCircle className="h-5 w-5 text-orange-600" />
                  <div>
                    <p className="font-medium text-sm">Promesas Incumplidas</p>
                    <p className="text-xs text-muted-foreground">
                      {stats.brokenPromises} promesa(s) no cumplida(s)
                    </p>
                  </div>
                </div>
                <Button size="sm" variant="outline">
                  Ver
                </Button>
              </div>
            )}

            {stats.overdueSchedules > 10 && (
              <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-yellow-600" />
                  <div>
                    <p className="font-medium text-sm">Alto Volumen Vencido</p>
                    <p className="text-xs text-muted-foreground">
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
                  <p className="text-sm text-gray-600">
                    No hay acciones urgentes
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Acciones Rápidas</CardTitle>
            <CardDescription>
              Acceso directo a funciones comunes
            </CardDescription>
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

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Actividad Reciente</CardTitle>
          <CardDescription>
            Últimos contactos de cobranza
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recentContacts.length === 0 ? (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600">
                No hay contactos registrados aún
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentContacts.map((contact) => (
                <div
                  key={contact.id}
                  className="flex items-start justify-between p-3 border rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-start gap-3">
                    {contact.contact_type === 'phone_call' && (
                      <Phone className="h-4 w-4 text-blue-600 mt-0.5" />
                    )}
                    {contact.contact_type === 'email' && (
                      <Mail className="h-4 w-4 text-purple-600 mt-0.5" />
                    )}
                    {contact.contact_type === 'whatsapp' && (
                      <MessageSquare className="h-4 w-4 text-green-600 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="font-medium text-sm">
                        {contact.customer_name}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {contact.outcome_display}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {formatDateTime(contact.contact_date)}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">
                    {contact.contact_type_display}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
