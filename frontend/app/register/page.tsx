'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
import { rncAPI, RNCData } from '@/lib/api/rnc';
import { validateRNC, validateCedula } from '@/lib/utils/rd-validation';
import { formatRNC, formatCedula, cleanIDNumber } from '@/lib/utils/id-formatter';
import { Button } from '@/components/ui/button';
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
  Check,
  Shield,
  Zap,
  BarChart3,
  Globe,
  Eye,
  EyeOff,
} from 'lucide-react';

const registerSchema = z.object({
  business_name: z.string().min(2, 'Nombre del negocio requerido'),
  tenant_name: z.string().optional(),
  tax_id: z.string().optional(),
  email: z.string().email('Email inválido'),
  phone: z.string().optional(),
  subdomain: z
    .string()
    .min(3, 'El subdominio debe tener al menos 3 caracteres')
    .regex(/^[a-z0-9-]+$/, 'Solo letras minúsculas, números y guiones'),
  owner_first_name: z.string().min(2, 'Nombre requerido'),
  owner_last_name: z.string().min(2, 'Apellido requerido'),
  owner_id_number: z.string().min(11, 'Cédula debe tener 11 dígitos'),
  owner_email: z.string().email('Email inválido'),
  owner_password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  owner_password_confirm: z.string(),
  owner_phone: z.string().optional(),
  subscription_plan: z.enum(['basic', 'professional', 'enterprise']),
}).refine((data) => data.owner_password === data.owner_password_confirm, {
  message: 'Las contraseñas no coinciden',
  path: ['owner_password_confirm'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

const STEPS = [
  { id: 1, name: 'Negocio', icon: Building2, description: 'Datos de tu empresa' },
  { id: 2, name: 'Administrador', icon: User, description: 'Tu cuenta personal' },
  { id: 3, name: 'Plan', icon: CreditCard, description: 'Elige tu plan' },
];

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [formattedRNC, setFormattedRNC] = useState<string>('');
  const [rncValidation, setRncValidation] = useState<{
    valid: boolean;
    warning?: boolean;
    message: string;
  } | null>(null);
  const [isValidatingRnc, setIsValidatingRnc] = useState(false);
  const [rncData, setRncData] = useState<RNCData | null>(null);
  const [rncValidationStatus, setRncValidationStatus] = useState<'success' | 'warning' | 'error' | null>(null);

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

  const handleRNCChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    const formatted = formatRNC(inputValue);
    setFormattedRNC(formatted);
    const cleaned = cleanIDNumber(formatted);
    setValue('tax_id', cleaned);
    if (cleaned.length >= 3) {
      const validationResult = validateRNC(cleaned);
      setRncValidation({ valid: validationResult.valid, warning: validationResult.warning, message: validationResult.message });
    } else {
      setRncValidation(null);
    }
  };

  const validateRNCWithDGII = async (rnc: string) => {
    if (!rnc || rnc.length < 9) { setRncData(null); setRncValidationStatus(null); return; }
    try {
      setIsValidatingRnc(true);
      setRncValidationStatus(null);
      const result = await rncAPI.validateRNC(rnc);
      if (result.exists && result.data) {
        setRncData(result.data);
        if (result.data.razon_social) setValue('business_name', result.data.razon_social);
        setRncValidationStatus(result.is_active ? 'success' : 'warning');
      } else {
        setRncData(null);
        setRncValidationStatus('error');
      }
    } catch {
      setRncValidationStatus('error');
    } finally {
      setIsValidatingRnc(false);
    }
  };

  const handleCedulaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    const formatted = formatCedula(inputValue);
    setFormattedCedula(formatted);
    const cleaned = cleanIDNumber(formatted);
    setValue('owner_id_number', cleaned);
    if (cleaned.length >= 3) {
      const validationResult = validateCedula(cleaned);
      setCedulaValidation({ valid: validationResult.valid, warning: validationResult.warning, message: validationResult.message });
    } else {
      setCedulaValidation(null);
    }
  };

  const validateCedulaWithDGII = async (cedula: string) => {
    if (!cedula || cedula.length < 11) { setCedulaData(null); setCedulaValidationStatus(null); return; }
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
            setValue('owner_first_name', nameParts[0]);
            setValue('owner_last_name', nameParts.slice(1).join(' '));
          }
        }
        setCedulaValidationStatus(result.is_active ? 'success' : 'warning');
      } else {
        setCedulaData(null);
        setCedulaValidationStatus('error');
      }
    } catch {
      setCedulaValidationStatus('error');
    } finally {
      setIsValidatingCedula(false);
    }
  };

  const validateStep = async (step: number): Promise<boolean> => {
    let fieldsToValidate: (keyof RegisterFormData)[] = [];
    switch (step) {
      case 1: fieldsToValidate = ['business_name', 'subdomain', 'email']; break;
      case 2: fieldsToValidate = ['owner_first_name', 'owner_last_name', 'owner_id_number', 'owner_email', 'owner_password', 'owner_password_confirm']; break;
      case 3: fieldsToValidate = ['subscription_plan']; break;
    }
    return await trigger(fieldsToValidate);
  };

  const nextStep = async () => {
    const isValid = await validateStep(currentStep);
    if (isValid && currentStep < STEPS.length) { setCurrentStep(currentStep + 1); setError(''); }
  };

  const previousStep = () => {
    if (currentStep > 1) { setCurrentStep(currentStep - 1); setError(''); }
  };

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true);
      setError('');
      await authAPI.registerTenant({ ...data, tenant_name: data.subdomain });
      setSuccess(true);
    } catch (err: any) {
      console.error('Registration error:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.detail) setError(errorData.detail);
        else if (errorData.subdomain) setError(`Subdominio: ${errorData.subdomain[0]}`);
        else if (errorData.owner_email) setError(`Email: ${errorData.owner_email[0]}`);
        else if (errorData.email) setError(`Email del negocio: ${errorData.email[0]}`);
        else setError('Error al registrar. Por favor verifica los datos.');
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Success screen
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8f9fa] p-4">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 text-center">
            <div className="mx-auto w-20 h-20 rounded-full bg-[#163300]/10 flex items-center justify-center mb-6">
              <CheckCircle2 className="h-10 w-10 text-[#163300]" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">¡Registro Exitoso!</h1>
            <p className="text-gray-500 mb-2">Tu cuenta ha sido creada exitosamente.</p>
            <p className="text-sm text-gray-600 mb-8">
              <strong>Verifica tu correo electrónico</strong> para activar tu cuenta.
              Revisa tu bandeja de entrada (o spam) y haz clic en el enlace de confirmación.
            </p>
            <Button
              onClick={() => router.push('/login')}
              className="w-full h-12 bg-[#163300] hover:bg-[#0f2400] text-white text-base font-semibold rounded-xl"
            >
              Ir al Login
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-[45%] bg-[#163300] relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-0 right-0 w-96 h-96 bg-[#1e4400] rounded-full -translate-y-1/2 translate-x-1/2 opacity-50" />
          <div className="absolute bottom-0 left-0 w-80 h-80 bg-[#0f2400] rounded-full translate-y-1/3 -translate-x-1/3 opacity-50" />
          <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-[#FFE026]/5 rounded-full -translate-x-1/2 -translate-y-1/2" />
        </div>

        <div className="relative z-10 flex flex-col justify-between p-12 w-full">
          <div>
            <Image
              src="/logo-white.svg"
              alt="CrediFlux"
              width={180}
              height={45}
              className="h-10 w-auto mb-2"
              priority
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <p className="text-white/60 text-sm">Gestión de Préstamos Inteligente</p>
          </div>

          <div className="space-y-8">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Digitaliza tu financiera<br />en minutos
            </h2>
            <div className="space-y-5">
              {[
                { icon: Shield, title: 'Seguro y Confiable', desc: 'Datos encriptados y respaldados automáticamente' },
                { icon: Zap, title: 'Rápido de Configurar', desc: 'Comienza a operar en menos de 5 minutos' },
                { icon: BarChart3, title: 'Reportes en Tiempo Real', desc: 'Dashboard con métricas de tu cartera al instante' },
                { icon: Globe, title: 'Acceso desde Cualquier Lugar', desc: 'Gestiona tu negocio desde tu celular o computadora' },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                    <Icon className="h-5 w-5 text-[#FFE026]" />
                  </div>
                  <div>
                    <p className="text-white font-medium text-sm">{title}</p>
                    <p className="text-white/50 text-sm">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-white/30 text-xs">
            © {new Date().getFullYear()} CrediFlux. Todos los derechos reservados.
          </p>
        </div>
      </div>

      {/* Right Panel — Form */}
      <div className="flex-1 flex flex-col bg-[#f8f9fa]">
        <div className="flex-1 flex items-start justify-center overflow-y-auto py-8 px-4 sm:px-8">
          <div className="w-full max-w-2xl">
            {/* Mobile Logo */}
            <div className="lg:hidden flex justify-center mb-6">
              <Image src="/logo.svg" alt="CrediFlux" width={160} height={40} className="h-9 w-auto" priority />
            </div>

            {/* Header */}
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900">Crear Cuenta</h1>
              <p className="text-gray-500 mt-1">Configura tu plataforma de préstamos en 3 pasos</p>
            </div>

            {/* Stepper */}
            <div className="flex items-center gap-2 mb-8">
              {STEPS.map((step, index) => {
                const isActive = currentStep === step.id;
                const isCompleted = currentStep > step.id;
                return (
                  <div key={step.id} className="flex items-center flex-1">
                    <div className="flex items-center gap-3 flex-1">
                      <div
                        className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 flex-shrink-0 ${
                          isCompleted
                            ? 'bg-[#163300] text-white'
                            : isActive
                            ? 'bg-[#163300] text-white ring-4 ring-[#163300]/20'
                            : 'bg-gray-200 text-gray-400'
                        }`}
                      >
                        {isCompleted ? <Check className="h-4 w-4" /> : step.id}
                      </div>
                      <div className="hidden sm:block min-w-0">
                        <p className={`text-sm font-semibold truncate ${isActive ? 'text-[#163300]' : 'text-gray-400'}`}>
                          {step.name}
                        </p>
                        <p className="text-xs text-gray-400 truncate">{step.description}</p>
                      </div>
                    </div>
                    {index < STEPS.length - 1 && (
                      <div className={`w-8 sm:w-12 h-0.5 mx-2 rounded-full flex-shrink-0 transition-colors ${
                        currentStep > step.id ? 'bg-[#163300]' : 'bg-gray-200'
                      }`} />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Form Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
              <form onSubmit={handleSubmit(onSubmit)}>
                {error && (
                  <Alert variant="destructive" className="mb-6">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Step 1: Business */}
                {currentStep === 1 && (
                  <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="flex items-center gap-2.5 pb-4 border-b border-gray-100">
                      <div className="w-8 h-8 rounded-lg bg-[#163300]/10 flex items-center justify-center">
                        <Building2 className="h-4 w-4 text-[#163300]" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Información del Negocio</h3>
                        <p className="text-xs text-gray-400">Datos de la empresa o financiera</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="tax_id" className="text-sm font-medium text-gray-700">
                        RNC del Negocio <span className="text-gray-400 font-normal">(opcional — auto-rellena datos)</span>
                      </Label>
                      <div className="relative">
                        <Input
                          id="tax_id"
                          placeholder="0-00-00000-0"
                          className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                          value={formattedRNC}
                          onChange={handleRNCChange}
                          onBlur={(e) => validateRNCWithDGII(cleanIDNumber(e.target.value))}
                          disabled={isLoading}
                        />
                        {isValidatingRnc && <Loader2 className="absolute right-3 top-3 h-5 w-5 animate-spin text-[#163300]" />}
                        {rncValidationStatus === 'success' && <CheckCircle className="absolute right-3 top-3 h-5 w-5 text-green-500" />}
                        {rncValidationStatus === 'warning' && <AlertCircle className="absolute right-3 top-3 h-5 w-5 text-yellow-500" />}
                      </div>
                      {rncValidation && (
                        <p className={`text-xs flex items-center gap-1 ${rncValidation.warning ? 'text-yellow-600' : rncValidation.valid ? 'text-green-600' : 'text-red-500'}`}>
                          {rncValidation.message}
                        </p>
                      )}
                      {rncData && (
                        <div className="text-sm text-[#163300] bg-[#163300]/5 p-3 rounded-xl border border-[#163300]/10">
                          <p className="font-medium">{rncData.razon_social}</p>
                          <p className="text-xs text-[#738566]">{rncData.actividad_economica}</p>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="business_name" className="text-sm font-medium text-gray-700">
                        Nombre del Negocio <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="business_name"
                        placeholder="Ej: Financiera ABC S.R.L."
                        className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                        {...register('business_name')}
                        disabled={isLoading}
                      />
                      {errors.business_name && (
                        <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.business_name.message}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                      <div className="space-y-2">
                        <Label htmlFor="subdomain" className="text-sm font-medium text-gray-700">
                          Subdominio <span className="text-red-500">*</span>
                        </Label>
                        <div className="flex items-center gap-0">
                          <Input
                            id="subdomain"
                            placeholder="mi-empresa"
                            className="h-11 rounded-xl rounded-r-none border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                            onChange={handleSubdomainChange}
                            disabled={isLoading}
                          />
                          <span className="inline-flex items-center h-11 px-3 text-xs font-medium text-[#738566] bg-gray-50 border border-l-0 border-gray-200 rounded-r-xl whitespace-nowrap">
                            .crediflux.com.do
                          </span>
                        </div>
                        {errors.subdomain && (
                          <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.subdomain.message}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="phone" className="text-sm font-medium text-gray-700">Teléfono</Label>
                        <Input
                          id="phone"
                          type="tel"
                          placeholder="+1 (809) 555-1234"
                          className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                          {...register('phone')}
                          disabled={isLoading}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                        Email del Negocio <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="contacto@empresa.com"
                        className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                        {...register('email')}
                        disabled={isLoading}
                      />
                      {errors.email && (
                        <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.email.message}</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Step 2: Administrator */}
                {currentStep === 2 && (
                  <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="flex items-center gap-2.5 pb-4 border-b border-gray-100">
                      <div className="w-8 h-8 rounded-lg bg-[#163300]/10 flex items-center justify-center">
                        <User className="h-4 w-4 text-[#163300]" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Cuenta del Administrador</h3>
                        <p className="text-xs text-gray-400">Usuario principal de la plataforma</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_id_number" className="text-sm font-medium text-gray-700">
                        Cédula <span className="text-red-500">*</span>
                        <span className="text-gray-400 font-normal ml-1">(auto-rellena nombre)</span>
                      </Label>
                      <div className="relative">
                        <Input
                          id="owner_id_number"
                          placeholder="000-0000000-0"
                          className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                          value={formattedCedula}
                          onChange={handleCedulaChange}
                          onBlur={(e) => validateCedulaWithDGII(cleanIDNumber(e.target.value))}
                          disabled={isLoading}
                        />
                        {isValidatingCedula && <Loader2 className="absolute right-3 top-3 h-5 w-5 animate-spin text-[#163300]" />}
                        {cedulaValidationStatus === 'success' && <CheckCircle className="absolute right-3 top-3 h-5 w-5 text-green-500" />}
                        {cedulaValidationStatus === 'warning' && <AlertCircle className="absolute right-3 top-3 h-5 w-5 text-yellow-500" />}
                      </div>
                      {cedulaValidation && (
                        <p className={`text-xs flex items-center gap-1 ${cedulaValidation.warning ? 'text-yellow-600' : cedulaValidation.valid ? 'text-green-600' : 'text-red-500'}`}>
                          {cedulaValidation.message}
                        </p>
                      )}
                      {cedulaData && (
                        <div className="text-sm text-[#163300] bg-[#163300]/5 p-3 rounded-xl border border-[#163300]/10">
                          <p className="font-medium">{cedulaData.razon_social}</p>
                        </div>
                      )}
                      {errors.owner_id_number && (
                        <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_id_number.message}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                      <div className="space-y-2">
                        <Label htmlFor="owner_first_name" className="text-sm font-medium text-gray-700">
                          Nombre <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="owner_first_name"
                          placeholder="Juan"
                          className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                          {...register('owner_first_name')}
                          disabled={isLoading}
                        />
                        {errors.owner_first_name && (
                          <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_first_name.message}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="owner_last_name" className="text-sm font-medium text-gray-700">
                          Apellido <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="owner_last_name"
                          placeholder="Pérez"
                          className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                          {...register('owner_last_name')}
                          disabled={isLoading}
                        />
                        {errors.owner_last_name && (
                          <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_last_name.message}</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_email" className="text-sm font-medium text-gray-700">
                        Email <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="owner_email"
                        type="email"
                        placeholder="juan@empresa.com"
                        className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                        {...register('owner_email')}
                        disabled={isLoading}
                      />
                      {errors.owner_email && (
                        <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_email.message}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                      <div className="space-y-2">
                        <Label htmlFor="owner_password" className="text-sm font-medium text-gray-700">
                          Contraseña <span className="text-red-500">*</span>
                        </Label>
                        <div className="relative">
                          <Input
                            id="owner_password"
                            type={showPassword ? 'text' : 'password'}
                            placeholder="Mínimo 8 caracteres"
                            className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300] pr-10"
                            {...register('owner_password')}
                            disabled={isLoading}
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                          >
                            {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                          </button>
                        </div>
                        {errors.owner_password && (
                          <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_password.message}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="owner_password_confirm" className="text-sm font-medium text-gray-700">
                          Confirmar <span className="text-red-500">*</span>
                        </Label>
                        <div className="relative">
                          <Input
                            id="owner_password_confirm"
                            type={showConfirmPassword ? 'text' : 'password'}
                            placeholder="Repite la contraseña"
                            className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300] pr-10"
                            {...register('owner_password_confirm')}
                            disabled={isLoading}
                          />
                          <button
                            type="button"
                            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                            className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                          >
                            {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                          </button>
                        </div>
                        {errors.owner_password_confirm && (
                          <p className="text-xs text-red-500 flex items-center gap-1"><AlertCircle className="h-3 w-3" />{errors.owner_password_confirm.message}</p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="owner_phone" className="text-sm font-medium text-gray-700">Teléfono</Label>
                      <Input
                        id="owner_phone"
                        type="tel"
                        placeholder="+1 (809) 555-1234"
                        className="h-11 rounded-xl border-gray-200 focus:border-[#163300] focus:ring-[#163300]"
                        {...register('owner_phone')}
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                )}

                {/* Step 3: Plan */}
                {currentStep === 3 && (
                  <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                    <div className="flex items-center gap-2.5 pb-4 border-b border-gray-100">
                      <div className="w-8 h-8 rounded-lg bg-[#163300]/10 flex items-center justify-center">
                        <CreditCard className="h-4 w-4 text-[#163300]" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">Selecciona tu Plan</h3>
                        <p className="text-xs text-gray-400">Puedes cambiar de plan en cualquier momento</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {[
                        {
                          value: 'basic',
                          name: 'Starter',
                          price: 'RD$1,499',
                          period: '/mes',
                          features: ['Hasta 50 préstamos', 'Soporte por email', 'Reportes básicos', '1 usuario'],
                          popular: false,
                        },
                        {
                          value: 'professional',
                          name: 'Professional',
                          price: 'RD$2,999',
                          period: '/mes',
                          features: ['Hasta 500 préstamos', 'Soporte prioritario', 'Reportes avanzados', 'API access', '5 usuarios'],
                          popular: true,
                        },
                        {
                          value: 'enterprise',
                          name: 'Enterprise',
                          price: 'RD$5,999',
                          period: '/mes',
                          features: ['Préstamos ilimitados', 'Soporte 24/7', 'Reportes personalizados', 'Integración completa', 'Usuarios ilimitados'],
                          popular: false,
                        },
                      ].map((plan) => (
                        <label
                          key={plan.value}
                          className={`relative flex flex-col p-5 border-2 rounded-2xl cursor-pointer transition-all duration-200 hover:shadow-md ${
                            selectedPlan === plan.value
                              ? 'border-[#163300] bg-[#163300]/[0.02] shadow-sm'
                              : 'border-gray-200 hover:border-[#738566]'
                          }`}
                        >
                          {plan.popular && (
                            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                              <span className="bg-[#FF7503] text-white text-xs font-bold px-3 py-1 rounded-full shadow-sm">
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
                            <CheckCircle className="absolute top-4 right-4 h-5 w-5 text-[#163300]" />
                          )}
                          <span className="font-bold text-lg text-gray-900">{plan.name}</span>
                          <div className="my-3">
                            <span className="text-2xl font-bold text-[#163300]">{plan.price}</span>
                            <span className="text-sm text-gray-400">{plan.period}</span>
                          </div>
                          <ul className="space-y-2 flex-grow">
                            {plan.features.map((feature, idx) => (
                              <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                                <Check className="h-4 w-4 text-[#163300] mt-0.5 flex-shrink-0" />
                                <span>{feature}</span>
                              </li>
                            ))}
                          </ul>
                        </label>
                      ))}
                    </div>
                    {errors.subscription_plan && (
                      <p className="text-xs text-red-500 flex items-center gap-1 justify-center"><AlertCircle className="h-3 w-3" />{errors.subscription_plan.message}</p>
                    )}
                  </div>
                )}

                {/* Navigation */}
                <div className="flex items-center justify-between pt-8 mt-6 border-t border-gray-100">
                  {currentStep > 1 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={previousStep}
                      disabled={isLoading}
                      className="text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                    >
                      <ArrowLeft className="mr-2 h-4 w-4" />
                      Anterior
                    </Button>
                  ) : (
                    <div />
                  )}

                  {currentStep < STEPS.length ? (
                    <Button
                      type="button"
                      onClick={nextStep}
                      disabled={isLoading}
                      className="h-11 px-8 bg-[#163300] hover:bg-[#0f2400] text-white rounded-xl font-semibold"
                    >
                      Siguiente
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      type="submit"
                      disabled={isLoading}
                      className="h-11 px-8 bg-[#163300] hover:bg-[#0f2400] text-white rounded-xl font-semibold"
                    >
                      {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Crear Cuenta
                    </Button>
                  )}
                </div>
              </form>
            </div>

            {/* Footer */}
            <p className="text-center text-sm text-gray-400 mt-6">
              ¿Ya tienes cuenta?{' '}
              <Link href="/login" className="text-[#163300] hover:underline font-medium">
                Inicia sesión aquí
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}