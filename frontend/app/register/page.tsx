import { useState } from 'react';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
import { rncAPI, RNCData } from '@/lib/api/rnc';
import { validateRNC, validateCedula } from '@/lib/utils/rd-validation';
import { formatRNC, formatCedula, cleanIDNumber } from '@/lib/utils/id-formatter';
import { AlertCircle, ArrowLeft, ArrowRight, Eye, EyeOff, Loader2 } from 'lucide-react';
import { AuthShell } from '@/components/auth/AuthShell';
import { PasswordRequirements } from '@/components/auth/PasswordRequirements';

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
  { id: 1, name: 'Empresa', title: 'Tu empresa' },
  { id: 2, name: 'Administrador', title: 'Tu cuenta de administrador' },
  { id: 3, name: 'Plan', title: 'Elige un plan' },
  { id: 4, name: 'Confirmar', title: 'Confirma los datos' },
];

// Precios del canvas (register.html), en pesos y sin ITBIS.
const PLANS = [
  { value: 'basic', name: 'Starter', price: '1,499', features: ['50 préstamos activos', '1 usuario', 'Reportes básicos', 'Soporte por correo'] },
  { value: 'professional', name: 'Professional', price: '2,999', features: ['500 préstamos activos', '5 usuarios', 'Reportes avanzados', 'Acceso por API', 'Soporte prioritario'] },
  { value: 'enterprise', name: 'Enterprise', price: '5,999', features: ['Préstamos sin límite', 'Usuarios sin límite', 'Reportes a la medida'] },
] as const;

// Errores de campo de la API → paso donde está el campo.
const FIELD_STEP: Partial<Record<keyof RegisterFormData, number>> = {
  business_name: 1, subdomain: 1, email: 1, phone: 1, tax_id: 1,
  owner_first_name: 2, owner_last_name: 2, owner_id_number: 2, owner_email: 2, owner_phone: 2, owner_password: 2,
};

export default function RegisterPage() {
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState<'created' | 'pending' | null>(null);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
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
    setError: setFieldError,
    getValues,
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
      case 4: return true;
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
      const result = await authAPI.registerTenant({ ...data, tenant_name: data.subdomain });
      // 202 {status: 'pending'}: por encima del tope diario, la cuenta aún no existe.
      setSuccess(result?.status === 'pending' ? 'pending' : 'created');
    } catch (err: any) {
      console.error('Registration error:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        const campo = (Object.keys(FIELD_STEP) as (keyof RegisterFormData)[]).find((k) => errorData[k]);
        if (campo) {
          setFieldError(campo, { message: [].concat(errorData[campo])[0] });
          setCurrentStep(FIELD_STEP[campo]!);
        } else if (errorData.detail) setError(errorData.detail);
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

  const goTo = (step: number) => {
    setCurrentStep(step);
    setError('');
  };

  if (success) {
    return (
      <AuthShell
        eyebrow="Listo"
        title={success === 'pending' ? 'Solicitud recibida' : 'Cuenta creada'}
        description={
          success === 'pending'
            ? 'Estamos revisando tu solicitud. Te escribiremos al correo del administrador cuando la cuenta esté lista.'
            : 'Revisa tu correo para activar tu cuenta: te enviamos un enlace de confirmación (si no lo ves, mira en spam).'
        }
      >
        <Link href="/login" className="cf-btn cf-btn--primary h-11 w-full">
          Ir a iniciar sesión
        </Link>
      </AuthShell>
    );
  }

  const step = STEPS[currentStep - 1];
  const values = getValues();
  const plan = PLANS.find((p) => p.value === selectedPlan) ?? PLANS[0];
  const fieldError = (msg?: string, id?: string) =>
    msg ? <p id={id} className="mt-1.5 text-[12px] text-flame-700">{msg}</p> : null;
  const cedulaHint = cedulaValidation && (
    <p className={`mt-1.5 text-[12px] ${cedulaValidation.valid ? 'text-sage-600' : 'text-flame-700'}`}>{cedulaValidation.message}</p>
  );

  return (
    <AuthShell
      eyebrow={`Paso ${currentStep} de ${STEPS.length}`}
      title={step.title}
      topRight={
        <>
          <span className="hidden sm:inline">¿Ya tienes cuenta?</span>
          <Link href="/login" className="font-medium text-forest-900 underline decoration-forest-900/25 underline-offset-4">
            Iniciar sesión
          </Link>
        </>
      }
    >
      <ol className="-mt-2 mb-8 grid grid-cols-4 gap-2" aria-label="Pasos del registro">
        {STEPS.map((s) => (
          <li key={s.id} aria-current={s.id === currentStep ? 'step' : undefined}>
            <div className={`h-1 rounded ${s.id <= currentStep ? 'bg-forest-900' : 'bg-forest-900/10'}`} aria-hidden="true" />
            <span className={`mt-1.5 block text-[11px] ${s.id === currentStep ? 'text-forest-900' : 'text-sage-500'}`}>{s.name}</span>
          </li>
        ))}
      </ol>

      {error && (
        <div role="alert" className="mb-6 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-flame-600" aria-hidden="true" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-6">
        {currentStep === 1 && (
          <>
            <div className="cf-field">
              <label className="cf-label" htmlFor="tax_id">RNC <span className="text-sage-500">(opcional)</span></label>
              <div className="flex gap-2">
                <input id="tax_id" className="cf-input cf-input--mono flex-1" placeholder="1-31-24587-3" value={formattedRNC} onChange={handleRNCChange} />
                <button type="button" className="cf-btn cf-btn--secondary" onClick={() => validateRNCWithDGII(cleanIDNumber(formattedRNC))} disabled={isValidatingRnc}>
                  {isValidatingRnc ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : 'Buscar en DGII'}
                </button>
              </div>
              {rncValidation && !rncValidation.valid && fieldError(rncValidation.message)}
              {rncValidationStatus && (
                <p className="mt-1.5 text-[12px] text-sage-600" role="status">
                  {rncValidationStatus === 'success' && rncData && `${rncData.razon_social} · activo en la DGII`}
                  {rncValidationStatus === 'warning' && rncData && `${rncData.razon_social} · no figura activo en la DGII`}
                  {rncValidationStatus === 'error' && 'No lo encontramos en la DGII; puedes seguir igual.'}
                </p>
              )}
            </div>
            <div className="cf-field">
              <label className="cf-label" htmlFor="business_name">Nombre de la empresa</label>
              <input id="business_name" className="cf-input" {...register('business_name')} aria-invalid={!!errors.business_name} aria-describedby={errors.business_name ? 'business_name-error' : undefined} />
              {fieldError(errors.business_name?.message, 'business_name-error')}
            </div>
            <div className="cf-field">
              <label className="cf-label" htmlFor="subdomain">Dirección web</label>
              <div className="flex items-center gap-2">
                <input id="subdomain" className="cf-input cf-input--mono flex-1" placeholder="mi-financiera" {...register('subdomain')} onChange={handleSubdomainChange} aria-invalid={!!errors.subdomain} aria-describedby={errors.subdomain ? 'subdomain-error' : undefined} />
                <span className="font-mono text-[12px] text-sage-500">.crediflux.com.do</span>
              </div>
              {fieldError(errors.subdomain?.message, 'subdomain-error')}
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="cf-field">
                <label className="cf-label" htmlFor="email">Correo de la empresa</label>
                <input id="email" type="email" className="cf-input" {...register('email')} aria-invalid={!!errors.email} aria-describedby={errors.email ? 'email-error' : undefined} />
                {fieldError(errors.email?.message, 'email-error')}
              </div>
              <div className="cf-field">
                <label className="cf-label" htmlFor="phone">Teléfono <span className="text-sage-500">(opcional)</span></label>
                <input id="phone" type="tel" className="cf-input cf-input--mono" {...register('phone')} />
              </div>
            </div>
          </>
        )}

        {currentStep === 2 && (
          <>
            <div className="cf-field">
              <label className="cf-label" htmlFor="owner_id_number">Cédula</label>
              <div className="flex gap-2">
                <input id="owner_id_number" className="cf-input cf-input--mono flex-1" placeholder="001-2345111-0" value={formattedCedula} onChange={handleCedulaChange} aria-invalid={!!errors.owner_id_number} aria-describedby={errors.owner_id_number ? 'owner_id_number-error' : undefined} />
                <button type="button" className="cf-btn cf-btn--secondary" onClick={() => validateCedulaWithDGII(cleanIDNumber(formattedCedula))} disabled={isValidatingCedula}>
                  {isValidatingCedula ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : 'Validar'}
                </button>
              </div>
              {fieldError(errors.owner_id_number?.message, 'owner_id_number-error') ?? cedulaHint}
              {cedulaValidationStatus === 'success' && cedulaData && <p className="mt-1.5 text-[12px] text-sage-600" role="status">{cedulaData.razon_social}</p>}
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="cf-field">
                <label className="cf-label" htmlFor="owner_first_name">Nombre</label>
                <input id="owner_first_name" className="cf-input" {...register('owner_first_name')} aria-invalid={!!errors.owner_first_name} />
                {fieldError(errors.owner_first_name?.message)}
              </div>
              <div className="cf-field">
                <label className="cf-label" htmlFor="owner_last_name">Apellidos</label>
                <input id="owner_last_name" className="cf-input" {...register('owner_last_name')} aria-invalid={!!errors.owner_last_name} />
                {fieldError(errors.owner_last_name?.message)}
              </div>
            </div>
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="cf-field">
                <label className="cf-label" htmlFor="owner_email">Correo</label>
                <input id="owner_email" type="email" className="cf-input" {...register('owner_email')} aria-invalid={!!errors.owner_email} aria-describedby={errors.owner_email ? 'owner_email-error' : undefined} />
                {fieldError(errors.owner_email?.message, 'owner_email-error')}
              </div>
              <div className="cf-field">
                <label className="cf-label" htmlFor="owner_phone">Celular <span className="text-sage-500">(opcional)</span></label>
                <input id="owner_phone" type="tel" className="cf-input cf-input--mono" {...register('owner_phone')} />
              </div>
            </div>
            <div className="cf-field">
              <label className="cf-label" htmlFor="owner_password">Contraseña</label>
              <div className="relative">
                <input id="owner_password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" className="cf-input pr-10" {...register('owner_password')} aria-invalid={!!errors.owner_password} aria-describedby={errors.owner_password ? 'owner_password-error owner-password-req' : 'owner-password-req'} />
                <button type="button" onClick={() => setShowPassword((v) => !v)} className="absolute right-0 top-1/2 -translate-y-1/2 p-1.5 text-sage-500 hover:text-forest-900" aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}>
                  {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                </button>
              </div>
              {fieldError(errors.owner_password?.message, 'owner_password-error')}
              <PasswordRequirements password={watch('owner_password') ?? ''} id="owner-password-req" />
            </div>
            <div className="cf-field">
              <label className="cf-label" htmlFor="owner_password_confirm">Repite la contraseña</label>
              <div className="relative">
                <input id="owner_password_confirm" type={showConfirmPassword ? 'text' : 'password'} autoComplete="new-password" className="cf-input pr-10" {...register('owner_password_confirm')} aria-invalid={!!errors.owner_password_confirm} />
                <button type="button" onClick={() => setShowConfirmPassword((v) => !v)} className="absolute right-0 top-1/2 -translate-y-1/2 p-1.5 text-sage-500 hover:text-forest-900" aria-label={showConfirmPassword ? 'Ocultar confirmación' : 'Mostrar confirmación'}>
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                </button>
              </div>
              {fieldError(errors.owner_password_confirm?.message)}
            </div>
          </>
        )}

        {currentStep === 3 && (
          <fieldset>
            <legend className="mb-4 text-[13px] text-sage-600">
              Precios mensuales en pesos, ITBIS no incluido. Puedes cambiar de plan cuando quieras desde Configuración.
            </legend>
            <div className="space-y-3">
              {PLANS.map((p) => (
                <label key={p.value} className={`block cursor-pointer rounded-lg border p-4 ${selectedPlan === p.value ? 'border-forest-900 bg-white' : 'border-forest-900/15 bg-white/60'}`}>
                  <span className="flex items-center justify-between">
                    <span className="flex items-center gap-3">
                      <input type="radio" value={p.value} {...register('subscription_plan')} className="accent-forest-900" />
                      <span className="font-display text-[16px] font-bold text-forest-900">{p.name}</span>
                    </span>
                    <span className="flex items-baseline gap-1">
                      <span className="font-mono text-[12px] text-sage-500">RD$</span>
                      <span className="font-mono text-[17px] font-medium tabular-nums text-forest-900">{p.price}</span>
                      <span className="font-mono text-[11px] text-sage-500">/mes</span>
                    </span>
                  </span>
                  <span className="mt-2 block text-[12px] text-sage-600">{p.features.join(' · ')}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {currentStep === 4 && (
          <>
            <section aria-label="Resumen" className="border-t border-forest-900/10">
              {[
                { step: 1, label: 'empresa', rows: [['Empresa', values.business_name], ['Dirección web', values.subdomain], ['Correo', values.email]] },
                { step: 2, label: 'administrador', rows: [['Administrador', `${values.owner_first_name ?? ''} ${values.owner_last_name ?? ''}`.trim()], ['Correo', values.owner_email]] },
                { step: 3, label: 'plan', rows: [['Plan', plan.name], ['Precio', `RD$ ${plan.price} /mes`]] },
              ].map((g) => (
                <div key={g.step} className="border-b border-forest-900/10 py-3">
                  {g.rows.map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-6 py-1">
                      <span className="text-[13px] text-sage-600">{k}</span>
                      <span className="text-right text-[13px] text-forest-900">{v}</span>
                    </div>
                  ))}
                  <button type="button" onClick={() => goTo(g.step)} className="mt-1 text-[12px] text-sage-600 underline underline-offset-4 hover:text-forest-900">
                    Editar {g.label}
                  </button>
                </div>
              ))}
            </section>
            <label className="flex items-start gap-2.5 text-[13px] text-sage-700">
              <input type="checkbox" className="mt-0.5 accent-forest-900" checked={acceptedTerms} onChange={(e) => setAcceptedTerms(e.target.checked)} />
              Acepto los términos y condiciones y la política de privacidad de CrediFlux.
            </label>
          </>
        )}

        <div className="flex items-center gap-3 pt-2">
          {currentStep > 1 && (
            <button type="button" onClick={previousStep} className="cf-btn cf-btn--secondary h-11">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Atrás
            </button>
          )}
          {currentStep < STEPS.length ? (
            <button type="button" onClick={nextStep} className="cf-btn cf-btn--primary h-11 flex-1">
              Continuar
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : (
            <button type="submit" className="cf-btn cf-btn--primary h-11 flex-1" disabled={isLoading || !acceptedTerms}>
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              Crear cuenta
            </button>
          )}
        </div>
      </form>
    </AuthShell>
  );
}
