import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from '@/lib/navigation';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { usePasswordReset } from '@/hooks/usePasswordReset';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { AuthShell } from '@/components/auth/AuthShell';
import { PasswordRequirements } from '@/components/auth/PasswordRequirements';

const resetPasswordSchema = z.object({
  new_password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Las contraseñas no coinciden',
  path: ['confirm_password'],
});

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

/** Tras restablecer, segundos hasta volver al login (reset-done del canvas). */
const SEGUNDOS_A_LOGIN = 5;

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { confirmReset, isConfirming } = usePasswordReset();

  const [localError, setLocalError] = useState<string>('');
  const [passwordError, setPasswordError] = useState<string>('');
  const [uid, setUid] = useState<string>('');
  const [token, setToken] = useState<string>('');
  // Sin parámetros o con un token que la API rechaza: el enlace no sirve.
  const [invalidLink, setInvalidLink] = useState(false);
  const [done, setDone] = useState(false);
  const [restantes, setRestantes] = useState(SEGUNDOS_A_LOGIN);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  useEffect(() => {
    const uidParam = searchParams.get('uid');
    const tokenParam = searchParams.get('token');

    if (!uidParam || !tokenParam) {
      setInvalidLink(true);
    } else {
      setUid(uidParam);
      setToken(tokenParam);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!done) return;
    const id = setInterval(() => setRestantes((s) => s - 1), 1000);
    const salida = setTimeout(() => router.push('/login'), SEGUNDOS_A_LOGIN * 1000);
    return () => {
      clearInterval(id);
      clearTimeout(salida);
    };
  }, [done, router]);

  const onSubmit = async (data: ResetPasswordFormData) => {
    try {
      setLocalError('');
      setPasswordError('');
      await confirmReset({
        uid,
        token,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      });
      setDone(true);
    } catch (err: any) {
      console.error('Password reset confirmation error:', err);
      const errorData = err.response?.data;
      if (!errorData) {
        setLocalError('Error al conectar con el servidor');
      } else if (errorData.token || errorData.uid) {
        setInvalidLink(true);
      } else if (errorData.new_password) {
        setPasswordError(errorData.new_password[0]);
      } else if (errorData.detail) {
        setLocalError(errorData.detail);
      } else {
        setLocalError('Error al restablecer contraseña');
      }
    }
  };

  if (invalidLink) {
    return (
      <AuthShell
        eyebrow="Enlace vencido"
        title="Enlace inválido"
        description="El enlace de recuperación es inválido o ya venció. Pide uno nuevo: llega en unos minutos y vale 24 horas."
      >
        <Link href="/forgot-password" className="cf-btn cf-btn--primary h-11 w-full">
          Pedir un enlace nuevo
        </Link>
        <Link href="/login" className="mt-4 inline-flex text-[13px] text-sage-600 hover:text-forest-900">
          Volver a iniciar sesión
        </Link>
      </AuthShell>
    );
  }

  if (done) {
    return (
      <AuthShell
        eyebrow="Listo"
        title="Contraseña restablecida"
        description="Ya puedes entrar con tu contraseña nueva."
      >
        <div className="h-1 overflow-hidden rounded bg-forest-900/10" aria-hidden="true">
          <div
            className="h-full bg-forest-900 transition-[width] duration-1000 ease-linear"
            style={{ width: `${((SEGUNDOS_A_LOGIN - restantes) / SEGUNDOS_A_LOGIN) * 100}%` }}
          />
        </div>
        <p className="mt-3 font-mono text-[11px] tabular-nums text-sage-600">
          Te llevamos al inicio de sesión en {Math.max(restantes, 0)} s
        </p>
        <Link href="/login" className="cf-btn cf-btn--primary mt-8 h-11 w-full">
          Iniciar sesión ahora
        </Link>
      </AuthShell>
    );
  }

  const newPasswordErrorId = errors.new_password || passwordError ? 'new-password-error' : undefined;

  return (
    <AuthShell
      eyebrow="Nueva contraseña"
      title="Restablecer contraseña"
      description="Elige una contraseña nueva para tu cuenta."
    >
      {localError && (
        <div role="alert" className="mb-6 flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
          <AlertTriangle className="mt-0.5 h-[15px] w-[15px] shrink-0 text-flame-600" aria-hidden="true" />
          {localError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-7">
        <div className="cf-field">
          <label className="cf-label" htmlFor="new_password">Contraseña nueva</label>
          <input
            id="new_password"
            type="password"
            className="cf-input"
            autoComplete="new-password"
            aria-invalid={newPasswordErrorId ? true : undefined}
            aria-describedby={[newPasswordErrorId, 'new-password-req'].filter(Boolean).join(' ')}
            {...register('new_password')}
            disabled={isConfirming}
          />
          {newPasswordErrorId && (
            <p id="new-password-error" className="mt-1.5 text-[12px] text-flame-700">
              {passwordError || errors.new_password?.message}
            </p>
          )}
          <PasswordRequirements password={watch('new_password') ?? ''} id="new-password-req" />
        </div>

        <div className="cf-field">
          <label className="cf-label" htmlFor="confirm_password">Repite la contraseña</label>
          <input
            id="confirm_password"
            type="password"
            className="cf-input"
            autoComplete="new-password"
            aria-invalid={errors.confirm_password ? true : undefined}
            aria-describedby={errors.confirm_password ? 'confirm-password-error' : undefined}
            {...register('confirm_password')}
            disabled={isConfirming}
          />
          {errors.confirm_password && (
            <p id="confirm-password-error" className="mt-1.5 text-[12px] text-flame-700">
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        <button type="submit" className="cf-btn cf-btn--primary h-11 w-full" disabled={isConfirming}>
          {isConfirming && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Restablecer contraseña
        </button>
      </form>
    </AuthShell>
  );
}
