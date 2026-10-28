import { useState } from 'react';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
import { esHostGeneral } from '@/lib/hosts';
import { AuthShell } from '@/components/auth/AuthShell';
import { ArrowLeft, Loader2, MailCheck } from 'lucide-react';

const reenvioSchema = z.object({
  email: z.string().email('Correo inválido'),
});

type ReenvioFormData = z.infer<typeof reenvioSchema>;

const ERROR_LIMITE = 'Demasiados intentos. Prueba de nuevo más tarde.';
const ERROR_GENERICO = 'No pudimos enviar la solicitud. Prueba de nuevo en unos minutos.';

/**
 * Pide un enlace nuevo de verificación de correo (`/verify-email/resend`).
 *
 * La API (`verify-email/send`) responde siempre lo mismo y sólo envía desde el host del tenant
 * del usuario, así que aquí tampoco se distingue nada: cualquier 200 da el mismo mensaje, sin
 * decir si la cuenta existe o ya está verificada. Un 429 da un aviso genérico de límite y
 * cualquier otro fallo, uno genérico; nunca se muestra el texto de la API.
 *
 * En el host general (`esHostGeneral`: el de dev o el de `VITE_APP_URL`, adonde redirige la
 * confirmación de allauth, que no revela el tenant) la API no le envía nada a un usuario de
 * empresa: la página lo dice antes y después de enviar, con el mismo texto para cualquier cuenta.
 */
export default function ReenviarVerificacionPage() {
  const [hostGeneral] = useState(() => esHostGeneral());
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ReenvioFormData>({
    resolver: zodResolver(reenvioSchema),
  });

  const onSubmit = async (data: ReenvioFormData) => {
    setError('');
    try {
      await authAPI.sendEmailVerification({ email: data.email });
      setEnviado(true);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(status === 429 ? ERROR_LIMITE : ERROR_GENERICO);
    }
  };

  return (
    <AuthShell>
      <div className="cf-surface-card cf-auth-panel">
        {/* Única región viva: anuncia el resultado del envío. Los errores van en su alerta
            (role="alert"), fuera de ella, para que no se anuncien dos veces. */}
        <div role="status">
          {enviado && (
            <>
              <MailCheck className="mb-6 h-8 w-8 text-forest-500" aria-hidden="true" />
              <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-forest-700">Enlace pedido</div>
              {hostGeneral ? (
                <>
                  <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Solicitud recibida</h1>
                  <p className="mt-3 text-[14px] leading-relaxed text-sage-600">
                    Si tu cuenta no es de ninguna empresa y necesita verificación, te enviamos un
                    enlace nuevo. Si es de una empresa, pídelo desde la dirección de tu empresa en
                    CrediFlux: desde aquí no te llegará.
                  </p>
                </>
              ) : (
                <>
                  <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Revisa tu correo</h1>
                  <p className="mt-3 text-[14px] leading-relaxed text-sage-600">
                    Si tu cuenta necesita verificación, te enviamos un enlace nuevo. Revisa tu
                    bandeja de entrada y la carpeta de spam.
                  </p>
                </>
              )}
            </>
          )}
        </div>

        {enviado ? (
          <Link href="/login" className="cf-btn cf-btn--secondary mt-8 h-11 w-full">
            Iniciar sesión
          </Link>
        ) : (
          <>
            <Link href="/login" className="mb-6 inline-flex items-center gap-1.5 text-[13px] text-sage-600 hover:text-forest-900">
              <ArrowLeft className="h-3 w-3" aria-hidden="true" />
              Iniciar sesión
            </Link>
            <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-sage-600">Verificación</div>
            <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">
              Solicitar enlace de verificación
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-sage-600">
              Escribe el correo de tu cuenta y te enviaremos un enlace nuevo para verificarlo.
            </p>

            {hostGeneral && (
              <p role="note" className="mt-6 rounded border border-sun-500/40 bg-sun-100 p-3 text-[13px] text-forest-900">
                Estás en la dirección general de CrediFlux. Si tu cuenta es de una empresa, pide el enlace desde la dirección de tu empresa: desde aquí no te llegará.
              </p>
            )}

            <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-8 space-y-7">
              {error && (
                <div role="alert" className="flex gap-2.5 rounded border border-flame-500/30 bg-flame-100 p-3 text-[13px] text-forest-900">
                  {error}
                </div>
              )}

              <div className="cf-field">
                <label className="cf-label" htmlFor="email">Correo electrónico</label>
                <input
                  id="email"
                  type="email"
                  className="cf-input"
                  autoComplete="email"
                  placeholder="ej: maria@financiera.com.do"
                  aria-invalid={errors.email ? true : undefined}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  {...register('email')}
                  disabled={isSubmitting}
                />
                {errors.email && (
                  <p id="email-error" className="mt-1.5 text-[12px] text-flame-700">
                    {errors.email.message}
                  </p>
                )}
              </div>

              <button type="submit" className="cf-btn cf-btn--primary h-11 w-full" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                Enviar enlace
              </button>
            </form>

            {!hostGeneral && (
              <p className="mt-8 border-t border-forest-900/10 pt-6 text-[12px] leading-relaxed text-sage-600">
                Pídelo desde la dirección de tu empresa en CrediFlux. Si no te llega en unos minutos, revisa la carpeta de spam antes de pedir otro.
              </p>
            )}
          </>
        )}
      </div>
    </AuthShell>
  );
}
