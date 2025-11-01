'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { customersAPI } from '@/lib/api/customers';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Plus,
  Search,
  Users,
  User,
  Phone,
  Mail,
  MapPin,
  Briefcase,
  DollarSign,
  ChevronLeft,
  ChevronRight,
  Eye,
  CreditCard,
  IdCard,
} from 'lucide-react';

export default function CustomersListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [customers, setCustomers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load customers only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadCustomers();
    }
  }, [isAuthenticated, currentPage, searchTerm]);

  const loadCustomers = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
      };

      if (searchTerm) params.search = searchTerm;

      const response = await customersAPI.getCustomers(params);
      setCustomers(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading customers:', err);
      setError('Error al cargar los clientes');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Reset to first page on search
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

  const totalPages = Math.ceil(totalCount / 10); // Assuming 10 items per page

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
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <Users className="h-8 w-8 text-blue-600" />
              Clientes
            </h1>
            <p className="text-gray-600 mt-1">
              Gestiona y consulta todos los clientes del sistema
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard">
              <Button variant="outline">Volver al Dashboard</Button>
            </Link>
            <Link href="/customers/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Cliente
              </Button>
            </Link>
          </div>
        </div>

        {/* Search Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Búsqueda de Clientes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label htmlFor="search">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  id="search"
                  placeholder="Buscar por nombre, cédula, teléfono o email..."
                  value={searchTerm}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Clientes</p>
                  <p className="text-2xl font-bold">{totalCount}</p>
                </div>
                <Users className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Clientes Activos</p>
                  <p className="text-2xl font-bold text-green-600">
                    {customers.filter((c) => c.total_loans > 0).length}
                  </p>
                </div>
                <CreditCard className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Sin Préstamos</p>
                  <p className="text-2xl font-bold text-gray-600">
                    {customers.filter((c) => c.total_loans === 0).length}
                  </p>
                </div>
                <User className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Página</p>
                  <p className="text-2xl font-bold">
                    {currentPage} / {totalPages || 1}
                  </p>
                </div>
                <Users className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Customers List */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando clientes...</p>
          </div>
        ) : customers.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-gray-100 p-6">
                  <Users className="h-12 w-12 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  No se encontraron clientes
                </h3>
                <p className="text-gray-600">
                  {searchTerm
                    ? 'Intenta ajustar tu búsqueda'
                    : 'Comienza agregando tu primer cliente'}
                </p>
                <Link href="/customers/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Agregar Primer Cliente
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {customers.map((customer) => (
              <Card
                key={customer.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/customers/${customer.id}`)}
              >
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    {/* Left Section - Main Info */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-2">
                            <User className="h-5 w-5 text-blue-600" />
                            {customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim()}
                          </h3>

                          {/* Contact Info */}
                          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-3">
                            <span className="flex items-center gap-1">
                              <IdCard className="h-4 w-4" />
                              {customer.id_number}
                            </span>
                            {customer.phone && (
                              <a
                                href={`tel:${customer.phone}`}
                                onClick={(e) => e.stopPropagation()}
                                className="flex items-center gap-1 hover:text-blue-600 transition-colors"
                              >
                                <Phone className="h-4 w-4" />
                                {customer.phone}
                              </a>
                            )}
                            {customer.email && (
                              <a
                                href={`mailto:${customer.email}`}
                                onClick={(e) => e.stopPropagation()}
                                className="flex items-center gap-1 hover:text-blue-600 transition-colors"
                              >
                                <Mail className="h-4 w-4" />
                                {customer.email}
                              </a>
                            )}
                          </div>

                          {/* Additional Info */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {customer.address && (
                              <div className="flex items-start gap-2">
                                <MapPin className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs text-gray-600">Dirección</p>
                                  <p className="text-sm">
                                    {customer.city
                                      ? `${customer.city}${
                                          customer.state ? `, ${customer.state}` : ''
                                        }`
                                      : customer.address}
                                  </p>
                                </div>
                              </div>
                            )}

                            {customer.occupation && (
                              <div className="flex items-start gap-2">
                                <Briefcase className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs text-gray-600">Ocupación</p>
                                  <p className="text-sm">{customer.occupation}</p>
                                </div>
                              </div>
                            )}

                            {customer.monthly_income && (
                              <div className="flex items-start gap-2">
                                <DollarSign className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="text-xs text-gray-600">Ingreso Mensual</p>
                                  <p className="text-sm font-semibold">
                                    {formatCurrency(customer.monthly_income)}
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Loan Stats */}
                      {customer.total_loans > 0 && (
                        <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                          <div className="grid grid-cols-3 gap-4 text-center">
                            <div>
                              <p className="text-xs text-gray-600">Total Préstamos</p>
                              <p className="text-lg font-bold text-blue-600">
                                {customer.total_loans}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-600">Préstamos Activos</p>
                              <p className="text-lg font-bold text-green-600">
                                {customer.active_loans || 0}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-600">Balance Total</p>
                              <p className="text-lg font-bold text-orange-600">
                                {formatCurrency(customer.total_balance || 0)}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Right Section - Actions */}
                    <div className="flex lg:flex-col gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/customers/${customer.id}`);
                        }}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ver Detalles
                      </Button>
                      <Button
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/loans/new?customer=${customer.id}`);
                        }}
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Nuevo Préstamo
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      Mostrando {(currentPage - 1) * 10 + 1} a{' '}
                      {Math.min(currentPage * 10, totalCount)} de {totalCount} clientes
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage + 1)}
                        disabled={currentPage === totalPages}
                      >
                        Siguiente
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
