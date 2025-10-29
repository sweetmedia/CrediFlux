'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
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
import { Loader2, Lock, CheckCircle2, AlertCircle } from 'lucide-react';

const resetPasswordSchema = z.object({
  new_password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Las contraseñas no coinciden',
  path: ['confirm_password'],
});

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { confirmReset, isConfirming, confirmError, confirmSuccess } = usePasswordReset();

  const [localError, setLocalError] = useState<string>('');
  const [uid, setUid] = useState<string>('');
  const [token, setToken] = useState<string>('');
  const [missingParams, setMissingParams] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  useEffect(() => {
    // Get uid and token from URL parameters
    const uidParam = searchParams.get('uid');
    const tokenParam = searchParams.get('token');

    if (!uidParam || !tokenParam) {
      setMissingParams(true);
      setLocalError('Enlace de recuperación inválido o expirado');
    } else {
      setUid(uidParam);
      setToken(tokenParam);
    }
  }, [searchParams]);

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!uid || !token) {
      setLocalError('Parámetros de recuperación no válidos');
      return;
    }

    try {
      setLocalError('');
      await confirmReset({
        uid,
        token,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      });

      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } catch (err: any) {
      console.error('Password reset confirmation error:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.detail) {
          setLocalError(errorData.detail);
        } else if (errorData.token) {
          setLocalError('El enlace de recuperación es inválido o ha expirado');
        } else if (errorData.new_password) {
          setLocalError(errorData.new_password[0]);
        } else {
          setLocalError('Error al restablecer contraseña');
        }
      } else {
        setLocalError('Error al conectar con el servidor');
      }
    }
  };

  if (missingParams) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <AlertCircle className="h-16 w-16 text-red-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              Enlace Inválido
            </CardTitle>
            <CardDescription className="text-center">
              El enlace de recuperación es inválido o ha expirado.
              Por favor solicita un nuevo enlace de recuperación.
            </CardDescription>
          </CardHeader>
          <CardFooter className="flex flex-col space-y-2">
            <Link href="/forgot-password" className="w-full">
              <Button className="w-full">
                Solicitar Nuevo Enlace
              </Button>
            </Link>
            <Link href="/login" className="w-full">
              <Button variant="outline" className="w-full">
                Volver al Login
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (confirmSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="h-16 w-16 text-green-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              ¡Contraseña Restablecida!
            </CardTitle>
            <CardDescription className="text-center">
              Tu contraseña ha sido restablecida exitosamente.
              Serás redirigido al login en unos segundos...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex justify-center mb-4">
            <Lock className="h-12 w-12 text-blue-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-center">
            Nueva Contraseña
          </CardTitle>
          <CardDescription className="text-center">
            Ingresa tu nueva contraseña
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            {(localError || confirmError) && (
              <Alert variant="destructive">
                <AlertDescription>{localError || confirmError?.message}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="new_password">
                Nueva Contraseña <span className="text-red-500">*</span>
              </Label>
              <Input
                id="new_password"
                type="password"
                placeholder="••••••••"
                {...register('new_password')}
                disabled={isConfirming}
              />
              {errors.new_password && (
                <p className="text-sm text-red-500">{errors.new_password.message}</p>
              )}
              <p className="text-xs text-gray-500">
                Mínimo 8 caracteres
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">
                Confirmar Contraseña <span className="text-red-500">*</span>
              </Label>
              <Input
                id="confirm_password"
                type="password"
                placeholder="••••••••"
                {...register('confirm_password')}
                disabled={isConfirming}
              />
              {errors.confirm_password && (
                <p className="text-sm text-red-500">{errors.confirm_password.message}</p>
              )}
            </div>

            <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded-md">
              <p className="font-medium mb-1">Tu contraseña debe:</p>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>Tener al menos 8 caracteres</li>
                <li>Incluir letras mayúsculas y minúsculas</li>
                <li>Incluir al menos un número</li>
                <li>Incluir al menos un carácter especial</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isConfirming}>
              {isConfirming && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Restablecer Contraseña
            </Button>

            <div className="text-sm text-center text-gray-600">
              ¿Recordaste tu contraseña?{' '}
              <Link href="/login" className="text-blue-600 hover:underline font-medium">
                Volver al login
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
