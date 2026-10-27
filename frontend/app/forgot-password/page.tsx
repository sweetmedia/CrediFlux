import { useState } from 'react';
import Link from '@/lib/navigation/link';
import Image from '@/components/ui/image';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { usePasswordReset } from '@/hooks/usePasswordReset';
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
import { Loader2, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';

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
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-[#e8eddf] p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="h-16 w-16 text-green-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              Email Enviado
            </CardTitle>
            <CardDescription className="text-center">
              Hemos enviado un email con instrucciones para recuperar tu contraseña.
              Por favor revisa tu bandeja de entrada y sigue los pasos indicados.
            </CardDescription>
          </CardHeader>
          <CardFooter className="flex justify-center">
            <Link href="/login">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver al Login
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-[#e8eddf] p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-4">
          <div className="flex justify-center">
            <Image
              src="/logo.svg"
              alt="CrediFlux"
              width={200}
              height={50}
              className="h-12 w-auto"
              priority
            />
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            Recuperar Contraseña
          </CardTitle>
          <CardDescription className="text-center">
            Ingresa tu email y te enviaremos instrucciones para restablecer tu contraseña
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <CardContent className="space-y-4">
            {localError && (
              <Alert variant="destructive">
                <AlertDescription>{localError}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="tu@email.com"
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? 'email-error' : undefined}
                {...register('email')}
                disabled={isRequesting}
              />
              {errors.email && (
                <p id="email-error" className="text-sm text-red-500">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded-md">
              <p>
                Recibirás un email con un enlace para restablecer tu contraseña.
                El enlace será válido por 24 horas.
              </p>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isRequesting}>
              {isRequesting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Enviar Instrucciones
            </Button>

            <Link href="/login" className="w-full">
              <Button variant="outline" className="w-full">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver al Login
              </Button>
            </Link>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
