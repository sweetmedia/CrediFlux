'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { TwoFactorVerify } from '@/components/auth';

const loginSchema = z.object({
  email: z.string().email('Email invalido'),
  password: z.string().min(1, 'Contrasena requerida'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, complete2FALogin } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [showVerified, setShowVerified] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState<string>('');
  const [twoFactorError, setTwoFactorError] = useState<string | null>(null);
  const [is2FALoading, setIs2FALoading] = useState(false);

  useEffect(() => {
    if (searchParams.get('verified') === 'true') {
      setShowVerified(true);
    }
  }, [searchParams]);

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
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-sm border-border shadow-none">
          <CardHeader className="pb-4 pt-8 px-8">
            <div className="flex justify-center">
              <Image
                src="/logo.svg"
                alt="CrediFlux"
                width={160}
                height={40}
                className="h-9 w-auto"
                priority
              />
            </div>
          </CardHeader>
          <CardContent className="px-8 pb-8">
            <TwoFactorVerify
              onVerify={handle2FAVerify}
              onCancel={handleCancel2FA}
              isLoading={is2FALoading}
              error={twoFactorError}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Logo above card */}
        <div className="flex justify-center mb-8">
          <Image
            src="/logo.svg"
            alt="CrediFlux"
            width={160}
            height={40}
            className="h-9 w-auto"
            priority
          />
        </div>

        <Card className="border-border shadow-none">
          <CardHeader className="px-7 pt-7 pb-1">
            <h2 className="text-base font-semibold text-foreground text-center">Iniciar Sesión</h2>
            <p className="text-sm text-muted-foreground text-center mt-0.5">
              Ingresa a tu cuenta para continuar
            </p>
          </CardHeader>

          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="px-7 py-5 space-y-4">
              {showVerified && (
                <Alert className="border-green-200 bg-green-50 text-green-800">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-xs">
                    Tu correo electronico ha sido verificado exitosamente. Ya puedes iniciar sesion.
                  </AlertDescription>
                </Alert>
              )}

              {error && (
                <Alert variant="destructive">
                  <AlertDescription className="text-xs">{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-sm">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="tu@email.com"
                  {...register('email')}
                  disabled={isLoading}
                  className="h-9 border-border shadow-none text-sm"
                />
                {errors.email && (
                  <p className="text-xs text-destructive">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm">Contraseña</Label>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    ¿Olvidaste tu contraseña?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...register('password')}
                  disabled={isLoading}
                  className="h-9 border-border shadow-none text-sm"
                />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-4 px-7 pb-7 pt-0">
              <Button
                type="submit"
                className="w-full h-9 bg-primary hover:bg-primary/90 text-primary-foreground shadow-none text-sm"
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                Iniciar Sesión
              </Button>

              <p className="text-xs text-center text-muted-foreground">
                ¿No tienes cuenta?{' '}
                <Link href="/register" className="text-primary hover:underline font-medium">
                  Regístrate aquí
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
