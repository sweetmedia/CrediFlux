'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI } from '@/lib/api/loans';
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
  ArrowLeft,
  Loader2,
  AlertCircle,
  Phone,
  Mail,
  DollarSign,
  Calendar,
  User,
  CreditCard,
} from 'lucide-react';

export default function OverdueLoansPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [loans, setLoans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalOverdueAmount, setTotalOverdueAmount] = useState(0);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load overdue loans only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadOverdueLoans();
    }
  }, [isAuthenticated]);

  const loadOverdueLoans = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Get all loans (active and defaulted) and filter those with overdue payments
      const response = await loansAPI.getLoans({});
      const allLoans = response.results || [];

      // Filter loans that:
      // 1. Are active or defaulted (not paid, rejected, or written off)
      // 2. Have is_overdue = true OR days_overdue > 0
      const overdueLoans = allLoans.filter((loan: any) =>
        ['active', 'defaulted'].includes(loan.status) &&
        (loan.is_overdue || (loan.days_overdue && loan.days_overdue > 0))
      );

      // Sort by days overdue (descending)
      overdueLoans.sort((a: any, b: any) => (b.days_overdue || 0) - (a.days_overdue || 0));

      setLoans(overdueLoans);

      // Calculate total overdue amount
      const total = overdueLoans.reduce(
        (sum: number, loan: any) => sum + (loan.outstanding_balance || 0),
        0
      );
      setTotalOverdueAmount(total);
    } catch (err: any) {
      console.error('Error loading overdue loans:', err);
      setError('Error al cargar los préstamos morosos');
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getSeverityColor = (days: number) => {
    if (days >= 90) return 'bg-red-100 border-red-500 text-red-900';
    if (days >= 30) return 'bg-orange-100 border-orange-500 text-orange-900';
    return 'bg-yellow-100 border-yellow-500 text-yellow-900';
  };

  const getSeverityLabel = (days: number) => {
    if (days >= 90) return 'Crítico';
    if (days >= 30) return 'Grave';
    return 'Moderado';
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <AlertCircle className="h-8 w-8 text-red-600" />
              Préstamos Morosos
            </h1>
            <p className="text-gray-600 mt-1">
              Préstamos con pagos atrasados que requieren atención
            </p>
          </div>
          <Link href="/dashboard">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver al Dashboard
            </Button>
          </Link>
        </div>

        {/* Summary Card */}
        <Card className="mb-6 border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-900">
              <AlertCircle className="h-5 w-5" />
              Resumen de Mora
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <p className="text-sm text-gray-600 mb-1">Total de Préstamos Morosos</p>
                <p className="text-3xl font-bold text-red-600">{loans.length}</p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <p className="text-sm text-gray-600 mb-1">Monto Total en Mora</p>
                <p className="text-3xl font-bold text-red-600">
                  {formatCurrency(totalOverdueAmount)}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-red-200">
                <p className="text-sm text-gray-600 mb-1">Promedio de Días en Mora</p>
                <p className="text-3xl font-bold text-red-600">
                  {loans.length > 0
                    ? Math.round(
                        loans.reduce((sum, loan) => sum + loan.days_overdue, 0) / loans.length
                      )
                    : 0}{' '}
                  días
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Content */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando préstamos morosos...</p>
          </div>
        ) : loans.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-green-100 p-6">
                  <AlertCircle className="h-12 w-12 text-green-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  ¡No hay préstamos morosos!
                </h3>
                <p className="text-gray-600">
                  Todos los préstamos activos están al día con sus pagos.
                </p>
                <Link href="/dashboard">
                  <Button>Volver al Dashboard</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {loans.map((loan) => (
              <Card
                key={loan.id}
                className={`border-l-4 transition-shadow hover:shadow-lg ${getSeverityColor(
                  loan.days_overdue
                )}`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="flex items-center gap-2">
                        <User className="h-5 w-5" />
                        {loan.customer_name}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        Préstamo #{loan.loan_number}
                      </CardDescription>
                    </div>
                    <div className="text-right">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-current">
                        <AlertCircle className="h-4 w-4" />
                        <span className="font-semibold">
                          {loan.days_overdue} días - {getSeverityLabel(loan.days_overdue)}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div className="flex items-center gap-3 bg-white rounded-lg p-3 border">
                      <DollarSign className="h-8 w-8 text-blue-600" />
                      <div>
                        <p className="text-xs text-gray-600">Balance Pendiente</p>
                        <p className="text-lg font-bold">{formatCurrency(loan.outstanding_balance)}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 bg-white rounded-lg p-3 border">
                      <CreditCard className="h-8 w-8 text-green-600" />
                      <div>
                        <p className="text-xs text-gray-600">Total Pagado</p>
                        <p className="text-lg font-bold">
                          {formatCurrency(loan.total_paid || 0)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 bg-white rounded-lg p-3 border">
                      <Calendar className="h-8 w-8 text-orange-600" />
                      <div>
                        <p className="text-xs text-gray-600">Fecha de Desembolso</p>
                        <p className="text-sm font-semibold">
                          {formatDate(loan.disbursement_date)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 bg-white rounded-lg p-3 border">
                      <AlertCircle className="h-8 w-8 text-red-600" />
                      <div>
                        <p className="text-xs text-gray-600">Estado</p>
                        <p className="text-sm font-semibold capitalize">{loan.status}</p>
                      </div>
                    </div>
                  </div>

                  {/* Customer Contact Info */}
                  {(loan.customer_phone || loan.customer_email) && (
                    <div className="bg-white rounded-lg p-3 border mb-4">
                      <p className="text-sm font-semibold text-gray-700 mb-2">
                        Información de Contacto:
                      </p>
                      <div className="flex flex-wrap gap-4">
                        {loan.customer_phone && (
                          <a
                            href={`tel:${loan.customer_phone}`}
                            className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                          >
                            <Phone className="h-4 w-4" />
                            {loan.customer_phone}
                          </a>
                        )}
                        {loan.customer_email && (
                          <a
                            href={`mailto:${loan.customer_email}`}
                            className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                          >
                            <Mail className="h-4 w-4" />
                            {loan.customer_email}
                          </a>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex flex-wrap gap-3">
                    <Link href={`/loans/${loan.id}`}>
                      <Button variant="outline" size="sm">
                        Ver Detalles
                      </Button>
                    </Link>
                    <Link href={`/payments/new?loan=${loan.id}`}>
                      <Button size="sm">
                        <CreditCard className="mr-2 h-4 w-4" />
                        Registrar Pago
                      </Button>
                    </Link>
                    {loan.customer_phone && (
                      <a href={`tel:${loan.customer_phone}`}>
                        <Button variant="outline" size="sm">
                          <Phone className="mr-2 h-4 w-4" />
                          Llamar Cliente
                        </Button>
                      </a>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
