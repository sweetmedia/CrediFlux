'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { customersAPI } from '@/lib/api/customers';
import { contractsAPI } from '@/lib/api/contracts';
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
  MessageCircle,
  MapPin,
  Briefcase,
  IdCard,
  FileText,
  CreditCard,
  Plus,
  Edit,
  AlertCircle,
  FileCheck,
  Eye,
} from 'lucide-react';
import { CustomerDocuments } from '@/components/documents';
import { formatDisplayIDNumber } from '@/lib/utils/id-formatter';

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

interface Contract {
  id: string;
  contract_number: string;
  loan: string;
  loan_number: string;
  status: 'draft' | 'pending_signature' | 'signed' | 'active' | 'completed' | 'cancelled';
  customer_signed_at?: string;
  officer_signed_at?: string;
  generated_at: string;
  is_fully_signed: boolean;
  template_name?: string;
}

export default function CustomerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const customerId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
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

      // Load contracts for all customer loans
      if (loansData && loansData.length > 0) {
        try {
          const allContracts = await Promise.all(
            loansData.map(loan =>
              contractsAPI.getContracts({ loan: loan.id }).then(response => response.results || [])
            )
          );
          // Flatten the array of arrays and filter only signed/active/completed contracts
          const customerContracts = allContracts.flat().filter(contract =>
            ['signed', 'active', 'completed'].includes(contract.status)
          );
          setContracts(customerContracts);
        } catch (contractErr) {
          console.error('Error loading contracts:', contractErr);
          // Don't show error to user, just log it
        }
      }
    } catch (err: any) {
      console.error('Error loading customer:', err);
      setError('Error al cargar los datos del cliente');
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

  const getContractStatusBadge = (status: string) => {
    const statusStyles: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-800 border-slate-200',
      pending_signature: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      signed: 'bg-blue-100 text-blue-800 border-blue-200',
      active: 'bg-green-100 text-green-800 border-green-200',
      completed: 'bg-purple-100 text-purple-800 border-purple-200',
      cancelled: 'bg-red-100 text-red-800 border-red-200',
    };

    const statusLabels: Record<string, string> = {
      draft: 'Borrador',
      pending_signature: 'Pendiente Firma',
      signed: 'Firmado',
      active: 'Activo',
      completed: 'Completado',
      cancelled: 'Cancelado',
    };

    return (
      <span
        className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium border ${
          statusStyles[status] || 'bg-gray-50 text-gray-700 border-gray-200'
        }`}
      >
        {statusLabels[status] || status}
      </span>
    );
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
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <Link href="/customers">
                <Button variant="outline" size="sm" className="bg-white">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <User className="h-3.5 w-3.5" />
                Perfil del cliente
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">
              Cliente y relación crediticia
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Vista central del cliente, sus préstamos, contratos y documentos.
            </p>
          </div>
          {customer && (
            <div className="flex flex-wrap gap-2">
              <Link href={`/customers/${customerId}/edit`}>
                <Button variant="outline" className="bg-white">
                  <Edit className="mr-2 h-4 w-4" />
                  Editar cliente
                </Button>
              </Link>
              <Link href={`/loans/new?customer=${customerId}`}>
                <Button className="bg-[#163300] hover:bg-[#0f2400]">
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo préstamo
                </Button>
              </Link>
            </div>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="mb-4 h-10 w-10 animate-spin text-[#163300]" />
            <p className="text-sm text-slate-600">Cargando información del cliente...</p>
          </div>
        ) : customer ? (
          <div className="space-y-6">
            <Card className="overflow-hidden border-[#d7e2db] shadow-none">
              <CardContent className="p-0">
                <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
                  <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex items-start gap-4">
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/15 bg-white/10">
                        <User className="h-8 w-8" />
                      </div>
                      <div>
                        <p className="text-sm text-white/70">Cliente</p>
                        <h2 className="mt-1 text-3xl font-semibold">{customer.full_name}</h2>
                        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-white/80">
                          <span>ID interno: {customer.customer_id}</span>
                          <span>•</span>
                          <span>{formatDisplayIDNumber(customer.id_number, customer.id_type)}</span>
                        </div>
                        <div className="mt-4">{getStatusBadge(customer.status)}</div>
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[360px] lg:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                        <p className="text-xs uppercase tracking-wide text-white/65">Préstamos</p>
                        <p className="mt-2 text-3xl font-semibold">{customer.total_loans}</p>
                        <p className="mt-1 text-xs text-white/70">Historial total</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
                        <p className="text-xs uppercase tracking-wide text-white/65">Activos</p>
                        <p className="mt-2 text-3xl font-semibold">{customer.active_loans}</p>
                        <p className="mt-1 text-xs text-white/70">Préstamos en curso</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm sm:col-span-2 lg:col-span-1">
                        <p className="text-xs uppercase tracking-wide text-white/65">Balance</p>
                        <p className="mt-2 text-xl font-semibold">{formatCurrency(calculateTotalBalance())}</p>
                        <p className="mt-1 text-xs text-white/70">Exposición actual</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Email</p>
                    <a href={`mailto:${customer.email}`} className="mt-2 block text-sm font-medium text-[#163300] hover:underline break-all">
                      {customer.email}
                    </a>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a href={`mailto:${customer.email}`}>
                        <Button size="sm" variant="outline" className="h-8 bg-white text-xs">
                          <Mail className="mr-1.5 h-3.5 w-3.5" />
                          Email
                        </Button>
                      </a>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Teléfono</p>
                    <a href={`tel:${customer.phone}`} className="mt-2 block text-sm font-medium text-[#163300] hover:underline">
                      {customer.phone}
                    </a>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <a href={`tel:${customer.phone}`}>
                        <Button size="sm" variant="outline" className="h-8 bg-white text-xs">
                          <Phone className="mr-1.5 h-3.5 w-3.5" />
                          Llamar
                        </Button>
                      </a>
                      <a href={`https://wa.me/${customer.phone.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="outline" className="h-8 bg-white text-xs">
                          <MessageCircle className="mr-1.5 h-3.5 w-3.5" />
                          WhatsApp
                        </Button>
                      </a>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Pagado acumulado</p>
                    <p className="mt-2 text-lg font-semibold text-emerald-700">{formatCurrency(calculateTotalPaid())}</p>
                  </div>
                  <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Score crediticio</p>
                    <p className="mt-2 text-lg font-semibold text-slate-900">{customer.credit_score || '—'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="space-y-6">
                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader className="pb-4">
                    <CardTitle className="text-base text-[#163300]">Resumen del cliente</CardTitle>
                    <CardDescription>
                      Datos personales, contacto e identificación en una sola vista.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 flex items-center gap-2 text-[#163300]">
                          <User className="h-4 w-4" />
                          <p className="text-sm font-medium">Información personal</p>
                        </div>
                        <div className="grid gap-3 text-sm">
                          <div>
                            <p className="text-xs text-slate-500">Nombre completo</p>
                            <p className="font-medium text-slate-900">{customer.full_name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Fecha de nacimiento</p>
                            <p className="font-medium text-slate-900">{formatDate(customer.date_of_birth)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Género</p>
                            <p className="font-medium text-slate-900">
                              {customer.gender
                                ? customer.gender === 'M'
                                  ? 'Masculino'
                                  : customer.gender === 'F'
                                  ? 'Femenino'
                                  : 'Otro'
                                : 'No especificado'}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 flex items-center gap-2 text-[#163300]">
                          <IdCard className="h-4 w-4" />
                          <p className="text-sm font-medium">Identificación</p>
                        </div>
                        <div className="grid gap-3 text-sm">
                          <div>
                            <p className="text-xs text-slate-500">Tipo de documento</p>
                            <p className="font-medium text-slate-900">
                              {customer.id_type === 'cedula'
                                ? 'Cédula'
                                : customer.id_type === 'passport'
                                ? 'Pasaporte'
                                : 'Licencia de conducir'}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Número</p>
                            <p className="font-medium text-slate-900">{formatDisplayIDNumber(customer.id_number, customer.id_type)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Vencimiento</p>
                            <p className="font-medium text-slate-900">
                              {customer.id_expiry_date ? formatDate(customer.id_expiry_date) : 'No registrado'}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 flex items-center gap-2 text-[#163300]">
                          <Mail className="h-4 w-4" />
                          <p className="text-sm font-medium">Contacto</p>
                        </div>
                        <div className="grid gap-3 text-sm">
                          <div>
                            <p className="text-xs text-slate-500">Email</p>
                            <p className="font-medium text-slate-900 break-all">{customer.email}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Teléfono principal</p>
                            <p className="font-medium text-slate-900">{customer.phone}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Teléfono alternativo</p>
                            <p className="font-medium text-slate-900">{customer.alternate_phone || 'No registrado'}</p>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 flex items-center gap-2 text-[#163300]">
                          <MapPin className="h-4 w-4" />
                          <p className="text-sm font-medium">Dirección</p>
                        </div>
                        <div className="grid gap-3 text-sm">
                          <div>
                            <p className="font-medium text-slate-900">{customer.address_line1}</p>
                            {customer.address_line2 && <p className="text-slate-700">{customer.address_line2}</p>}
                          </div>
                          <div>
                            <p className="text-slate-700">{customer.city}, {customer.state} {customer.postal_code}</p>
                            <p className="font-medium text-slate-900">{customer.country}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {(customer.employment_status || customer.employer_name || customer.occupation || customer.monthly_income) && (
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-3 flex items-center gap-2 text-[#163300]">
                          <Briefcase className="h-4 w-4" />
                          <p className="text-sm font-medium">Información laboral y capacidad</p>
                        </div>
                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 text-sm">
                          <div>
                            <p className="text-xs text-slate-500">Estado laboral</p>
                            <p className="font-medium text-slate-900 capitalize">{customer.employment_status?.replace('_', ' ') || 'No registrado'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Empleador</p>
                            <p className="font-medium text-slate-900">{customer.employer_name || 'No registrado'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Ocupación</p>
                            <p className="font-medium text-slate-900">{customer.occupation || 'No registrada'}</p>
                          </div>
                          <div>
                            <p className="text-xs text-slate-500">Ingreso mensual</p>
                            <p className="font-medium text-slate-900">{customer.monthly_income ? formatCurrency(customer.monthly_income) : 'No registrado'}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {customer.notes && (
                  <Card className="border-[#d7e2db] shadow-none">
                    <CardHeader>
                      <CardTitle className="text-base text-[#163300]">Notas internas</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{customer.notes}</p>
                    </CardContent>
                  </Card>
                )}

                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader>
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-[#163300]">
                          <CreditCard className="h-5 w-5" />
                          Préstamos ({loans.length})
                        </CardTitle>
                        <CardDescription>
                          Exposición crediticia y desempeño de este cliente.
                        </CardDescription>
                      </div>
                      <Link href={`/loans/new?customer=${customerId}`}>
                        <Button size="sm" className="bg-[#163300] hover:bg-[#0f2400]">
                          <Plus className="mr-2 h-4 w-4" />
                          Nuevo préstamo
                        </Button>
                      </Link>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {loans.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
                        <CreditCard className="mx-auto mb-3 h-12 w-12 text-slate-400" />
                        <p className="text-sm text-slate-600">Este cliente todavía no tiene préstamos registrados.</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {loans.map((loan) => (
                          <div
                            key={loan.id}
                            className="cursor-pointer rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-[#163300]/15 hover:bg-slate-50"
                            onClick={() => router.push(`/loans/${loan.id}`)}
                          >
                            <div className="space-y-4">
                              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                <div className="min-w-0 flex-1">
                                  <div className="mb-2 flex flex-wrap items-center gap-2">
                                    <h4 className="text-base font-semibold text-slate-900">{loan.loan_number}</h4>
                                    {getStatusBadge(loan.status)}
                                  </div>
                                  <p className="text-sm text-slate-600">
                                    {getLoanTypeBadge(loan.loan_type)} • {loan.payment_frequency} • {loan.term_months} meses • {loan.interest_rate}% mensual
                                  </p>
                                  <p className="mt-1 text-xs text-slate-500">Desembolsado: {formatDate(loan.disbursement_date)}</p>
                                </div>
                              </div>

                              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                                  <p className="text-xs text-slate-500">Monto</p>
                                  <p className="mt-1 font-semibold text-slate-900">{formatCurrency(loan.principal_amount)}</p>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                                  <p className="text-xs text-slate-500">Pagado</p>
                                  <p className="mt-1 font-semibold text-emerald-700">{formatCurrency(loan.total_paid || 0)}</p>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                                  <p className="text-xs text-slate-500">Balance</p>
                                  <p className="mt-1 font-semibold text-orange-600">{formatCurrency(loan.outstanding_balance)}</p>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                                  <p className="text-xs text-slate-500">Mora</p>
                                  <p className={`mt-1 font-semibold ${loan.days_overdue && loan.days_overdue > 0 ? 'text-red-600' : 'text-slate-900'}`}>
                                    {loan.days_overdue && loan.days_overdue > 0 ? `${loan.days_overdue} días` : 'Al día'}
                                  </p>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader>
                    <CardTitle className="text-base text-[#163300]">Contratos ({contracts.length})</CardTitle>
                    <CardDescription>
                      Documentos contractuales asociados al cliente.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {contracts.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-8">
                        <div className="flex flex-col items-center text-center">
                          <FileCheck className="mb-3 h-10 w-10 text-slate-400" />
                          <p className="text-sm font-medium text-slate-900">No hay contratos firmados todavía</p>
                          <p className="mt-1 max-w-sm text-sm text-slate-600">
                            Cuando este cliente tenga préstamos con contratos generados y firmados, aparecerán aquí.
                          </p>
                          <div className="mt-4 flex flex-wrap justify-center gap-2">
                            <Link href={`/loans/new?customer=${customerId}`}>
                              <Button size="sm" className="bg-[#163300] hover:bg-[#0f2400]">
                                <Plus className="mr-2 h-4 w-4" />
                                Crear préstamo
                              </Button>
                            </Link>
                            <Link href="/contracts">
                              <Button size="sm" variant="outline" className="bg-white">
                                <Eye className="mr-2 h-4 w-4" />
                                Ver contratos
                              </Button>
                            </Link>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {contracts.map((contract) => (
                          <div key={contract.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                            <div className="flex flex-col gap-3">
                              <div className="flex flex-wrap items-center gap-2">
                                <h4 className="font-semibold text-slate-900">{contract.contract_number}</h4>
                                {getContractStatusBadge(contract.status)}
                                {contract.is_fully_signed && (
                                  <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                                    <FileCheck className="h-3 w-3" />
                                    Completamente firmado
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-slate-600">
                                Préstamo: {contract.loan_number}
                                {contract.template_name && ` • ${contract.template_name}`}
                              </p>
                              <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                                <span>Generado: {formatDate(contract.generated_at)}</span>
                                <span>Cliente: {contract.customer_signed_at ? formatDate(contract.customer_signed_at) : 'Pendiente'}</span>
                                <span>Oficial: {contract.officer_signed_at ? formatDate(contract.officer_signed_at) : 'Pendiente'}</span>
                              </div>
                              <div>
                                <Link href={`/contracts/${contract.id}`}>
                                  <Button variant="outline" size="sm" className="bg-white">
                                    <Eye className="mr-2 h-4 w-4" />
                                    Ver contrato
                                  </Button>
                                </Link>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader>
                    <CardTitle className="text-base text-[#163300]">Documentos</CardTitle>
                    <CardDescription>
                      Gestión documental del expediente del cliente.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CustomerDocuments customerId={customerId} canManage={true} />
                  </CardContent>
                </Card>

                <Card className="border-[#d7e2db] shadow-none">
                  <CardHeader>
                    <CardTitle className="text-base text-[#163300]">Información del sistema</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 text-sm sm:grid-cols-2">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs text-slate-500">Fecha de registro</p>
                        <p className="mt-1 font-medium text-slate-900">{formatDate(customer.created_at)}</p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs text-slate-500">Última actualización</p>
                        <p className="mt-1 font-medium text-slate-900">{formatDate(customer.updated_at)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        ) : (
          <Card className="border-[#d7e2db] shadow-none">
            <CardContent className="py-12 text-center">
              <AlertCircle className="mx-auto mb-3 h-12 w-12 text-slate-400" />
              <p className="text-slate-600">Cliente no encontrado</p>
              <Link href="/customers">
                <Button className="mt-4" variant="outline">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver a clientes
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
