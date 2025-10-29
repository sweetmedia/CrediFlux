'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import { usersAPI, User } from '@/lib/api/users';
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
  Loader2,
  Plus,
  Search,
  Users,
  Mail,
  Phone,
  Briefcase,
  Shield,
  CheckCircle,
  XCircle,
  Crown,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react';

export default function UsersListPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [totalCount, setTotalCount] = useState(0);

  // Filters and pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load users only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadUsers();
    }
  }, [isAuthenticated, currentPage, searchTerm, roleFilter, statusFilter]);

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      setError('');

      const params: any = {
        page: currentPage,
      };

      if (searchTerm) params.search = searchTerm;
      if (roleFilter) params.role = roleFilter;
      if (statusFilter) params.is_active = statusFilter === 'active';

      const response = await usersAPI.getTeamMembers(params);
      setUsers(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error loading users:', err);
      setError('Error al cargar los usuarios');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1);
  };

  const handleRoleFilter = (value: string) => {
    setRoleFilter(value);
    setCurrentPage(1);
  };

  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    setCurrentPage(1);
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

  const totalPages = Math.ceil(totalCount / 20);
  const activeUsers = users.filter((u) => u.is_active).length;

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
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <Users className="h-8 w-8 text-blue-600" />
              Equipo
            </h1>
            <p className="text-gray-600 mt-1">
              Gestiona los usuarios y empleados de tu financiera
            </p>
          </div>
          <div className="flex gap-2">
            <Link href="/dashboard">
              <Button variant="outline">Volver al Dashboard</Button>
            </Link>
            <Link href="/users/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Agregar Usuario
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Filtros de Búsqueda
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="search">Buscar</Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    id="search"
                    placeholder="Nombre, email, teléfono..."
                    value={searchTerm}
                    onChange={(e) => handleSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Rol</Label>
                <Select
                  id="role"
                  value={roleFilter}
                  onChange={(e) => handleRoleFilter(e.target.value)}
                >
                  <option value="">Todos los roles</option>
                  <option value="admin">Administrador</option>
                  <option value="manager">Gerente</option>
                  <option value="loan_officer">Oficial de Préstamos</option>
                  <option value="accountant">Contador</option>
                  <option value="cashier">Cajero</option>
                  <option value="viewer">Visualizador</option>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">Estado</Label>
                <Select
                  id="status"
                  value={statusFilter}
                  onChange={(e) => handleStatusFilter(e.target.value)}
                >
                  <option value="">Todos los estados</option>
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Usuarios</p>
                  <p className="text-2xl font-bold">{totalCount}</p>
                </div>
                <Users className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Activos</p>
                  <p className="text-2xl font-bold text-green-600">{activeUsers}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Inactivos</p>
                  <p className="text-2xl font-bold text-red-600">{totalCount - activeUsers}</p>
                </div>
                <XCircle className="h-8 w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Página</p>
                  <p className="text-2xl font-bold">
                    {currentPage} / {totalPages || 1}
                  </p>
                </div>
                <Users className="h-8 w-8 text-gray-400" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Users List */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando usuarios...</p>
          </div>
        ) : users.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <div className="flex flex-col items-center gap-4">
                <div className="rounded-full bg-gray-100 p-6">
                  <Users className="h-12 w-12 text-gray-400" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900">
                  No se encontraron usuarios
                </h3>
                <p className="text-gray-600">
                  {searchTerm || roleFilter || statusFilter
                    ? 'Intenta ajustar tus filtros'
                    : 'Comienza agregando tu primer usuario al equipo'}
                </p>
                <Link href="/users/new">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Agregar Primer Usuario
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {users.map((user) => (
              <Card
                key={user.id}
                className="hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/users/${user.id}`)}
              >
                <CardContent className="p-6">
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    {/* Left Section - User Info */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-lg font-semibold text-gray-900">
                              {user.full_name}
                            </h3>
                            {user.is_tenant_owner && (
                              <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-amber-100 text-amber-700">
                                <Crown className="h-3 w-3" />
                                <span className="font-semibold">Dueño</span>
                              </div>
                            )}
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

                          {/* Contact Info */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="flex items-center gap-2">
                              <Mail className="h-4 w-4 text-gray-400" />
                              <div>
                                <p className="text-xs text-gray-600">Email</p>
                                <p className="text-sm font-medium">{user.email}</p>
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
                          </div>

                          {/* Job Info */}
                          {(user.job_title || user.department) && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-gray-200">
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
                                  <Users className="h-4 w-4 text-gray-400" />
                                  <div>
                                    <p className="text-xs text-gray-600">Departamento</p>
                                    <p className="text-sm font-medium">{user.department}</p>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right Section - Actions */}
                    <div className="flex lg:flex-col gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/users/${user.id}`);
                        }}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Ver Detalles
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">
                      Mostrando {(currentPage - 1) * 20 + 1} a{' '}
                      {Math.min(currentPage * 20, totalCount)} de {totalCount} usuarios
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage - 1)}
                        disabled={currentPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Anterior
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(currentPage + 1)}
                        disabled={currentPage === totalPages}
                      >
                        Siguiente
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
