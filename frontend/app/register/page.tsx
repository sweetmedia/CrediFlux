'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
import { rncAPI, RNCData } from '@/lib/api/rnc';
import { validateRNC, validateCedula } from '@/lib/utils/rd-validation';
import { formatRNC, formatCedula, cleanIDNumber } from '@/lib/utils/id-formatter';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  CheckCircle2,
  CheckCircle,
  AlertCircle,
  Info,
  Building2,
  User,
  CreditCard,
  ArrowRight,
  ArrowLeft,
  Check
} from 'lucide-react';

const registerSchema = z.object({
  // Business Information
  business_name: z.string().min(2, 'Nombre del negocio requerido'),
  tenant_name: z.string().optional(),
  tax_id: z.string().optional(),
  email: z.string().email('Email inválido'),
  phone: z.string().optional(),
  subdomain: z
    .string()
    .min(3, 'El subdominio debe tener al menos 3 caracteres')
    .regex(/^[a-z0-9-]+$/, 'Solo letras minúsculas, números y guiones'),

  // Owner Information
  owner_first_name: z.string().min(2, 'Nombre requerido'),
  owner_last_name: z.string().min(2, 'Apellido requerido'),
  owner_id_number: z.string().min(11, 'Cédula debe tener 11 dígitos'),
  owner_email: z.string().email('Email inválido'),
  owner_password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  owner_password_confirm: z.string(),
  owner_phone: z.string().optional(),

  // Subscription Plan
  subscription_plan: z.enum(['basic', 'professional', 'enterprise']),
}).refine((data) => data.owner_password === data.owner_password_confirm, {
  message: 'Las contraseñas no coinciden',
  path: ['owner_password_confirm'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

const STEPS = [
  { id: 1, name: 'Negocio', icon: Building2 },
  { id: 2, name: 'Administrador', icon: User },
  { id: 3, name: 'Plan', icon: CreditCard },
];

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);

  // RNC validation and formatting states
  const [formattedRNC, setFormattedRNC] = useState<string>('');
  const [rncValidation, setRncValidation] = useState<{
    valid: boolean;
    warning?: boolean;
    message: string;
  } | null>(null);
  const [isValidatingRnc, setIsValidatingRnc] = useState(false);
  const [rncData, setRncData] = useState<RNCData | null>(null);
  const [rncValidationStatus, setRncValidationStatus] = useState<'success' | 'warning' | 'error' | null>(null);

  // Owner Cedula validation and formatting states
  const [formattedCedula, setFormattedCedula] = useState<string>('');
  const [cedulaValidation, setCedulaValidation] = useState<{
    valid: boolean;
    warning?: boolean;
    message: string;
  } | null>(null);
  const [isValidatingCedula, setIsValidatingCedula] = useState(false);
  const [cedulaData, setCedulaData] = useState<RNCData | null>(null);
  const [cedulaValidationStatus, setCedulaValidationStatus] = useState<'success' | 'warning' | 'error' | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    trigger,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      subscription_plan: 'basic',
    },
  });

  const selectedPlan = watch('subscription_plan');

  // Handle subdomain change with automatic transformation
  const handleSubdomainChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;

    const transformed = inputValue
      .toLowerCase()
      .replace(/\s+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/--+/g, '-')
      .replace(/^-|-$/g, '');

    setValue('subdomain', transformed);
    setValue('tenant_name', transformed);
  };

  // Handle RNC change with automatic formatting
  const handleRNCChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    const formatted = formatRNC(inputValue);
    setFormattedRNC(formatted);
    const cleaned = cleanIDNumber(formatted);
    setValue('tax_id', cleaned);

    if (cleaned.length >= 3) {
      const validationResult = validateRNC(cleaned);
      setRncValidation({
        valid: validationResult.valid,
        warning: validationResult.warning,
        message: validationResult.message,
      });
    } else {
      setRncValidation(null);
    }
  };

  // Validate RNC with DGII API
  const validateRNCWithDGII = async (rnc: string) => {
    if (!rnc || rnc.length < 9) {
      setRncData(null);
      setRncValidationStatus(null);
      return;
    }

    try {
      setIsValidatingRnc(true);
      setRncValidationStatus(null);

      const result = await rncAPI.validateRNC(rnc);

      if (result.exists && result.data) {
        setRncData(result.data);
        if (result.data.razon_social) {
          setValue('business_name', result.data.razon_social);
        }

        if (result.is_active) {
          setRncValidationStatus('success');
        } else {
          setRncValidationStatus('warning');
        }
      } else {
        setRncData(null);
        setRncValidationStatus('error');
      }
    } catch (error) {
      console.error('Error validating RNC:', error);
      setRncValidationStatus('error');
    } finally {
      setIsValidatingRnc(false);
    }
  };

  // Handle Cedula change with automatic formatting
  const handleCedulaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    const formatted = formatCedula(inputValue);
    setFormattedCedula(formatted);
    const cleaned = cleanIDNumber(formatted);
    setValue('owner_id_number', cleaned);

    if (cleaned.length >= 3) {
      const validationResult = validateCedula(cleaned);
      setCedulaValidation({
        valid: validationResult.valid,
        warning: validationResult.warning,
        message: validationResult.message,
      });
    } else {
      setCedulaValidation(null);
    }
  };

  // Validate Cedula with DGII API
  const validateCedulaWithDGII = async (cedula: string) => {
    if (!cedula || cedula.length < 11) {
      setCedulaData(null);
      setCedulaValidationStatus(null);
      return;
    }

    try {
      setIsValidatingCedula(true);
      setCedulaValidationStatus(null);

      const result = await rncAPI.validateRNC(cedula);

      if (result.exists && result.data) {
        setCedulaData(result.data);
        if (result.data.razon_social) {
          const fullName = result.data.razon_social.trim();
          const nameParts = fullName.split(' ');
          if (nameParts.length >= 2) {
            const firstName = nameParts[0];
            const lastName = nameParts.slice(1).join(' ');
            setValue('owner_first_name', firstName);
            setValue('owner_last_name', lastName);
          }
        }

        if (result.is_active) {
          setCedulaValidationStatus('success');
        } else {
          setCedulaValidationStatus('warning');
        }
      } else {
        setCedulaData(null);
        setCedulaValidationStatus('error');
      }
    } catch (error) {
      console.error('Error validating Cedula:', error);
      setCedulaValidationStatus('error');
    } finally {
      setIsValidatingCedula(false);
    }
  };

  // Validate current step before proceeding
  const validateStep = async (step: number): Promise<boolean> => {
    let fieldsToValidate: (keyof RegisterFormData)[] = [];

    switch (step) {
      case 1:
        fieldsToValidate = ['business_name', 'subdomain', 'email'];
        break;
      case 2:
        fieldsToValidate = ['owner_first_name', 'owner_last_name', 'owner_id_number', 'owner_email', 'owner_password', 'owner_password_confirm'];
        break;
      case 3:
        fieldsToValidate = ['subscription_plan'];
        break;
    }

    const result = await trigger(fieldsToValidate);
    return result;
  };

  const nextStep = async () => {
    const isValid = await validateStep(currentStep);
    if (isValid && currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1);
      setError('');
    }
  };

  const previousStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      setError('');
    }
  };

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true);
      setError('');

      await authAPI.registerTenant({
        ...data,
        tenant_name: data.subdomain,
      });

      setSuccess(true);
      // Don't auto-redirect - user needs to check email first
    } catch (err: any) {
      console.error('Registration error:', err);

      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.detail) {
          setError(errorData.detail);
        } else if (errorData.subdomain) {
          setError(`Subdominio: ${errorData.subdomain[0]}`);
        } else if (errorData.owner_email) {
          setError(`Email: ${errorData.owner_email[0]}`);
        } else if (errorData.email) {
          setError(`Email del negocio: ${errorData.email[0]}`);
        } else {
          setError('Error al registrar. Por favor verifica los datos.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4">
        <Card className="w-full max-w-md shadow-2xl">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
            </div>
            <CardTitle className="text-3xl font-bold text-center bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
              ¡Registro Exitoso!
            </CardTitle>
            <CardDescription className="text-center text-base">
              Tu cuenta ha sido creada exitosamente.
              <br />
              <br />
              <strong>Verifica tu correo electrónico</strong> para activar tu cuenta.
              <br />
              Revisa tu bandeja de entrada (o spam) y haz clic en el enlace de confirmación.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => router.push('/login')}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
            >
              Ir al Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4 py-8">
      <Card className="w-full max-w-4xl shadow-2xl">
        <CardHeader className="space-y-1 pb-8">
          <CardTitle className="text-3xl font-bold text-center bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Crear Cuenta en CrediFlux
          </CardTitle>
          <CardDescription className="text-center text-base">
            Gestiona tus préstamos de manera profesional
          </CardDescription>

          {/* Stepper */}
          <div className="flex items-center justify-center gap-4 pt-8">
            {STEPS.map((step, index) => {
              const Icon = step.icon;
              const isActive = currentStep === step.id;
              const isCompleted = currentStep > step.id;

              return (
                <div key={step.id} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
                        isCompleted
                          ? 'bg-green-500 text-white'
                          : isActive
                          ? 'bg-blue-600 text-white ring-4 ring-blue-200'
                          : 'bg-gray-200 text-gray-400'
                      }`}
                    >
                      {isCompleted ? (
                        <Check className="h-6 w-6" />
                      ) : (
                        <Icon className="h-6 w-6" />
                      )}
                    </div>
                    <span
                      className={`mt-2 text-sm font-medium ${
                        isActive ? 'text-blue-600' : 'text-gray-500'
                      }`}
                    >
                      {step.name}
                    </span>
                  </div>
                  {index < STEPS.length - 1 && (
                    <div
                      className={`w-16 h-1 mx-2 rounded transition-all duration-300 ${
                        currentStep > step.id ? 'bg-green-500' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </CardHeader>

        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Step 1: Business Information */}
            {currentStep === 1 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-900">
                      Información del Negocio
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="business_name" className="text-base">
                        Nombre del Negocio <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="business_name"
                        placeholder="Ej: Financiera ABC S.A."
                        className="h-11"
                        {...register('business_name')}
                        disabled={isLoading}
                      />
                      {errors.business_name && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.business_name.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="tax_id" className="text-base">
                        RNC del Negocio (Opcional)
                      </Label>
                      <div className="relative">
                        <Input
                          id="tax_id"
                          placeholder="0-00-00000-0"
                          className="h-11"
                          value={formattedRNC}
                          onChange={handleRNCChange}
                          onBlur={(e) => validateRNCWithDGII(cleanIDNumber(e.target.value))}
                          disabled={isLoading}
                        />
                        {isValidatingRnc && (
                          <Loader2 className="absolute right-3 top-3 h-5 w-5 animate-spin text-blue-500" />
                        )}
                        {rncValidationStatus === 'success' && (
                          <CheckCircle className="absolute right-3 top-3 h-5 w-5 text-green-500" />
                        )}
                        {rncValidationStatus === 'warning' && (
                          <AlertCircle className="absolute right-3 top-3 h-5 w-5 text-yellow-500" />
                        )}
                      </div>
                      {rncValidation && (
                        <p className={`text-sm flex items-center gap-1 ${
                          rncValidation.warning ? 'text-yellow-600' : rncValidation.valid ? 'text-green-600' : 'text-red-500'
                        }`}>
                          {rncValidation.message}
                        </p>
                      )}
                      {rncData && (
                        <div className="text-sm text-green-700 bg-green-50 p-2 rounded">
                          <p className="font-medium">{rncData.razon_social}</p>
                          <p className="text-xs">{rncData.actividad_economica}</p>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="subdomain" className="text-base">
                        Subdominio <span className="text-red-500">*</span>
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id="subdomain"
                          placeholder="mi-empresa"
                          className="h-11"
                          onChange={handleSubdomainChange}
                          disabled={isLoading}
                        />
                        <span className="text-sm text-gray-500 whitespace-nowrap font-medium">
                          .crediflux.com
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 flex items-start gap-1">
                        <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span>Se convertirá automáticamente a minúsculas. Los espacios se reemplazarán con guiones.</span>
                      </p>
                      {errors.subdomain && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.subdomain.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="email" className="text-base">
                        Email del Negocio <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="contacto@empresa.com"
                        className="h-11"
                        {...register('email')}
                        disabled={isLoading}
                      />
                      {errors.email && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.email.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone" className="text-base">
                        Teléfono (Opcional)
                      </Label>
                      <Input
                        id="phone"
                        type="tel"
                        placeholder="+1 (809) 555-1234"
                        className="h-11"
                        {...register('phone')}
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Owner Information */}
            {currentStep === 2 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <User className="h-5 w-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-900">
                      Información del Administrador
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="owner_id_number" className="text-base">
                        Cédula del Administrador <span className="text-red-500">*</span>
                      </Label>
                      <div className="relative">
                        <Input
                          id="owner_id_number"
                          placeholder="000-0000000-0"
                          className="h-11"
                          value={formattedCedula}
                          onChange={handleCedulaChange}
                          onBlur={(e) => validateCedulaWithDGII(cleanIDNumber(e.target.value))}
                          disabled={isLoading}
                        />
                        {isValidatingCedula && (
                          <Loader2 className="absolute right-3 top-3 h-5 w-5 animate-spin text-blue-500" />
                        )}
                        {cedulaValidationStatus === 'success' && (
                          <CheckCircle className="absolute right-3 top-3 h-5 w-5 text-green-500" />
                        )}
                        {cedulaValidationStatus === 'warning' && (
                          <AlertCircle className="absolute right-3 top-3 h-5 w-5 text-yellow-500" />
                        )}
                      </div>
                      {cedulaValidation && (
                        <p className={`text-sm flex items-center gap-1 ${
                          cedulaValidation.warning ? 'text-yellow-600' : cedulaValidation.valid ? 'text-green-600' : 'text-red-500'
                        }`}>
                          {cedulaValidation.message}
                        </p>
                      )}
                      {cedulaData && (
                        <div className="text-sm text-green-700 bg-green-50 p-2 rounded">
                          <p className="font-medium">{cedulaData.razon_social}</p>
                        </div>
                      )}
                      {errors.owner_id_number && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_id_number.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_first_name" className="text-base">
                        Nombre <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_first_name"
                        placeholder="Juan"
                        className="h-11"
                        {...register('owner_first_name')}
                        disabled={isLoading}
                      />
                      {errors.owner_first_name && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_first_name.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_last_name" className="text-base">
                        Apellido <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_last_name"
                        placeholder="Pérez"
                        className="h-11"
                        {...register('owner_last_name')}
                        disabled={isLoading}
                      />
                      {errors.owner_last_name && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_last_name.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="owner_email" className="text-base">
                        Email <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_email"
                        type="email"
                        placeholder="juan@empresa.com"
                        className="h-11"
                        {...register('owner_email')}
                        disabled={isLoading}
                      />
                      {errors.owner_email && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_email.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_password" className="text-base">
                        Contraseña <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_password"
                        type="password"
                        placeholder="••••••••"
                        className="h-11"
                        {...register('owner_password')}
                        disabled={isLoading}
                      />
                      {errors.owner_password && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_password.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_password_confirm" className="text-base">
                        Confirmar Contraseña <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_password_confirm"
                        type="password"
                        placeholder="••••••••"
                        className="h-11"
                        {...register('owner_password_confirm')}
                        disabled={isLoading}
                      />
                      {errors.owner_password_confirm && (
                        <p className="text-sm text-red-500 flex items-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          {errors.owner_password_confirm.message}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_phone" className="text-base">
                        Teléfono (Opcional)
                      </Label>
                      <Input
                        id="owner_phone"
                        type="tel"
                        placeholder="+1 (809) 555-1234"
                        className="h-11"
                        {...register('owner_phone')}
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Subscription Plan */}
            {currentStep === 3 && (
              <div className="space-y-6 animate-in fade-in duration-300">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <CreditCard className="h-5 w-5 text-blue-600" />
                    <h3 className="text-lg font-semibold text-gray-900">
                      Selecciona tu Plan
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {[
                      {
                        value: 'basic',
                        name: 'Básico',
                        price: 'Gratis',
                        features: ['Hasta 50 préstamos', 'Soporte por email', 'Reportes básicos'],
                        popular: false,
                      },
                      {
                        value: 'professional',
                        name: 'Professional',
                        price: '$49/mes',
                        features: ['Hasta 500 préstamos', 'Soporte prioritario', 'Reportes avanzados', 'API access'],
                        popular: true,
                      },
                      {
                        value: 'enterprise',
                        name: 'Enterprise',
                        price: '$199/mes',
                        features: ['Préstamos ilimitados', 'Soporte 24/7', 'Reportes personalizados', 'Integración completa'],
                        popular: false,
                      },
                    ].map((plan) => (
                      <label
                        key={plan.value}
                        className={`relative flex flex-col p-6 border-2 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-lg ${
                          errors.subscription_plan
                            ? 'border-red-500'
                            : selectedPlan === plan.value
                            ? 'border-blue-500 bg-blue-50 shadow-md'
                            : 'border-gray-200 hover:border-blue-300'
                        }`}
                      >
                        {plan.popular && (
                          <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                            <span className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                              Más Popular
                            </span>
                          </div>
                        )}
                        <input
                          type="radio"
                          value={plan.value}
                          {...register('subscription_plan')}
                          disabled={isLoading}
                          className="sr-only"
                        />
                        {selectedPlan === plan.value && (
                          <CheckCircle className="absolute top-4 right-4 h-6 w-6 text-blue-500" />
                        )}
                        <span className="font-bold text-xl text-gray-900">{plan.name}</span>
                        <span className="text-3xl font-bold my-4 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                          {plan.price}
                        </span>
                        <ul className="space-y-2 flex-grow">
                          {plan.features.map((feature, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                              <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                              <span>{feature}</span>
                            </li>
                          ))}
                        </ul>
                      </label>
                    ))}
                  </div>
                  {errors.subscription_plan && (
                    <p className="text-sm text-red-500 flex items-center gap-1 justify-center">
                      <AlertCircle className="h-3 w-3" />
                      {errors.subscription_plan.message}
                    </p>
                  )}
                </div>
              </div>
            )}
          </CardContent>

          <CardFooter className="flex flex-col space-y-4 pt-6">
            <div className="flex justify-between w-full gap-4">
              {currentStep > 1 && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={previousStep}
                  disabled={isLoading}
                  className="flex-1"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Anterior
                </Button>
              )}

              {currentStep < STEPS.length ? (
                <Button
                  type="button"
                  onClick={nextStep}
                  disabled={isLoading}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  Siguiente
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                >
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Crear Cuenta
                </Button>
              )}
            </div>

            <div className="text-sm text-center text-gray-600">
              ¿Ya tienes cuenta?{' '}
              <Link href="/login" className="text-blue-600 hover:underline font-medium">
                Inicia sesión aquí
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
