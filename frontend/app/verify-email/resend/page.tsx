import { useState } from 'react';
import Link from '@/lib/navigation/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
import { esHostSinTenant } from '@/components/layout/TenantHostGuard';
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
 * En el host sin tenant (adonde redirige la confirmación de allauth, que no revela el tenant)
 * la API no le envía nada a un usuario de empresa: la página lo dice antes y después de enviar,
 * con el mismo texto para cualquier cuenta.
 */
export default function ReenviarVerificacionPage() {
  const [sinTenant] = useState(() => esHostSinTenant());
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
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="cf-surface-card w-full max-w-md">
        {/* Única región viva: anuncia el resultado del envío. Los errores van en su `Alert`
            (role="alert"), fuera de ella, para que no se anuncien dos veces. */}
        <div role="status">
          {enviado && (
            <CardHeader className="space-y-1">
              <div className="flex justify-center mb-4">
                <span className="flex h-16 w-16 items-center justify-center rounded-full border border-success-border bg-success-bg text-success-fg">
                  <MailCheck className="h-9 w-9" aria-hidden="true" />
                </span>
              </div>
              {sinTenant ? (
                <>
                  <CardTitle className="text-2xl font-bold text-center">Solicitud recibida</CardTitle>
                  <CardDescription className="text-center">
                    Si tu cuenta no es de ninguna empresa y necesita verificación, te enviamos un
                    enlace nuevo. Si es de una empresa, pídelo desde la dirección de tu empresa en
                    CrediFlux: desde aquí no te llegará.
                  </CardDescription>
                </>
              ) : (
                <>
                  <CardTitle className="text-2xl font-bold text-center">Revisa tu correo</CardTitle>
                  <CardDescription className="text-center">
                    Si tu cuenta necesita verificación, te enviamos un enlace nuevo. Revisa tu
                    bandeja de entrada y la carpeta de spam.
                  </CardDescription>
                </>
              )}
            </CardHeader>
          )}
        </div>

        {enviado ? (
          <CardFooter>
            <Button asChild variant="outline" className="w-full">
              <Link href="/login">Iniciar sesión</Link>
            </Button>
          </CardFooter>
        ) : (
          <>
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-bold text-center">
                Solicitar enlace de verificación
              </CardTitle>
              <CardDescription className="text-center">
                Escribe el correo de tu cuenta y te enviaremos un enlace nuevo para verificarlo.
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit(onSubmit)} noValidate>
              <CardContent className="space-y-4">
                {error && (
                  <Alert className="border-danger-border bg-danger-bg text-danger-fg">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">Correo electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="tu@email.com"
                    aria-invalid={errors.email ? true : undefined}
                    aria-describedby={errors.email ? 'email-error' : undefined}
                    {...register('email')}
                    disabled={isSubmitting}
                  />
                  {errors.email && (
                    <p id="email-error" className="text-sm text-danger-fg">
                      {errors.email.message}
                    </p>
                  )}
                </div>

                <p className="cf-muted-panel p-3 text-sm text-muted-foreground">
                  {sinTenant
                    ? 'Estás en la dirección general de CrediFlux. Si tu cuenta es de una empresa, pide el enlace desde la dirección de tu empresa: desde aquí no te llegará.'
                    : 'Pídelo desde la dirección de tu empresa en CrediFlux. Si no te llega en unos minutos, revisa la carpeta de spam antes de pedir otro.'}
                </p>
              </CardContent>

              <CardFooter className="flex flex-col space-y-4">
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                  Enviar enlace
                </Button>

                <Button asChild variant="outline" className="w-full">
                  <Link href="/login">
                    <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
                    Iniciar sesión
                  </Link>
                </Button>
              </CardFooter>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}
