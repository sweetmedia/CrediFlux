'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI, paymentsAPI } from '@/lib/api/loans';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Loader2, Save, DollarSign, CreditCard, AlertCircle } from 'lucide-react';

const paymentSchema = z.object({
  loan: z.string().min(1, 'Préstamo requerido'),
  amount: z.string().min(1, 'Monto requerido'),
  payment_date: z.string().min(1, 'Fecha de pago requerida'),
  payment_method: z.enum(['cash', 'check', 'bank_transfer', 'card', 'other']),
  reference_number: z.string().optional(),
  notes: z.string().optional(),
});

type PaymentFormData = z.infer<typeof paymentSchema>;

export default function NewPaymentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [loans, setLoans] = useState<any[]>([]);
  const [loadingLoans, setLoadingLoans] = useState(true);
  const [selectedLoan, setSelectedLoan] = useState<any>(null);
  const [loadingLoanDetails, setLoadingLoanDetails] = useState(false);

  const preselectedLoanId = searchParams.get('loan');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: {
      payment_method: 'cash',
      payment_date: new Date().toISOString().split('T')[0],
      loan: preselectedLoanId || '',
    },
  });

  const watchedLoan = watch('loan');

  // Load active loans only when authenticated
  useEffect(() => {
    const loadLoans = async () => {
      if (!isAuthenticated) {
        setLoadingLoans(false);
        return;
      }

      try {
        const response = await loansAPI.getLoans({ status: 'active' });
        setLoans(response.results || []);
      } catch (err) {
        console.error('Error loading loans:', err);
      } finally {
        setLoadingLoans(false);
      }
    };
    loadLoans();
  }, [isAuthenticated]);

  // Load loan details when selected
  useEffect(() => {
    const loadLoanDetails = async () => {
      if (!watchedLoan) {
        setSelectedLoan(null);
        return;
      }

      try {
        setLoadingLoanDetails(true);
        const loan = await loansAPI.getLoan(watchedLoan);
        setSelectedLoan(loan);

        // Auto-fill amount with outstanding balance
        if (loan.outstanding_balance) {
          setValue('amount', loan.outstanding_balance.toString());
        }
      } catch (err) {
        console.error('Error loading loan details:', err);
      } finally {
        setLoadingLoanDetails(false);
      }
    };

    loadLoanDetails();
  }, [watchedLoan, setValue]);

  const onSubmit = async (data: PaymentFormData) => {
    try {
      setIsLoading(true);
      setError('');

      const submitData = {
        loan: data.loan, // UUID string, not integer
        amount: parseFloat(data.amount),
        payment_date: data.payment_date,
        payment_method: data.payment_method,
        reference_number: data.reference_number,
        notes: data.notes,
      };

      await paymentsAPI.createPayment(submitData);

      // Redirect to payments list or loan detail
      router.push(`/loans/${data.loan}`);
    } catch (err: any) {
      console.error('Error creating payment:', err);

      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.detail) {
          setError(errorData.detail);
        } else if (errorData.amount) {
          setError(`Monto: ${errorData.amount[0]}`);
        } else if (errorData.loan) {
          setError(`Préstamo: ${errorData.loan[0]}`);
        } else {
          setError('Error al registrar el pago. Por favor verifica los datos.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
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
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <CreditCard className="h-8 w-8 text-blue-600" />
              Registrar Pago
            </h1>
            <p className="text-gray-600 mt-1">Registra un nuevo pago para un préstamo</p>
          </div>
          <Link href="/loans">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Button>
          </Link>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-6">
            {/* Payment Information Card */}
            <Card>
              <CardHeader>
                <CardTitle>Información del Pago</CardTitle>
                <CardDescription>
                  Completa los detalles del pago. Los campos marcados con * son obligatorios.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Loan Selection */}
                <div className="space-y-2">
                  <Label htmlFor="loan">
                    Préstamo <span className="text-red-500">*</span>
                  </Label>
                  {loadingLoans ? (
                    <div className="flex items-center gap-2 text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Cargando préstamos...</span>
                    </div>
                  ) : (
                    <Select id="loan" {...register('loan')} disabled={isLoading}>
                      <option value="">Seleccionar préstamo...</option>
                      {loans.map((loan) => (
                        <option key={loan.id} value={loan.id}>
                          {loan.loan_number} - {loan.customer_name} (Balance:{' '}
                          {formatCurrency(loan.outstanding_balance)})
                        </option>
                      ))}
                    </Select>
                  )}
                  {errors.loan && <p className="text-sm text-red-500">{errors.loan.message}</p>}
                </div>

                {/* Loan Details Card */}
                {loadingLoanDetails ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                  </div>
                ) : selectedLoan ? (
                  <Card className="bg-blue-50 border-blue-200">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg">Detalles del Préstamo</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="font-semibold">Cliente:</span>{' '}
                          {selectedLoan.customer_name}
                        </div>
                        <div>
                          <span className="font-semibold">Número:</span> {selectedLoan.loan_number}
                        </div>
                        <div>
                          <span className="font-semibold">Monto Original:</span>{' '}
                          {formatCurrency(selectedLoan.principal_amount)}
                        </div>
                        <div>
                          <span className="font-semibold">Tasa:</span> {selectedLoan.interest_rate}
                          %
                        </div>
                        <div>
                          <span className="font-semibold">Pagado:</span>{' '}
                          {formatCurrency(selectedLoan.total_paid || 0)}
                        </div>
                        <div className="font-bold text-blue-700">
                          <span className="font-semibold">Balance Pendiente:</span>{' '}
                          {formatCurrency(selectedLoan.outstanding_balance)}
                        </div>
                      </div>

                      {selectedLoan.days_overdue > 0 && (
                        <Alert variant="destructive" className="mt-3">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            Este préstamo tiene {selectedLoan.days_overdue} días de mora
                          </AlertDescription>
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                ) : null}

                {/* Payment Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="amount">
                      Monto del Pago (USD) <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="amount"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      {...register('amount')}
                      disabled={isLoading}
                    />
                    {errors.amount && (
                      <p className="text-sm text-red-500">{errors.amount.message}</p>
                    )}
                    {selectedLoan && (
                      <p className="text-xs text-gray-500">
                        Balance pendiente: {formatCurrency(selectedLoan.outstanding_balance)}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="payment_date">
                      Fecha de Pago <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="payment_date"
                      type="date"
                      {...register('payment_date')}
                      disabled={isLoading}
                    />
                    {errors.payment_date && (
                      <p className="text-sm text-red-500">{errors.payment_date.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="payment_method">
                      Método de Pago <span className="text-red-500">*</span>
                    </Label>
                    <Select
                      id="payment_method"
                      {...register('payment_method')}
                      disabled={isLoading}
                    >
                      <option value="cash">Efectivo</option>
                      <option value="check">Cheque</option>
                      <option value="bank_transfer">Transferencia Bancaria</option>
                      <option value="card">Tarjeta</option>
                      <option value="other">Otro</option>
                    </Select>
                    {errors.payment_method && (
                      <p className="text-sm text-red-500">{errors.payment_method.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="reference_number">Número de Referencia</Label>
                    <Input
                      id="reference_number"
                      placeholder="Ej: TRX-12345"
                      {...register('reference_number')}
                      disabled={isLoading}
                    />
                    {errors.reference_number && (
                      <p className="text-sm text-red-500">{errors.reference_number.message}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      Número de cheque, confirmación, o referencia del pago
                    </p>
                  </div>
                </div>

                {/* Notes */}
                <div className="space-y-2">
                  <Label htmlFor="notes">Notas Adicionales</Label>
                  <Textarea
                    id="notes"
                    placeholder="Información adicional sobre el pago..."
                    rows={3}
                    {...register('notes')}
                    disabled={isLoading}
                  />
                  {errors.notes && <p className="text-sm text-red-500">{errors.notes.message}</p>}
                </div>
              </CardContent>

              <CardFooter className="flex justify-between">
                <Link href="/loans">
                  <Button type="button" variant="outline" disabled={isLoading}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isLoading || !selectedLoan}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Registrar Pago
                </Button>
              </CardFooter>
            </Card>
          </div>
        </form>
      </div>
    </div>
  );
}
