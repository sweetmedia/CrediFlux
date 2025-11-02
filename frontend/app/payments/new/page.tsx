'use client';

import { useState, useEffect } from 'react';
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
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Loader2, Save, DollarSign, CreditCard, AlertCircle, Search, X, FileText } from 'lucide-react';

const paymentSchema = z.object({
  loan: z.string().min(1, 'Préstamo requerido'),
  amount: z.string().min(1, 'Monto requerido'),
  payment_date: z.string().min(1, 'Fecha de pago requerida'),
  payment_method: z.enum(['cash', 'check', 'bank_transfer', 'card', 'mobile_payment']),
  reference_number: z.string().optional(),
  notes: z.string().optional(),
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

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
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

  // Load loans that can receive payments when authenticated
  useEffect(() => {
    const loadLoans = async () => {
      if (!isAuthenticated) {
        setLoadingLoans(false);
        return;
      }

      try {
        // Load all loans except paid, rejected, and written_off
        // This includes: active, pending, approved, and defaulted loans
        const response = await loansAPI.getLoans({});
        const allLoans = response.results || [];

        // Filter to only show loans that can receive payments
        const loansList = allLoans.filter((loan: any) =>
          !['paid', 'rejected', 'written_off'].includes(loan.status)
        );

        setLoans(loansList);
        setFilteredLoans(loansList);

        // If there's a preselected loan, load it
        if (preselectedLoanId) {
          const preSelectedLoan = loansList.find((l: any) => l.id === preselectedLoanId);
          if (preSelectedLoan) {
            setSelectedLoan(preSelectedLoan);
            setValue('loan', preSelectedLoan.id);
            setSearchTerm(`${preSelectedLoan.loan_number} - ${preSelectedLoan.customer_name}`);
          } else {
            // If loan not found in list, fetch it directly
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

  // Filter loans based on search term
  useEffect(() => {
    if (!searchTerm || selectedLoan) {
      setFilteredLoans(loans);
      return;
    }

    const term = searchTerm.toLowerCase().trim();
    const filtered = loans.filter((loan: any) => {
      const loanNumber = loan.loan_number || '';
      const customerName = loan.customer_name || '';

      return (
        loanNumber.toLowerCase().includes(term) ||
        customerName.toLowerCase().includes(term)
      );
    });

    setFilteredLoans(filtered);
  }, [searchTerm, loans, selectedLoan]);

  // Handle loan selection
  const handleSelectLoan = (loan: any) => {
    console.log('Selected loan data:', {
      id: loan.id,
      loan_number: loan.loan_number,
      total_installments: loan.total_installments,
      paid_installments: loan.paid_installments,
      term_months: loan.term_months,
      payment_amount: loan.payment_amount,
      payment_frequency: loan.payment_frequency,
      interest_type: loan.interest_type,
    });

    setSelectedLoan(loan);
    setValue('loan', loan.id);
    setSearchTerm(`${loan.loan_number} - ${loan.customer_name}`);
    setShowDropdown(false);

    // Auto-fill amount with outstanding balance
    if (loan.outstanding_balance && !isNaN(loan.outstanding_balance) && loan.outstanding_balance > 0) {
      setValue('amount', loan.outstanding_balance.toString());
    }
  };

  // Handle clearing loan selection
  const handleClearLoan = () => {
    setSelectedLoan(null);
    setValue('loan', '');
    setValue('amount', '');
    setSearchTerm('');
    setShowDropdown(false);
  };

  // Handle search input change
  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setShowDropdown(true);
    if (!value) {
      setSelectedLoan(null);
      setValue('loan', '');
      setValue('amount', '');
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('#loan-search') && !target.closest('.loan-dropdown')) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

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

  const formatCurrency = (amount: number | undefined | null) => {
    if (amount === undefined || amount === null || isNaN(amount)) {
      return `${config.currency_symbol}0.00`;
    }
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
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

                {/* Loan Search */}
                <div className="space-y-2">
                  <Label htmlFor="loan-search">
                    Préstamo <span className="text-red-500">*</span>
                  </Label>
                  {loadingLoans ? (
                    <div className="flex items-center gap-2 text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Cargando préstamos...</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          id="loan-search"
                          type="text"
                          placeholder="Buscar por número de préstamo o nombre del cliente..."
                          value={searchTerm}
                          onChange={(e) => handleSearchChange(e.target.value)}
                          onFocus={() => setShowDropdown(true)}
                          className="pl-10 pr-10"
                          disabled={isLoading}
                        />
                        {selectedLoan && (
                          <button
                            type="button"
                            onClick={handleClearLoan}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>

                      {/* Dropdown Results */}
                      {showDropdown && searchTerm && !selectedLoan && (
                        <div className="loan-dropdown absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                          {filteredLoans.length > 0 ? (
                            <div className="py-1">
                              {filteredLoans.map((loan) => (
                                <button
                                  key={loan.id}
                                  type="button"
                                  onClick={() => handleSelectLoan(loan)}
                                  className="w-full px-4 py-3 text-left hover:bg-blue-50 focus:bg-blue-50 focus:outline-none transition-colors border-b border-gray-100 last:border-b-0"
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2 mb-1">
                                        <FileText className="h-4 w-4 text-blue-600 flex-shrink-0" />
                                        <p className="font-medium text-gray-900">
                                          {loan.loan_number}
                                        </p>
                                      </div>
                                      <div className="flex flex-wrap gap-2 text-sm text-gray-600 items-center">
                                        <span>Cliente: {loan.customer_name || 'N/A'}</span>
                                        <span>Balance: {formatCurrency(loan.outstanding_balance)}</span>
                                        {loan.status === 'defaulted' && (
                                          <Badge variant="destructive" className="text-xs">
                                            En Mora Grave
                                          </Badge>
                                        )}
                                        {(loan.days_overdue || 0) > 0 && loan.status !== 'defaulted' && (
                                          <span className="text-red-600 font-medium">
                                            {loan.days_overdue || 0} días de mora
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                </button>
                              ))}
                            </div>
                          ) : (
                            <div className="px-4 py-8 text-center">
                              <p className="text-gray-600 mb-2">No se encontraron préstamos</p>
                              <p className="text-sm text-gray-500">
                                Intenta buscar por número de préstamo o nombre del cliente
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  {errors.loan && <p className="text-sm text-red-500">{errors.loan.message}</p>}
                </div>

                {/* Loan Details Card */}
                {selectedLoan ? (
                  <Card className={`border-2 ${selectedLoan.status === 'defaulted' ? 'bg-red-50 border-red-300' : 'bg-blue-50 border-blue-200'}`}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">Detalles del Préstamo</CardTitle>
                        <div className="flex gap-2">
                          {selectedLoan.status === 'defaulted' && (
                            <Badge variant="destructive">En Mora Grave</Badge>
                          )}
                          {selectedLoan.status === 'active' && (selectedLoan.days_overdue || 0) > 0 && (
                            <Badge variant="destructive">
                              {selectedLoan.days_overdue || 0} días mora
                            </Badge>
                          )}
                          {selectedLoan.status === 'active' && (selectedLoan.days_overdue || 0) === 0 && (
                            <Badge className="bg-green-600">Al Día</Badge>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* Cliente y Número */}
                      <div className="grid grid-cols-2 gap-4 pb-3 border-b border-gray-200">
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Cliente</p>
                          <p className="font-semibold text-gray-900">{selectedLoan.customer_name}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Número de Préstamo</p>
                          <p className="font-semibold text-gray-900">{selectedLoan.loan_number}</p>
                        </div>
                      </div>

                      {/* Montos */}
                      <div>
                        <p className="text-xs font-semibold text-gray-700 mb-2 uppercase">Montos</p>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-gray-500 mb-1">Monto Original</p>
                            <p className="font-semibold text-gray-900">
                              {formatCurrency(selectedLoan.principal_amount)}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Total Pagado</p>
                            <p className="font-semibold text-green-600">
                              {formatCurrency(selectedLoan.total_paid || 0)}
                            </p>
                          </div>
                          <div className="col-span-2">
                            <p className="text-gray-500 mb-1">Balance Pendiente</p>
                            <p className="font-bold text-xl text-blue-700">
                              {formatCurrency(selectedLoan.outstanding_balance)}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Términos del Préstamo */}
                      <div className="pt-3 border-t border-gray-200">
                        <p className="text-xs font-semibold text-gray-700 mb-2 uppercase">Términos</p>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-gray-500 mb-1">Tasa de Interés</p>
                            <p className="font-semibold text-gray-900">
                              {selectedLoan.interest_rate || 0}% anual
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Tipo de Interés</p>
                            <p className="font-semibold text-gray-900 capitalize">
                              {selectedLoan.interest_type === 'fixed' ? 'Fijo' :
                               selectedLoan.interest_type === 'variable' ? 'Variable' :
                               selectedLoan.interest_type === 'variable_rd' ? 'Variable' :
                               selectedLoan.interest_type === 'compound' ? 'Compuesto' :
                               selectedLoan.interest_type || 'Fijo'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Plazo</p>
                            <p className="font-semibold text-gray-900">
                              {selectedLoan.term_months || 0} meses
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Tipo de Préstamo</p>
                            <p className="font-semibold text-gray-900 capitalize">
                              {selectedLoan.loan_type === 'personal' ? 'Personal' :
                               selectedLoan.loan_type === 'business' ? 'Empresarial' :
                               selectedLoan.loan_type === 'mortgage' ? 'Hipotecario' :
                               selectedLoan.loan_type === 'auto' ? 'Vehículo' :
                               selectedLoan.loan_type === 'student' ? 'Estudiantil' :
                               selectedLoan.loan_type || 'Personal'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Cuota</p>
                            <p className="font-semibold text-gray-900">
                              {selectedLoan.interest_type === 'variable_rd' ? (
                                <span className="text-orange-600">Variable</span>
                              ) : (
                                formatCurrency(selectedLoan.payment_amount)
                              )}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 mb-1">Frecuencia</p>
                            <p className="font-semibold text-gray-900 capitalize">
                              {selectedLoan.payment_frequency === 'monthly' ? 'Mensual' :
                               selectedLoan.payment_frequency === 'weekly' ? 'Semanal' :
                               selectedLoan.payment_frequency === 'biweekly' ? 'Quincenal' :
                               selectedLoan.payment_frequency === 'quarterly' ? 'Trimestral' :
                               selectedLoan.payment_frequency || 'N/A'}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Fechas */}
                      {(selectedLoan.disbursement_date || selectedLoan.first_payment_date ||
                        selectedLoan.next_payment_date || selectedLoan.maturity_date) && (
                        <div className="pt-3 border-t border-gray-200">
                          <p className="text-xs font-semibold text-gray-700 mb-2 uppercase">Fechas</p>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            {selectedLoan.disbursement_date && (
                              <div>
                                <p className="text-gray-500 mb-1">Fecha de Desembolso</p>
                                <p className="font-semibold text-gray-900">
                                  {new Date(selectedLoan.disbursement_date).toLocaleDateString('es-DO', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </p>
                              </div>
                            )}
                            {selectedLoan.first_payment_date && (
                              <div>
                                <p className="text-gray-500 mb-1">Primera Cuota</p>
                                <p className="font-semibold text-gray-900">
                                  {new Date(selectedLoan.first_payment_date).toLocaleDateString('es-DO', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </p>
                              </div>
                            )}
                            {selectedLoan.next_payment_date && (
                              <div>
                                <p className="text-gray-500 mb-1">Próximo Pago</p>
                                <p className="font-semibold text-orange-600">
                                  {new Date(selectedLoan.next_payment_date).toLocaleDateString('es-DO', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </p>
                              </div>
                            )}
                            {selectedLoan.maturity_date && (
                              <div>
                                <p className="text-gray-500 mb-1">Fecha de Vencimiento</p>
                                <p className="font-semibold text-gray-900">
                                  {new Date(selectedLoan.maturity_date).toLocaleDateString('es-DO', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Progreso de Pagos */}
                      {(() => {
                        // Usar total_installments si está disponible, sino usar term_months basado en frecuencia
                        const totalInstallments = selectedLoan.total_installments || selectedLoan.term_months || 0;
                        const paidInstallments = selectedLoan.paid_installments || 0;

                        // Solo mostrar si hay al menos 1 cuota
                        if (totalInstallments > 0) {
                          return (
                            <div className="pt-3 border-t border-gray-200">
                              <p className="text-xs font-semibold text-gray-700 mb-2 uppercase">Progreso</p>
                              <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                  <span className="text-gray-600">Cuotas Pagadas</span>
                                  <span className="font-semibold text-gray-900">
                                    {paidInstallments} / {totalInstallments}
                                  </span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2.5">
                                  <div
                                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                                    style={{
                                      width: `${Math.min((paidInstallments / totalInstallments) * 100, 100)}%`
                                    }}
                                  />
                                </div>
                                <div className="text-xs text-gray-500 text-right">
                                  {Math.round((paidInstallments / totalInstallments) * 100)}% completado
                                </div>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      })()}

                      {/* Información de Mora */}
                      {((selectedLoan.days_overdue && selectedLoan.days_overdue > 0) ||
                        (selectedLoan.late_fees && selectedLoan.late_fees > 0)) && (
                        <div className="pt-3 border-t border-gray-200">
                          <p className="text-xs font-semibold text-red-700 mb-2 uppercase">Información de Mora</p>
                          <div className="grid grid-cols-2 gap-3 text-sm">
                            {selectedLoan.days_overdue && selectedLoan.days_overdue > 0 && (
                              <div>
                                <p className="text-gray-500 mb-1">Días de Mora</p>
                                <p className="font-semibold text-red-600">
                                  {selectedLoan.days_overdue} {selectedLoan.days_overdue === 1 ? 'día' : 'días'}
                                </p>
                              </div>
                            )}
                            {selectedLoan.late_fees !== undefined && (
                              <div>
                                <p className="text-gray-500 mb-1">Cargos por Mora</p>
                                <p className="font-semibold text-red-600">
                                  {formatCurrency(selectedLoan.late_fees)}
                                </p>
                              </div>
                            )}
                            {selectedLoan.is_overdue && (
                              <div className="col-span-2">
                                <p className="text-gray-500 mb-1">Estado</p>
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                  <AlertCircle className="h-3 w-3 mr-1" />
                                  Préstamo en Mora
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Alertas */}
                      {selectedLoan.status === 'defaulted' && (
                        <Alert variant="destructive" className="mt-3">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            <strong>Préstamo en Mora Grave:</strong> Este préstamo requiere atención urgente.
                            {(selectedLoan.days_overdue || 0) > 0 && ` Tiene ${selectedLoan.days_overdue || 0} días de atraso.`}
                          </AlertDescription>
                        </Alert>
                      )}

                      {(selectedLoan.days_overdue || 0) > 0 && selectedLoan.status !== 'defaulted' && (
                        <Alert variant="destructive" className="mt-3">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            Este préstamo tiene {selectedLoan.days_overdue || 0} días de mora
                            {(selectedLoan.late_fees || 0) > 0 && ` con ${formatCurrency(selectedLoan.late_fees)} en cargos por mora`}
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
                      Monto del Pago ({config.currency}) <span className="text-red-500">*</span>
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
                    <select
                      id="payment_method"
                      {...register('payment_method')}
                      disabled={isLoading}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <option value="cash">Efectivo</option>
                      <option value="check">Cheque</option>
                      <option value="bank_transfer">Transferencia Bancaria</option>
                      <option value="card">Tarjeta</option>
                      <option value="mobile_payment">Pago Móvil</option>
                    </select>
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
