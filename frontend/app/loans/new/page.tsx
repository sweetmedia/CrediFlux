'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useConfig } from '@/lib/contexts/ConfigContext';
import { loansAPI, collateralsAPI } from '@/lib/api/loans';
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
import { NativeSelect } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Save,
  DollarSign,
  Calculator,
  Search,
  X,
  User,
  IdCard,
  Mail,
  Phone,
  Shield,
  Plus,
  Trash2,
  FileText,
  Info,
  CheckCircle,
  Calendar,
  Percent,
} from 'lucide-react';
import { CollateralCreate } from '@/types';

const loanSchema = z.object({
  customer: z.string().min(1, 'Cliente requerido'),
  principal_amount: z.string().min(1, 'Monto requerido'),
  interest_rate: z.string().min(1, 'Tasa de interés requerida'),
  interest_type: z.enum(['fixed', 'variable', 'variable_rd']),
  term_months: z.string().min(1, 'Plazo requerido'),
  loan_type: z.enum(['personal', 'auto', 'mortgage', 'business', 'student', 'payday']),
  purpose: z.string().optional(),
  payment_frequency: z.enum(['daily', 'weekly', 'biweekly', 'monthly']),
  disbursement_date: z.string().min(1, 'Fecha de desembolso requerida'),
  first_payment_date: z.string().optional(),
  notes: z.string().optional(),
});

type LoanFormData = z.infer<typeof loanSchema>;

const STEPS = [
  { id: 1, name: 'Cliente', icon: User, description: 'Selecciona el cliente' },
  { id: 2, name: 'Préstamo', icon: DollarSign, description: 'Información básica' },
  { id: 3, name: 'Términos', icon: Calendar, description: 'Fechas y frecuencia' },
  { id: 4, name: 'Garantías', icon: Shield, description: 'Colaterales (opcional)' },
  { id: 5, name: 'Revisión', icon: CheckCircle, description: 'Confirmar y crear' },
];

export default function NewLoanPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { config } = useConfig();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [calculatedPayment, setCalculatedPayment] = useState<number | null>(null);
  const [currentStep, setCurrentStep] = useState(1);

  // Customer search states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [filteredCustomers, setFilteredCustomers] = useState<any[]>([]);

  // Collateral states
  const [collaterals, setCollaterals] = useState<CollateralCreate[]>([]);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors },
  } = useForm<LoanFormData>({
    resolver: zodResolver(loanSchema),
    defaultValues: {
      loan_type: 'personal',
      interest_type: 'fixed',
      payment_frequency: 'monthly',
      disbursement_date: new Date().toISOString().split('T')[0],
    },
  });

  const watchedFields = watch(['principal_amount', 'interest_rate', 'term_months', 'payment_frequency']);
  const paymentFrequency = watch('payment_frequency');
  const interestType = watch('interest_type');
  const disbursementDate = watch('disbursement_date');
  const principalAmount = watch('principal_amount');
  const loanType = watch('loan_type');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Auto-calculate first payment date
  useEffect(() => {
    if (!disbursementDate || !paymentFrequency) return;
    const baseDate = new Date(disbursementDate);
    let firstPaymentDate = new Date(baseDate);

    switch (paymentFrequency) {
      case 'daily':
        firstPaymentDate.setDate(baseDate.getDate() + 1);
        break;
      case 'weekly':
        firstPaymentDate.setDate(baseDate.getDate() + 7);
        break;
      case 'biweekly':
        firstPaymentDate.setDate(baseDate.getDate() + 14);
        break;
      case 'monthly':
        firstPaymentDate.setMonth(baseDate.getMonth() + 1);
        break;
    }

    setValue('first_payment_date', firstPaymentDate.toISOString().split('T')[0]);
  }, [paymentFrequency, disbursementDate, setValue]);

  // Load customers
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

        const preSelectedCustomerId = searchParams.get('customer');
        if (preSelectedCustomerId) {
          const preSelectedCustomer = customersList.find(
            (c: any) => c.id === parseInt(preSelectedCustomerId)
          );

          if (preSelectedCustomer) {
            setSelectedCustomer(preSelectedCustomer);
            setValue('customer', preSelectedCustomer.id.toString());
            setSearchTerm(preSelectedCustomer.full_name || `${preSelectedCustomer.first_name || ''} ${preSelectedCustomer.last_name || ''}`.trim());
          } else {
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

  // Calculate payment
  useEffect(() => {
    const [principal, rate, term, frequency] = watchedFields;
    if (principal && rate && term && frequency) {
      const P = parseFloat(principal);
      const annualRate = parseFloat(rate) / 100;
      const termMonths = parseInt(term);

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

  // Filter customers
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

  const handleSelectCustomer = (customer: any) => {
    setSelectedCustomer(customer);
    setValue('customer', customer.id.toString());
    setSearchTerm(customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim());
    setShowDropdown(false);
  };

  const handleClearCustomer = () => {
    setSelectedCustomer(null);
    setValue('customer', '');
    setSearchTerm('');
    setShowDropdown(false);
  };

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setShowDropdown(true);
    if (!value) {
      setSelectedCustomer(null);
      setValue('customer', '');
    }
  };

  const addCollateral = () => {
    setCollaterals([...collaterals, {
      collateral_type: 'vehicle',
      description: '',
      estimated_value: 0,
    }]);
  };

  const updateCollateral = (index: number, field: keyof CollateralCreate, value: any) => {
    const updated = [...collaterals];
    updated[index] = { ...updated[index], [field]: value };
    setCollaterals(updated);
  };

  const removeCollateral = (index: number) => {
    if (confirm('¿Estás seguro de que deseas eliminar esta garantía?')) {
      setCollaterals(collaterals.filter((_, i) => i !== index));
    }
  };

  const validateCollaterals = (): string | null => {
    for (let i = 0; i < collaterals.length; i++) {
      const c = collaterals[i];
      if (!c.description || c.description.trim() === '') {
        return `Garantía ${i + 1}: La descripción es requerida`;
      }
      if (!c.estimated_value || c.estimated_value <= 0) {
        return `Garantía ${i + 1}: El valor estimado debe ser mayor a 0`;
      }
    }
    return null;
  };

  const getTotalCollateralValue = (): number => {
    return collaterals.reduce((sum, c) => sum + (c.estimated_value || 0), 0);
  };

  const getCollateralTypeLabel = (type: string): string => {
    const labels: Record<string, string> = {
      vehicle: 'Vehículo',
      property: 'Propiedad/Inmueble',
      equipment: 'Equipamiento',
      inventory: 'Inventario',
      securities: 'Valores/Acciones',
      cash_deposit: 'Depósito en Efectivo',
      other: 'Otro',
    };
    return labels[type] || type;
  };

  const getPaymentFrequencyLabel = (frequency: string) => {
    const labels: Record<string, string> = {
      daily: 'Diario',
      weekly: 'Semanal',
      biweekly: 'Quincenal',
      monthly: 'Mensual',
    };
    return labels[frequency] || 'Mensual';
  };

  const getLoanTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      personal: 'Personal',
      auto: 'Automóvil',
      mortgage: 'Hipotecario',
      business: 'Empresarial',
      student: 'Estudiantil',
      payday: 'Día de Pago',
    };
    return labels[type] || type;
  };

  const getInterestTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      fixed: 'Fijo',
      variable: 'Variable',
      variable_rd: 'Variable (RD)',
    };
    return labels[type] || type;
  };

  const formatCurrency = (amount: number) => {
    return `${config.currency_symbol}${amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Navigate between steps with validation
  const nextStep = async () => {
    let fieldsToValidate: (keyof LoanFormData)[] = [];

    switch (currentStep) {
      case 1:
        fieldsToValidate = ['customer'];
        break;
      case 2:
        fieldsToValidate = ['principal_amount', 'interest_rate', 'interest_type', 'term_months', 'loan_type'];
        break;
      case 3:
        fieldsToValidate = ['payment_frequency', 'disbursement_date'];
        break;
      case 4:
        // Validate collaterals if any exist
        if (collaterals.length > 0) {
          const collateralError = validateCollaterals();
          if (collateralError) {
            setError(collateralError);
            return;
          }
        }
        break;
    }

    const isValid = await trigger(fieldsToValidate);

    if (isValid) {
      setError('');
      setCurrentStep(currentStep + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const prevStep = () => {
    setError('');
    setCurrentStep(currentStep - 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const onSubmit = async (data: LoanFormData) => {
    if (collaterals.length > 0) {
      const collateralError = validateCollaterals();
      if (collateralError) {
        setError(collateralError);
        return;
      }
    }

    let paymentAmount = calculatedPayment;
    if (!paymentAmount) {
      const P = parseFloat(data.principal_amount);
      const r = parseFloat(data.interest_rate) / 100 / 12;
      const n = parseInt(data.term_months);
      if (P > 0 && r > 0 && n > 0) {
        paymentAmount = P * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
      }
    }

    const submitData = {
      customer: data.customer,
      principal_amount: parseFloat(data.principal_amount),
      interest_rate: parseFloat(data.interest_rate),
      interest_type: data.interest_type,
      term_months: parseInt(data.term_months),
      loan_type: data.loan_type,
      purpose: data.purpose,
      payment_frequency: data.payment_frequency,
      application_date: data.disbursement_date,
      first_payment_date: data.first_payment_date,
      payment_amount: paymentAmount ? parseFloat(paymentAmount.toFixed(2)) : 0,
      notes: data.notes,
    };

    try {
      setIsLoading(true);
      setError('');

      const createdLoan = await loansAPI.createLoan(submitData);

      if (collaterals.length > 0) {
        const collateralPromises = collaterals.map(async (collateral) => {
          const collateralData: any = {
            loan: createdLoan.id,
            collateral_type: collateral.collateral_type,
            description: collateral.description,
            estimated_value: collateral.estimated_value,
            status: 'active',
          };

          // Only include optional fields if they have values
          if (collateral.appraisal_value) {
            collateralData.appraisal_value = collateral.appraisal_value;
          }
          if (collateral.appraisal_date) {
            collateralData.appraisal_date = collateral.appraisal_date;
          }
          if (collateral.notes) {
            collateralData.notes = collateral.notes;
          }

          return collateralsAPI.createCollateral(collateralData);
        });
        await Promise.all(collateralPromises);
      }

      router.push('/loans');
    } catch (err: any) {
      console.error('Error creating loan:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
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

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Nuevo Préstamo</h1>
              <p className="text-sm text-slate-600 mt-1">
                Completa el formulario paso a paso para crear un nuevo préstamo
              </p>
            </div>
            <Link href="/loans">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </Link>
          </div>
        </div>

        {/* Progress Stepper */}
        <Card className="mb-8 border-slate-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              {STEPS.map((step, index) => {
                const StepIcon = step.icon;
                const isActive = currentStep === step.id;
                const isCompleted = currentStep > step.id;

                return (
                  <div key={step.id} className="flex-1">
                    <div className="flex items-center">
                      <div className="flex flex-col items-center flex-1">
                        <div className={`
                          flex items-center justify-center w-12 h-12 rounded-full border-2 mb-2
                          ${isActive ? 'bg-blue-600 border-blue-600 text-white' : ''}
                          ${isCompleted ? 'bg-green-600 border-green-600 text-white' : ''}
                          ${!isActive && !isCompleted ? 'bg-slate-100 border-slate-300 text-slate-400' : ''}
                        `}>
                          {isCompleted ? (
                            <CheckCircle className="h-6 w-6" />
                          ) : (
                            <StepIcon className="h-6 w-6" />
                          )}
                        </div>
                        <p className={`text-xs font-medium text-center ${isActive ? 'text-blue-600' : 'text-slate-600'}`}>
                          {step.name}
                        </p>
                      </div>

                      {index < STEPS.length - 1 && (
                        <div className={`h-0.5 flex-1 mx-2 mt-[-24px] ${
                          currentStep > step.id ? 'bg-green-600' : 'bg-slate-300'
                        }`} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Step 1: Customer Selection */}
          {currentStep === 1 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="flex items-center gap-2 text-slate-900">
                  <User className="h-5 w-5 text-blue-600" />
                  Seleccionar Cliente
                </CardTitle>
                <CardDescription className="text-slate-600">
                  Busca y selecciona el cliente para este préstamo
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="customer-search" className="text-sm font-medium text-slate-700">
                      Cliente <span className="text-red-500">*</span>
                    </Label>
                    {loadingCustomers ? (
                      <div className="flex items-center gap-2 text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Cargando clientes...</span>
                      </div>
                    ) : (
                      <div className="relative">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                          <Input
                            id="customer-search"
                            type="text"
                            placeholder="Buscar por nombre, cédula, email o teléfono..."
                            value={searchTerm}
                            onChange={(e) => handleSearchChange(e.target.value)}
                            onFocus={() => setShowDropdown(true)}
                            className="pl-10 pr-10"
                          />
                          {selectedCustomer && (
                            <button
                              type="button"
                              onClick={handleClearCustomer}
                              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          )}
                        </div>

                        {showDropdown && searchTerm && !selectedCustomer && (
                          <div className="customer-dropdown absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                            {filteredCustomers.length > 0 ? (
                              <div className="py-1">
                                {filteredCustomers.map((customer) => (
                                  <button
                                    key={customer.id}
                                    type="button"
                                    onClick={() => handleSelectCustomer(customer)}
                                    className="w-full px-4 py-3 text-left hover:bg-blue-50 transition-colors border-b border-slate-100 last:border-b-0"
                                  >
                                    <div className="flex items-start gap-3">
                                      <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                          <User className="h-4 w-4 text-blue-600" />
                                          <p className="font-medium text-slate-900">
                                            {customer.full_name || `${customer.first_name || ''} ${customer.last_name || ''}`.trim()}
                                          </p>
                                        </div>
                                        <div className="flex flex-wrap gap-3 text-sm text-slate-600">
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
                                <p className="text-slate-600 mb-2">No se encontraron clientes</p>
                                <p className="text-sm text-slate-500">
                                  Intenta con otro término de búsqueda
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        {selectedCustomer && (
                          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <div className="flex items-start gap-3">
                              <div className="h-12 w-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                                {selectedCustomer.first_name?.charAt(0)}{selectedCustomer.last_name?.charAt(0)}
                              </div>
                              <div className="flex-1">
                                <p className="font-bold text-slate-900 text-lg">
                                  {selectedCustomer.full_name || `${selectedCustomer.first_name || ''} ${selectedCustomer.last_name || ''}`.trim()}
                                </p>
                                <div className="flex flex-wrap gap-3 text-sm text-slate-600 mt-2">
                                  {selectedCustomer.id_number && (
                                    <span className="flex items-center gap-1">
                                      <IdCard className="h-4 w-4" />
                                      {selectedCustomer.id_number}
                                    </span>
                                  )}
                                  {selectedCustomer.email && (
                                    <span className="flex items-center gap-1">
                                      <Mail className="h-4 w-4" />
                                      {selectedCustomer.email}
                                    </span>
                                  )}
                                  {selectedCustomer.phone && (
                                    <span className="flex items-center gap-1">
                                      <Phone className="h-4 w-4" />
                                      {selectedCustomer.phone}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        <input type="hidden" {...register('customer')} />
                      </div>
                    )}
                    {errors.customer && (
                      <p className="text-sm text-red-500">{errors.customer.message}</p>
                    )}
                    <p className="text-xs text-slate-500">
                      ¿No encuentras el cliente?{' '}
                      <Link href="/customers/new" className="text-blue-600 hover:underline font-medium">
                        Agregar nuevo cliente
                      </Link>
                    </p>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-200 flex justify-between">
                <div></div>
                <Button type="button" onClick={nextStep} className="bg-blue-600 hover:bg-blue-700">
                  Siguiente
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 2: Loan Information */}
          {currentStep === 2 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="flex items-center gap-2 text-slate-900">
                  <DollarSign className="h-5 w-5 text-blue-600" />
                  Información del Préstamo
                </CardTitle>
                <CardDescription className="text-slate-600">
                  Ingresa los detalles básicos del préstamo
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="principal_amount" className="text-sm font-medium text-slate-700">
                        Monto del Préstamo ({config.currency}) <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="principal_amount"
                        type="number"
                        step="0.01"
                        placeholder="10000.00"
                        {...register('principal_amount')}
                      />
                      {errors.principal_amount && (
                        <p className="text-sm text-red-500">{errors.principal_amount.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="loan_type" className="text-sm font-medium text-slate-700">
                        Tipo de Préstamo <span className="text-red-500">*</span>
                      </Label>
                      <NativeSelect id="loan_type" {...register('loan_type')}>
                        <option value="personal">Personal</option>
                        <option value="auto">Automóvil</option>
                        <option value="mortgage">Hipotecario</option>
                        <option value="business">Empresarial</option>
                        <option value="student">Estudiantil</option>
                        <option value="payday">Día de Pago</option>
                      </NativeSelect>
                      {errors.loan_type && (
                        <p className="text-sm text-red-500">{errors.loan_type.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="interest_rate" className="text-sm font-medium text-slate-700">
                        Tasa de Interés (% anual) <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="interest_rate"
                        type="number"
                        step="0.01"
                        placeholder="12.5"
                        {...register('interest_rate')}
                      />
                      {errors.interest_rate && (
                        <p className="text-sm text-red-500">{errors.interest_rate.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="interest_type" className="text-sm font-medium text-slate-700">
                        Tipo de Interés <span className="text-red-500">*</span>
                      </Label>
                      <NativeSelect id="interest_type" {...register('interest_type')}>
                        <option value="fixed">Fijo</option>
                        <option value="variable">Variable</option>
                        <option value="variable_rd">Variable (RD)</option>
                      </NativeSelect>
                      {errors.interest_type && (
                        <p className="text-sm text-red-500">{errors.interest_type.message}</p>
                      )}
                    </div>

                    <div className="space-y-2 col-span-2">
                      <Label htmlFor="term_months" className="text-sm font-medium text-slate-700">
                        Plazo (meses) <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="term_months"
                        type="number"
                        placeholder="12"
                        {...register('term_months')}
                      />
                      {errors.term_months && (
                        <p className="text-sm text-red-500">{errors.term_months.message}</p>
                      )}
                    </div>
                  </div>

                  {interestType === 'fixed' && (
                    <Alert className="bg-blue-50 border-blue-200">
                      <Info className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-blue-800">
                        <strong>Interés Fijo:</strong> El interés total se distribuye equitativamente en todas las cuotas.
                      </AlertDescription>
                    </Alert>
                  )}

                  {interestType === 'variable' && (
                    <Alert className="bg-amber-50 border-amber-200">
                      <Info className="h-4 w-4 text-amber-600" />
                      <AlertDescription className="text-amber-800">
                        <strong>Interés Variable/Amortizado:</strong> El interés se calcula sobre el capital restante que va disminuyendo.
                      </AlertDescription>
                    </Alert>
                  )}

                  {interestType === 'variable_rd' && (
                    <Alert className="bg-purple-50 border-purple-200">
                      <Info className="h-4 w-4 text-purple-600" />
                      <AlertDescription className="text-purple-800">
                        <strong>Interés Variable (RD):</strong> El interés se calcula aplicando la tasa directamente al capital restante.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-200 flex justify-between">
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Anterior
                </Button>
                <Button type="button" onClick={nextStep} className="bg-blue-600 hover:bg-blue-700">
                  Siguiente
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 3: Terms and Dates */}
          {currentStep === 3 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="flex items-center gap-2 text-slate-900">
                  <Calendar className="h-5 w-5 text-blue-600" />
                  Términos y Condiciones
                </CardTitle>
                <CardDescription className="text-slate-600">
                  Define las fechas y frecuencia de pago
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="payment_frequency" className="text-sm font-medium text-slate-700">
                        Frecuencia de Pago <span className="text-red-500">*</span>
                      </Label>
                      <NativeSelect id="payment_frequency" {...register('payment_frequency')}>
                        <option value="daily">Diario</option>
                        <option value="weekly">Semanal</option>
                        <option value="biweekly">Quincenal</option>
                        <option value="monthly">Mensual</option>
                      </NativeSelect>
                      {errors.payment_frequency && (
                        <p className="text-sm text-red-500">{errors.payment_frequency.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="disbursement_date" className="text-sm font-medium text-slate-700">
                        Fecha de Desembolso <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="disbursement_date"
                        type="date"
                        {...register('disbursement_date')}
                      />
                      {errors.disbursement_date && (
                        <p className="text-sm text-red-500">{errors.disbursement_date.message}</p>
                      )}
                    </div>

                    <div className="space-y-2 col-span-2">
                      <Label htmlFor="first_payment_date" className="text-sm font-medium text-slate-700">
                        Fecha del Primer Pago
                        <span className="ml-2 text-xs font-normal text-slate-500">(Auto-calculado)</span>
                      </Label>
                      <Input
                        id="first_payment_date"
                        type="date"
                        {...register('first_payment_date')}
                        className="bg-blue-50"
                      />
                      <p className="text-xs text-slate-500">
                        Se calcula automáticamente según la frecuencia de pago. Puedes modificarla si es necesario.
                      </p>
                    </div>
                  </div>

                  {calculatedPayment !== null && (
                    <Alert className="bg-blue-50 border-blue-200">
                      <Calculator className="h-5 w-5 text-blue-600" />
                      <AlertDescription>
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-blue-900">
                            Pago {getPaymentFrequencyLabel(paymentFrequency)} Estimado:
                          </span>
                          <span className="text-2xl font-bold text-blue-600">
                            {formatCurrency(calculatedPayment)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 mt-2">
                          Cálculo aproximado basado en el método de amortización francesa
                        </p>
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="purpose" className="text-sm font-medium text-slate-700">Propósito del Préstamo</Label>
                    <Input
                      id="purpose"
                      placeholder="Ej: Compra de vehículo, mejoras al hogar, etc."
                      {...register('purpose')}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notes" className="text-sm font-medium text-slate-700">Notas Adicionales</Label>
                    <Textarea
                      id="notes"
                      placeholder="Información adicional sobre el préstamo..."
                      rows={3}
                      {...register('notes')}
                    />
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-200 flex justify-between">
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Anterior
                </Button>
                <Button type="button" onClick={nextStep} className="bg-blue-600 hover:bg-blue-700">
                  Siguiente
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 4: Collaterals */}
          {currentStep === 4 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-slate-900">
                      <Shield className="h-5 w-5 text-blue-600" />
                      Garantías (Opcional)
                    </CardTitle>
                    <CardDescription className="text-slate-600">
                      Agrega garantías o colaterales para este préstamo
                    </CardDescription>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addCollateral}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Agregar
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                {collaterals.length === 0 ? (
                  <div className="text-center py-12">
                    <Shield className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">Sin garantías</h3>
                    <p className="text-slate-600 mb-4">
                      Este préstamo no tiene garantías asociadas. Puedes continuar sin agregar garantías.
                    </p>
                    <Button type="button" variant="outline" onClick={addCollateral}>
                      <Plus className="mr-2 h-4 w-4" />
                      Agregar Primera Garantía
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {collaterals.map((collateral, index) => (
                      <div key={index} className="border-2 border-slate-200 rounded-lg p-4 space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-slate-900">Garantía {index + 1}</h4>
                            <Badge className="bg-blue-100 text-blue-700">
                              {getCollateralTypeLabel(collateral.collateral_type)}
                            </Badge>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeCollateral(index)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label className="text-sm font-medium text-slate-700">
                              Tipo <span className="text-red-500">*</span>
                            </Label>
                            <NativeSelect
                              value={collateral.collateral_type}
                              onChange={(e) => updateCollateral(index, 'collateral_type', e.target.value)}
                            >
                              <option value="vehicle">Vehículo</option>
                              <option value="property">Propiedad/Inmueble</option>
                              <option value="equipment">Equipamiento</option>
                              <option value="inventory">Inventario</option>
                              <option value="securities">Valores/Acciones</option>
                              <option value="cash_deposit">Depósito en Efectivo</option>
                              <option value="other">Otro</option>
                            </NativeSelect>
                          </div>

                          <div className="space-y-2">
                            <Label className="text-sm font-medium text-slate-700">
                              Valor Estimado ({config.currency}) <span className="text-red-500">*</span>
                            </Label>
                            <Input
                              type="number"
                              step="0.01"
                              placeholder="0.00"
                              value={collateral.estimated_value}
                              onChange={(e) => updateCollateral(index, 'estimated_value', parseFloat(e.target.value) || 0)}
                            />
                          </div>

                          <div className="space-y-2 col-span-2">
                            <Label className="text-sm font-medium text-slate-700">
                              Descripción <span className="text-red-500">*</span>
                            </Label>
                            <Textarea
                              placeholder="Descripción detallada (marca, modelo, año, placa, etc.)"
                              rows={2}
                              value={collateral.description}
                              onChange={(e) => updateCollateral(index, 'description', e.target.value)}
                            />
                          </div>
                        </div>
                      </div>
                    ))}

                    {collaterals.length > 0 && (
                      <Alert className="bg-blue-50 border-blue-200">
                        <Shield className="h-4 w-4 text-blue-600" />
                        <AlertDescription>
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-blue-900">Valor Total de Garantías:</span>
                            <span className="text-xl font-bold text-blue-600">
                              {formatCurrency(getTotalCollateralValue())}
                            </span>
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </CardContent>
              <CardFooter className="border-t border-slate-200 flex justify-between">
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Anterior
                </Button>
                <Button type="button" onClick={nextStep} className="bg-blue-600 hover:bg-blue-700">
                  Siguiente
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          )}

          {/* Step 5: Review */}
          {currentStep === 5 && (
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="border-b border-slate-200">
                <CardTitle className="flex items-center gap-2 text-slate-900">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                  Revisión Final
                </CardTitle>
                <CardDescription className="text-slate-600">
                  Verifica que toda la información sea correcta antes de crear el préstamo
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-6">
                <div className="space-y-6">
                  {/* Customer Info */}
                  <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                    <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <User className="h-4 w-4 text-blue-600" />
                      Cliente
                    </h3>
                    {selectedCustomer && (
                      <div className="flex items-center gap-3">
                        <div className="h-12 w-12 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">
                          {selectedCustomer.first_name?.charAt(0)}{selectedCustomer.last_name?.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">
                            {selectedCustomer.full_name || `${selectedCustomer.first_name} ${selectedCustomer.last_name}`}
                          </p>
                          <p className="text-sm text-slate-600">{selectedCustomer.id_number}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Loan Details */}
                  <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                    <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-blue-600" />
                      Detalles del Préstamo
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-slate-600">Monto:</p>
                        <p className="font-medium text-slate-900">{formatCurrency(parseFloat(principalAmount || '0'))}</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Tipo:</p>
                        <p className="font-medium text-slate-900">{getLoanTypeLabel(loanType)}</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Tasa de Interés:</p>
                        <p className="font-medium text-slate-900">{watch('interest_rate')}% anual ({getInterestTypeLabel(interestType)})</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Plazo:</p>
                        <p className="font-medium text-slate-900">{watch('term_months')} meses</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Frecuencia de Pago:</p>
                        <p className="font-medium text-slate-900">{getPaymentFrequencyLabel(paymentFrequency)}</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Pago Estimado:</p>
                        <p className="font-bold text-blue-600">{calculatedPayment ? formatCurrency(calculatedPayment) : 'N/A'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Dates */}
                  <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                    <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-blue-600" />
                      Fechas
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-slate-600">Desembolso:</p>
                        <p className="font-medium text-slate-900">{formatDate(disbursementDate)}</p>
                      </div>
                      <div>
                        <p className="text-slate-600">Primer Pago:</p>
                        <p className="font-medium text-slate-900">{formatDate(watch('first_payment_date') || '')}</p>
                      </div>
                    </div>
                  </div>

                  {/* Collaterals */}
                  {collaterals.length > 0 && (
                    <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                      <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                        <Shield className="h-4 w-4 text-blue-600" />
                        Garantías ({collaterals.length})
                      </h3>
                      <div className="space-y-2">
                        {collaterals.map((col, idx) => (
                          <div key={idx} className="flex items-center justify-between text-sm">
                            <span className="text-slate-600">{getCollateralTypeLabel(col.collateral_type)}</span>
                            <span className="font-medium text-slate-900">{formatCurrency(col.estimated_value)}</span>
                          </div>
                        ))}
                        <div className="flex items-center justify-between text-sm font-bold border-t border-slate-300 pt-2 mt-2">
                          <span className="text-slate-900">Total:</span>
                          <span className="text-blue-600">{formatCurrency(getTotalCollateralValue())}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="border-t border-slate-200 flex justify-between">
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Anterior
                </Button>
                <Button type="submit" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700">
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Crear Préstamo
                </Button>
              </CardFooter>
            </Card>
          )}
        </form>
      </div>
    </div>
  );
}
