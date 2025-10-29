'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { loansAPI } from '@/lib/api/loans';
import { customersAPI } from '@/lib/api/customers';
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
import { ArrowLeft, Loader2, Save, DollarSign, Calculator, Search, X, User, IdCard, Mail, Phone } from 'lucide-react';

const loanSchema = z.object({
  customer: z.string().min(1, 'Cliente requerido'),
  principal_amount: z.string().min(1, 'Monto requerido'),
  interest_rate: z.string().min(1, 'Tasa de interés requerida'),
  term_months: z.string().min(1, 'Plazo requerido'),
  loan_type: z.enum(['personal', 'auto', 'mortgage', 'business', 'student', 'payday']),
  purpose: z.string().optional(),
  payment_frequency: z.enum(['daily', 'weekly', 'biweekly', 'monthly']),
  disbursement_date: z.string().min(1, 'Fecha de desembolso requerida'),
  first_payment_date: z.string().optional(),
  notes: z.string().optional(),
});

type LoanFormData = z.infer<typeof loanSchema>;

export default function NewLoanPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [calculatedPayment, setCalculatedPayment] = useState<number | null>(null);

  // Customer search states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [filteredCustomers, setFilteredCustomers] = useState<any[]>([]);

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
  } = useForm<LoanFormData>({
    resolver: zodResolver(loanSchema),
    defaultValues: {
      loan_type: 'personal',
      payment_frequency: 'monthly',
      disbursement_date: new Date().toISOString().split('T')[0],
    },
  });

  const watchedFields = watch(['principal_amount', 'interest_rate', 'term_months', 'payment_frequency']);
  const paymentFrequency = watch('payment_frequency');

  // Get payment frequency label for display
  const getPaymentFrequencyLabel = (frequency: string) => {
    const labels: Record<string, string> = {
      daily: 'Diario',
      weekly: 'Semanal',
      biweekly: 'Quincenal',
      monthly: 'Mensual',
    };
    return labels[frequency] || 'Mensual';
  };

  // Load customers and handle pre-selected customer from URL
  useEffect(() => {
    const loadCustomers = async () => {
      if (!isAuthenticated) {
        setLoadingCustomers(false);
        return;
      }

      try {
        const response = await customersAPI.getCustomers({});
        const customersList = response.results || [];
        setCustomers(customersList);
        setFilteredCustomers(customersList);

        // Check if there's a customer ID in URL params
        const preSelectedCustomerId = searchParams.get('customer');
        if (preSelectedCustomerId) {
          // Find the customer in the list
          const preSelectedCustomer = customersList.find(
            (c: any) => c.id === parseInt(preSelectedCustomerId)
          );

          if (preSelectedCustomer) {
            setSelectedCustomer(preSelectedCustomer);
            setValue('customer', preSelectedCustomer.id.toString());
            setSearchTerm(preSelectedCustomer.full_name || `${preSelectedCustomer.first_name || ''} ${preSelectedCustomer.last_name || ''}`.trim());
          } else {
            // If customer not found in list, fetch it directly
            try {
              const customerData = await customersAPI.getCustomer(preSelectedCustomerId);
              setSelectedCustomer(customerData);
              setValue('customer', customerData.id.toString());
              setSearchTerm(customerData.full_name || `${customerData.first_name || ''} ${customerData.last_name || ''}`.trim());
            } catch (err) {
              console.error('Error loading pre-selected customer:', err);
            }
          }
        }
      } catch (err) {
        console.error('Error loading customers:', err);
      } finally {
        setLoadingCustomers(false);
      }
    };
    loadCustomers();
  }, [isAuthenticated, searchParams, setValue]);

  // Calculate payment amount based on payment frequency
  useEffect(() => {
    const [principal, rate, term, frequency] = watchedFields;
    if (principal && rate && term && frequency) {
      const P = parseFloat(principal);
      const annualRate = parseFloat(rate) / 100;
      const termMonths = parseInt(term);

      // Calculate number of payments based on frequency
      let paymentsPerYear: number;
      switch (frequency) {
        case 'daily':
          paymentsPerYear = 365;
          break;
        case 'weekly':
          paymentsPerYear = 52;
          break;
        case 'biweekly':
          paymentsPerYear = 26;
          break;
        case 'monthly':
        default:
          paymentsPerYear = 12;
          break;
      }

      const periodicRate = annualRate / paymentsPerYear;
      const totalPayments = Math.ceil((termMonths / 12) * paymentsPerYear);

      if (P > 0 && periodicRate > 0 && totalPayments > 0) {
        // Amortization formula: P * [r(1+r)^n] / [(1+r)^n - 1]
        const payment = P * (periodicRate * Math.pow(1 + periodicRate, totalPayments)) /
                       (Math.pow(1 + periodicRate, totalPayments) - 1);
        setCalculatedPayment(payment);
      } else {
        setCalculatedPayment(null);
      }
    } else {
      setCalculatedPayment(null);
    }
  }, [watchedFields]);

  // Filter customers based on search term
  useEffect(() => {
    if (!searchTerm || selectedCustomer) {
      setFilteredCustomers(customers);
      return;
    }

    const term = searchTerm.toLowerCase().trim();
    const filtered = customers.filter((customer: any) => {
      const fullName = customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim();
      const idNumber = customer.id_number || '';
      const email = customer.email || '';
      const phone = customer.phone || '';

      return (
        fullName.toLowerCase().includes(term) ||
        idNumber.toLowerCase().includes(term) ||
        email.toLowerCase().includes(term) ||
        phone.toLowerCase().includes(term)
      );
    });

    setFilteredCustomers(filtered);
  }, [searchTerm, customers, selectedCustomer]);

  // Handle customer selection
  const handleSelectCustomer = (customer: any) => {
    setSelectedCustomer(customer);
    setValue('customer', customer.id.toString());
    setSearchTerm(customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim());
    setShowDropdown(false);
  };

  // Handle clearing customer selection
  const handleClearCustomer = () => {
    setSelectedCustomer(null);
    setValue('customer', '');
    setSearchTerm('');
    setShowDropdown(false);
  };

  // Handle search input change
  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setShowDropdown(true);
    if (!value) {
      setSelectedCustomer(null);
      setValue('customer', '');
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('#customer-search') && !target.closest('.customer-dropdown')) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const onSubmit = async (data: LoanFormData) => {
    // Calculate payment amount if not already calculated
    let paymentAmount = calculatedPayment;
    if (!paymentAmount) {
      const P = parseFloat(data.principal_amount);
      const r = parseFloat(data.interest_rate) / 100 / 12; // Monthly rate
      const n = parseInt(data.term_months);
      if (P > 0 && r > 0 && n > 0) {
        paymentAmount = P * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      }
    }

    const submitData = {
      customer: data.customer, // Keep as UUID string, don't parse
      principal_amount: parseFloat(data.principal_amount),
      interest_rate: parseFloat(data.interest_rate),
      term_months: parseInt(data.term_months),
      loan_type: data.loan_type,
      purpose: data.purpose,
      payment_frequency: data.payment_frequency,
      application_date: data.disbursement_date, // Backend expects application_date
      first_payment_date: data.first_payment_date,
      payment_amount: paymentAmount ? parseFloat(paymentAmount.toFixed(2)) : 0, // Round to 2 decimals
      notes: data.notes,
    };

    try {
      setIsLoading(true);
      setError('');

      console.log('Submitting loan data:', submitData);

      await loansAPI.createLoan(submitData);

      // Redirect to loans list
      router.push('/loans');
    } catch (err: any) {
      console.error('Error creating loan:', err);
      console.error('Error response data:', err.response?.data);
      console.error('Error response status:', err.response?.status);
      console.error('Submit data was:', submitData);

      if (err.response?.data) {
        const errorData = err.response.data;

        // Show all validation errors
        let errorMessages: string[] = [];

        Object.keys(errorData).forEach(key => {
          if (Array.isArray(errorData[key])) {
            errorMessages.push(`${key}: ${errorData[key].join(', ')}`);
          } else if (typeof errorData[key] === 'string') {
            errorMessages.push(`${key}: ${errorData[key]}`);
          }
        });

        if (errorMessages.length > 0) {
          setError(errorMessages.join(' | '));
        } else {
          setError('Error al crear el préstamo. Por favor verifica los datos.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
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
              <DollarSign className="h-8 w-8 text-blue-600" />
              Nuevo Préstamo
            </h1>
            <p className="text-gray-600 mt-1">Crea un nuevo préstamo para un cliente</p>
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
            {/* Loan Information Card */}
            <Card>
              <CardHeader>
                <CardTitle>Información del Préstamo</CardTitle>
                <CardDescription>
                  Completa los detalles del préstamo. Los campos marcados con * son obligatorios.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-6">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Customer Search */}
                <div className="space-y-2">
                  <Label htmlFor="customer-search">
                    Cliente <span className="text-red-500">*</span>
                  </Label>
                  {loadingCustomers ? (
                    <div className="flex items-center gap-2 text-gray-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Cargando clientes...</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          id="customer-search"
                          type="text"
                          placeholder="Buscar por nombre, cédula, email o teléfono..."
                          value={searchTerm}
                          onChange={(e) => handleSearchChange(e.target.value)}
                          onFocus={() => setShowDropdown(true)}
                          className="pl-10 pr-10"
                          disabled={isLoading}
                        />
                        {selectedCustomer && (
                          <button
                            type="button"
                            onClick={handleClearCustomer}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>

                      {/* Dropdown Results */}
                      {showDropdown && searchTerm && !selectedCustomer && (
                        <div className="customer-dropdown absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                          {filteredCustomers.length > 0 ? (
                            <div className="py-1">
                              {filteredCustomers.map((customer) => (
                                <button
                                  key={customer.id}
                                  type="button"
                                  onClick={() => handleSelectCustomer(customer)}
                                  className="w-full px-4 py-3 text-left hover:bg-blue-50 focus:bg-blue-50 focus:outline-none transition-colors border-b border-gray-100 last:border-b-0"
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2 mb-1">
                                        <User className="h-4 w-4 text-blue-600 flex-shrink-0" />
                                        <p className="font-medium text-gray-900 truncate">
                                          {customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim()}
                                        </p>
                                      </div>
                                      <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                                        {customer.id_number && (
                                          <span className="flex items-center gap-1">
                                            <IdCard className="h-3 w-3" />
                                            {customer.id_number}
                                          </span>
                                        )}
                                        {customer.email && (
                                          <span className="flex items-center gap-1">
                                            <Mail className="h-3 w-3" />
                                            {customer.email}
                                          </span>
                                        )}
                                        {customer.phone && (
                                          <span className="flex items-center gap-1">
                                            <Phone className="h-3 w-3" />
                                            {customer.phone}
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
                              <p className="text-gray-600 mb-2">No se encontraron clientes</p>
                              <p className="text-sm text-gray-500">
                                Intenta con otro término de búsqueda
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Selected Customer Display */}
                      {selectedCustomer && (
                        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-blue-600" />
                              <div>
                                <p className="font-medium text-gray-900">
                                  {selectedCustomer.full_name || `${selectedCustomer.first_name || ''} ${selectedCustomer.last_name || ''}`.trim()}
                                </p>
                                <div className="flex gap-3 text-xs text-gray-600 mt-1">
                                  {selectedCustomer.id_number && (
                                    <span>{selectedCustomer.id_number}</span>
                                  )}
                                  {selectedCustomer.email && (
                                    <span>{selectedCustomer.email}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Hidden input for form submission */}
                      <input type="hidden" {...register('customer')} />
                    </div>
                  )}
                  {errors.customer && (
                    <p className="text-sm text-red-500">{errors.customer.message}</p>
                  )}
                  <p className="text-xs text-gray-500">
                    ¿No encuentras el cliente?{' '}
                    <Link href="/customers/new" className="text-blue-600 hover:underline">
                      Agregar nuevo cliente
                    </Link>
                  </p>
                </div>

                {/* Loan Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="principal_amount">
                      Monto del Préstamo (USD) <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="principal_amount"
                      type="number"
                      step="0.01"
                      placeholder="10000.00"
                      {...register('principal_amount')}
                      disabled={isLoading}
                    />
                    {errors.principal_amount && (
                      <p className="text-sm text-red-500">{errors.principal_amount.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="interest_rate">
                      Tasa de Interés (% anual) <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="interest_rate"
                      type="number"
                      step="0.01"
                      placeholder="12.5"
                      {...register('interest_rate')}
                      disabled={isLoading}
                    />
                    {errors.interest_rate && (
                      <p className="text-sm text-red-500">{errors.interest_rate.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="term_months">
                      Plazo (meses) <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="term_months"
                      type="number"
                      placeholder="12"
                      {...register('term_months')}
                      disabled={isLoading}
                    />
                    {errors.term_months && (
                      <p className="text-sm text-red-500">{errors.term_months.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="payment_frequency">
                      Frecuencia de Pago <span className="text-red-500">*</span>
                    </Label>
                    <Select
                      id="payment_frequency"
                      {...register('payment_frequency')}
                      disabled={isLoading}
                    >
                      <option value="daily">Diario</option>
                      <option value="weekly">Semanal</option>
                      <option value="biweekly">Quincenal</option>
                      <option value="monthly">Mensual</option>
                    </Select>
                    {errors.payment_frequency && (
                      <p className="text-sm text-red-500">{errors.payment_frequency.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="loan_type">
                      Tipo de Préstamo <span className="text-red-500">*</span>
                    </Label>
                    <Select id="loan_type" {...register('loan_type')} disabled={isLoading}>
                      <option value="personal">Personal</option>
                      <option value="auto">Automóvil</option>
                      <option value="mortgage">Hipotecario</option>
                      <option value="business">Empresarial</option>
                      <option value="student">Estudiantil</option>
                      <option value="payday">Día de Pago</option>
                    </Select>
                    {errors.loan_type && (
                      <p className="text-sm text-red-500">{errors.loan_type.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="disbursement_date">
                      Fecha de Desembolso <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="disbursement_date"
                      type="date"
                      {...register('disbursement_date')}
                      disabled={isLoading}
                    />
                    {errors.disbursement_date && (
                      <p className="text-sm text-red-500">{errors.disbursement_date.message}</p>
                    )}
                  </div>

                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="first_payment_date">Fecha del Primer Pago</Label>
                    <Input
                      id="first_payment_date"
                      type="date"
                      {...register('first_payment_date')}
                      disabled={isLoading}
                    />
                    {errors.first_payment_date && (
                      <p className="text-sm text-red-500">{errors.first_payment_date.message}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      Si no se especifica, se calculará automáticamente según la frecuencia de pago
                    </p>
                  </div>
                </div>

                {/* Calculated Payment */}
                {calculatedPayment !== null && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-2">
                      <Calculator className="h-5 w-5 text-blue-600" />
                      <span className="font-semibold text-blue-900">
                        Pago {getPaymentFrequencyLabel(paymentFrequency)} Estimado:
                      </span>
                      <span className="text-2xl font-bold text-blue-600">
                        ${calculatedPayment.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-2">
                      Este es un cálculo aproximado basado en el método de amortización francesa
                    </p>
                  </div>
                )}

                {/* Purpose and Notes */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="purpose">Propósito del Préstamo</Label>
                    <Input
                      id="purpose"
                      placeholder="Ej: Compra de vehículo, mejoras al hogar, etc."
                      {...register('purpose')}
                      disabled={isLoading}
                    />
                    {errors.purpose && (
                      <p className="text-sm text-red-500">{errors.purpose.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notes">Notas Adicionales</Label>
                    <Textarea
                      id="notes"
                      placeholder="Información adicional sobre el préstamo..."
                      rows={3}
                      {...register('notes')}
                      disabled={isLoading}
                    />
                    {errors.notes && (
                      <p className="text-sm text-red-500">{errors.notes.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>

              <CardFooter className="flex justify-between">
                <Link href="/loans">
                  <Button type="button" variant="outline" disabled={isLoading}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isLoading}>
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Crear Préstamo
                </Button>
              </CardFooter>
            </Card>
          </div>
        </form>
      </div>
    </div>
  );
}
