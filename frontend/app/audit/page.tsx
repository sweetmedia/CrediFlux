'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { auditAPI, AuditLog, AuditLogFilters, AuditLogStats } from '@/lib/api/audit';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  ClipboardList,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  User,
  Calendar,
  Globe,
  ArrowUpDown,
} from 'lucide-react';

const ACTION_COLORS: Record<string, string> = {
  create: 'bg-green-100 text-green-800',
  update: 'bg-blue-100 text-blue-800',
  delete: 'bg-red-100 text-red-800',
  approve: 'bg-emerald-100 text-emerald-800',
  reject: 'bg-orange-100 text-orange-800',
  login: 'bg-purple-100 text-purple-800',
  logout: 'bg-gray-100 text-gray-800',
  payment: 'bg-teal-100 text-teal-800',
  '2fa_enable': 'bg-indigo-100 text-indigo-800',
  '2fa_disable': 'bg-amber-100 text-amber-800',
  password_change: 'bg-yellow-100 text-yellow-800',
};

const MODEL_NAMES: Record<string, string> = {
  Loan: 'Prestamo',
  LoanPayment: 'Pago',
  Customer: 'Cliente',
  Collateral: 'Garantia',
  Contract: 'Contrato',
  User: 'Usuario',
  Tenant: 'Empresa',
};

export default function AuditPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAction, setSelectedAction] = useState<string>('all');
  const [selectedModel, setSelectedModel] = useState<string>('all');

  // Detail dialog
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Check permission
  useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'manager') {
      setError('No tienes permiso para ver los registros de auditoria');
      setIsLoading(false);
    }
  }, [user]);

  // Load audit logs
  useEffect(() => {
    if (isAuthenticated && user && (user.role === 'admin' || user.role === 'manager')) {
      loadLogs();
      loadStats();
    }
  }, [isAuthenticated, user, currentPage, searchQuery, selectedAction, selectedModel]);

  const loadLogs = async () => {
    try {
      setIsLoading(true);
      setError('');

      const filters: AuditLogFilters = {
        page: currentPage,
        page_size: pageSize,
      };

      if (searchQuery) filters.search = searchQuery;
      if (selectedAction && selectedAction !== 'all') filters.action = selectedAction;
      if (selectedModel && selectedModel !== 'all') filters.model_name = selectedModel;

      const response = await auditAPI.getLogs(filters);
      setLogs(response.results);
      setTotalCount(response.count);
    } catch (err: any) {
      console.error('Error loading audit logs:', err);
      setError(err.response?.data?.error || 'Error al cargar los registros de auditoria');
    } finally {
      setIsLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await auditAPI.getStats();
      setStats(response);
    } catch (err) {
      console.error('Error loading audit stats:', err);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadLogs();
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !logs.length) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <ClipboardList className="h-6 w-6 text-blue-600" />
            Registro de Auditoria
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Historial de todas las acciones realizadas en el sistema
          </p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-slate-900">{stats.total_logs}</div>
                <p className="text-sm text-slate-600">Eventos (30 dias)</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-slate-900">
                  {stats.actions_by_type.find(a => a.action === 'create')?.count || 0}
                </div>
                <p className="text-sm text-slate-600">Creaciones</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-slate-900">
                  {stats.actions_by_type.find(a => a.action === 'update')?.count || 0}
                </div>
                <p className="text-sm text-slate-600">Actualizaciones</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-2xl font-bold text-slate-900">
                  {stats.actions_by_user.length}
                </div>
                <p className="text-sm text-slate-600">Usuarios activos</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Buscar por usuario, descripcion..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="w-[180px]">
                <Select value={selectedAction} onValueChange={setSelectedAction}>
                  <SelectTrigger>
                    <SelectValue placeholder="Tipo de accion" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas las acciones</SelectItem>
                    <SelectItem value="create">Crear</SelectItem>
                    <SelectItem value="update">Actualizar</SelectItem>
                    <SelectItem value="delete">Eliminar</SelectItem>
                    <SelectItem value="approve">Aprobar</SelectItem>
                    <SelectItem value="reject">Rechazar</SelectItem>
                    <SelectItem value="login">Iniciar Sesion</SelectItem>
                    <SelectItem value="logout">Cerrar Sesion</SelectItem>
                    <SelectItem value="payment">Pago</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="w-[180px]">
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Tipo de objeto" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos los objetos</SelectItem>
                    <SelectItem value="Loan">Prestamos</SelectItem>
                    <SelectItem value="LoanPayment">Pagos</SelectItem>
                    <SelectItem value="Customer">Clientes</SelectItem>
                    <SelectItem value="Collateral">Garantias</SelectItem>
                    <SelectItem value="Contract">Contratos</SelectItem>
                    <SelectItem value="User">Usuarios</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button type="submit">
                <Search className="h-4 w-4 mr-2" />
                Buscar
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Logs Table */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Eventos Recientes</span>
              <span className="text-sm font-normal text-slate-600">
                {totalCount} registros encontrados
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            ) : logs.length === 0 ? (
              <div className="text-center py-8 text-slate-600">
                No se encontraron registros de auditoria
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Fecha/Hora</TableHead>
                      <TableHead>Usuario</TableHead>
                      <TableHead>Accion</TableHead>
                      <TableHead>Objeto</TableHead>
                      <TableHead>Descripcion</TableHead>
                      <TableHead>IP</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="whitespace-nowrap">
                          <div className="flex items-center gap-2 text-sm">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            {formatTimestamp(log.timestamp)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            <span className="text-sm">{log.user_name || log.user_email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={ACTION_COLORS[log.action] || 'bg-gray-100 text-gray-800'}>
                            {log.action_display}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm font-medium">
                            {MODEL_NAMES[log.model_name] || log.model_name}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-slate-600 max-w-[200px] truncate block">
                            {log.object_repr}
                          </span>
                        </TableCell>
                        <TableCell>
                          {log.ip_address && (
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                              <Globe className="h-4 w-4" />
                              {log.ip_address}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedLog(log);
                              setIsDetailOpen(true);
                            }}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-slate-600">
                    Mostrando {((currentPage - 1) * pageSize) + 1} -{' '}
                    {Math.min(currentPage * pageSize, totalCount)} de {totalCount}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="flex items-center px-3 text-sm">
                      Pagina {currentPage} de {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Detail Dialog */}
        <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Detalle del Evento</DialogTitle>
              <DialogDescription>
                Informacion completa del registro de auditoria
              </DialogDescription>
            </DialogHeader>

            {selectedLog && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm text-slate-600">Fecha/Hora</Label>
                    <p className="font-medium">{formatTimestamp(selectedLog.timestamp)}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Usuario</Label>
                    <p className="font-medium">{selectedLog.user_name || selectedLog.user_email}</p>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Accion</Label>
                    <Badge className={ACTION_COLORS[selectedLog.action] || 'bg-gray-100 text-gray-800'}>
                      {selectedLog.action_display}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-sm text-slate-600">Tipo de Objeto</Label>
                    <p className="font-medium">
                      {MODEL_NAMES[selectedLog.model_name] || selectedLog.model_name}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <Label className="text-sm text-slate-600">Descripcion</Label>
                    <p className="font-medium">{selectedLog.object_repr}</p>
                  </div>
                  {selectedLog.ip_address && (
                    <div>
                      <Label className="text-sm text-slate-600">Direccion IP</Label>
                      <p className="font-medium">{selectedLog.ip_address}</p>
                    </div>
                  )}
                </div>

                {/* Changes */}
                {Object.keys(selectedLog.changes).length > 0 && (
                  <div>
                    <Label className="text-sm text-slate-600 mb-2 block">Cambios Realizados</Label>
                    <div className="bg-slate-50 rounded-lg p-4">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Campo</TableHead>
                            <TableHead>Valor Anterior</TableHead>
                            <TableHead>Valor Nuevo</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {Object.entries(selectedLog.changes).map(([field, values]) => (
                            <TableRow key={field}>
                              <TableCell className="font-medium">{field}</TableCell>
                              <TableCell className="text-red-600">
                                {values.old !== null ? String(values.old) : '-'}
                              </TableCell>
                              <TableCell className="text-green-600">
                                {values.new !== null ? String(values.new) : '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}

                {selectedLog.user_agent && (
                  <div>
                    <Label className="text-sm text-slate-600">User Agent</Label>
                    <p className="text-sm text-slate-500 break-all">{selectedLog.user_agent}</p>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
