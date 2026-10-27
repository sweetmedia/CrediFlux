import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from '@/lib/navigation';
import Link from '@/lib/navigation/link';
import { authAPI } from '@/lib/api/auth';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

type Resultado = 'verificado' | 'invalido';

/**
 * Destino del enlace de verificación de correo (`/verify-email?uid=…&token=…`), que el backend arma
 * con el dominio del tenant del usuario. Confirma una sola vez al montar.
 *
 * El token no sale de aquí salvo hacia nuestra API (mismo host): no se escribe en la consola ni se
 * cargan recursos externos. Cualquier fallo se muestra igual, sin distinguir causas, como la API.
 */
export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const uid = searchParams.get('uid') ?? '';
  const token = searchParams.get('token') ?? '';
  const completo = Boolean(uid && token);

  const [resultado, setResultado] = useState<Resultado | null>(null);
  // StrictMode ejecuta el efecto dos veces al montar: el ref recuerda qué enlace ya se confirmó.
  const intento = useRef<string | null>(null);

  useEffect(() => {
    if (!completo) return;
    const clave = `${uid}\n${token}`;
    if (intento.current === clave) return;
    intento.current = clave;
    setResultado(null);

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-[#e8eddf] p-4">
      <Card className="cf-surface-card w-full max-w-md" aria-live="polite">
        {estado === 'confirmando' && (
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary" aria-hidden="true" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">Verificando tu correo…</CardTitle>
            <CardDescription className="text-center">Esto tomará solo un momento.</CardDescription>
          </CardHeader>
        )}

        {estado === 'verificado' && (
          <>
            <CardHeader className="space-y-1">
              <div className="flex justify-center mb-4">
                <CheckCircle2 className="h-16 w-16 text-green-500" aria-hidden="true" />
              </div>
              <CardTitle className="text-2xl font-bold text-center">Correo verificado</CardTitle>
              <CardDescription className="text-center">
                Tu dirección de correo quedó verificada. Ya puedes iniciar sesión.
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button asChild className="w-full">
                <Link href="/login">Iniciar sesión</Link>
              </Button>
            </CardFooter>
          </>
        )}

        {estado === 'invalido' && (
          <>
            <CardHeader className="space-y-1">
              <div className="flex justify-center mb-4">
                <AlertCircle className="h-16 w-16 text-red-500" aria-hidden="true" />
              </div>
              <CardTitle className="text-2xl font-bold text-center">Enlace inválido o vencido</CardTitle>
              <CardDescription className="text-center">
                No pudimos verificar tu correo con este enlace. Inicia sesión y solicita un nuevo
                enlace de verificación.
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Button asChild variant="outline" className="w-full">
                <Link href="/login">Iniciar sesión</Link>
              </Button>
            </CardFooter>
          </>
        )}
      </Card>
    </div>
  );
}
