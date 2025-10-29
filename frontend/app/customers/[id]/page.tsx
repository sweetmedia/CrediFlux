'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { customersAPI } from '@/lib/api/customers';
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
  User,
  Mail,
  Phone,
  MapPin,
  Briefcase,
  DollarSign,
  Calendar,
  IdCard,
  FileText,
  CreditCard,
  Plus,
  Edit,
  TrendingUp,
  AlertCircle,
} from 'lucide-react';

interface Customer {
  id: string;
  customer_id: string;
  first_name: string;
  last_name: string;
  middle_name?: string;
  full_name: string;
  date_of_birth: string;
  gender?: string;
  email: string;
  phone: string;
  alternate_phone?: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  country: string;
  postal_code: string;
  id_type: string;
  id_number: string;
  id_expiry_date?: string;
  employment_status?: string;
  employer_name?: string;
  occupation?: string;
  monthly_income?: number;
  credit_score?: number;
  status: string;
  notes?: string;
  total_loans: number;
  active_loans: number;
  created_at: string;
  updated_at: string;
}

interface Loan {
  id: string;
  loan_number: string;
  loan_type: string;
  principal_amount: number;
  interest_rate: number;
  term_months: number;
  payment_frequency: string;
  disbursement_date: string;
  status: string;
  outstanding_balance: number;
  total_paid: number;
  days_overdue?: number;
}

export default function CustomerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const customerId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load customer data
  useEffect(() => {
    if (isAuthenticated && customerId) {
      loadCustomerData();
    }
  }, [isAuthenticated, customerId]);

  const loadCustomerData = async () => {
    try {
      setIsLoading(true);
      setError('');

      const [customerData, loansData] = await Promise.all([
        customersAPI.getCustomer(customerId),
        customersAPI.getCustomerLoans(customerId).catch(() => []),
      ]);

      setCustomer(customerData);
      setLoans(loansData);
    } catch (err: any) {
      console.error('Error loading customer:', err);
      setError('Error al cargar los datos del cliente');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: string) => {
    const statusStyles: Record<string, string> = {
      active: 'bg-green-50 text-green-700 border-green-200',
      inactive: 'bg-gray-50 text-gray-700 border-gray-200',
      blacklisted: 'bg-red-50 text-red-700 border-red-200',
      pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      approved: 'bg-blue-50 text-blue-700 border-blue-200',
      paid: 'bg-gray-50 text-gray-700 border-gray-200',
      defaulted: 'bg-red-50 text-red-700 border-red-200',
    };

    const statusLabels: Record<string, string> = {
      active: 'Activo',
      inactive: 'Inactivo',
      blacklisted: 'Lista Negra',
      pending: 'Pendiente',
      approved: 'Aprobado',
      paid: 'Pagado',
      defaulted: 'Moroso',
    };

    return (
      <span
        className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium border ${
          statusStyles[status] || 'bg-gray-50 text-gray-700 border-gray-200'
        }`}
      >
        {statusLabels[status] || status}
      </span>
    );
  };

  const getLoanTypeBadge = (type: string) => {
    const typeLabels: Record<string, string> = {
      personal: 'Personal',
      auto: 'Auto',
      mortgage: 'Hipoteca',
      business: 'Empresarial',
      other: 'Otro',
    };

    return typeLabels[type] || type;
  };

  const calculateTotalBalance = () => {
    return loans.reduce((sum, loan) => sum + (loan.outstanding_balance || 0), 0);
  };

  const calculateTotalPaid = () => {
    return loans.reduce((sum, loan) => sum + (loan.total_paid || 0), 0);
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
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/customers">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Volver
                </Button>
              </Link>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <User className="h-8 w-8 text-blue-600" />
              Detalles del Cliente
            </h1>
            <p className="text-gray-600 mt-1">
              Información completa y préstamos del cliente
            </p>
          </div>
          {customer && (
            <div className="flex gap-2">
              <Link href={`/customers/${customerId}/edit`}>
                <Button variant="outline">
                  <Edit className="mr-2 h-4 w-4" />
                  Editar Cliente
                </Button>
              </Link>
              <Link href={`/loans/new?customer=${customerId}`}>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo Préstamo
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando información del cliente...</p>
          </div>
        ) : customer ? (
          <div className="space-y-6">
            {/* Customer Header Card */}
            <Card className="border-2 border-blue-100">
              <CardContent className="pt-6">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-blue-100 p-4">
                        <User className="h-8 w-8 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <h2 className="text-2xl font-bold text-gray-900 mb-1">
                          {customer.full_name}
                        </h2>
                        <p className="text-gray-600 text-sm mb-3">
                          ID: {customer.customer_id}
                        </p>
                        {getStatusBadge(customer.status)}
                      </div>
                    </div>
                  </div>

                  {/* Quick Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-blue-50 rounded-lg">
                      <p className="text-sm text-gray-600">Total Préstamos</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {customer.total_loans}
                      </p>
                    </div>
                    <div className="text-center p-3 bg-green-50 rounded-lg">
                      <p className="text-sm text-gray-600">Activos</p>
                      <p className="text-2xl font-bold text-green-600">
                        {customer.active_loans}
                      </p>
                    </div>
                    <div className="text-center p-3 bg-orange-50 rounded-lg col-span-2 md:col-span-1">
                      <p className="text-sm text-gray-600">Balance Total</p>
                      <p className="text-xl font-bold text-orange-600">
                        {formatCurrency(calculateTotalBalance())}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Information Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Personal Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <User className="h-5 w-5 text-blue-600" />
                    Información Personal
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-gray-600">Nombre Completo</p>
                      <p className="font-semibold">{customer.full_name}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Fecha de Nacimiento</p>
                      <p className="font-semibold">{formatDate(customer.date_of_birth)}</p>
                    </div>
                    {customer.gender && (
                      <div>
                        <p className="text-gray-600">Género</p>
                        <p className="font-semibold">
                          {customer.gender === 'M'
                            ? 'Masculino'
                            : customer.gender === 'F'
                            ? 'Femenino'
                            : 'Otro'}
                        </p>
                      </div>
                    )}
                    <div>
                      <p className="text-gray-600">Estado</p>
                      <p className="font-semibold capitalize">{customer.status}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Contact Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Mail className="h-5 w-5 text-blue-600" />
                    Información de Contacto
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Mail className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-600">Email</p>
                      <a
                        href={`mailto:${customer.email}`}
                        className="text-sm font-semibold text-blue-600 hover:underline"
                      >
                        {customer.email}
                      </a>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-600">Teléfono</p>
                      <a
                        href={`tel:${customer.phone}`}
                        className="text-sm font-semibold text-blue-600 hover:underline"
                      >
                        {customer.phone}
                      </a>
                    </div>
                  </div>
                  {customer.alternate_phone && (
                    <div className="flex items-center gap-3">
                      <Phone className="h-4 w-4 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-600">Teléfono Alternativo</p>
                        <a
                          href={`tel:${customer.alternate_phone}`}
                          className="text-sm font-semibold text-blue-600 hover:underline"
                        >
                          {customer.alternate_phone}
                        </a>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Address */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-blue-600" />
                    Dirección
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-sm">{customer.address_line1}</p>
                  {customer.address_line2 && (
                    <p className="text-sm">{customer.address_line2}</p>
                  )}
                  <p className="text-sm">
                    {customer.city}, {customer.state} {customer.postal_code}
                  </p>
                  <p className="text-sm font-semibold">{customer.country}</p>
                </CardContent>
              </Card>

              {/* Identification */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <IdCard className="h-5 w-5 text-blue-600" />
                    Identificación
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-600">Tipo de Documento</p>
                    <p className="text-sm font-semibold capitalize">
                      {customer.id_type === 'cedula'
                        ? 'Cédula'
                        : customer.id_type === 'passport'
                        ? 'Pasaporte'
                        : 'Licencia de Conducir'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-600">Número</p>
                    <p className="text-sm font-semibold">{customer.id_number}</p>
                  </div>
                  {customer.id_expiry_date && (
                    <div>
                      <p className="text-xs text-gray-600">Fecha de Vencimiento</p>
                      <p className="text-sm font-semibold">
                        {formatDate(customer.id_expiry_date)}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Employment Information */}
              {(customer.employment_status ||
                customer.employer_name ||
                customer.occupation ||
                customer.monthly_income) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Briefcase className="h-5 w-5 text-blue-600" />
                      Información Laboral
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {customer.employment_status && (
                      <div>
                        <p className="text-xs text-gray-600">Estado Laboral</p>
                        <p className="text-sm font-semibold capitalize">
                          {customer.employment_status.replace('_', ' ')}
                        </p>
                      </div>
                    )}
                    {customer.employer_name && (
                      <div>
                        <p className="text-xs text-gray-600">Empleador</p>
                        <p className="text-sm font-semibold">{customer.employer_name}</p>
                      </div>
                    )}
                    {customer.occupation && (
                      <div>
                        <p className="text-xs text-gray-600">Ocupación</p>
                        <p className="text-sm font-semibold">{customer.occupation}</p>
                      </div>
                    )}
                    {customer.monthly_income && (
                      <div>
                        <p className="text-xs text-gray-600">Ingreso Mensual</p>
                        <p className="text-sm font-semibold">
                          {formatCurrency(customer.monthly_income)}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Financial Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-blue-600" />
                    Información Financiera
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {customer.credit_score && (
                    <div>
                      <p className="text-xs text-gray-600">Score de Crédito</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {customer.credit_score}
                      </p>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-gray-600">Total Pagado</p>
                      <p className="text-sm font-semibold text-green-600">
                        {formatCurrency(calculateTotalPaid())}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Balance Pendiente</p>
                      <p className="text-sm font-semibold text-orange-600">
                        {formatCurrency(calculateTotalBalance())}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Notes */}
            {customer.notes && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-600" />
                    Notas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {customer.notes}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Loans Section */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <CreditCard className="h-5 w-5 text-blue-600" />
                    Préstamos ({loans.length})
                  </CardTitle>
                  <Link href={`/loans/new?customer=${customerId}`}>
                    <Button size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Nuevo Préstamo
                    </Button>
                  </Link>
                </div>
                <CardDescription>
                  Historial de préstamos del cliente
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loans.length === 0 ? (
                  <div className="text-center py-8">
                    <CreditCard className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">
                      Este cliente no tiene préstamos registrados
                    </p>
                    <Link href={`/loans/new?customer=${customerId}`}>
                      <Button className="mt-4" size="sm">
                        <Plus className="mr-2 h-4 w-4" />
                        Crear Primer Préstamo
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {loans.map((loan) => (
                      <div
                        key={loan.id}
                        className="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => router.push(`/loans/${loan.id}`)}
                      >
                        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-semibold text-gray-900">
                                {loan.loan_number}
                              </h4>
                              {getStatusBadge(loan.status)}
                            </div>
                            <p className="text-sm text-gray-600">
                              {getLoanTypeBadge(loan.loan_type)} •{' '}
                              {loan.payment_frequency} • {loan.term_months} meses
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              Desembolsado: {formatDate(loan.disbursement_date)}
                            </p>
                          </div>

                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <p className="text-xs text-gray-600">Monto</p>
                              <p className="font-semibold">
                                {formatCurrency(loan.principal_amount)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-600">Pagado</p>
                              <p className="font-semibold text-green-600">
                                {formatCurrency(loan.total_paid || 0)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-600">Balance</p>
                              <p className="font-semibold text-orange-600">
                                {formatCurrency(loan.outstanding_balance)}
                              </p>
                            </div>
                          </div>

                          {loan.days_overdue && loan.days_overdue > 0 && (
                            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                              <div className="flex items-center gap-2 text-red-700">
                                <AlertCircle className="h-4 w-4" />
                                <span className="text-sm font-semibold">
                                  {loan.days_overdue} días de mora
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5 text-blue-600" />
                  Información del Sistema
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Fecha de Registro</p>
                    <p className="font-semibold">{formatDate(customer.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Última Actualización</p>
                    <p className="font-semibold">{formatDate(customer.updated_at)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-600">Cliente no encontrado</p>
              <Link href="/customers">
                <Button className="mt-4" variant="outline">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver a Clientes
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
