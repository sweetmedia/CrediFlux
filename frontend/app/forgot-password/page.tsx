import { useState } from 'react';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { usePasswordReset } from '@/hooks/usePasswordReset';
import { AlertTriangle, ChevronLeft, Loader2 } from 'lucide-react';
import { AuthShell } from '@/components/auth/AuthShell';

const forgotPasswordSchema = z.object({
  email: z.string().email('Email inválido'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const { requestReset, isRequesting, requestSuccess } = usePasswordReset();
  const [localError, setLocalError] = useState<string>('');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    try {
      setLocalError('');
      await requestReset(data);
    } catch (err: unknown) {
      // Nunca el texto de la API (como /verify-email/resend): un 429 da el aviso de límite y
      // cualquier otro fallo, uno genérico. El formato del correo ya lo valida zod.
      const status = (err as { response?: { status?: number } })?.response?.status;
      setLocalError(
        status === 429
          ? 'Demasiados intentos. Prueba de nuevo más tarde.'
          : 'No pudimos enviar la solicitud. Prueba de nuevo en unos minutos.'
      );
    }
  };

  if (requestSuccess) {
    return (
      <AuthShell eyebrow="Email enviado" title="Revisa tu correo">
        <p className="text-[14px] leading-relaxed text-sage-600">
          Hemos enviado un email con instrucciones para recuperar tu contraseña. Revisa tu bandeja de entrada y sigue
          los pasos indicados.
        </p>
        <dl className="mt-8 border-t border-forest-900/10">
          <div className="flex items-baseline justify-between border-b border-forest-900/10 py-3">
            <dt className="text-[13px] text-sage-600">Enlace válido por</dt>
            <dd className="font-mono text-[13px] tabular-nums text-forest-900">24 h</dd>
          </div>
          <div className="flex items-baseline justify-between gap-4 border-b border-forest-900/10 py-3">
            <dt className="text-[13px] text-sage-600">¿No llegó?</dt>
            <dd className="text-right text-[13px] text-forest-900">Revisa spam y vuelve a pedirlo en unos minutos</dd>
          </div>
        </dl>
        <Link href="/login" className="cf-btn cf-btn--primary mt-8 h-11 w-full">
          Volver a iniciar sesión
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Acceso"
      title="Recuperar contraseña"
      description="Escribe el correo de tu cuenta y te enviaremos instrucciones para restablecer la contraseña."
    >
      <Link href="/login" className="-mt-2 mb-6 inline-flex items-center gap-1.5 text-[13px] text-sage-600 hover:text-forest-900">
        <ChevronLeft className="h-3 w-3" aria-hidden="true" />
        Iniciar sesión
      </Link>

      {localError && (
        <div role="alert" className="mb-6 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertTriangle className="mt-0.5 h-[15px] w-[15px] shrink-0 text-flame-600" aria-hidden="true" />
          {localError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-7">
        <div className="cf-field">
          <label className="cf-label" htmlFor="email">
            Correo<span className="sr-only"> (email)</span>
          </label>
          <input
            id="email"
            type="email"
            className="cf-input"
            placeholder="ej: maria@financiera.com.do"
            autoComplete="username"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? 'email-error' : undefined}
            {...register('email')}
            disabled={isRequesting}
          />
          {errors.email && (
            <p id="email-error" className="mt-1.5 text-[12px] text-flame-700">
              {errors.email.message}
            </p>
          )}
        </div>
        <button type="submit" className="cf-btn cf-btn--primary h-11 w-full" disabled={isRequesting}>
          {isRequesting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Enviar instrucciones
        </button>
      </form>

      <div className="mt-8 border-t border-forest-900/10 pt-6 text-[12px] leading-relaxed text-sage-600">
        El enlace vale <span className="font-mono tabular-nums text-forest-900">24</span> horas. Si no te llega en unos
        minutos, revisa la carpeta de spam.
      </div>
    </AuthShell>
  );
}
