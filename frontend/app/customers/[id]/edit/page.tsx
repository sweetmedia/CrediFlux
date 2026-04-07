'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { customersAPI } from '@/lib/api/customers';
import { formatIDNumber, cleanIDNumber, getIDPlaceholder } from '@/lib/utils/id-formatter';
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
import { NativeSelect as Select } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Loader2, Save, UserCog } from 'lucide-react';

const customerSchema = z.object({
  first_name: z.string().min(2, 'Nombre requerido'),
  last_name: z.string().min(2, 'Apellido requerido'),
  date_of_birth: z.string().min(1, 'Fecha de nacimiento requerida'),
  gender: z.enum(['M', 'F', 'O']).optional(),
  email: z.string().email('Email inválido'),
  phone: z.string().min(10, 'Teléfono debe tener al menos 10 caracteres'),
  id_type: z.string().min(1, 'Tipo de identificación requerido'),
  id_number: z.string().min(5, 'Número de identificación requerido'),
  address_line1: z.string().min(5, 'Dirección requerida'),
  address_line2: z.string().optional(),
  city: z.string().min(2, 'Ciudad requerida'),
  state: z.string().min(2, 'Estado/Provincia requerido'),
  postal_code: z.string().min(2, 'Código postal requerido'),
  country: z.string().min(2, 'País requerido'),
  employment_status: z.string().optional(),
  employer_name: z.string().optional(),
  occupation: z.string().optional(),
  monthly_income: z.string().optional(),
  notes: z.string().optional(),
});

type CustomerFormData = z.infer<typeof customerSchema>;

export default function EditCustomerPage() {
  const router = useRouter();
  const params = useParams();
  const customerId = params.id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCustomer, setIsFetchingCustomer] = useState(true);

  // ID number formatted value (with dashes)
  const [formattedIdNumber, setFormattedIdNumber] = useState<string>('');
  const [idType, setIdType] = useState<string>('');

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CustomerFormData>({
    resolver: zodResolver(customerSchema),
  });

  const watchedIdType = watch('id_type');
  const watchedIdNumber = watch('id_number');

  // Fetch customer data
  useEffect(() => {
    const fetchCustomer = async () => {
      try {
        setIsFetchingCustomer(true);
        const customer = await customersAPI.getCustomer(customerId);

        // Populate form with existing data
        setValue('first_name', customer.first_name);
        setValue('last_name', customer.last_name);
        setValue('date_of_birth', customer.date_of_birth);
        if (customer.gender) setValue('gender', customer.gender as 'M' | 'F' | 'O');
        setValue('email', customer.email);
        setValue('phone', customer.phone);
        setValue('id_type', customer.id_type);
        setValue('id_number', customer.id_number);

        // Format ID number for display
        setIdType(customer.id_type);
        if (customer.id_number && customer.id_type) {
          const formatted = formatIDNumber(customer.id_number, customer.id_type as any);
          setFormattedIdNumber(formatted);
        }

        setValue('address_line1', customer.address_line1);
        if (customer.address_line2) setValue('address_line2', customer.address_line2);
        setValue('city', customer.city);
        setValue('state', customer.state);
        setValue('postal_code', customer.postal_code);
        setValue('country', customer.country);
        if (customer.employment_status) setValue('employment_status', customer.employment_status);
        if (customer.employer_name) setValue('employer_name', customer.employer_name);
        if (customer.occupation) setValue('occupation', customer.occupation);
        if (customer.monthly_income) setValue('monthly_income', customer.monthly_income.toString());
        if (customer.notes) setValue('notes', customer.notes);
      } catch (err: any) {
        console.error('Error fetching customer:', err);
        setError('Error al cargar los datos del cliente');
      } finally {
        setIsFetchingCustomer(false);
      }
    };

    if (customerId && isAuthenticated) {
      fetchCustomer();
    }
  }, [customerId, isAuthenticated, setValue]);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Handle ID number change with automatic formatting
  const handleIdNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;

    if (!idType) {
      setFormattedIdNumber(inputValue);
      setValue('id_number', inputValue);
      return;
    }

    // Format the value with dashes
    const formatted = formatIDNumber(inputValue, idType as any);
    setFormattedIdNumber(formatted);

    // Store cleaned value (without dashes) in form
    const cleaned = cleanIDNumber(formatted);
    setValue('id_number', cleaned);
  };

  // Update formatted value when ID type changes
  useEffect(() => {
    if (watchedIdType && watchedIdType !== idType) {
      setIdType(watchedIdType);
      if (watchedIdNumber) {
        const formatted = formatIDNumber(watchedIdNumber, watchedIdType as any);
        setFormattedIdNumber(formatted);
      }
    }
  }, [watchedIdType, watchedIdNumber, idType]);

  const onSubmit = async (data: CustomerFormData) => {
    try {
      setIsLoading(true);
      setError('');

      // Convert monthly_income to number if provided
      const submitData = {
        ...data,
        monthly_income: data.monthly_income ? parseFloat(data.monthly_income) : undefined,
      };

      await customersAPI.updateCustomer(customerId, submitData);

      // Redirect to customer detail page
      router.push(`/customers/${customerId}`);
    } catch (err: any) {
      console.error('Error updating customer:', err);

      if (err.response?.data) {
        const errorData = err.response.data;

        // Handle field-specific errors
        const fieldErrors = [];
        if (errorData.id_number) fieldErrors.push(`RNC: ${errorData.id_number[0]}`);
        if (errorData.email) fieldErrors.push(`Email: ${errorData.email[0]}`);
        if (errorData.phone) fieldErrors.push(`Teléfono: ${errorData.phone[0]}`);
        if (errorData.date_of_birth) fieldErrors.push(`Fecha de nacimiento: ${errorData.date_of_birth[0]}`);
        if (errorData.address_line1) fieldErrors.push(`Dirección: ${errorData.address_line1[0]}`);

        if (fieldErrors.length > 0) {
          setError(fieldErrors.join(', '));
        } else if (errorData.detail) {
          setError(errorData.detail);
        } else {
          setError('Error al actualizar el cliente. Por favor verifica los datos.');
        }
      } else {
        setError('Error al conectar con el servidor');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking authentication or fetching customer
  if (authLoading || isFetchingCustomer) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
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
              <UserCog className="h-8 w-8 text-blue-600" />
              Editar Cliente
            </h1>
            <p className="text-gray-600 mt-1">Actualiza la información del cliente</p>
          </div>
          <Link href={`/customers/${customerId}`}>
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver
            </Button>
          </Link>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-6">
            {/* Error Message */}
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Personal Information */}
            <Card>
              <CardHeader>
                <CardTitle>Datos Personales</CardTitle>
                <CardDescription>
                  Información personal del cliente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">
                      Nombre <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="first_name"
                      placeholder="Juan"
                      {...register('first_name')}
                      disabled={isLoading}
                    />
                    {errors.first_name && (
                      <p className="text-sm text-red-500">{errors.first_name.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="last_name">
                      Apellido <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="last_name"
                      placeholder="Pérez"
                      {...register('last_name')}
                      disabled={isLoading}
                    />
                    {errors.last_name && (
                      <p className="text-sm text-red-500">{errors.last_name.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="date_of_birth">
                      Fecha de Nacimiento <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="date_of_birth"
                      type="date"
                      {...register('date_of_birth')}
                      disabled={isLoading}
                    />
                    {errors.date_of_birth && (
                      <p className="text-sm text-red-500">{errors.date_of_birth.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="gender">Género</Label>
                    <Select id="gender" {...register('gender')} disabled={isLoading}>
                      <option value="">Seleccionar...</option>
                      <option value="M">Masculino</option>
                      <option value="F">Femenino</option>
                      <option value="O">Otro</option>
                    </Select>
                    {errors.gender && (
                      <p className="text-sm text-red-500">{errors.gender.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Contact Information */}
            <Card>
              <CardHeader>
                <CardTitle>Información de Contacto</CardTitle>
                <CardDescription>
                  Datos de contacto del cliente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">
                      Email <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="cliente@ejemplo.com"
                      {...register('email')}
                      disabled={isLoading}
                    />
                    {errors.email && (
                      <p className="text-sm text-red-500">{errors.email.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">
                      Teléfono <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="phone"
                      placeholder="+1 (809) 555-1234"
                      {...register('phone')}
                      disabled={isLoading}
                    />
                    {errors.phone && (
                      <p className="text-sm text-red-500">{errors.phone.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Identification */}
            <Card>
              <CardHeader>
                <CardTitle>Identificación</CardTitle>
                <CardDescription>
                  Documentos de identidad del cliente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="id_type">
                      Tipo de ID <span className="text-red-500">*</span>
                    </Label>
                    <Select id="id_type" {...register('id_type')} disabled={isLoading}>
                      <option value="">Seleccionar...</option>
                      <option value="cedula">Cédula (11 dígitos)</option>
                      <option value="rnc">RNC (9 dígitos)</option>
                      <option value="passport">Pasaporte</option>
                    </Select>
                    {errors.id_type && (
                      <p className="text-sm text-red-500">{errors.id_type.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="id_number">
                      Número de ID <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="id_number"
                      placeholder={idType ? getIDPlaceholder(idType as any) : '000-0000000-0'}
                      value={formattedIdNumber}
                      onChange={handleIdNumberChange}
                      disabled={isLoading}
                    />
                    {errors.id_number && (
                      <p className="text-sm text-red-500">{errors.id_number.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Address */}
            <Card>
              <CardHeader>
                <CardTitle>Dirección</CardTitle>
                <CardDescription>
                  Domicilio del cliente
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="address_line1">
                    Dirección Línea 1 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="address_line1"
                    placeholder="Calle Principal #123"
                    {...register('address_line1')}
                    disabled={isLoading}
                  />
                  {errors.address_line1 && (
                    <p className="text-sm text-red-500">{errors.address_line1.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address_line2">Dirección Línea 2</Label>
                  <Input
                    id="address_line2"
                    placeholder="Apto/Suite (opcional)"
                    {...register('address_line2')}
                    disabled={isLoading}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="city">
                      Ciudad <span className="text-red-500">*</span>
                    </Label>
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
                    <Label htmlFor="state">
                      Estado/Provincia <span className="text-red-500">*</span>
                    </Label>
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
                    <Label htmlFor="postal_code">
                      Código Postal <span className="text-red-500">*</span>
                    </Label>
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

                  <div className="space-y-2">
                    <Label htmlFor="country">
                      País <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="country"
                      placeholder="República Dominicana"
                      {...register('country')}
                      disabled={isLoading}
                    />
                    {errors.country && (
                      <p className="text-sm text-red-500">{errors.country.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Employment Information */}
            <Card>
              <CardHeader>
                <CardTitle>Información Laboral</CardTitle>
                <CardDescription>
                  Datos de empleo e ingresos (opcional)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="employment_status">Estado Laboral</Label>
                    <Select
                      id="employment_status"
                      {...register('employment_status')}
                      disabled={isLoading}
                    >
                      <option value="">Seleccionar...</option>
                      <option value="employed">Empleado</option>
                      <option value="self_employed">Trabajador Independiente</option>
                      <option value="unemployed">Desempleado</option>
                      <option value="retired">Retirado</option>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="employer_name">Nombre del Empleador</Label>
                    <Input
                      id="employer_name"
                      placeholder="Empresa XYZ"
                      {...register('employer_name')}
                      disabled={isLoading}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="occupation">Ocupación</Label>
                    <Input
                      id="occupation"
                      placeholder="Ingeniero, Contador, etc."
                      {...register('occupation')}
                      disabled={isLoading}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="monthly_income">Ingreso Mensual (USD)</Label>
                    <Input
                      id="monthly_income"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      {...register('monthly_income')}
                      disabled={isLoading}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader>
                <CardTitle>Notas Adicionales</CardTitle>
                <CardDescription>
                  Información adicional sobre el cliente (opcional)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  id="notes"
                  placeholder="Notas, comentarios o información relevante..."
                  rows={4}
                  {...register('notes')}
                  disabled={isLoading}
                />
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <Link href={`/customers/${customerId}`}>
                <Button type="button" variant="outline" disabled={isLoading}>
                  Cancelar
                </Button>
              </Link>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Save className="mr-2 h-4 w-4" />
                Guardar Cambios
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
