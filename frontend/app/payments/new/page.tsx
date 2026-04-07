'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI, paymentsAPI } from '@/lib/api/loans';
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
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { NativeSelect as Select } from '@/components/ui/native-select';
import {
  ArrowLeft,
  Loader2,
  Save,
  Search,
  X,
  FileText,
  AlertCircle,
  Landmark,
  Receipt,
  Wallet,
  Calendar,
  BadgeDollarSign,
  CircleDollarSign,
  User,
  CheckCircle,
} from 'lucide-react';

const paymentSchema = z.object({
  loan: z.string().min(1, 'Préstamo requerido'),
  amount: z.string().min(1, 'Monto requerido'),
  payment_date: z.string().min(1, 'Fecha de pago requerida'),
  payment_method: z.enum(['cash', 'check', 'bank_transfer', 'card', 'mobile_payment']),
  reference_number: z.string().optional(),
  notes: z.string().optional(),
  waive_late_fee: z.boolean().optional(),
  late_fee_waiver_reason: z.string().optional(),
});

type PaymentFormData = z.infer<typeof paymentSchema>;

export default function NewPaymentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [loans, setLoans] = useState<any[]>([]);
  const [filteredLoans, setFilteredLoans] = useState<any[]>([]);
  const [loadingLoans, setLoadingLoans] = useState(true);
  const [selectedLoan, setSelectedLoan] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  const preselectedLoanId = searchParams.get('loan');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<PaymentFormData>({
    resolver: zodResolver(paymentSchema),
    defaultValues: {
      payment_method: 'cash',
      payment_date: new Date().toISOString().split('T')[0],
      loan: preselectedLoanId || '',
      amount: '',
      waive_late_fee: false,
      late_fee_waiver_reason: '',
    },
  });

  const watchedAmount = Number(watch('amount') || 0);
  const watchedMethod = watch('payment_method');
  const watchedWaiveLateFee = watch('waive_late_fee');

  useEffect(() => {
    const loadLoans = async () => {
      if (!isAuthenticated) {
        setLoadingLoans(false);
        return;
      }

      try {
        const response = await loansAPI.getLoans({});
        const allLoans = response.results || [];
        const loansList = allLoans.filter((loan: any) => !['paid', 'rejected', 'written_off'].includes(loan.status));

        setLoans(loansList);
        setFilteredLoans(loansList);

        if (preselectedLoanId) {
          const preSelectedLoan = loansList.find((l: any) => l.id === preselectedLoanId);
          if (preSelectedLoan) {
            setSelectedLoan(preSelectedLoan);
            setValue('loan', preSelectedLoan.id);
            setSearchTerm(`${preSelectedLoan.loan_number} - ${preSelectedLoan.customer_name}`);
          } else {
            try {
              const loanData = await loansAPI.getLoan(preselectedLoanId);
              setSelectedLoan(loanData);
              setValue('loan', loanData.id);
              setSearchTerm(`${loanData.loan_number} - ${loanData.customer_name}`);
            } catch (err) {
              console.error('Error loading pre-selected loan:', err);
            }
          }
        }
      } catch (err) {
        console.error('Error loading loans:', err);
      } finally {
        setLoadingLoans(false);
      }
    };

    loadLoans();
  }, [isAuthenticated, preselectedLoanId, setValue]);

  useEffect(() => {
    if (!searchTerm || selectedLoan) {
      setFilteredLoans(loans);
      return;
    }

    const term = searchTerm.toLowerCase().trim();
    const filtered = loans.filter((loan: any) => {
      const loanNumber = loan.loan_number || '';
      const customerName = loan.customer_name || '';
      return loanNumber.toLowerCase().includes(term) || customerName.toLowerCase().includes(term);
    });

    setFilteredLoans(filtered);
  }, [searchTerm, loans, selectedLoan]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('#loan-search') && !target.closest('.loan-dropdown')) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLoan = (loan: any) => {
    setSelectedLoan(loan);
    setValue('loan', loan.id);
    setSearchTerm(`${loan.loan_number} - ${loan.customer_name}`);
    setShowDropdown(false);

    if (loan.payment_amount && !isNaN(loan.payment_amount)) {
      setValue('amount', String(loan.payment_amount));
    } else if (loan.outstanding_balance && !isNaN(loan.outstanding_balance)) {
      setValue('amount', String(loan.outstanding_balance));
    }
  };

  const handleClearLoan = () => {
    setSelectedLoan(null);
    setValue('loan', '');
    setValue('amount', '');
    setSearchTerm('');
    setShowDropdown(false);
  };

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setShowDropdown(true);
    if (!value) {
      setSelectedLoan(null);
      setValue('loan', '');
      setValue('amount', '');
    }
  };

  const onSubmit = async (data: PaymentFormData) => {
    try {
      setIsLoading(true);
      setError('');

      await paymentsAPI.createPayment({
        loan: data.loan,
        amount: parseFloat(data.amount),
        payment_date: data.payment_date,
        payment_method: data.payment_method,
        reference_number: data.reference_number,
        notes: data.notes,
        waive_late_fee: data.waive_late_fee,
        late_fee_waiver_reason: data.waive_late_fee ? data.late_fee_waiver_reason : '',
      });

      window.location.href = `/loans/${data.loan}`;
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
          setError('Error al registrar el pago. Verifica los datos e inténtalo otra vez.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null || isNaN(amount)) {
      return `${config.currency_symbol}0.00`;
    }
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-DO', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getPaymentMethodLabel = (method: string) => {
    const methods: Record<string, string> = {
      cash: 'Efectivo',
      check: 'Cheque',
      bank_transfer: 'Transferencia bancaria',
      card: 'Tarjeta',
      mobile_payment: 'Pago móvil',
    };
    return methods[method] || method;
  };

  const loanProgress = useMemo(() => {
    if (!selectedLoan?.payment_schedules?.length) return { paid: 0, total: 0, pct: 0 };
    const total = selectedLoan.payment_schedules.length;
    const paid = selectedLoan.payment_schedules.filter((s: any) => s.status === 'paid').length;
    return {
      paid,
      total,
      pct: total > 0 ? Math.round((paid / total) * 100) : 0,
    };
  }, [selectedLoan]);

  const projectedRemaining = useMemo(() => {
    if (!selectedLoan) return 0;
    const outstanding = Number(selectedLoan.outstanding_balance || 0);
    if (!watchedAmount || watchedAmount <= 0) return outstanding;
    return Math.max(outstanding - watchedAmount, 0);
  }, [selectedLoan, watchedAmount]);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#163300]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f8f7] p-4 py-8 md:p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-3">
              <Link href={selectedLoan ? `/loans/${selectedLoan.id}` : '/payments'}>
                <Button variant="outline" size="sm" className="bg-white">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <div className="inline-flex items-center gap-2 rounded-full border border-[#d7e2db] bg-white px-3 py-1 text-xs font-medium text-[#486152]">
                <Landmark className="h-3.5 w-3.5" />
                Estación de cobro
              </div>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[#163300]">Registrar pago</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Registra el cobro con contexto del préstamo, lectura rápida del balance y una vista clara del impacto operativo.
            </p>
          </div>
        </div>

        <Card className="overflow-hidden border-[#d7e2db] shadow-none">
          <CardContent className="p-0">
            <div className="border-b border-[#d7e2db] bg-gradient-to-r from-[#163300] via-[#244508] to-[#325c10] px-6 py-6 text-white">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div>
                  <p className="text-sm text-white/70">Cobro en proceso</p>
                  <h2 className="mt-1 text-3xl font-semibold">
                    {selectedLoan ? formatCurrency(selectedLoan.outstanding_balance) : 'Selecciona un préstamo'}
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm text-white/80">
                    {selectedLoan
                      ? `Cliente: ${selectedLoan.customer_name} • Préstamo ${selectedLoan.loan_number}`
                      : 'Busca un préstamo para ver balance pendiente, progreso y registrar el pago con mejor contexto.'}
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[420px] xl:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Balance</p>
                    <p className="mt-2 text-2xl font-semibold">{selectedLoan ? formatCurrency(selectedLoan.outstanding_balance) : '--'}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Monto sugerido</p>
                    <p className="mt-2 text-2xl font-semibold">{selectedLoan ? formatCurrency(selectedLoan.payment_amount) : '--'}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Pagado</p>
                    <p className="mt-2 text-2xl font-semibold">{selectedLoan ? formatCurrency(selectedLoan.total_paid || 0) : '--'}</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                    <p className="text-xs uppercase tracking-wide text-white/65">Método</p>
                    <p className="mt-2 text-lg font-semibold">{getPaymentMethodLabel(watchedMethod)}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 bg-white px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Cliente</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{selectedLoan?.customer_name || 'Pendiente de selección'}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Préstamo</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{selectedLoan?.loan_number || 'Sin seleccionar'}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Fecha propuesta</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatDate(watch('payment_date'))}</p>
              </div>
              <div className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Monto digitado</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{formatCurrency(watchedAmount)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-6">
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="text-base text-[#163300]">Seleccionar préstamo</CardTitle>
                  <CardDescription>
                    Busca por número de préstamo o nombre del cliente.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="loan-search">Préstamo</Label>
                    {loadingLoans ? (
                      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Cargando préstamos...
                      </div>
                    ) : (
                      <div className="relative">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                          <Input
                            id="loan-search"
                            type="text"
                            placeholder="Buscar por número o nombre del cliente..."
                            value={searchTerm}
                            onChange={(e) => handleSearchChange(e.target.value)}
                            onFocus={() => setShowDropdown(true)}
                            className="border-slate-200 bg-white pl-10 pr-10 shadow-none"
                            disabled={isLoading}
                          />
                          {selectedLoan && (
                            <button
                              type="button"
                              onClick={handleClearLoan}
                              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>

                        {showDropdown && searchTerm && !selectedLoan && (
                          <div className="loan-dropdown absolute z-50 mt-1 max-h-80 w-full overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-lg">
                            {filteredLoans.length > 0 ? (
                              <div className="py-1">
                                {filteredLoans.map((loan) => (
                                  <button
                                    key={loan.id}
                                    type="button"
                                    onClick={() => handleSelectLoan(loan)}
                                    className="w-full border-b border-slate-100 px-4 py-3 text-left transition-colors hover:bg-slate-50 focus:bg-slate-50 focus:outline-none last:border-b-0"
                                  >
                                    <div className="flex items-start justify-between gap-3">
                                      <div className="min-w-0 flex-1">
                                        <div className="mb-1 flex items-center gap-2">
                                          <FileText className="h-4 w-4 flex-shrink-0 text-[#163300]" />
                                          <p className="font-medium text-slate-900">{loan.loan_number}</p>
                                        </div>
                                        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
                                          <span>{loan.customer_name || 'N/A'}</span>
                                          <span>•</span>
                                          <span>Balance: {formatCurrency(loan.outstanding_balance)}</span>
                                          {(loan.days_overdue || 0) > 0 && (
                                            <span className="font-medium text-red-600">{loan.days_overdue} días mora</span>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </button>
                                ))}
                              </div>
                            ) : (
                              <div className="px-4 py-8 text-center">
                                <p className="text-sm text-slate-600">No se encontraron préstamos</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    <input type="hidden" {...register('loan')} />
                    {errors.loan && <p className="text-xs text-red-600">{errors.loan.message}</p>}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="text-base text-[#163300]">Datos del pago</CardTitle>
                  <CardDescription>
                    Completa monto, fecha, método y referencia del cobro.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="amount">Monto del pago</Label>
                      <Input
                        id="amount"
                        type="number"
                        step="0.01"
                        placeholder="0.00"
                        {...register('amount')}
                        disabled={isLoading}
                        className="border-slate-200 bg-white shadow-none"
                      />
                      {errors.amount && <p className="text-xs text-red-600">{errors.amount.message}</p>}
                      {selectedLoan && (
                        <p className="text-xs text-slate-500">Balance actual: {formatCurrency(selectedLoan.outstanding_balance)}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="payment_date">Fecha de pago</Label>
                      <Input
                        id="payment_date"
                        type="date"
                        {...register('payment_date')}
                        disabled={isLoading}
                        className="border-slate-200 bg-white shadow-none"
                      />
                      {errors.payment_date && <p className="text-xs text-red-600">{errors.payment_date.message}</p>}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="payment_method">Método de pago</Label>
                      <Select id="payment_method" {...register('payment_method')} disabled={isLoading}>
                        <option value="cash">Efectivo</option>
                        <option value="check">Cheque</option>
                        <option value="bank_transfer">Transferencia bancaria</option>
                        <option value="card">Tarjeta</option>
                        <option value="mobile_payment">Pago móvil</option>
                      </Select>
                      {errors.payment_method && <p className="text-xs text-red-600">{errors.payment_method.message}</p>}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="reference_number">Número de referencia</Label>
                      <Input
                        id="reference_number"
                        placeholder="Ej: TRX-12345"
                        {...register('reference_number')}
                        disabled={isLoading}
                        className="border-slate-200 bg-white shadow-none"
                      />
                      <p className="text-xs text-slate-500">Cheque, confirmación bancaria o identificador interno.</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notes">Notas</Label>
                    <Textarea
                      id="notes"
                      placeholder="Detalle adicional sobre el pago..."
                      rows={4}
                      {...register('notes')}
                      disabled={isLoading}
                      className="border-slate-200 bg-white shadow-none"
                    />
                  </div>

                  {selectedLoan && Number(selectedLoan.late_fees || 0) > 0 && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
                      <div className="flex items-start gap-3">
                        <input
                          id="waive_late_fee"
                          type="checkbox"
                          {...register('waive_late_fee')}
                          className="mt-1 h-4 w-4 rounded border-slate-300 text-[#163300] focus:ring-[#163300]"
                        />
                        <div className="flex-1">
                          <Label htmlFor="waive_late_fee" className="text-sm font-medium text-slate-900">
                            Condonar mora de este pago
                          </Label>
                          <p className="mt-1 text-xs text-slate-600">
                            Mora visible en el préstamo: {formatCurrency(Number(selectedLoan.late_fees || 0))}. Si la condonas, quedará registrada en auditoría y en el recibo con tu usuario.
                          </p>
                        </div>
                      </div>

                      {watchedWaiveLateFee && (
                        <div className="mt-4 space-y-2">
                          <Label htmlFor="late_fee_waiver_reason">Motivo de la condonación</Label>
                          <Textarea
                            id="late_fee_waiver_reason"
                            placeholder="Ej: cortesía comercial, autorización de gerencia, ajuste excepcional..."
                            rows={3}
                            {...register('late_fee_waiver_reason')}
                            disabled={isLoading}
                            className="border-slate-200 bg-white shadow-none"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <Link href={selectedLoan ? `/loans/${selectedLoan.id}` : '/payments'}>
                  <Button type="button" variant="outline" className="bg-white" disabled={isLoading}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isLoading || !selectedLoan} className="bg-[#163300] hover:bg-[#0f2400]">
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                  Registrar pago
                </Button>
              </div>
            </div>

            <div className="space-y-6">
              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <User className="h-5 w-5" />
                    Contexto del préstamo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {selectedLoan ? (
                    <div className="space-y-4">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs text-slate-500">Cliente</p>
                        <p className="mt-1 font-medium text-slate-900">{selectedLoan.customer_name}</p>
                        <p className="mt-2 text-xs font-medium text-[#163300]">{selectedLoan.loan_number}</p>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs text-slate-500">Balance pendiente</p>
                          <p className="mt-1 font-semibold text-slate-900">{formatCurrency(selectedLoan.outstanding_balance)}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs text-slate-500">Cuota de referencia</p>
                          <p className="mt-1 font-semibold text-slate-900">{formatCurrency(selectedLoan.payment_amount)}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs text-slate-500">Pagado acumulado</p>
                          <p className="mt-1 font-semibold text-emerald-700">{formatCurrency(selectedLoan.total_paid || 0)}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs text-slate-500">Tasa</p>
                          <p className="mt-1 font-semibold text-slate-900">{selectedLoan.interest_rate || 0}% mensual</p>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                        <div className="mb-2 flex items-center justify-between text-sm">
                          <span className="text-slate-600">Progreso</span>
                          <span className="font-medium text-slate-900">{loanProgress.paid} / {loanProgress.total || 0}</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-slate-200">
                          <div className="h-2.5 rounded-full bg-gradient-to-r from-[#163300] to-[#3d6a16]" style={{ width: `${loanProgress.pct}%` }} />
                        </div>
                        <p className="mt-2 text-right text-xs text-slate-500">{loanProgress.pct}% completado</p>
                      </div>

                      {(selectedLoan.days_overdue || 0) > 0 && (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            Este préstamo tiene {selectedLoan.days_overdue} días de mora.
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
                      Selecciona un préstamo para ver su contexto operativo.
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <BadgeDollarSign className="h-5 w-5" />
                    Impacto estimado
                  </CardTitle>
                  <CardDescription>
                    Vista rápida de cómo se vería el balance luego de registrar este pago.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Monto digitado</span>
                      <span className="font-medium text-slate-900">{formatCurrency(watchedAmount)}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Balance actual</span>
                      <span className="font-medium text-slate-900">{selectedLoan ? formatCurrency(selectedLoan.outstanding_balance) : '--'}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Balance proyectado</span>
                      <span className="font-semibold text-[#163300]">{selectedLoan ? formatCurrency(projectedRemaining) : '--'}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <span className="text-sm text-slate-600">Método</span>
                      <span className="font-medium text-slate-900">{getPaymentMethodLabel(watchedMethod)}</span>
                    </div>
                    {selectedLoan && Number(selectedLoan.late_fees || 0) > 0 && (
                      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                        <span className="text-sm text-slate-600">Mora</span>
                        <span className={`font-medium ${watchedWaiveLateFee ? 'text-amber-700' : 'text-slate-900'}`}>
                          {watchedWaiveLateFee ? `Condonada (${formatCurrency(Number(selectedLoan.late_fees || 0))})` : formatCurrency(Number(selectedLoan.late_fees || 0))}
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-[#d7e2db] shadow-none">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[#163300]">
                    <CircleDollarSign className="h-5 w-5" />
                    Checklist operativo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 text-sm text-slate-700">
                    <div className="flex items-start gap-3">
                      <CheckCircle className="mt-0.5 h-4 w-4 text-emerald-600" />
                      <p>Confirma que el préstamo seleccionado sea el correcto antes de registrar el cobro.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Calendar className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>Usa la fecha real del pago para no distorsionar mora, cronograma y reportes.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Wallet className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>Si tienes referencia bancaria o de caja, guárdala aquí para trazabilidad.</p>
                    </div>
                    <div className="flex items-start gap-3">
                      <Receipt className="mt-0.5 h-4 w-4 text-slate-500" />
                      <p>Después del registro podrás revisar el detalle del pago y descargar su recibo.</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
