'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI, collectionsAPI } from '@/lib/api/loans';
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
  TrendingUp,
  TrendingDown,
  Users,
  DollarSign,
  Phone,
  Calendar,
  AlertCircle,
  CheckCircle,
  Clock,
  Target,
  BarChart3,
} from 'lucide-react';

export default function CollectionReportsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Statistics
  const [loanStats, setLoanStats] = useState({
    total_loans: 0,
    active_loans: 0,
    overdue_loans: 0,
    defaulted_loans: 0,
    total_outstanding: 0,
    total_collected: 0,
  });

  const [reminders, setReminders] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load data only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadReportData();
    }
  }, [isAuthenticated]);

  const loadReportData = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Load statistics and collection data in parallel
      const [stats, remindersData, contactsData] = await Promise.all([
        loansAPI.getStatistics(),
        collectionsAPI.getReminders({ page: 1 }),
        collectionsAPI.getContacts({ page: 1 }),
      ]);

      setLoanStats(stats);
      setReminders(remindersData.results || []);
      setContacts(contactsData.results || []);
    } catch (err: any) {
      console.error('Error loading report data:', err);
      setError('Error al cargar los datos del reporte');
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

  const calculateCollectionRate = () => {
    const total = loanStats.total_collected + loanStats.total_outstanding;
    if (total === 0) return 0;
    return ((loanStats.total_collected / total) * 100).toFixed(1);
  };

  const calculateOverdueRate = () => {
    if (loanStats.active_loans === 0) return 0;
    return ((loanStats.overdue_loans / loanStats.active_loans) * 100).toFixed(1);
  };

  // Reminder statistics
  const pendingReminders = reminders.filter((r) => r.status === 'pending').length;
  const sentReminders = reminders.filter((r) => r.status === 'sent').length;
  const failedReminders = reminders.filter((r) => r.status === 'failed').length;

  // Contact statistics
  const successfulContacts = contacts.filter(
    (c) => c.outcome === 'answered' || c.outcome === 'full_payment' || c.outcome === 'partial_payment'
  ).length;
  const promiseToPay = contacts.filter((c) => c.outcome === 'promise_to_pay').length;
  const noAnswer = contacts.filter((c) => c.outcome === 'no_answer').length;

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/collections"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Volver a Cobranza
          </Link>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <BarChart3 className="h-8 w-8" />
            Reportes de Cobranza
          </h1>
          <p className="text-muted-foreground mt-2">
            Análisis y métricas del proceso de cobranza
          </p>
        </div>
        <Button onClick={() => window.print()}>
          <FileText className="mr-2 h-4 w-4" />
          Imprimir Reporte
        </Button>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
          <p className="text-muted-foreground">Cargando datos del reporte...</p>
        </div>
      ) : (
        <>
          {/* Main KPIs */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Target className="h-5 w-5" />
              Indicadores Clave (KPIs)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Tasa de Recuperación</p>
                      <p className="text-3xl font-bold text-green-600">
                        {calculateCollectionRate()}%
                      </p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-green-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Tasa de Mora</p>
                      <p className="text-3xl font-bold text-red-600">
                        {calculateOverdueRate()}%
                      </p>
                    </div>
                    <TrendingDown className="h-8 w-8 text-red-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Préstamos Morosos</p>
                      <p className="text-3xl font-bold text-orange-600">
                        {loanStats.overdue_loans}
                      </p>
                    </div>
                    <AlertCircle className="h-8 w-8 text-orange-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Cobrado</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {formatCurrency(loanStats.total_collected)}
                      </p>
                    </div>
                    <DollarSign className="h-8 w-8 text-blue-600" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Financial Overview */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Resumen Financiero
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Total Cartera</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">
                    {formatCurrency(loanStats.total_collected + loanStats.total_outstanding)}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Total Cobrado</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(loanStats.total_collected)}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Balance Pendiente</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-orange-600">
                    {formatCurrency(loanStats.total_outstanding)}
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Loan Portfolio Status */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Estado de la Cartera
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">Total Préstamos</p>
                    <p className="text-3xl font-bold">{loanStats.total_loans}</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">Activos</p>
                    <p className="text-3xl font-bold text-green-600">
                      {loanStats.active_loans}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">Morosos</p>
                    <p className="text-3xl font-bold text-orange-600">
                      {loanStats.overdue_loans}
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">En Incumplimiento</p>
                    <p className="text-3xl font-bold text-red-600">
                      {loanStats.defaulted_loans}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Reminder Statistics */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Recordatorios de Pago
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total</p>
                      <p className="text-2xl font-bold">{reminders.length}</p>
                    </div>
                    <Calendar className="h-6 w-6 text-gray-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Pendientes</p>
                      <p className="text-2xl font-bold text-yellow-600">{pendingReminders}</p>
                    </div>
                    <Clock className="h-6 w-6 text-yellow-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Enviados</p>
                      <p className="text-2xl font-bold text-green-600">{sentReminders}</p>
                    </div>
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Fallidos</p>
                      <p className="text-2xl font-bold text-red-600">{failedReminders}</p>
                    </div>
                    <AlertCircle className="h-6 w-6 text-red-600" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Contact Statistics */}
          <div>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Phone className="h-5 w-5" />
              Gestión de Contacto
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Contactos</p>
                      <p className="text-2xl font-bold">{contacts.length}</p>
                    </div>
                    <Users className="h-6 w-6 text-gray-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Exitosos</p>
                      <p className="text-2xl font-bold text-green-600">{successfulContacts}</p>
                    </div>
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Promesa de Pago</p>
                      <p className="text-2xl font-bold text-blue-600">{promiseToPay}</p>
                    </div>
                    <Calendar className="h-6 w-6 text-blue-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Sin Respuesta</p>
                      <p className="text-2xl font-bold text-gray-600">{noAnswer}</p>
                    </div>
                    <Phone className="h-6 w-6 text-gray-600" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Acciones Rápidas</CardTitle>
              <CardDescription>
                Navega a las diferentes secciones de cobranza
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Link href="/loans/overdue">
                <Button variant="outline">
                  <AlertCircle className="mr-2 h-4 w-4" />
                  Ver Préstamos Morosos
                </Button>
              </Link>
              <Link href="/collections/reminders">
                <Button variant="outline">
                  <Calendar className="mr-2 h-4 w-4" />
                  Gestionar Recordatorios
                </Button>
              </Link>
              <Link href="/collections">
                <Button variant="outline">
                  <Phone className="mr-2 h-4 w-4" />
                  Registrar Contacto
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Report Footer */}
          <div className="text-center text-sm text-muted-foreground pt-4 border-t">
            <p>
              Reporte generado el {new Date().toLocaleDateString('es-ES', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })} a las {new Date().toLocaleTimeString('es-ES')}
            </p>
            <p className="mt-1">
              Usuario: {user?.email} | Rol: {user?.role || 'N/A'}
            </p>
          </div>
        </>
      )}
    </div>
  );
}
