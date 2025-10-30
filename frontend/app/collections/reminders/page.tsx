'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
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
import { Badge } from '@/components/ui/badge';
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
  Send,
  XCircle,
  Clock,
  CheckCircle,
  AlertCircle,
  Mail,
  MessageSquare,
  Phone,
  Bell,
  Calendar,
  User,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { CollectionReminder } from '@/types';

export default function RemindersListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [reminders, setReminders] = useState<CollectionReminder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load reminders
  useEffect(() => {
    if (isAuthenticated) {
      loadReminders();
    }
  }, [isAuthenticated, currentPage, statusFilter, channelFilter, typeFilter]);

  const loadReminders = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = { page: currentPage };
      if (statusFilter) params.status = statusFilter;
      if (channelFilter) params.channel = channelFilter;
      if (typeFilter) params.reminder_type = typeFilter;

      const response = await collectionsAPI.getReminders(params);
      setReminders(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading reminders:', err);
      setError('Error al cargar recordatorios');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendReminder = async (id: string) => {
    try {
      await collectionsAPI.sendReminder(id);
      loadReminders();
    } catch (err: any) {
      console.error('Error sending reminder:', err);
      setError('Error al enviar recordatorio');
    }
  };

  const handleCancelReminder = async (id: string) => {
    if (!confirm('¿Está seguro de cancelar este recordatorio?')) return;

    try {
      await collectionsAPI.cancelReminder(id);
      loadReminders();
    } catch (err: any) {
      console.error('Error canceling reminder:', err);
      setError('Error al cancelar recordatorio');
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: { icon: Clock, color: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
      sent: { icon: CheckCircle, color: 'bg-green-50 text-green-700 border-green-200' },
      failed: { icon: XCircle, color: 'bg-red-50 text-red-700 border-red-200' },
      cancelled: { icon: AlertCircle, color: 'bg-gray-50 text-gray-700 border-gray-200' },
    };
    const config = variants[status] || variants.pending;
    const Icon = config.icon;
    return (
      <Badge variant="outline" className={config.color}>
        <Icon className="h-3 w-3 mr-1" />
        {status}
      </Badge>
    );
  };

  const getChannelIcon = (channel: string) => {
    const icons: Record<string, any> = {
      email: Mail,
      sms: MessageSquare,
      whatsapp: MessageSquare,
      call: Phone,
    };
    const Icon = icons[channel] || Bell;
    return <Icon className="h-4 w-4" />;
  };

  const totalPages = Math.ceil(totalCount / 25);

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Recordatorios de Cobranza</h1>
          <p className="text-muted-foreground mt-2">
            Gestión de recordatorios automáticos y manuales
          </p>
        </div>
        <Button onClick={() => router.push('/collections/reminders/new')}>
          <Plus className="h-4 w-4 mr-2" />
          Nuevo Recordatorio
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Filtros</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Estado</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los estados" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                  <SelectItem value="sent">Enviado</SelectItem>
                  <SelectItem value="failed">Fallido</SelectItem>
                  <SelectItem value="cancelled">Cancelado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Canal</label>
              <Select value={channelFilter} onValueChange={setChannelFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los canales" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="sms">SMS</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="call">Llamada</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Tipo</label>
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos los tipos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="upcoming_3">Próximo (3 días)</SelectItem>
                  <SelectItem value="upcoming_1">Próximo (1 día)</SelectItem>
                  <SelectItem value="due_today">Vence Hoy</SelectItem>
                  <SelectItem value="overdue_1">Atrasado 1 día</SelectItem>
                  <SelectItem value="overdue_3">Atrasado 3 días</SelectItem>
                  <SelectItem value="overdue_7">Atrasado 7 días</SelectItem>
                  <SelectItem value="overdue_15">Atrasado 15 días</SelectItem>
                  <SelectItem value="overdue_30">Atrasado 30 días</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reminders Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Recordatorios</CardTitle>
          <CardDescription>
            {totalCount} recordatorio(s) encontrado(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reminders.length === 0 ? (
            <div className="text-center py-12">
              <Bell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No hay recordatorios
              </h3>
              <p className="text-gray-500 mb-4">
                Crea un nuevo recordatorio para comenzar
              </p>
              <Button onClick={() => router.push('/collections/reminders/new')}>
                <Plus className="h-4 w-4 mr-2" />
                Nuevo Recordatorio
              </Button>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Préstamo</TableHead>
                      <TableHead>Tipo</TableHead>
                      <TableHead>Canal</TableHead>
                      <TableHead>Programado</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Enviado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reminders.map((reminder) => (
                      <TableRow key={reminder.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            {reminder.customer_name}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Link
                            href={`/loans/${reminder.loan}`}
                            className="text-blue-600 hover:underline"
                          >
                            #{reminder.loan_number}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{reminder.reminder_type_display}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getChannelIcon(reminder.channel)}
                            {reminder.channel_display}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-gray-400" />
                            {formatDateTime(reminder.scheduled_for)}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(reminder.status)}</TableCell>
                        <TableCell>
                          {reminder.sent_at ? formatDateTime(reminder.sent_at) : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            {reminder.status === 'pending' && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleSendReminder(reminder.id)}
                                >
                                  <Send className="h-4 w-4 mr-1" />
                                  Enviar
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleCancelReminder(reminder.id)}
                                >
                                  <XCircle className="h-4 w-4" />
                                </Button>
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-600">
                    Página {currentPage} de {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === 1}
                      onClick={() => setCurrentPage(currentPage - 1)}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={currentPage === totalPages}
                      onClick={() => setCurrentPage(currentPage + 1)}
                    >
                      Siguiente
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
