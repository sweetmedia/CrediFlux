import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from '@/lib/navigation';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Loader2, CheckCircle2, AlertCircle, AlertTriangle, Eye, EyeOff, Shield } from 'lucide-react';
import { TwoFactorVerify } from '@/components/auth';
import { AuthShell } from '@/components/auth/AuthShell';
import { toast } from 'sonner';
import { consumeSessionEndNotice } from '@/lib/api/session';
import { esHostGeneral } from '@/lib/hosts';

const loginSchema = z.object({
  email: z.string().email('Correo inválido'),
  password: z.string().min(1, 'Escribe tu contraseña'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, complete2FALogin } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [showVerified, setShowVerified] = useState(false);
  const [showVerifyInvalid, setShowVerifyInvalid] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState<string>('');
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);
  const [is2FALoading, setIs2FALoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    // Redirección de la confirmación de correo de allauth (un solo `verified`).
    const verified = searchParams.get('verified');
    if (verified === 'true') {
      setShowVerified(true);
    } else if (verified === 'invalid') {
      setShowVerifyInvalid(true);
    }
  }, [searchParams]);

  // Aviso dejado por el cliente HTTP al cerrar una sesión revocada.
  useEffect(() => {
    const notice = consumeSessionEndNotice();
    if (notice) toast.info(notice, { id: 'session-end-notice' });
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      setIsLoading(true);
      setError('');
      const response = await login(data);
      if ('requires_2fa' in response && response.requires_2fa) {
        setRequires2FA(true);
        setTempToken(response.temp_token);
        return;
      }
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Login error:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.non_field_errors) {
          setError(errorData.non_field_errors[0]);
        } else if (errorData.detail) {
          setError(errorData.detail);
        } else {
          setError('Credenciales invalidas');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handle2FAVerify = async (code: string, isBackupCode: boolean) => {
    try {
      setIs2FALoading(true);
      setTwoFactorError(null);
      await complete2FALogin(code, tempToken, isBackupCode);
      router.push('/dashboard');
    } catch (err: any) {
      console.error('2FA verification error:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.code) {
          setTwoFactorError(errorData.code[0] || 'Codigo invalido');
        } else if (errorData.backup_code) {
          setTwoFactorError(errorData.backup_code[0] || 'Codigo de respaldo invalido');
        } else if (errorData.detail) {
          setTwoFactorError(errorData.detail);
        } else if (errorData.error) {
          setTwoFactorError(errorData.error);
        } else {
          setTwoFactorError('Codigo incorrecto. Por favor intenta de nuevo.');
        }
      } else {
        setTwoFactorError('Error al verificar el codigo');
      }
    } finally {
      setIs2FALoading(false);
    }
  };

  const handleCancel2FA = () => {
    setRequires2FA(false);
    setTempToken('');
    setTwoFactorError(null);
  };

  if (requires2FA) {
    return (
      <AuthShell>
        <TwoFactorVerify
          onVerify={handle2FAVerify}
          onCancel={handleCancel2FA}
          isLoading={is2FALoading}
          error={twoFactorError}
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Acceso"
      title="Iniciar sesión"
      description="Entra con el correo que te asignó el administrador de tu financiera."
      topRight={
        <>
          <span className="hidden sm:inline">¿Tu financiera aún no usa CrediFlux?</span>
          <Link href="/register" className="font-medium text-forest-900 underline decoration-forest-900/25 underline-offset-4 hover:decoration-forest-900">
            Crear cuenta
          </Link>
        </>
      }
    >
      {showVerified && (
        <div role="status" className="mb-6 flex gap-2.5 rounded border border-forest-500/30 bg-forest-50 p-3 text-[13px] text-forest-900">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-forest-500" aria-hidden="true" />
          Tu correo electronico ha sido verificado exitosamente. Ya puedes iniciar sesion.
        </div>
      )}

      {showVerifyInvalid && (
        <div className="mb-6 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-flame-600" aria-hidden="true" />
          <div>
            No pudimos verificar tu correo con ese enlace: es inválido o ya venció.{' '}
            {/* Host general (`esHostGeneral`, adonde redirige allauth sin revelar el
                tenant): desde aquí la API no le envía nada a un usuario de empresa.
                Mismo texto para todos. */}
            {esHostGeneral() &&
              'Si tu cuenta es de una empresa, pide un enlace nuevo desde la dirección de tu empresa en CrediFlux: desde aquí no te llegará. '}
            <Link href="/verify-email/resend" className="font-medium underline">
              Solicitar un enlace nuevo
            </Link>
          </div>
        </div>
      )}

      {error && (
        <div role="alert" className="mb-6 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertTriangle className="mt-0.5 h-[15px] w-[15px] shrink-0 text-flame-600" aria-hidden="true" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-7" noValidate>
        <div className="cf-field">
          <label className="cf-label" htmlFor="email">Correo</label>
          <input
            id="email"
            type="email"
            className="cf-input"
            placeholder="ej: maria@financiera.com.do"
            autoComplete="username"
            {...register('email')}
            disabled={isLoading}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
          />
          {errors.email && <p id="email-error" className="mt-1.5 text-[12px] text-flame-700">{errors.email.message}</p>}
        </div>

        <div className="cf-field">
          <div className="flex items-baseline justify-between">
            <label className="cf-label" htmlFor="password">Contraseña</label>
            <Link href="/forgot-password" className="text-[12px] text-sage-600 transition-colors hover:text-forest-900">
              ¿La olvidaste?
            </Link>
          </div>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className="cf-input pr-10"
              placeholder="••••••••"
              autoComplete="current-password"
              {...register('password')}
              disabled={isLoading}
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-0 top-1/2 -translate-y-1/2 p-1.5 text-sage-500 hover:text-forest-900"
              aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            >
              {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            </button>
          </div>
          {errors.password && <p id="password-error" className="mt-1.5 text-[12px] text-flame-700">{errors.password.message}</p>}
        </div>

        <button type="submit" className="cf-btn cf-btn--primary h-11 w-full" disabled={isLoading}>
          {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
          Entrar
        </button>
      </form>

      <div className="mt-8 flex items-start gap-3 border-t border-forest-900/10 pt-6 text-[12px] leading-relaxed text-sage-600">
        <Shield className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>Cada inicio de sesión queda en la bitácora de auditoría con fecha, IP y equipo.</span>
      </div>
    </AuthShell>
  );
}
