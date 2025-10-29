'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { usersAPI, User, UpdateUserData } from '@/lib/api/users';
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
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ArrowLeft,
  Loader2,
  User as UserIcon,
  Mail,
  Phone,
  Briefcase,
  Shield,
  Calendar,
  CheckCircle,
  XCircle,
  Edit,
  Save,
  X,
  Crown,
  AlertCircle,
  Trash2,
} from 'lucide-react';

export default function UserDetailPage() {
  const router = useRouter();
  const params = useParams();
  const userId = params?.id as string;
  const { isAuthenticated, isLoading: authLoading, user: currentUser } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Edit form state
  const [editForm, setEditForm] = useState<UpdateUserData>({});

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load user details
  useEffect(() => {
    if (isAuthenticated && userId) {
      loadUser();
    }
  }, [isAuthenticated, userId]);

  const loadUser = async () => {
    try {
      setIsLoading(true);
      setError('');
      const userData = await usersAPI.getTeamMember(userId);
      setUser(userData);

      // Initialize edit form
      setEditForm({
        first_name: userData.first_name,
        last_name: userData.last_name,
        phone: userData.phone || '',
        role: userData.role,
        job_title: userData.job_title || '',
        department: userData.department || '',
        is_active: userData.is_active,
      });
    } catch (err: any) {
      console.error('Error loading user:', err);
      setError('Error al cargar el usuario');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!user) return;

    try {
      setIsSaving(true);
      setError('');

      await usersAPI.updateTeamMember(userId, editForm);

      // Reload user data
      await loadUser();
      setIsEditing(false);
    } catch (err: any) {
      console.error('Error updating user:', err);
      if (err.response?.data) {
        const errors = err.response.data;
        if (errors.role) {
          setError(`Rol: ${errors.role[0]}`);
        } else {
          setError('Error al actualizar el usuario. Verifica los datos e intenta nuevamente.');
        }
      } else {
        setError('Error al actualizar el usuario. Intenta nuevamente.');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!user) return;

    if (!confirm(`¿Estás seguro de que deseas ${user.is_active ? 'desactivar' : 'activar'} a ${user.full_name}?`)) {
      return;
    }

    try {
      setIsSaving(true);
      setError('');

      if (user.is_active) {
        // Deactivate
        await usersAPI.deleteTeamMember(userId);
      } else {
        // Reactivate
        await usersAPI.updateTeamMember(userId, { is_active: true });
      }

      // Reload user data
      await loadUser();
    } catch (err: any) {
      console.error('Error updating user status:', err);
      setError(err.response?.data?.error || 'Error al actualizar el estado del usuario');
    } finally {
      setIsSaving(false);
    }
  };

  const getRoleLabel = (role: string) => {
    const roles: Record<string, string> = {
      admin: 'Administrador',
      manager: 'Gerente',
      loan_officer: 'Oficial de Préstamos',
      accountant: 'Contador',
      cashier: 'Cajero',
      viewer: 'Visualizador',
    };
    return roles[role] || role;
  };

  const getRoleBadgeClass = (role: string) => {
    const classes: Record<string, string> = {
      admin: 'bg-purple-100 text-purple-700',
      manager: 'bg-blue-100 text-blue-700',
      loan_officer: 'bg-green-100 text-green-700',
      accountant: 'bg-yellow-100 text-yellow-700',
      cashier: 'bg-orange-100 text-orange-700',
      viewer: 'bg-gray-100 text-gray-700',
    };
    return classes[role] || 'bg-gray-100 text-gray-700';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const canEdit = currentUser?.is_tenant_owner || currentUser?.role === 'admin';
  const canDeactivate = canEdit && !user?.is_tenant_owner && user?.id !== currentUser?.id;

  // Show loading state while checking authentication
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error && !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
        <div className="container mx-auto max-w-4xl">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Link href="/users">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a Usuarios
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 py-8">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/users">
            <Button variant="outline" size="sm" className="mb-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Volver a Equipo
            </Button>
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                <UserIcon className="h-8 w-8 text-blue-600" />
                {user.full_name}
                {user.is_tenant_owner && (
                  <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-amber-100 text-amber-700">
                    <Crown className="h-4 w-4" />
                    <span className="font-semibold">Dueño</span>
                  </div>
                )}
              </h1>
              <div className="flex items-center gap-2 mt-2">
                <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${getRoleBadgeClass(user.role)}`}>
                  <Shield className="h-3 w-3" />
                  <span className="font-semibold">{getRoleLabel(user.role)}</span>
                </div>
                {user.is_active ? (
                  <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">
                    <CheckCircle className="h-3 w-3" />
                    <span className="font-semibold">Activo</span>
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-red-100 text-red-700">
                    <XCircle className="h-3 w-3" />
                    <span className="font-semibold">Inactivo</span>
                  </div>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              {canEdit && !isEditing && (
                <Button onClick={() => setIsEditing(true)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Editar
                </Button>
              )}
              {isEditing && (
                <>
                  <Button variant="outline" onClick={() => {
                    setIsEditing(false);
                    setEditForm({
                      first_name: user.first_name,
                      last_name: user.last_name,
                      phone: user.phone || '',
                      role: user.role,
                      job_title: user.job_title || '',
                      department: user.department || '',
                      is_active: user.is_active,
                    });
                  }}>
                    <X className="mr-2 h-4 w-4" />
                    Cancelar
                  </Button>
                  <Button onClick={handleSave} disabled={isSaving}>
                    {isSaving ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Guardando...
                      </>
                    ) : (
                      <>
                        <Save className="mr-2 h-4 w-4" />
                        Guardar
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

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
              {isEditing ? (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="first_name">Nombre</Label>
                      <Input
                        id="first_name"
                        value={editForm.first_name}
                        onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="last_name">Apellido</Label>
                      <Input
                        id="last_name"
                        value={editForm.last_name}
                        onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">Teléfono</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="phone"
                        value={editForm.phone}
                        onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                        className="pl-10"
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex items-center gap-2">
                      <UserIcon className="h-4 w-4 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-600">Nombre Completo</p>
                        <p className="text-sm font-medium">{user.full_name}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-600">Email</p>
                        <p className="text-sm font-medium">{user.email}</p>
                      </div>
                    </div>
                  </div>

                  {user.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-gray-400" />
                      <div>
                        <p className="text-xs text-gray-600">Teléfono</p>
                        <p className="text-sm font-medium">{user.phone}</p>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <UserIcon className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-600">Usuario</p>
                      <p className="text-sm font-medium">{user.username}</p>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Role & Position */}
          <Card>
            <CardHeader>
              <CardTitle>Rol y Cargo</CardTitle>
              <CardDescription>
                Nivel de acceso y posición del usuario
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isEditing ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="role">Rol del Sistema</Label>
                    <div className="relative">
                      <Shield className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Select
                        id="role"
                        value={editForm.role}
                        onChange={(e) => setEditForm({ ...editForm, role: e.target.value as any })}
                        className="pl-10"
                        disabled={user.is_tenant_owner}
                      >
                        <option value="viewer">Visualizador</option>
                        <option value="cashier">Cajero</option>
                        <option value="accountant">Contador</option>
                        <option value="loan_officer">Oficial de Préstamos</option>
                        <option value="manager">Gerente</option>
                        {currentUser?.is_tenant_owner && <option value="admin">Administrador</option>}
                      </Select>
                    </div>
                    {user.is_tenant_owner && (
                      <p className="text-xs text-gray-500">
                        No se puede cambiar el rol del dueño
                      </p>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="job_title">Cargo</Label>
                      <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          id="job_title"
                          value={editForm.job_title}
                          onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="department">Departamento</Label>
                      <Input
                        id="department"
                        value={editForm.department}
                        onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                      />
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-600">Rol</p>
                      <p className="text-sm font-medium">{getRoleLabel(user.role)}</p>
                    </div>
                  </div>

                  {(user.job_title || user.department) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {user.job_title && (
                        <div className="flex items-center gap-2">
                          <Briefcase className="h-4 w-4 text-gray-400" />
                          <div>
                            <p className="text-xs text-gray-600">Cargo</p>
                            <p className="text-sm font-medium">{user.job_title}</p>
                          </div>
                        </div>
                      )}

                      {user.department && (
                        <div className="flex items-center gap-2">
                          <Briefcase className="h-4 w-4 text-gray-400" />
                          <div>
                            <p className="text-xs text-gray-600">Departamento</p>
                            <p className="text-sm font-medium">{user.department}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Account Information */}
          <Card>
            <CardHeader>
              <CardTitle>Información de la Cuenta</CardTitle>
              <CardDescription>
                Estado y estadísticas de la cuenta
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-400" />
                  <div>
                    <p className="text-xs text-gray-600">Fecha de Creación</p>
                    <p className="text-sm font-medium">{formatDate(user.created_at)}</p>
                  </div>
                </div>

                {user.last_login_at && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <div>
                      <p className="text-xs text-gray-600">Último Acceso</p>
                      <p className="text-sm font-medium">{formatDate(user.last_login_at)}</p>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  {user.is_active ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <div>
                    <p className="text-xs text-gray-600">Estado</p>
                    <p className="text-sm font-medium">
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {user.email_verified ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-yellow-600" />
                  )}
                  <div>
                    <p className="text-xs text-gray-600">Email Verificado</p>
                    <p className="text-sm font-medium">
                      {user.email_verified ? 'Sí' : 'No'}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          {canDeactivate && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-red-600">Zona de Peligro</CardTitle>
                <CardDescription>
                  Acciones que afectan el acceso del usuario
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="destructive"
                  onClick={handleDeactivate}
                  disabled={isSaving}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      {user.is_active ? (
                        <>
                          <XCircle className="mr-2 h-4 w-4" />
                          Desactivar Usuario
                        </>
                      ) : (
                        <>
                          <CheckCircle className="mr-2 h-4 w-4" />
                          Activar Usuario
                        </>
                      )}
                    </>
                  )}
                </Button>
                <p className="text-xs text-gray-500 mt-2">
                  {user.is_active
                    ? 'El usuario no podrá iniciar sesión ni acceder al sistema.'
                    : 'El usuario podrá iniciar sesión y acceder al sistema.'}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
