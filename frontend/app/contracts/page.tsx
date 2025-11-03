'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { contractsAPI, Contract } from '@/lib/api/contracts';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Loader2,
  Plus,
  Search,
  FileText,
  Eye,
  PenTool,
  CheckCircle2,
  XCircle,
  FileCheck,
  FileClock,
  FileX,
  FileEdit,
  Archive,
} from 'lucide-react';

const STATUS_LABELS: Record<string, string> = {
  draft: 'Borrador',
  pending_signature: 'Pendiente Firma',
  signed: 'Firmado',
  active: 'Activo',
  completed: 'Completado',
  cancelled: 'Cancelado',
};

const STATUS_ICONS: Record<string, any> = {
  draft: FileEdit,
  pending_signature: FileClock,
  signed: FileCheck,
  active: CheckCircle2,
  completed: CheckCircle2,
  cancelled: FileX,
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-800',
  pending_signature: 'bg-yellow-100 text-yellow-800',
  signed: 'bg-blue-100 text-blue-800',
  active: 'bg-green-100 text-green-800',
  completed: 'bg-purple-100 text-purple-800',
  cancelled: 'bg-red-100 text-red-800',
};

export default function ContractsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showArchived, setShowArchived] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load contracts
  useEffect(() => {
    if (isAuthenticated) {
      loadContracts();
    }
  }, [isAuthenticated, currentPage, searchTerm, statusFilter, showArchived]);

  const loadContracts = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
      };

      if (searchTerm) params.search = searchTerm;
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter;
      if (showArchived) params.show_archived = 'true';

      const response = await contractsAPI.getContracts(params);
      setContracts(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading contracts:', err);
      setError('Error al cargar los contratos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    setCurrentPage(1);
  };

  const getStatusStats = () => {
    return {
      draft: contracts.filter((c) => c.status === 'draft').length,
      pending_signature: contracts.filter((c) => c.status === 'pending_signature').length,
      signed: contracts.filter((c) => c.status === 'signed').length,
      active: contracts.filter((c) => c.status === 'active').length,
      completed: contracts.filter((c) => c.status === 'completed').length,
      cancelled: contracts.filter((c) => c.status === 'cancelled').length,
    };
  };

  const totalPages = Math.ceil(totalCount / 10);
  const stats = getStatusStats();

  if (authLoading) {
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
          <h1 className="text-2xl font-bold text-slate-900">Contratos</h1>
          <p className="text-sm text-slate-600 mt-1">
            Gestiona los contratos de préstamo y sus firmas digitales
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Total Contratos
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{totalCount}</p>
                </div>
                <div className="rounded-xl bg-blue-100 p-3">
                  <FileText className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Pendiente Firma
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">
                    {stats.pending_signature}
                  </p>
                </div>
                <div className="rounded-xl bg-yellow-100 p-3">
                  <FileClock className="h-6 w-6 text-yellow-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Activos
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{stats.active}</p>
                </div>
                <div className="rounded-xl bg-green-100 p-3">
                  <CheckCircle2 className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Firmados
                  </p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{stats.signed}</p>
                </div>
                <div className="rounded-xl bg-blue-100 p-3">
                  <FileCheck className="h-6 w-6 text-blue-600" />
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
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Lista de Contratos
                </CardTitle>
                <CardDescription className="text-sm text-slate-600 mt-1">
                  {totalCount} contrato{totalCount !== 1 ? 's' : ''} disponible
                  {totalCount !== 1 ? 's' : ''}
                </CardDescription>
              </div>
              <div className="flex gap-3">
                <Select value={statusFilter} onValueChange={handleStatusFilter}>
                  <SelectTrigger className="w-48 border-slate-200">
                    <SelectValue placeholder="Filtrar por estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los estados</SelectItem>
                    <SelectItem value="draft">Borrador</SelectItem>
                    <SelectItem value="pending_signature">Pendiente Firma</SelectItem>
                    <SelectItem value="signed">Firmado</SelectItem>
                    <SelectItem value="active">Activo</SelectItem>
                    <SelectItem value="completed">Completado</SelectItem>
                    <SelectItem value="cancelled">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
                <label className="flex items-center gap-2 px-3 py-2 border border-slate-200 rounded-md bg-white hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showArchived}
                    onChange={(e) => setShowArchived(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <Archive className="h-4 w-4 text-slate-600" />
                  <span className="text-sm font-medium text-slate-700">
                    Mostrar archivados
                  </span>
                </label>
                <div className="relative w-80">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Buscar contratos..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10 border-slate-200"
                  />
                </div>
                <Link href="/contracts/generate">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Generar Contrato
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
                <p className="text-slate-600">Cargando contratos...</p>
              </div>
            ) : contracts.length === 0 ? (
              <div className="text-center py-12">
                <div className="rounded-xl bg-slate-100 p-6 w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                  <FileText className="h-10 w-10 text-slate-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  No hay contratos
                </h3>
                <p className="text-sm text-slate-600 mb-6">
                  {searchTerm || statusFilter !== 'all'
                    ? 'No se encontraron contratos con ese criterio'
                    : 'Genera tu primer contrato de préstamo'}
                </p>
                <Link href="/contracts/generate">
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="mr-2 h-4 w-4" />
                    Generar Primer Contrato
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {contracts.map((contract) => {
                  const StatusIcon = STATUS_ICONS[contract.status];
                  return (
                    <div
                      key={contract.id}
                      className="p-6 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-slate-900">
                              {contract.contract_number}
                            </h3>
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                                STATUS_COLORS[contract.status]
                              }`}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {STATUS_LABELS[contract.status]}
                            </span>
                            {contract.is_fully_signed && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                <CheckCircle2 className="h-3 w-3" />
                                Firmado Completamente
                              </span>
                            )}
                            {contract.is_archived && (
                              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                                <Archive className="h-3 w-3" />
                                Archivado
                              </span>
                            )}
                          </div>

                          <div className="grid grid-cols-2 gap-4 mb-3">
                            <div>
                              <p className="text-xs text-slate-600 mb-0.5">
                                Préstamo
                              </p>
                              <p className="text-sm font-medium text-slate-900">
                                {contract.loan_number}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-600 mb-0.5">
                                Cliente
                              </p>
                              <p className="text-sm font-medium text-slate-900">
                                {contract.customer_name}
                              </p>
                            </div>
                          </div>

                          {contract.template_name && (
                            <div className="mb-3">
                              <p className="text-xs text-slate-600 mb-0.5">
                                Plantilla
                              </p>
                              <p className="text-sm text-slate-700">
                                {contract.template_name}
                              </p>
                            </div>
                          )}

                          <div className="flex items-center gap-4 text-xs text-slate-500">
                            <span>
                              Generado:{' '}
                              {new Date(contract.generated_at).toLocaleDateString(
                                'es-ES'
                              )}
                            </span>
                            {contract.generated_by_name && (
                              <span>Por: {contract.generated_by_name}</span>
                            )}
                            {contract.customer_signed_at && (
                              <span className="text-green-600">
                                Cliente firmó:{' '}
                                {new Date(
                                  contract.customer_signed_at
                                ).toLocaleDateString('es-ES')}
                              </span>
                            )}
                            {contract.officer_signed_at && (
                              <span className="text-blue-600">
                                Oficial firmó:{' '}
                                {new Date(
                                  contract.officer_signed_at
                                ).toLocaleDateString('es-ES')}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 ml-4">
                          <Link href={`/contracts/${contract.id}`}>
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-slate-200"
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              Ver
                            </Button>
                          </Link>
                          {(contract.status === 'pending_signature' ||
                            contract.status === 'signed') && (
                            <Link href={`/contracts/${contract.id}/sign`}>
                              <Button
                                variant="outline"
                                size="sm"
                                className="border-blue-200 text-blue-600 hover:bg-blue-50"
                              >
                                <PenTool className="h-4 w-4 mr-1" />
                                Firmar
                              </Button>
                            </Link>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
