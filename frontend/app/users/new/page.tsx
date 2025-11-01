'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { usersAPI, CreateUserData } from '@/lib/api/users';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ArrowLeft,
  Loader2,
  Save,
  UserPlus,
  Mail,
  Phone,
  Briefcase,
  Shield,
  Key,
  AlertCircle,
} from 'lucide-react';

const userSchema = z.object({
  email: z.string().email('Email inválido'),
  username: z.string().optional(),
  first_name: z.string().min(1, 'Nombre requerido'),
  last_name: z.string().min(1, 'Apellido requerido'),
  phone: z.string().optional(),
  password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  confirm_password: z.string().min(1, 'Confirma la contraseña'),
  role: z.enum(['admin', 'manager', 'loan_officer', 'accountant', 'cashier', 'viewer']),
  job_title: z.string().optional(),
  department: z.string().optional(),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Las contraseñas no coinciden',
  path: ['confirm_password'],
});

type UserFormData = z.infer<typeof userSchema>;

export default function NewUserPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<UserFormData>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      role: 'viewer',
    },
  });

  const selectedRole = watch('role');

  const onSubmit = async (data: UserFormData) => {
    try {
      setIsLoading(true);
      setError('');

      // Remove confirm_password from data
      const { confirm_password, ...userData } = data;

      // Create user
      await usersAPI.createTeamMember(userData as CreateUserData);

      // Redirect to users list
      router.push('/users');
    } catch (err: any) {
      console.error('Error creating user:', err);
      if (err.response?.data) {
        // Handle specific field errors
        const errors = err.response.data;
        if (errors.email) {
          setError(`Email: ${errors.email[0]}`);
        } else if (errors.username) {
          setError(`Usuario: ${errors.username[0]}`);
        } else {
          setError('Error al crear el usuario. Verifica los datos e intenta nuevamente.');
        }
      } else {
        setError('Error al crear el usuario. Intenta nuevamente.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getRoleDescription = (role: string) => {
    const descriptions: Record<string, string> = {
      admin: 'Acceso completo a todas las funciones del sistema, puede gestionar usuarios y configuraciones.',
      manager: 'Acceso de gestión a préstamos, clientes y reportes. No puede crear usuarios.',
      loan_officer: 'Puede crear y gestionar préstamos, clientes y cronogramas de pago.',
      accountant: 'Acceso a reportes financieros, pagos y estados de cuenta.',
      cashier: 'Puede registrar pagos y consultar información de préstamos.',
      viewer: 'Solo lectura. Puede ver información pero no realizar cambios.',
    };
    return descriptions[role] || '';
  };

  // Show loading state while checking authentication
  if (authLoading) {
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
        <div className="mb-6">
          <Link href="/users">
            <Button variant="outline" size="sm" className="mb-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a Usuarios
            </Button>
          </Link>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <UserPlus className="h-8 w-8 text-blue-600" />
            Agregar Nuevo Usuario
          </h1>
          <p className="text-gray-600 mt-1">
            Completa la información para crear un nuevo miembro del equipo
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-6">
            {/* Personal Information */}
            <Card>
              <CardHeader>
                <CardTitle>Información Personal</CardTitle>
                <CardDescription>
                  Datos básicos del usuario
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
                      {...register('first_name')}
                      placeholder="Juan"
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
                      {...register('last_name')}
                      placeholder="Pérez"
                    />
                    {errors.last_name && (
                      <p className="text-sm text-red-500">{errors.last_name.message}</p>
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
                      {...register('email')}
                      placeholder="juan.perez@empresa.com"
                      className="pl-10"
                    />
                  </div>
                  {errors.email && (
                    <p className="text-sm text-red-500">{errors.email.message}</p>
                  )}
                  <p className="text-xs text-gray-500">
                    Este email será usado para iniciar sesión
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="phone"
                      {...register('phone')}
                      placeholder="+1 (555) 123-4567"
                      className="pl-10"
                    />
                  </div>
                  {errors.phone && (
                    <p className="text-sm text-red-500">{errors.phone.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="username">Usuario (opcional)</Label>
                  <Input
                    id="username"
                    {...register('username')}
                    placeholder="Se generará automáticamente si no se especifica"
                  />
                  {errors.username && (
                    <p className="text-sm text-red-500">{errors.username.message}</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Security */}
            <Card>
              <CardHeader>
                <CardTitle>Seguridad</CardTitle>
                <CardDescription>
                  Establece una contraseña temporal para el usuario
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="password">
                    Contraseña <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="password"
                      type="password"
                      {...register('password')}
                      placeholder="Mínimo 8 caracteres"
                      className="pl-10"
                    />
                  </div>
                  {errors.password && (
                    <p className="text-sm text-red-500">{errors.password.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm_password">
                    Confirmar Contraseña <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      id="confirm_password"
                      type="password"
                      {...register('confirm_password')}
                      placeholder="Repite la contraseña"
                      className="pl-10"
                    />
                  </div>
                  {errors.confirm_password && (
                    <p className="text-sm text-red-500">{errors.confirm_password.message}</p>
                  )}
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-700">
                    <strong>Nota:</strong> El usuario podrá cambiar su contraseña después del primer inicio de sesión.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Role & Position */}
            <Card>
              <CardHeader>
                <CardTitle>Rol y Cargo</CardTitle>
                <CardDescription>
                  Define el nivel de acceso y posición del usuario
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="role">
                    Rol del Sistema <span className="text-red-500">*</span>
                  </Label>
                  <div className="relative">
                    <Shield className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Select
                      id="role"
                      {...register('role')}
                      className="pl-10"
                    >
                      <option value="viewer">Visualizador</option>
                      <option value="cashier">Cajero</option>
                      <option value="accountant">Contador</option>
                      <option value="loan_officer">Oficial de Préstamos</option>
                      <option value="manager">Gerente</option>
                      <option value="admin">Administrador</option>
                    </Select>
                  </div>
                  {errors.role && (
                    <p className="text-sm text-red-500">{errors.role.message}</p>
                  )}
                  {selectedRole && (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mt-2">
                      <p className="text-sm text-gray-700">
                        <strong className="text-gray-900">
                          {selectedRole === 'admin' && 'Administrador'}
                          {selectedRole === 'manager' && 'Gerente'}
                          {selectedRole === 'loan_officer' && 'Oficial de Préstamos'}
                          {selectedRole === 'accountant' && 'Contador'}
                          {selectedRole === 'cashier' && 'Cajero'}
                          {selectedRole === 'viewer' && 'Visualizador'}:
                        </strong>{' '}
                        {getRoleDescription(selectedRole)}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="job_title">Cargo</Label>
                    <div className="relative">
                      <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="job_title"
                        {...register('job_title')}
                        placeholder="Ej: Gerente de Créditos"
                        className="pl-10"
                      />
                    </div>
                    {errors.job_title && (
                      <p className="text-sm text-red-500">{errors.job_title.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="department">Departamento</Label>
                    <Input
                      id="department"
                      {...register('department')}
                      placeholder="Ej: Operaciones"
                    />
                    {errors.department && (
                      <p className="text-sm text-red-500">{errors.department.message}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex gap-4 justify-end">
              <Link href="/users">
                <Button type="button" variant="outline" disabled={isLoading}>
                  Cancelar
                </Button>
              </Link>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creando Usuario...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Crear Usuario
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
