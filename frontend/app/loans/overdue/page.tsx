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
  Loader2,
  AlertCircle,
  Phone,
  Mail,
  DollarSign,
  Calendar,
  CreditCard,
  TrendingUp,
} from 'lucide-react';

export default function OverdueLoansPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [loans, setLoans] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalOverdueAmount, setTotalOverdueAmount] = useState(0);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadOverdueLoans();
    }
  }, [isAuthenticated]);

  const loadOverdueLoans = async () => {
    try {
      setIsLoading(true);
      setError('');

      const response = await loansAPI.getLoans({});
      const allLoans = response.results || [];

      const overdueLoans = allLoans.filter((loan: any) =>
        ['active', 'defaulted'].includes(loan.status) &&
        (loan.is_overdue || (loan.days_overdue && loan.days_overdue > 0))
      );

      overdueLoans.sort((a: any, b: any) => (b.days_overdue || 0) - (a.days_overdue || 0));

      setLoans(overdueLoans);

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

  const getSeverityBadge = (days: number) => {
    if (days >= 90) {
      return <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-100 text-red-700">Crítico - {days}d</span>;
    }
    if (days >= 30) {
      return <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-orange-100 text-orange-700">Grave - {days}d</span>;
    }
    return <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-yellow-100 text-yellow-700">Moderado - {days}d</span>;
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const avgDaysOverdue = loans.length > 0
    ? Math.round(loans.reduce((sum, loan) => sum + loan.days_overdue, 0) / loans.length)
    : 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Préstamos Morosos</h1>
            <p className="text-sm text-slate-600 mt-1">
              Préstamos con pagos atrasados que requieren atención
            </p>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Préstamos Morosos</p>
            <p className="text-2xl font-bold text-slate-900">{loans.length}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-orange-100 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-orange-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Monto Total en Mora</p>
            <p className="text-2xl font-bold text-slate-900">{formatCurrency(totalOverdueAmount)}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="h-12 w-12 rounded-xl bg-yellow-100 flex items-center justify-center">
                <Calendar className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
            <p className="text-sm text-slate-600 mb-1">Promedio de Días en Mora</p>
            <p className="text-2xl font-bold text-slate-900">{avgDaysOverdue} días</p>
          </CardContent>
        </Card>
      </div>

      {/* Error */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
          <p className="text-slate-600">Cargando préstamos morosos...</p>
        </div>
      ) : loans.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-green-100 p-6">
                <AlertCircle className="h-12 w-12 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">
                ¡No hay préstamos morosos!
              </h3>
              <p className="text-slate-600">
                Todos los préstamos activos están al día con sus pagos.
              </p>
              <Link href="/dashboard">
                <Button className="bg-blue-600 hover:bg-blue-700">Volver al Dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg font-bold text-slate-900">
              Lista de Préstamos en Mora
            </CardTitle>
            <CardDescription>
              Ordenados por días de atraso (mayor a menor)
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Cliente</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Préstamo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Balance</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Pagado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Mora</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Contacto</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loans.map((loan) => (
                  <tr key={loan.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => router.push(`/loans/${loan.id}`)}>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{loan.customer_name}</p>
                        <p className="text-xs text-slate-500">{formatDate(loan.disbursement_date)}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900">{loan.loan_number}</p>
                        <p className="text-xs text-slate-500 capitalize">{loan.loan_type}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-bold text-red-600">{formatCurrency(loan.outstanding_balance)}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="font-medium text-green-600">{formatCurrency(loan.total_paid || 0)}</p>
                    </td>
                    <td className="py-3 px-4">
                      {getSeverityBadge(loan.days_overdue)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        {loan.customer_phone && (
                          <a
                            href={`tel:${loan.customer_phone}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <Phone className="h-4 w-4" />
                          </a>
                        )}
                        {loan.customer_email && (
                          <a
                            href={`mailto:${loan.customer_email}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-purple-600 hover:text-purple-800"
                          >
                            <Mail className="h-4 w-4" />
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/loans/${loan.id}`);
                          }}
                        >
                          Ver
                        </Button>
                        <Link href={`/payments/new?loan=${loan.id}`}>
                          <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-700"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <CreditCard className="mr-1 h-3 w-3" />
                            Pagar
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
