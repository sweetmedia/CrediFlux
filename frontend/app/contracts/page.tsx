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
  signed: 'bg-[#163300]/10 text-[#163300]',
  active: 'bg-green-100 text-green-800',
  completed: 'bg-[#738566]/10 text-[#738566]',
  cancelled: 'bg-red-100 text-red-800',
};

function getMissingSignatureInfo(contract: Contract): { label: string; className: string } | null {
  const missingCustomer = !contract.customer_signed_at;
  const missingOfficer = !contract.officer_signed_at;

  if (!missingCustomer && !missingOfficer) {
    return null;
  }

  if (missingCustomer && missingOfficer) {
    return {
      label: 'Faltan cliente y oficial',
      className: 'bg-amber-100 text-amber-800',
    };
  }

  if (missingCustomer) {
    return {
      label: 'Falta firma del cliente',
      className: 'bg-orange-100 text-orange-800',
    };
  }

  return {
    label: 'Falta firma del oficial',
    className: 'bg-[#163300]/10 text-[#163300]',
  };
}

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

  const stats = getStatusStats();
  const signatureStats = {
    missingCustomer: contracts.filter((contract) => !contract.customer_signed_at).length,
    missingOfficer: contracts.filter((contract) => !contract.officer_signed_at).length,
    fullySigned: contracts.filter((contract) => contract.is_fully_signed).length,
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-5 md:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <section className="grid gap-4 xl:grid-cols-[minmax(0,2.15fr)_320px]">
          <Card className="overflow-hidden border-0 bg-gradient-to-br from-[#163300] via-[#244508] to-[#325c10] text-white shadow-[0_28px_80px_-32px_rgba(22,51,0,0.75)]">
            <CardContent className="p-5 md:p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-white/85">
                    <FileText className="h-3.5 w-3.5" />
                    Flujo documental
                  </div>
                  <h1 className="text-3xl font-semibold tracking-tight">Contratos</h1>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-white/80">
                    Controla generación, seguimiento y firma de contratos sin perder de vista quién falta por firmar y qué expedientes ya están listos para activar.
                  </p>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
                      <p className="text-xs uppercase tracking-[0.18em] text-white/60">Total visibles</p>
                      <p className="mt-1.5 text-2xl font-semibold">{totalCount}</p>
                      <p className="mt-1 text-xs text-white/65">Contratos cargados en esta vista</p>
                    </div>
                    <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
                      <p className="text-xs uppercase tracking-[0.18em] text-white/60">Pendiente firma</p>
                      <p className="mt-1.5 text-2xl font-semibold">{stats.pending_signature}</p>
                      <p className="mt-1 text-xs text-white/65">Requieren seguimiento inmediato</p>
                    </div>
                    <div className="rounded-2xl border border-white/15 bg-white/10 px-4 py-3 backdrop-blur-sm">
                      <p className="text-xs uppercase tracking-[0.18em] text-white/60">Completos</p>
                      <p className="mt-1.5 text-2xl font-semibold">{signatureStats.fullySigned}</p>
                      <p className="mt-1 text-xs text-white/65">Listos para avance operativo</p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 lg:flex-col lg:items-stretch">
                  <Link href="/contracts/generate">
                    <Button className="h-10 w-full bg-white text-[#163300] hover:bg-white/90 lg:min-w-[200px]">
                      <Plus className="mr-2 h-4 w-4" />
                      Generar contrato
                    </Button>
                  </Link>
                  <Link href="/contracts/templates">
                    <Button variant="outline" className="h-10 w-full border-white/20 bg-white/5 text-white hover:bg-white/10 hover:text-white lg:min-w-[200px]">
                      <FileEdit className="mr-2 h-4 w-4" />
                      Ver plantillas
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border border-[#d7e2db] bg-white shadow-sm">
            <CardHeader className="border-b border-[#d7e2db] px-5 pb-3 pt-5">
              <CardTitle className="text-base font-semibold text-slate-900">Lectura operativa</CardTitle>
              <CardDescription className="text-sm text-slate-600">
                Qué mirar primero antes de entrar al detalle.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 px-5 pb-5 pt-4">
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">Cliente pendiente</p>
                <p className="mt-1.5 text-2xl font-semibold text-amber-900">{signatureStats.missingCustomer}</p>
                <p className="mt-1 text-sm text-amber-800">Contratos donde aún falta la firma del cliente.</p>
              </div>
              <div className="rounded-2xl border border-[#d7e2db] bg-[#f6f8f7] px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#163300]">Oficial pendiente</p>
                <p className="mt-1.5 text-2xl font-semibold text-slate-900">{signatureStats.missingOfficer}</p>
                <p className="mt-1 text-sm text-slate-600">Útil para saber qué expedientes están trabados internamente.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <p className="font-semibold text-slate-900">Siguiente paso sugerido</p>
                <p className="mt-2 leading-6">
                  Prioriza <span className="font-medium text-slate-900">Pendiente Firma</span> y usa los nuevos badges de la lista para saber en segundos si falta el cliente, el oficial o ambos.
                </p>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Card className="border-[#d7e2db] bg-white shadow-sm">
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Borradores</p>
                <p className="mt-1.5 text-2xl font-semibold text-slate-900">{stats.draft}</p>
                <p className="mt-1 text-xs text-slate-500">Pendientes de revisión</p>
              </div>
              <div className="rounded-2xl bg-slate-100 p-3 text-slate-700">
                <FileEdit className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-[#d7e2db] bg-white shadow-sm">
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Pendiente firma</p>
                <p className="mt-1.5 text-2xl font-semibold text-slate-900">{stats.pending_signature}</p>
                <p className="mt-1 text-xs text-slate-500">Requieren seguimiento</p>
              </div>
              <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
                <FileClock className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-[#d7e2db] bg-white shadow-sm">
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Firmados</p>
                <p className="mt-1.5 text-2xl font-semibold text-slate-900">{stats.signed}</p>
                <p className="mt-1 text-xs text-slate-500">Firma completa o validada</p>
              </div>
              <div className="rounded-2xl bg-[#163300]/10 p-3 text-[#163300]">
                <FileCheck className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-[#d7e2db] bg-white shadow-sm">
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Activos</p>
                <p className="mt-1.5 text-2xl font-semibold text-slate-900">{stats.active}</p>
                <p className="mt-1 text-xs text-slate-500">Contratos ya operativos</p>
              </div>
              <div className="rounded-2xl bg-green-100 p-3 text-green-700">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Card className="overflow-hidden border-[#d7e2db] bg-white shadow-sm">
          <CardHeader className="border-b border-[#d7e2db] bg-white px-5 py-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div className="flex-1">
                <CardTitle className="text-lg font-semibold text-slate-900">
                  Bandeja de contratos
                </CardTitle>
                <CardDescription className="mt-1 text-sm text-slate-600">
                  {totalCount} contrato{totalCount !== 1 ? 's' : ''} disponible
                  {totalCount !== 1 ? 's' : ''}
                </CardDescription>
              </div>
              <div className="grid gap-2 md:grid-cols-2 xl:flex xl:flex-wrap xl:items-center xl:justify-end">
                <div className="relative min-w-[240px] flex-1 xl:w-72 xl:flex-none">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    placeholder="Buscar por contrato, préstamo o cliente..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="h-10 border-slate-200 pl-10"
                  />
                </div>
                <Select value={statusFilter} onValueChange={handleStatusFilter}>
                  <SelectTrigger className="h-10 w-full border-slate-200 xl:w-48">
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
                <label className="flex h-10 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showArchived}
                    onChange={(e) => setShowArchived(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-[#163300] focus:ring-[#163300]"
                  />
                  <Archive className="h-4 w-4 text-slate-600" />
                  <span className="text-sm font-medium text-slate-700">
                    Mostrar archivados
                  </span>
                </label>
                <Link href="/contracts/generate">
                  <Button className="h-10 w-full bg-[#163300] hover:bg-[#0f2400] xl:w-auto">
                    <Plus className="mr-2 h-4 w-4" />
                    Generar Contrato
                  </Button>
                </Link>
              </div>
            </div>
          </CardHeader>

          <CardContent className="bg-[#fbfcfb] p-0">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12">
                <Loader2 className="h-12 w-12 animate-spin text-[#163300] mb-4" />
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
                  <Button className="bg-[#163300] hover:bg-[#0f2400]">
                    <Plus className="mr-2 h-4 w-4" />
                    Generar Primer Contrato
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3 p-3 md:p-4">
                {contracts.map((contract) => {
                  const StatusIcon = STATUS_ICONS[contract.status];
                  const missingSignatureInfo = getMissingSignatureInfo(contract);
                  return (
                    <div
                      key={contract.id}
                      className="rounded-3xl border border-[#d7e2db] bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                        <div className="flex-1">
                          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-base font-semibold text-slate-900">
                                  {contract.contract_number}
                                </h3>
                                <span
                                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                                STATUS_COLORS[contract.status]
                                  }`}
                                >
                                  <StatusIcon className="h-3 w-3" />
                                  {STATUS_LABELS[contract.status]}
                                </span>
                                {contract.is_fully_signed && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-800">
                                    <CheckCircle2 className="h-3 w-3" />
                                    Firmado completamente
                                  </span>
                                )}
                                {missingSignatureInfo && (
                                  <span
                                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${missingSignatureInfo.className}`}
                                  >
                                    <PenTool className="h-3 w-3" />
                                    {missingSignatureInfo.label}
                                  </span>
                                )}
                                {contract.is_archived && (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                                    <Archive className="h-3 w-3" />
                                    Archivado
                                  </span>
                                )}
                              </div>
                              <p className="mt-1.5 text-sm text-slate-600">
                                {contract.customer_name} · préstamo {contract.loan_number}
                              </p>
                            </div>

                            <div className="grid gap-2 sm:grid-cols-2 xl:min-w-[220px]">
                              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Cliente</p>
                                <p className={`mt-1 text-sm font-medium ${contract.customer_signed_at ? 'text-green-700' : 'text-amber-700'}`}>
                                  {contract.customer_signed_at ? 'Firmó' : 'Pendiente'}
                                </p>
                              </div>
                              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Oficial</p>
                                <p className={`mt-1 text-sm font-medium ${contract.officer_signed_at ? 'text-[#163300]' : 'text-orange-700'}`}>
                                  {contract.officer_signed_at ? 'Firmó' : 'Pendiente'}
                                </p>
                              </div>
                            </div>
                          </div>

                          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
                            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                              <p className="text-xs text-slate-500 mb-1">
                                Préstamo
                              </p>
                              <p className="text-sm font-semibold text-slate-900">
                                {contract.loan_number}
                              </p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                              <p className="text-xs text-slate-500 mb-1">
                                Cliente
                              </p>
                              <p className="text-sm font-semibold text-slate-900">
                                {contract.customer_name}
                              </p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                              <p className="text-xs text-slate-500 mb-1">
                                Plantilla
                              </p>
                              <p className="text-sm font-medium text-slate-700 truncate">
                                {contract.template_name || 'Plantilla estándar'}
                              </p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                              <p className="text-xs text-slate-500 mb-1">Generado</p>
                              <p className="text-sm font-medium text-slate-700">
                                {new Date(contract.generated_at).toLocaleDateString('es-ES')}
                              </p>
                            </div>
                          </div>

                          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                            <span className="inline-flex items-center gap-1">
                              Generado:{' '}
                              {new Date(contract.generated_at).toLocaleDateString('es-ES')}
                            </span>
                            {contract.generated_by_name && (
                              <span className="inline-flex items-center gap-1">Por: {contract.generated_by_name}</span>
                            )}
                            {contract.customer_signed_at && (
                              <span className="inline-flex items-center gap-1 text-green-600">
                                Cliente firmó:{' '}
                                {new Date(contract.customer_signed_at).toLocaleDateString('es-ES')}
                              </span>
                            )}
                            {contract.officer_signed_at && (
                              <span className="inline-flex items-center gap-1 text-[#163300]">
                                Oficial firmó:{' '}
                                {new Date(contract.officer_signed_at).toLocaleDateString('es-ES')}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 xl:ml-3 xl:w-auto xl:flex-col xl:items-stretch">
                          <Link href={`/contracts/${contract.id}`}>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-9 w-full border-slate-200 bg-white hover:bg-slate-50 xl:min-w-[128px]"
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
                                className="h-9 w-full border-[#163300]/30 text-[#163300] hover:bg-[#163300]/5 xl:min-w-[128px]"
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
