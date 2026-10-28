import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from '@/lib/navigation';
import Link from '@/lib/navigation/link';
import { authAPI } from '@/lib/api/auth';
import { AuthShell } from '@/components/auth/AuthShell';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

type Resultado = 'verificado' | 'invalido';

/**
 * Destino del enlace de verificación de correo (`/verify-email?uid=…&token=…`), que el backend arma
 * con el dominio del tenant del usuario. Confirma una sola vez al montar.
 *
 * El token no sale de aquí salvo hacia nuestra API (mismo host): se lee una vez, se quita de la
 * barra de direcciones y del historial (`replace`), no se escribe en la consola y no se cargan
 * recursos externos. Cualquier fallo se muestra igual, sin distinguir causas, como la API.
 */
export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Se capturan en el primer render: después de `replace` la URL ya no los tiene.
  const [enlace] = useState(() => ({
    uid: searchParams.get('uid') ?? '',
    token: searchParams.get('token') ?? '',
  }));
  const { uid, token } = enlace;
  const completo = Boolean(uid && token);
  const conParametros = searchParams.has('uid') || searchParams.has('token');

  const [resultado, setResultado] = useState<Resultado | null>(null);
  // StrictMode ejecuta el efecto dos veces al montar: el ref recuerda qué enlace ya se confirmó.
  const intento = useRef<string | null>(null);

  useEffect(() => {
    if (conParametros) router.replace('/verify-email');
  }, [conParametros, router]);

  useEffect(() => {
    if (!completo) return;
    const clave = `${uid}\n${token}`;
    if (intento.current === clave) return;
    intento.current = clave;

    authAPI
      .confirmEmailVerification({ uid, token })
      .then(() => {
        if (intento.current === clave) setResultado('verificado');
      })
      .catch(() => {
        if (intento.current === clave) setResultado('invalido');
      });
  }, [completo, uid, token]);

  const estado = !completo ? 'invalido' : resultado ?? 'confirmando';

  return (
    <AuthShell>
      <div className="cf-surface-card cf-auth-panel" aria-live="polite">
        {estado === 'confirmando' && (
          <>
            <Loader2 className="mb-6 h-8 w-8 animate-spin text-forest-900" aria-hidden="true" />
            <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-sage-600">Verificación</div>
            <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Verificando tu correo…</h1>
            <p className="mt-3 text-[14px] text-sage-600">Esto tomará solo un momento.</p>
          </>
        )}

        {estado === 'verificado' && (
          <>
            <CheckCircle2 className="mb-6 h-8 w-8 text-forest-500" aria-hidden="true" />
            <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-forest-700">Listo</div>
            <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Correo verificado</h1>
            <p className="mt-3 text-[14px] text-sage-600">
              Tu dirección de correo quedó verificada. Ya puedes iniciar sesión.
            </p>
            <Link href="/login" className="cf-btn cf-btn--primary mt-8 h-11 w-full">
              Iniciar sesión
            </Link>
          </>
        )}

        {estado === 'invalido' && (
          <>
            <AlertCircle className="mb-6 h-8 w-8 text-flame-600" aria-hidden="true" />
            <div className="mb-4 font-mono text-[10px] uppercase tracking-widest text-sage-600">Verificación</div>
            <h1 className="font-display text-[38px] font-black leading-none tracking-tight text-forest-900">Enlace inválido o vencido</h1>
            <p className="mt-3 text-[14px] text-sage-600">
              No pudimos verificar tu correo con este enlace. Solicita un enlace nuevo de
              verificación.
            </p>
            <Link href="/verify-email/resend" className="cf-btn cf-btn--primary mt-8 h-11 w-full">
              Solicitar un enlace nuevo
            </Link>
            <Link href="/login" className="cf-btn cf-btn--secondary mt-3 h-11 w-full">
              Iniciar sesión
            </Link>
          </>
        )}
      </div>
    </AuthShell>
  );
}
