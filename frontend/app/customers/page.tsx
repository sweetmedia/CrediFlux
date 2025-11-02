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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
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
  FileText,
  ExternalLink,
} from 'lucide-react';

export default function CustomersListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config, isLoading: configLoading } = useConfig();
  const [customers, setCustomers] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');

  // Map modal
  const [mapModalOpen, setMapModalOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null);

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

  // Show loading state while checking authentication and config
  if (authLoading || configLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Clientes</h1>
          <p className="text-sm text-slate-600 mt-1">
            Gestiona y consulta todos los clientes del sistema
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Total Clientes</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{totalCount}</p>
                </div>
                <div className="rounded-xl bg-blue-100 p-3">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Activos</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {customers.filter((c) => c.total_loans > 0).length}
                  </p>
                </div>
                <div className="rounded-xl bg-green-100 p-3">
                  <CreditCard className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Sin Préstamos</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {customers.filter((c) => c.total_loans === 0).length}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-100 p-3">
                  <User className="h-6 w-6 text-slate-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Página</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {currentPage} / {totalPages || 1}
                  </p>
                </div>
                <div className="rounded-xl bg-purple-100 p-3">
                  <FileText className="h-6 w-6 text-purple-600" />
                </div>
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

        {/* Main Content Card */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="border-b border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg font-semibold text-slate-900">Lista de Clientes</CardTitle>
                <CardDescription className="text-sm text-slate-600 mt-1">
                  {totalCount} cliente{totalCount !== 1 ? 's' : ''} registrado{totalCount !== 1 ? 's' : ''}
                </CardDescription>
              </div>
              <div className="flex gap-3">
                <div className="relative w-80">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Buscar clientes..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10 border-slate-200"
                  />
                </div>
                <Link href="/customers/new">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Nuevo Cliente
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
                <p className="text-slate-600">Cargando clientes...</p>
              </div>
            ) : customers.length === 0 ? (
              <div className="text-center py-12">
                <div className="rounded-xl bg-slate-100 p-6 w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                  <Users className="h-10 w-10 text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  No se encontraron clientes
                </h3>
                <p className="text-sm text-slate-600 mb-6">
                  {searchTerm
                    ? 'Intenta ajustar tu búsqueda'
                    : 'Comienza agregando tu primer cliente'}
                </p>
                <Link href="/customers/new">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Agregar Primer Cliente
                  </Button>
                </Link>
              </div>
            ) : (
              <>
                {/* Data Table */}
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Cliente
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Contacto
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Ubicación
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Préstamos
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Balance
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-slate-200">
                      {customers.map((customer) => (
                        <tr
                          key={customer.id}
                          className="hover:bg-slate-50 transition-colors cursor-pointer"
                          onClick={() => router.push(`/customers/${customer.id}`)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                <User className="h-5 w-5 text-blue-600" />
                              </div>
                              <div className="ml-4">
                                <div className="text-sm font-semibold text-slate-900">
                                  {customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim()}
                                </div>
                                <div className="text-xs text-slate-500 flex items-center gap-1">
                                  <IdCard className="h-3 w-3" />
                                  {customer.id_number}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-slate-900">
                              {customer.phone && (
                                <div className="flex items-center gap-1 text-slate-600">
                                  <Phone className="h-3 w-3" />
                                  {customer.phone}
                                </div>
                              )}
                              {customer.email && (
                                <div className="flex items-center gap-1 text-slate-600 mt-1">
                                  <Mail className="h-3 w-3" />
                                  <span className="truncate max-w-[200px]">{customer.email}</span>
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-slate-600">
                              {customer.address_line1 && (
                                <div className="text-xs text-slate-600 mb-1">{customer.address_line1}</div>
                              )}
                              {customer.city && customer.state && (
                                <div className="text-xs text-slate-500 mb-2">{customer.city}, {customer.state}</div>
                              )}
                              {customer.address_line1 && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedCustomer(customer);
                                    setMapModalOpen(true);
                                  }}
                                  className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                                >
                                  <MapPin className="h-3 w-3" />
                                  Ver mapa
                                </button>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            {customer.loan_details && customer.loan_details.length > 0 ? (
                              <div className="text-xs">
                                {customer.loan_details.map((loan: any, index: number) => (
                                  <div key={index} className="text-slate-600 py-0.5">
                                    {loan.loan_number}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-slate-500">Sin préstamos</span>
                            )}
                          </td>
                          <td className="px-6 py-4">
                            {customer.loan_details && customer.loan_details.length > 0 ? (
                              <div className="text-xs">
                                {customer.loan_details.map((loan: any, index: number) => (
                                  <div key={index} className={`py-0.5 font-medium ${loan.remaining_balance > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                                    {formatCurrency(loan.remaining_balance)}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-slate-500">-</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  router.push(`/customers/${customer.id}`);
                                }}
                                className="border-slate-200"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  router.push(`/loans/new?customer=${customer.id}`);
                                }}
                                className="bg-blue-600 hover:bg-blue-700"
                              >
                                <Plus className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="px-6 py-4 border-t border-slate-200 bg-slate-50">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-slate-600">
                        Mostrando {(currentPage - 1) * 10 + 1} a{' '}
                        {Math.min(currentPage * 10, totalCount)} de {totalCount} clientes
                      </p>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(currentPage - 1)}
                          disabled={currentPage === 1}
                          className="border-slate-200"
                        >
                          <ChevronLeft className="h-4 w-4 mr-1" />
                          Anterior
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(currentPage + 1)}
                          disabled={currentPage === totalPages}
                          className="border-slate-200"
                        >
                          Siguiente
                          <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Map Modal */}
        <Dialog open={mapModalOpen} onOpenChange={setMapModalOpen}>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle className="text-lg font-semibold text-slate-900">
                Ubicación de {selectedCustomer?.full_name}
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-600">
                {selectedCustomer?.address_line1}
                {selectedCustomer?.city && selectedCustomer?.state && (
                  <>, {selectedCustomer.city}, {selectedCustomer.state}</>
                )}
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              {selectedCustomer && (
                <div className="w-full h-96 bg-slate-100 rounded-lg flex items-center justify-center">
                  <iframe
                    width="100%"
                    height="100%"
                    frameBorder="0"
                    style={{ border: 0 }}
                    src={`https://www.google.com/maps?q=${encodeURIComponent(
                      `${selectedCustomer.address_line1}, ${selectedCustomer.city}, ${selectedCustomer.state}, ${selectedCustomer.country || 'República Dominicana'}`
                    )}&output=embed`}
                    allowFullScreen
                  />
                </div>
              )}
              <div className="mt-4 flex justify-end">
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                    `${selectedCustomer?.address_line1}, ${selectedCustomer?.city}, ${selectedCustomer?.state}, ${selectedCustomer?.country || 'República Dominicana'}`
                  )}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                >
                  <ExternalLink className="h-4 w-4" />
                  Abrir en Google Maps
                </a>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
