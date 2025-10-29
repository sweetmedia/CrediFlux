'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { authAPI } from '@/lib/api/auth';
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
import { Loader2, CheckCircle2 } from 'lucide-react';

const registerSchema = z.object({
  // Business Information
  business_name: z.string().min(2, 'Nombre del negocio requerido'),
  tenant_name: z.string().min(2, 'Nombre del tenant requerido'),
  tax_id: z.string().optional(),
  email: z.string().email('Email inválido'),
  phone: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  country: z.string().optional(),
  postal_code: z.string().optional(),
  subdomain: z
    .string()
    .min(3, 'El subdominio debe tener al menos 3 caracteres')
    .regex(/^[a-z0-9-]+$/, 'Solo letras minúsculas, números y guiones'),

  // Owner Information
  owner_first_name: z.string().min(2, 'Nombre requerido'),
  owner_last_name: z.string().min(2, 'Apellido requerido'),
  owner_email: z.string().email('Email inválido'),
  owner_password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  owner_password_confirm: z.string(),
  owner_phone: z.string().optional(),

  // Subscription Plan
  subscription_plan: z.enum(['basic', 'professional', 'enterprise']),
}).refine((data) => data.owner_password === data.owner_password_confirm, {
  message: 'Las contraseñas no coinciden',
  path: ['owner_password_confirm'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      subscription_plan: 'basic',
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setIsLoading(true);
      setError('');

      // Remove the password confirmation field before sending
      const { owner_password_confirm, ...registrationData } = data;

      await authAPI.registerTenant(registrationData);

      setSuccess(true);

      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } catch (err: any) {
      console.error('Registration error:', err);

      if (err.response?.data) {
        const errorData = err.response.data;
        // Handle various error formats from the API
        if (errorData.detail) {
          setError(errorData.detail);
        } else if (errorData.subdomain) {
          setError(`Subdominio: ${errorData.subdomain[0]}`);
        } else if (errorData.owner_email) {
          setError(`Email: ${errorData.owner_email[0]}`);
        } else if (errorData.email) {
          setError(`Email del negocio: ${errorData.email[0]}`);
        } else {
          setError('Error al registrar. Por favor verifica los datos.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="h-16 w-16 text-green-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              ¡Registro Exitoso!
            </CardTitle>
            <CardDescription className="text-center">
              Tu cuenta ha sido creada exitosamente. Serás redirigido al login en unos segundos...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4 py-8">
      <Card className="w-full max-w-4xl">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Registrar Nuevo Negocio
          </CardTitle>
          <CardDescription className="text-center">
            Crea tu cuenta de CrediFlux y comienza a gestionar tus préstamos
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Business Information Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold border-b pb-2">
                Información del Negocio
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="business_name">
                    Nombre del Negocio <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="business_name"
                    placeholder="Mi Empresa S.A."
                    {...register('business_name')}
                    disabled={isLoading}
                  />
                  {errors.business_name && (
                    <p className="text-sm text-red-500">{errors.business_name.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tenant_name">
                    Nombre Corto <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="tenant_name"
                    placeholder="Mi Empresa"
                    {...register('tenant_name')}
                    disabled={isLoading}
                  />
                  {errors.tenant_name && (
                    <p className="text-sm text-red-500">{errors.tenant_name.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="subdomain">
                    Subdominio <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="subdomain"
                      placeholder="mi-empresa"
                      {...register('subdomain')}
                      disabled={isLoading}
                    />
                    <span className="text-sm text-gray-500 whitespace-nowrap">
                      .crediflux.com
                    </span>
                  </div>
                  {errors.subdomain && (
                    <p className="text-sm text-red-500">{errors.subdomain.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email del Negocio <span className="text-red-500">*</span></Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="contacto@empresa.com"
                    {...register('email')}
                    disabled={isLoading}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-500">{errors.email.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono</Label>
                  <Input
                    id="phone"
                    placeholder="+1234567890"
                    {...register('phone')}
                    disabled={isLoading}
                  />
                  {errors.phone && (
                    <p className="text-sm text-red-500">{errors.phone.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="tax_id">RNC/Tax ID</Label>
                  <Input
                    id="tax_id"
                    placeholder="000-0000000-0"
                    {...register('tax_id')}
                    disabled={isLoading}
                  />
                  {errors.tax_id && (
                    <p className="text-sm text-red-500">{errors.tax_id.message}</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">Dirección</Label>
                <Input
                  id="address"
                  placeholder="Calle Principal #123"
                  {...register('address')}
                  disabled={isLoading}
                />
                {errors.address && (
                  <p className="text-sm text-red-500">{errors.address.message}</p>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">Ciudad</Label>
                  <Input
                    id="city"
                    placeholder="Santo Domingo"
                    {...register('city')}
                    disabled={isLoading}
                  />
                  {errors.city && (
                    <p className="text-sm text-red-500">{errors.city.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="state">Provincia/Estado</Label>
                  <Input
                    id="state"
                    placeholder="Distrito Nacional"
                    {...register('state')}
                    disabled={isLoading}
                  />
                  {errors.state && (
                    <p className="text-sm text-red-500">{errors.state.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="postal_code">Código Postal</Label>
                  <Input
                    id="postal_code"
                    placeholder="10100"
                    {...register('postal_code')}
                    disabled={isLoading}
                  />
                  {errors.postal_code && (
                    <p className="text-sm text-red-500">{errors.postal_code.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Owner Information Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold border-b pb-2">
                Información del Administrador
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="owner_first_name">
                    Nombre <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="owner_first_name"
                    placeholder="Juan"
                    {...register('owner_first_name')}
                    disabled={isLoading}
                  />
                  {errors.owner_first_name && (
                    <p className="text-sm text-red-500">{errors.owner_first_name.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_last_name">
                    Apellido <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="owner_last_name"
                    placeholder="Pérez"
                    {...register('owner_last_name')}
                    disabled={isLoading}
                  />
                  {errors.owner_last_name && (
                    <p className="text-sm text-red-500">{errors.owner_last_name.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_email">
                    Email <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="owner_email"
                    type="email"
                    placeholder="juan@empresa.com"
                    {...register('owner_email')}
                    disabled={isLoading}
                  />
                  {errors.owner_email && (
                    <p className="text-sm text-red-500">{errors.owner_email.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_phone">Teléfono</Label>
                  <Input
                    id="owner_phone"
                    placeholder="+1234567890"
                    {...register('owner_phone')}
                    disabled={isLoading}
                  />
                  {errors.owner_phone && (
                    <p className="text-sm text-red-500">{errors.owner_phone.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_password">
                    Contraseña <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="owner_password"
                    type="password"
                    placeholder="••••••••"
                    {...register('owner_password')}
                    disabled={isLoading}
                  />
                  {errors.owner_password && (
                    <p className="text-sm text-red-500">{errors.owner_password.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="owner_password_confirm">
                    Confirmar Contraseña <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="owner_password_confirm"
                    type="password"
                    placeholder="••••••••"
                    {...register('owner_password_confirm')}
                    disabled={isLoading}
                  />
                  {errors.owner_password_confirm && (
                    <p className="text-sm text-red-500">
                      {errors.owner_password_confirm.message}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Subscription Plan Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold border-b pb-2">Plan de Suscripción</h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <label
                  className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer hover:border-blue-500 transition-colors ${
                    errors.subscription_plan ? 'border-red-500' : 'border-gray-200'
                  }`}
                >
                  <input
                    type="radio"
                    value="basic"
                    {...register('subscription_plan')}
                    disabled={isLoading}
                    className="sr-only"
                  />
                  <span className="font-semibold text-lg">Básico</span>
                  <span className="text-2xl font-bold my-2">Gratis</span>
                  <span className="text-sm text-gray-600">Hasta 50 préstamos</span>
                </label>

                <label
                  className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer hover:border-blue-500 transition-colors ${
                    errors.subscription_plan ? 'border-red-500' : 'border-gray-200'
                  }`}
                >
                  <input
                    type="radio"
                    value="professional"
                    {...register('subscription_plan')}
                    disabled={isLoading}
                    className="sr-only"
                  />
                  <span className="font-semibold text-lg">Professional</span>
                  <span className="text-2xl font-bold my-2">$49/mes</span>
                  <span className="text-sm text-gray-600">Hasta 500 préstamos</span>
                </label>

                <label
                  className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer hover:border-blue-500 transition-colors ${
                    errors.subscription_plan ? 'border-red-500' : 'border-gray-200'
                  }`}
                >
                  <input
                    type="radio"
                    value="enterprise"
                    {...register('subscription_plan')}
                    disabled={isLoading}
                    className="sr-only"
                  />
                  <span className="font-semibold text-lg">Enterprise</span>
                  <span className="text-2xl font-bold my-2">$199/mes</span>
                  <span className="text-sm text-gray-600">Préstamos ilimitados</span>
                </label>
              </div>
              {errors.subscription_plan && (
                <p className="text-sm text-red-500">{errors.subscription_plan.message}</p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Crear Cuenta
            </Button>

            <div className="text-sm text-center text-gray-600">
              ¿Ya tienes cuenta?{' '}
              <Link href="/login" className="text-blue-600 hover:underline font-medium">
                Inicia sesión aquí
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
