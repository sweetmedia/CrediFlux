'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { billingAPI } from '@/lib/api/billing';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Plus,
  Search,
  FileText,
  Send,
  CheckCircle,
  XCircle,
  Filter,
  Clock,
  TrendingUp,
  Receipt,
} from 'lucide-react';
import {
  Invoice,
  InvoiceStatus,
  INVOICE_STATUS_LABELS,
  INVOICE_STATUS_COLORS,
  ECF_TYPE_LABELS,
  ECFType,
} from '@/types/billing';

export default function BillingPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [ecfTypeFilter, setEcfTypeFilter] = useState('');
  const [ordering, setOrdering] = useState('-issue_date');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadInvoices();
    }
  }, [isAuthenticated, currentPage, searchTerm, statusFilter, ecfTypeFilter, ordering]);

  const loadInvoices = async () => {
    try {
      setIsLoading(true);
      setError('');
      const params: any = {
        page: currentPage,
        ordering,
      };
      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.status = statusFilter;
      if (ecfTypeFilter) params.ecf_type = ecfTypeFilter;

      const response = await billingAPI.getInvoices(params);
      setInvoices(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading invoices:', err);
      setError('Error al cargar las facturas');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return `RD$${Number(amount).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getStatusBadge = (status: InvoiceStatus) => {
    const colors = INVOICE_STATUS_COLORS[status] || 'bg-slate-100 text-slate-700';
    const label = INVOICE_STATUS_LABELS[status] || status;
    return (
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${colors}`}>
        {label}
      </span>
    );
  };

  // Stats from current data
  const drafts = invoices.filter((i) => i.status === 'draft').length;
  const submitted = invoices.filter((i) => i.status === 'submitted').length;
  const accepted = invoices.filter((i) => i.status === 'accepted').length;
  const rejected = invoices.filter((i) => i.status === 'rejected').length;
  const totalBilled = invoices.reduce((sum, i) => sum + Number(i.total || 0), 0);

  const totalPages = Math.ceil(totalCount / 10);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6 lg:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Facturación Electrónica</h1>
            <p className="text-sm text-gray-500 mt-1">
              Genera, firma y envía comprobantes fiscales electrónicos (e-CF) a la DGII
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/billing/sequences">
              <Button variant="outline">
                <Receipt className="mr-2 h-4 w-4" />
                Secuencias
              </Button>
            </Link>
            <Link href="/billing/certificates">
              <Button variant="outline">
                🔐 Certificados
              </Button>
            </Link>
            <Link href="/billing/new">
              <Button className="bg-[#163300] hover:bg-[#0f2400] text-white">
                <Plus className="mr-2 h-4 w-4" />
                Nueva Factura
              </Button>
            </Link>
          </div>
        </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-10 w-10 rounded-xl bg-[#163300]/10 flex items-center justify-center">
                <FileText className="h-5 w-5 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-1">Total Facturas</p>
            <p className="text-xl font-bold text-slate-900">{totalCount}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-10 w-10 rounded-xl bg-slate-100 flex items-center justify-center">
                <Clock className="h-5 w-5 text-slate-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-1">Borradores</p>
            <p className="text-xl font-bold text-slate-900">{drafts}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-10 w-10 rounded-xl bg-yellow-100 flex items-center justify-center">
                <Send className="h-5 w-5 text-yellow-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-1">Enviados</p>
            <p className="text-xl font-bold text-slate-900">{submitted}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-10 w-10 rounded-xl bg-green-100 flex items-center justify-center">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-1">Aceptados</p>
            <p className="text-xl font-bold text-green-600">{accepted}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="h-10 w-10 rounded-xl bg-[#738566]/10 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-[#738566]" />
              </div>
            </div>
            <p className="text-xs text-slate-500 mb-1">Total Facturado</p>
            <p className="text-lg font-bold text-slate-900">{formatCurrency(totalBilled)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6 border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-200">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-semibold text-slate-900">Filtros</CardTitle>
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Filter className="mr-2 h-4 w-4" />
              {showFilters ? 'Ocultar' : 'Mostrar'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="search" className="text-sm font-medium text-slate-700">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  id="search"
                  placeholder="e-NCF, RNC, razón social..."
                  value={searchTerm}
                  onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
                  className="pl-10"
                />
              </div>
            </div>

            {showFilters && (
              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-200">
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Estado</Label>
                  <Select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}>
                    <option value="">Todos</option>
                    <option value="draft">Borrador</option>
                    <option value="generated">XML Generado</option>
                    <option value="signed">Firmado</option>
                    <option value="submitted">Enviado</option>
                    <option value="accepted">Aceptado</option>
                    <option value="conditionally_accepted">Aceptado Condicional</option>
                    <option value="rejected">Rechazado</option>
                    <option value="cancelled">Anulado</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Tipo e-CF</Label>
                  <Select value={ecfTypeFilter} onChange={(e) => { setEcfTypeFilter(e.target.value); setCurrentPage(1); }}>
                    <option value="">Todos</option>
                    <option value="31">31 - Crédito Fiscal</option>
                    <option value="32">32 - Consumo</option>
                    <option value="33">33 - Nota de Débito</option>
                    <option value="34">34 - Nota de Crédito</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-slate-700">Ordenar</Label>
                  <Select value={ordering} onChange={(e) => setOrdering(e.target.value)}>
                    <option value="-issue_date">Más recientes</option>
                    <option value="issue_date">Más antiguos</option>
                    <option value="-total">Mayor monto</option>
                    <option value="total">Menor monto</option>
                  </Select>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Invoice Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-12 w-12 animate-spin text-[#163300] mb-4" />
          <p className="text-slate-600">Cargando facturas...</p>
        </div>
      ) : invoices.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="text-center py-12">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-slate-100 p-6">
                <FileText className="h-12 w-12 text-slate-400" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900">
                No se encontraron facturas
              </h3>
              <p className="text-slate-600">
                {searchTerm || statusFilter || ecfTypeFilter
                  ? 'Intenta ajustar los filtros de búsqueda'
                  : 'Comienza creando tu primera factura electrónica'}
              </p>
              <Link href="/billing/new">
                <Button className="bg-[#163300] hover:bg-[#0f2400]">
                  <Plus className="mr-2 h-4 w-4" />
                  Crear Primera Factura
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">e-NCF</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Tipo</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Comprador</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Fecha</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Total</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Estado</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">DGII</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr
                    key={invoice.id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => router.push(`/billing/${invoice.id}`)}
                  >
                    <td className="py-3 px-4">
                      <p className="font-mono font-medium text-slate-900 text-sm">
                        {invoice.encf_number || '—'}
                      </p>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center rounded-md bg-[#163300]/10 px-2 py-1 text-xs font-medium text-[#163300]">
                        {invoice.ecf_type}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div>
                        <p className="font-medium text-slate-900 text-sm">{invoice.comprador_razon_social || '—'}</p>
                        <p className="text-xs text-slate-500">{invoice.comprador_rnc}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-sm text-slate-700">{formatDate(invoice.issue_date)}</p>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <p className="font-bold text-blue-600">{formatCurrency(invoice.total)}</p>
                      {invoice.total_itbis > 0 && (
                        <p className="text-xs text-slate-500">ITBIS: {formatCurrency(invoice.total_itbis)}</p>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(invoice.status)}
                    </td>
                    <td className="py-3 px-4">
                      {invoice.dgii_trackid ? (
                        <div>
                          <p className="text-xs font-mono text-slate-600">{invoice.dgii_status || '—'}</p>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="border-t border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-slate-600">
                    Mostrando {(currentPage - 1) * 10 + 1} a {Math.min(currentPage * 10, totalCount)} de {totalCount}
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(currentPage - 1)} disabled={currentPage === 1}>
                      Anterior
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => setCurrentPage(currentPage + 1)} disabled={currentPage === totalPages}>
                      Siguiente
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
