'use client';

import { useState, useEffect } from 'react';
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
  DollarSign,
  User,
  Phone,
  CreditCard,
  TrendingUp,
  Clock,
  ArrowLeft,
} from 'lucide-react';
import { LoanSchedule } from '@/types';

export default function OverdueSchedulesPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [schedules, setSchedules] = useState<LoanSchedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Stats
  const [totalOverdue, setTotalOverdue] = useState(0);
  const [totalLateFees, setTotalLateFees] = useState(0);
  const [scheduleCount, setScheduleCount] = useState(0);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load overdue schedules
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
      setSchedules(response || []);
      setScheduleCount(response.length);

      // Calculate stats
      const overdue = response.reduce((sum, s) => sum + (Number(s.balance) || 0), 0);
      const lateFees = response.reduce((sum, s) => {
        const lateFeeDue = (Number(s.late_fee_amount) || 0) - (Number(s.late_fee_paid) || 0);
        return sum + lateFeeDue;
      }, 0);

      setTotalOverdue(overdue);
      setTotalLateFees(lateFees);
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
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getDaysOverdueBadge = (days: number) => {
    if (days <= 7) {
      return <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">{days} día(s)</Badge>;
    } else if (days <= 30) {
      return <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">{days} día(s)</Badge>;
    } else {
      return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">{days} día(s)</Badge>;
    }
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
          href="/collections"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Volver a Cobranza
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Pagos Vencidos</h1>
        <p className="text-muted-foreground mt-2">
          Cronogramas de pago que requieren atención inmediata
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Vencido</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {formatCurrency(totalOverdue)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {scheduleCount} pago(s) vencido(s)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mora Acumulada</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {formatCurrency(totalLateFees)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Cargos por mora pendientes
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total a Cobrar</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(totalOverdue + totalLateFees)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Principal + mora
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Overdue Schedules Table */}
      <Card>
        <CardHeader>
          <CardTitle>Listado de Pagos Vencidos</CardTitle>
          <CardDescription>
            Ordenados por días de atraso (mayor a menor)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {schedules.length === 0 ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No hay pagos vencidos
              </h3>
              <p className="text-gray-500">
                ¡Excelente! Todos los pagos están al día.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Préstamo</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Cuota #</TableHead>
                    <TableHead>Vencimiento</TableHead>
                    <TableHead>Días Atraso</TableHead>
                    <TableHead className="text-right">Saldo</TableHead>
                    <TableHead className="text-right">Mora</TableHead>
                    <TableHead className="text-right">Total</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {schedules.map((schedule) => {
                    const lateFeeDue = (Number(schedule.late_fee_amount) || 0) - (Number(schedule.late_fee_paid) || 0);
                    const totalDue = (Number(schedule.balance) || 0) + lateFeeDue;

                    return (
                      <TableRow key={schedule.id}>
                        <TableCell className="font-medium">
                          <Link
                            href={`/loans/${schedule.loan}`}
                            className="text-blue-600 hover:underline"
                          >
                            {schedule.loan_number}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            <span>{schedule.customer_name}</span>
                          </div>
                        </TableCell>
                        <TableCell>{schedule.installment_number}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            {formatDate(schedule.due_date)}
                          </div>
                        </TableCell>
                        <TableCell>
                          {getDaysOverdueBadge(schedule.days_overdue)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(schedule.balance)}
                        </TableCell>
                        <TableCell className="text-right text-orange-600 font-medium">
                          {formatCurrency(lateFeeDue)}
                        </TableCell>
                        <TableCell className="text-right font-bold">
                          {formatCurrency(totalDue)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => router.push(`/payments/new?loan=${schedule.loan}&schedule=${schedule.id}`)}
                            >
                              <CreditCard className="h-4 w-4 mr-1" />
                              Pagar
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => router.push(`/loans/${schedule.loan}`)}
                            >
                              <Phone className="h-4 w-4 mr-1" />
                              Contactar
                            </Button>
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
  );
}
