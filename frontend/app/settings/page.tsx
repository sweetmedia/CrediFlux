'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { tenantsAPI, Tenant, TenantUpdateData } from '@/lib/api/tenants';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Save,
  Settings as SettingsIcon,
  Building2,
  Mail,
  Phone,
  MapPin,
  Palette,
  ArrowLeft,
  CheckCircle2
} from 'lucide-react';

const tenantSettingsSchema = z.object({
  business_name: z.string().min(2, 'Nombre del negocio debe tener al menos 2 caracteres'),
  tax_id: z.string().optional(),
  email: z.string().email('Email inválido'),
  phone: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  country: z.string().optional(),
  postal_code: z.string().optional(),
  primary_color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Color debe ser formato hexadecimal (ej: #6366f1)').optional(),
});

type TenantSettingsFormData = z.infer<typeof tenantSettingsSchema>;

export default function TenantSettingsPage() {
  const router = useRouter();
  const { user, tenant: authTenant, isAuthenticated, isLoading: authLoading } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<TenantSettingsFormData>({
    resolver: zodResolver(tenantSettingsSchema),
  });

  // Load tenant settings
  useEffect(() => {
    if (isAuthenticated) {
      loadTenantSettings();
    }
  }, [isAuthenticated]);

  const loadTenantSettings = async () => {
    try {
      setIsLoading(true);
      setError('');

      const data = await tenantsAPI.getSettings();
      setTenant(data);

      // Populate form
      setValue('business_name', data.business_name);
      setValue('tax_id', data.tax_id || '');
      setValue('email', data.email);
      setValue('phone', data.phone || '');
      setValue('address', data.address || '');
      setValue('city', data.city || '');
      setValue('state', data.state || '');
      setValue('country', data.country || '');
      setValue('postal_code', data.postal_code || '');
      setValue('primary_color', data.primary_color || '#6366f1');
    } catch (err: any) {
      console.error('Error loading tenant settings:', err);
      setError('Error al cargar la configuración del tenant');
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (data: TenantSettingsFormData) => {
    try {
      setIsSaving(true);
      setError('');
      setSuccessMessage('');

      const updateData: TenantUpdateData = {
        business_name: data.business_name,
        tax_id: data.tax_id || undefined,
        email: data.email,
        phone: data.phone || undefined,
        address: data.address || undefined,
        city: data.city || undefined,
        state: data.state || undefined,
        country: data.country || undefined,
        postal_code: data.postal_code || undefined,
        primary_color: data.primary_color || undefined,
      };

      const response = await tenantsAPI.updateSettings(updateData);
      setTenant(response.tenant);
      setSuccessMessage('Configuración actualizada exitosamente');

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err: any) {
      console.error('Error updating tenant settings:', err);

      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.error) {
          setError(errorData.error);
        } else if (errorData.email) {
          setError(`Email: ${errorData.email[0]}`);
        } else if (errorData.business_name) {
          setError(`Nombre del negocio: ${errorData.business_name[0]}`);
        } else {
          setError('Error al actualizar la configuración');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsSaving(false);
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  // Check if user has permission
  if (user && !user.is_tenant_owner && user.role !== 'admin') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
        <div className="container mx-auto max-w-4xl">
          <Alert variant="destructive">
            <AlertDescription>
              No tienes permiso para acceder a la configuración del tenant. Solo el propietario o administradores pueden modificar estos ajustes.
            </AlertDescription>
          </Alert>
          <div className="mt-4">
            <Link href="/dashboard">
              <Button variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Volver al Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <SettingsIcon className="h-8 w-8 text-blue-600" />
              Configuración del Tenant
            </h1>
            <p className="text-gray-600 mt-1">
              Administra la información y configuración de tu organización
            </p>
          </div>
          <Link href="/dashboard">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Button>
          </Link>
        </div>

        {/* Success Message */}
        {successMessage && (
          <Alert className="mb-6 bg-green-50 border-green-200">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              {successMessage}
            </AlertDescription>
          </Alert>
        )}

        {/* Error Message */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando configuración...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-6">
              {/* Business Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    Información del Negocio
                  </CardTitle>
                  <CardDescription>
                    Información básica de tu organización
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="business_name">
                        Nombre del Negocio <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="business_name"
                        {...register('business_name')}
                        disabled={isSaving}
                      />
                      {errors.business_name && (
                        <p className="text-sm text-red-500">{errors.business_name.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="tax_id">RIF / Tax ID</Label>
                      <Input
                        id="tax_id"
                        placeholder="J-12345678-9"
                        {...register('tax_id')}
                        disabled={isSaving}
                      />
                      {errors.tax_id && (
                        <p className="text-sm text-red-500">{errors.tax_id.message}</p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">
                      Email <span className="text-red-500">*</span>
                    </Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="email"
                        type="email"
                        className="pl-10"
                        {...register('email')}
                        disabled={isSaving}
                      />
                    </div>
                    {errors.email && (
                      <p className="text-sm text-red-500">{errors.email.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">Teléfono</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="phone"
                        type="tel"
                        placeholder="+58 212 1234567"
                        className="pl-10"
                        {...register('phone')}
                        disabled={isSaving}
                      />
                    </div>
                    {errors.phone && (
                      <p className="text-sm text-red-500">{errors.phone.message}</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Address Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-blue-600" />
                    Dirección
                  </CardTitle>
                  <CardDescription>
                    Ubicación física de tu organización
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="address">Dirección</Label>
                    <Input
                      id="address"
                      placeholder="Av. Principal, Edificio X, Piso Y"
                      {...register('address')}
                      disabled={isSaving}
                    />
                    {errors.address && (
                      <p className="text-sm text-red-500">{errors.address.message}</p>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="city">Ciudad</Label>
                      <Input
                        id="city"
                        placeholder="Caracas"
                        {...register('city')}
                        disabled={isSaving}
                      />
                      {errors.city && (
                        <p className="text-sm text-red-500">{errors.city.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="state">Estado / Provincia</Label>
                      <Input
                        id="state"
                        placeholder="Distrito Capital"
                        {...register('state')}
                        disabled={isSaving}
                      />
                      {errors.state && (
                        <p className="text-sm text-red-500">{errors.state.message}</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="country">País</Label>
                      <Input
                        id="country"
                        placeholder="Venezuela"
                        {...register('country')}
                        disabled={isSaving}
                      />
                      {errors.country && (
                        <p className="text-sm text-red-500">{errors.country.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="postal_code">Código Postal</Label>
                      <Input
                        id="postal_code"
                        placeholder="1010"
                        {...register('postal_code')}
                        disabled={isSaving}
                      />
                      {errors.postal_code && (
                        <p className="text-sm text-red-500">{errors.postal_code.message}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Branding */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Palette className="h-5 w-5 text-blue-600" />
                    Personalización
                  </CardTitle>
                  <CardDescription>
                    Personaliza la apariencia de tu tenant
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="primary_color">Color Principal</Label>
                    <div className="flex gap-3 items-center">
                      <Input
                        id="primary_color"
                        type="color"
                        className="w-20 h-10 cursor-pointer"
                        {...register('primary_color')}
                        disabled={isSaving}
                      />
                      <Input
                        type="text"
                        placeholder="#6366f1"
                        className="flex-1"
                        {...register('primary_color')}
                        disabled={isSaving}
                      />
                    </div>
                    {errors.primary_color && (
                      <p className="text-sm text-red-500">{errors.primary_color.message}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      Formato hexadecimal (ej: #6366f1)
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Subscription Info (Read-only) */}
              {tenant && (
                <Card>
                  <CardHeader>
                    <CardTitle>Información de Suscripción</CardTitle>
                    <CardDescription>
                      Detalles de tu plan actual (solo lectura)
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Label className="text-sm text-gray-600">Plan</Label>
                        <p className="text-lg font-semibold capitalize">{tenant.subscription_plan}</p>
                      </div>
                      <div>
                        <Label className="text-sm text-gray-600">Usuarios Máximos</Label>
                        <p className="text-lg font-semibold">{tenant.max_users}</p>
                      </div>
                      <div>
                        <Label className="text-sm text-gray-600">Estado</Label>
                        <p className="text-lg font-semibold">
                          {tenant.is_active ? (
                            <span className="text-green-600">Activo</span>
                          ) : (
                            <span className="text-red-600">Inactivo</span>
                          )}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3">
                <Link href="/dashboard">
                  <Button type="button" variant="outline" disabled={isSaving}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isSaving}>
                  {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Guardar Cambios
                </Button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
