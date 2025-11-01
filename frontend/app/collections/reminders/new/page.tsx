'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { collectionsAPI, loansAPI } from '@/lib/api/loans';
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, ArrowLeft, Save, AlertCircle } from 'lucide-react';
import { Loan } from '@/types';

export default function NewReminderPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState(false);

  // Form state
  const [searchTerm, setSearchTerm] = useState('');
  const [loans, setLoans] = useState<Loan[]>([]);
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [reminderType, setReminderType] = useState('due_today');
  const [channel, setChannel] = useState('email');
  const [scheduledFor, setScheduledFor] = useState('');
  const [messageContent, setMessageContent] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Search loans
  useEffect(() => {
    if (searchTerm.length >= 2) {
      searchLoans();
    } else {
      setLoans([]);
    }
  }, [searchTerm]);

  // Set default scheduled date to tomorrow
  useEffect(() => {
    if (!scheduledFor) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(9, 0, 0, 0);
      const formatted = tomorrow.toISOString().slice(0, 16);
      setScheduledFor(formatted);
    }
  }, []);

  // Set default message when type or customer changes
  useEffect(() => {
    if (selectedLoan) {
      generateDefaultMessage();
    }
  }, [reminderType, channel, selectedLoan]);

  const searchLoans = async () => {
    try {
      const response = await loansAPI.getLoans({ search: searchTerm, status: 'active' });
      setLoans(response.results || []);
    } catch (err: any) {
      console.error('Error searching loans:', err);
    }
  };

  const generateDefaultMessage = () => {
    if (!selectedLoan) return;

    const customerName = selectedLoan.customer_name;
    const loanNumber = selectedLoan.loan_number;
    const balance = new Intl.NumberFormat('es-DO', {
      style: 'currency',
      currency: 'DOP',
    }).format(selectedLoan.outstanding_balance);

    const messages: Record<string, string> = {
      upcoming_3: `Estimado/a ${customerName}, le recordamos que su pago del préstamo ${loanNumber} vence en 3 días. Monto pendiente: ${balance}.`,
      upcoming_1: `Estimado/a ${customerName}, le recordamos que su pago del préstamo ${loanNumber} vence mañana. Monto pendiente: ${balance}.`,
      due_today: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} vence hoy. Por favor realice su pago a tiempo. Monto: ${balance}.`,
      overdue_1: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 1 día de atraso. Por favor comuníquese con nosotros. Monto adeudado: ${balance}.`,
      overdue_3: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 3 días de atraso. Es importante que regularice su situación. Monto adeudado: ${balance}.`,
      overdue_7: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 7 días de atraso. Por favor contacte a nuestro departamento de cobranza. Monto adeudado: ${balance}.`,
      overdue_15: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 15 días de atraso. Necesitamos urgente comunicación de su parte. Monto adeudado: ${balance}.`,
      overdue_30: `Estimado/a ${customerName}, su pago del préstamo ${loanNumber} tiene 30 días de atraso. Su cuenta está en riesgo. Por favor contacte inmediatamente. Monto adeudado: ${balance}.`,
    };

    setMessageContent(messages[reminderType] || messages.due_today);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!selectedLoan) {
      setError('Por favor seleccione un préstamo');
      return;
    }

    if (!scheduledFor) {
      setError('Por favor seleccione fecha y hora');
      return;
    }

    if (!messageContent.trim()) {
      setError('Por favor ingrese el mensaje');
      return;
    }

    try {
      setIsLoading(true);

      // Find the first pending schedule for the loan (if needed for loan_schedule field)
      const schedules = selectedLoan.payment_schedules || [];
      const pendingSchedule = schedules.find((s) => s.status === 'pending');

      const data = {
        loan_schedule: pendingSchedule?.id || '',
        loan: selectedLoan.id,
        customer: selectedLoan.customer,
        reminder_type: reminderType,
        channel: channel,
        scheduled_for: scheduledFor,
        message_content: messageContent.trim(),
      };

      await collectionsAPI.createReminder(data);
      setSuccess(true);

      setTimeout(() => {
        router.push('/collections/reminders');
      }, 1500);
    } catch (err: any) {
      console.error('Error creating reminder:', err);
      setError(err.detail || 'Error al crear el recordatorio');
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-3xl">
      {/* Header */}
      <div className="mb-6">
        <Link
          href="/collections/reminders"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Volver a Recordatorios
        </Link>
        <h1 className="text-3xl font-bold tracking-tight">Nuevo Recordatorio</h1>
        <p className="text-muted-foreground mt-2">
          Crear un nuevo recordatorio de pago para un cliente
        </p>
      </div>

      {/* Success Alert */}
      {success && (
        <Alert className="mb-6 border-green-200 bg-green-50">
          <AlertCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-600">
            Recordatorio creado exitosamente. Redirigiendo...
          </AlertDescription>
        </Alert>
      )}

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Información del Recordatorio</CardTitle>
          <CardDescription>
            Complete los datos para crear el recordatorio
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Loan Search */}
            <div className="space-y-2">
              <Label htmlFor="loan-search">Buscar Préstamo *</Label>
              <Input
                id="loan-search"
                type="text"
                placeholder="Buscar por número de préstamo o nombre del cliente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                disabled={!!selectedLoan}
              />
              {loans.length > 0 && !selectedLoan && (
                <div className="border rounded-md max-h-60 overflow-y-auto">
                  {loans.map((loan) => (
                    <div
                      key={loan.id}
                      className="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                      onClick={() => {
                        setSelectedLoan(loan);
                        setSearchTerm('');
                        setLoans([]);
                      }}
                    >
                      <div className="font-medium">#{loan.loan_number}</div>
                      <div className="text-sm text-gray-600">
                        Cliente: {loan.customer_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        Balance: {new Intl.NumberFormat('es-DO', {
                          style: 'currency',
                          currency: 'DOP',
                        }).format(loan.outstanding_balance)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {selectedLoan && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">#{selectedLoan.loan_number}</div>
                      <div className="text-sm text-gray-600">
                        Cliente: {selectedLoan.customer_name}
                      </div>
                      <div className="text-sm text-gray-600">
                        Balance: {new Intl.NumberFormat('es-DO', {
                          style: 'currency',
                          currency: 'DOP',
                        }).format(selectedLoan.outstanding_balance)}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedLoan(null)}
                    >
                      Cambiar
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* Reminder Type */}
            <div className="space-y-2">
              <Label htmlFor="reminder-type">Tipo de Recordatorio *</Label>
              <Select value={reminderType} onValueChange={setReminderType}>
                <SelectTrigger id="reminder-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
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

            {/* Channel */}
            <div className="space-y-2">
              <Label htmlFor="channel">Canal de Comunicación *</Label>
              <Select value={channel} onValueChange={setChannel}>
                <SelectTrigger id="channel">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="sms">SMS</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                  <SelectItem value="call">Llamada</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Scheduled Date/Time */}
            <div className="space-y-2">
              <Label htmlFor="scheduled-for">Fecha y Hora Programada *</Label>
              <Input
                id="scheduled-for"
                type="datetime-local"
                value={scheduledFor}
                onChange={(e) => setScheduledFor(e.target.value)}
                required
              />
            </div>

            {/* Message Content */}
            <div className="space-y-2">
              <Label htmlFor="message">Mensaje *</Label>
              <Textarea
                id="message"
                rows={6}
                placeholder="Escriba el mensaje del recordatorio..."
                value={messageContent}
                onChange={(e) => setMessageContent(e.target.value)}
                required
              />
              <p className="text-xs text-gray-500">
                {messageContent.length} caracteres
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-4">
              <Button type="submit" disabled={isLoading || !selectedLoan}>
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Guardando...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Crear Recordatorio
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/collections/reminders')}
                disabled={isLoading}
              >
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
