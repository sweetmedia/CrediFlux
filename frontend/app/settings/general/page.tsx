'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuth } from '@/lib/contexts/AuthContext';
import { tenantsAPI, Tenant, TenantUpdateData } from '@/lib/api/tenants';
import { authAPI } from '@/lib/api/auth';
import { getApiUrl } from '@/lib/api/client';
import { ProfileUpdateData, PasswordChangeData } from '@/types';
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
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
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
  CheckCircle2,
  Image as ImageIcon,
  Upload,
  X,
  User as UserIcon,
  Lock,
  Bell,
  Briefcase,
  DollarSign
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
  default_currency: z.enum(['USD', 'DOP', 'EUR', 'GBP']).optional(),
  currency_symbol: z.string().max(10, 'Símbolo de moneda debe tener máximo 10 caracteres').optional(),
});

const profileSchema = z.object({
  first_name: z.string().min(2, 'Nombre debe tener al menos 2 caracteres'),
  last_name: z.string().min(2, 'Apellido debe tener al menos 2 caracteres'),
  phone: z.string().optional(),
  job_title: z.string().optional(),
  department: z.string().optional(),
  bio: z.string().optional(),
  receive_notifications: z.boolean().optional(),
});

const passwordChangeSchema = z.object({
  current_password: z.string().min(1, 'Contraseña actual requerida'),
  new_password: z.string().min(8, 'La nueva contraseña debe tener al menos 8 caracteres'),
  confirm_password: z.string().min(8, 'Confirmación requerida'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Las contraseñas no coinciden",
  path: ["confirm_password"],
});

type TenantSettingsFormData = z.infer<typeof tenantSettingsSchema>;
type ProfileFormData = z.infer<typeof profileSchema>;
type PasswordChangeFormData = z.infer<typeof passwordChangeSchema>;

export default function TenantSettingsPage() {
  const router = useRouter();
  const { user, tenant: authTenant, isAuthenticated, isLoading: authLoading, refreshTenant, refreshUser } = useAuth();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  // Profile states
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState<string>('');
  const [profileSuccess, setProfileSuccess] = useState<string>('');
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);

  // Password change states
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string>('');
  const [passwordSuccess, setPasswordSuccess] = useState<string>('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Tenant settings form
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<TenantSettingsFormData>({
    resolver: zodResolver(tenantSettingsSchema),
  });

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleSubmitProfile,
    setValue: setValueProfile,
    watch: watchProfile,
    formState: { errors: profileErrors },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
  });

  // Password change form
  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    reset: resetPassword,
    formState: { errors: passwordErrors },
  } = useForm<PasswordChangeFormData>({
    resolver: zodResolver(passwordChangeSchema),
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
      setValue('default_currency', data.default_currency || 'USD');
      setValue('currency_symbol', data.currency_symbol || '$');

      // Set logo preview - prepend API URL if logo is a relative path
      if (data.logo) {
        const apiUrl = getApiUrl();
        const logoUrl = data.logo.startsWith('http') ? data.logo : `${apiUrl}${data.logo}`;
        setLogoPreview(logoUrl);
      } else {
        setLogoPreview(null);
      }
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
        default_currency: data.default_currency || undefined,
        currency_symbol: data.currency_symbol || undefined,
      };

      const response = await tenantsAPI.updateSettings(updateData);
      setTenant(response.tenant);
      setSuccessMessage('Configuración actualizada exitosamente');

      // Refresh tenant in auth context
      await refreshTenant();

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err: any) {
      console.error('Error updating tenant settings:', err);

      // Handle 401 Unauthorized - redirect to login
      if (err.response?.status === 401) {
        setError('Tu sesión ha expirado. Redirigiendo al login...');
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
        return;
      }

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

  const handleLogoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Por favor selecciona un archivo de imagen válido');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('La imagen debe ser menor a 5MB');
      return;
    }

    try {
      setIsUploadingLogo(true);
      setError('');
      setSuccessMessage('');

      const response = await tenantsAPI.uploadLogo(file);
      setTenant(response.tenant);

      // Set logo preview - prepend API URL if logo is a relative path
      if (response.tenant.logo) {
        const apiUrl = getApiUrl();
        const logoUrl = response.tenant.logo.startsWith('http')
          ? response.tenant.logo
          : `${apiUrl}${response.tenant.logo}`;
        setLogoPreview(logoUrl);
      } else {
        setLogoPreview(null);
      }

      setSuccessMessage('Logo actualizado exitosamente');

      // Refresh tenant in auth context so logo appears in dashboard header
      await refreshTenant();

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err: any) {
      console.error('Error uploading logo:', err);

      // Handle 401 Unauthorized - redirect to login
      if (err.response?.status === 401) {
        setError('Tu sesión ha expirado. Redirigiendo al login...');
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
        return;
      }

      // Handle different error types
      let errorMessage = 'Error al subir el logo';

      if (err.response?.data) {
        // Server validation error
        if (err.response.data.logo) {
          errorMessage = Array.isArray(err.response.data.logo)
            ? err.response.data.logo[0]
            : err.response.data.logo;
        } else if (err.response.data.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.response.data.error) {
          errorMessage = err.response.data.error;
        } else {
          errorMessage = `Error ${err.response.status}: ${err.response.statusText}`;
        }
      } else if (err.message) {
        // Network error or custom error message
        errorMessage = err.message;
      }

      setError(errorMessage);
    } finally {
      setIsUploadingLogo(false);
    }
  };

  const handleLogoRemove = async () => {
    if (!confirm('¿Estás seguro de que deseas eliminar el logo?')) {
      return;
    }

    try {
      setIsUploadingLogo(true);
      setError('');
      setSuccessMessage('');

      const response = await tenantsAPI.removeLogo();
      setTenant(response.tenant);
      setLogoPreview(null);
      setSuccessMessage('Logo eliminado exitosamente');

      // Refresh tenant in auth context
      await refreshTenant();

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (err: any) {
      console.error('Error removing logo:', err);

      // Handle 401 Unauthorized - redirect to login
      if (err.response?.status === 401) {
        setError('Tu sesión ha expirado. Redirigiendo al login...');
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
        return;
      }

      setError('Error al eliminar el logo');
    } finally{
      setIsUploadingLogo(false);
    }
  };

  // Load user profile
  useEffect(() => {
    if (user) {
      setValueProfile('first_name', user.first_name);
      setValueProfile('last_name', user.last_name);
      setValueProfile('phone', user.phone || '');
      setValueProfile('job_title', user.job_title || '');
      setValueProfile('department', user.department || '');
      setValueProfile('bio', user.bio || '');
      setValueProfile('receive_notifications', user.receive_notifications);

      // Set avatar preview
      if (user.avatar) {
        const apiUrl = getApiUrl();
        const avatarUrl = user.avatar.startsWith('http') ? user.avatar : `${apiUrl}${user.avatar}`;
        setAvatarPreview(avatarUrl);
      }
    }
  }, [user]);

  // Handle profile update
  const onProfileSubmit = async (data: ProfileFormData) => {
    try {
      setIsSavingProfile(true);
      setProfileError('');
      setProfileSuccess('');

      const updateData: ProfileUpdateData = {
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone || undefined,
        job_title: data.job_title || undefined,
        department: data.department || undefined,
        bio: data.bio || undefined,
        receive_notifications: data.receive_notifications,
      };

      await authAPI.updateProfile(updateData);
      await refreshUser();
      setProfileSuccess('Perfil actualizado exitosamente');
      setTimeout(() => setProfileSuccess(''), 5000);
    } catch (err: any) {
      console.error('Error updating profile:', err);
      setProfileError(err.response?.data?.error || 'Error al actualizar el perfil');
    } finally {
      setIsSavingProfile(false);
    }
  };

  // Handle avatar upload
  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setProfileError('Por favor selecciona un archivo de imagen válido');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setProfileError('La imagen debe ser menor a 5MB');
      return;
    }

    try {
      setIsUploadingAvatar(true);
      setProfileError('');
      setProfileSuccess('');

      await authAPI.updateProfile({ avatar: file });
      await refreshUser();

      // Update preview
      const apiUrl = getApiUrl();
      const freshUser = await authAPI.getProfile();
      if (freshUser.avatar) {
        const avatarUrl = freshUser.avatar.startsWith('http')
          ? freshUser.avatar
          : `${apiUrl}${freshUser.avatar}`;
        setAvatarPreview(avatarUrl);
      }

      setProfileSuccess('Avatar actualizado exitosamente');
      setTimeout(() => setProfileSuccess(''), 5000);
    } catch (err: any) {
      console.error('Error uploading avatar:', err);
      setProfileError('Error al subir el avatar');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  // Handle avatar remove
  const handleAvatarRemove = async () => {
    if (!confirm('¿Estás seguro de que deseas eliminar tu foto de perfil?')) {
      return;
    }

    try {
      setIsUploadingAvatar(true);
      setProfileError('');
      setProfileSuccess('');

      await authAPI.updateProfile({ avatar: null });
      await refreshUser();
      setAvatarPreview(null);
      setProfileSuccess('Foto de perfil eliminada exitosamente');
      setTimeout(() => setProfileSuccess(''), 5000);
    } catch (err: any) {
      console.error('Error removing avatar:', err);
      setProfileError('Error al eliminar la foto de perfil');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  // Handle password change
  const onPasswordSubmit = async (data: PasswordChangeFormData) => {
    try {
      setIsChangingPassword(true);
      setPasswordError('');
      setPasswordSuccess('');

      await authAPI.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
        confirm_password: data.confirm_password,
      });

      setPasswordSuccess('Contraseña cambiada exitosamente');
      resetPassword();
      setTimeout(() => setPasswordSuccess(''), 5000);
    } catch (err: any) {
      console.error('Error changing password:', err);
      if (err.response?.data) {
        const errorData = err.response.data;
        if (errorData.current_password) {
          setPasswordError(`Contraseña actual: ${errorData.current_password[0]}`);
        } else if (errorData.new_password) {
          setPasswordError(`Nueva contraseña: ${errorData.new_password[0]}`);
        } else if (errorData.error) {
          setPasswordError(errorData.error);
        } else {
          setPasswordError('Error al cambiar la contraseña');
        }
      } else {
        setPasswordError('Error al conectar con el servidor');
      }
    } finally {
      setIsChangingPassword(false);
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
    <div className="p-8">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/settings"
            className="inline-flex items-center text-sm text-slate-600 hover:text-slate-900 mb-2"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Configuración
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                <Building2 className="h-6 w-6 text-blue-600" />
                Información del Negocio
              </h1>
              <p className="text-sm text-slate-600 mt-1">
                Administra la información y configuración de tu organización
              </p>
            </div>
          </div>
        </div>

        {/* Success Message */}
        {successMessage && (
          <Alert className="mb-6 bg-green-50 border-green-200 shadow-sm">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              {successMessage}
            </AlertDescription>
          </Alert>
        )}

        {/* Error Message */}
        {error && (
          <Alert variant="destructive" className="mb-6 shadow-sm">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
            <p className="text-gray-600">Cargando configuración...</p>
          </div>
        ) : (
          <Tabs defaultValue="profile" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-6 bg-slate-100">
              <TabsTrigger value="profile" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Perfil</TabsTrigger>
              <TabsTrigger value="security" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Seguridad</TabsTrigger>
              <TabsTrigger value="business" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Negocio</TabsTrigger>
              <TabsTrigger value="appearance" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Apariencia</TabsTrigger>
            </TabsList>

            {/* PROFILE TAB */}
            <TabsContent value="profile">
              <form onSubmit={handleSubmitProfile(onProfileSubmit)}>
                <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-slate-900">
                    <UserIcon className="h-5 w-5 text-blue-600" />
                    Perfil Personal
                  </CardTitle>
                  <CardDescription className="text-slate-600">
                    Tu información personal y preferencias
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Profile Success/Error Messages */}
                  {profileSuccess && (
                    <Alert className="bg-green-50 border-green-200">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <AlertDescription className="text-green-800">
                        {profileSuccess}
                      </AlertDescription>
                    </Alert>
                  )}
                  {profileError && (
                    <Alert variant="destructive">
                      <AlertDescription>{profileError}</AlertDescription>
                    </Alert>
                  )}

                  {/* Avatar Section */}
                  <div className="flex items-start gap-6">
                    <div className="flex-shrink-0">
                      {avatarPreview ? (
                        <div className="relative">
                          <img
                            src={avatarPreview}
                            alt="Avatar"
                            className="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
                          />
                          {!isUploadingAvatar && (
                            <Button
                              type="button"
                              variant="destructive"
                              size="sm"
                              className="absolute -top-1 -right-1 h-6 w-6 rounded-full p-0"
                              onClick={handleAvatarRemove}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      ) : (
                        <div className="w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center border-2 border-gray-200">
                          <UserIcon className="h-12 w-12 text-gray-400" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 space-y-2">
                      <Label>Foto de Perfil</Label>
                      <div className="flex gap-2">
                        <label htmlFor="avatar-upload">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={isUploadingAvatar}
                            onClick={() => document.getElementById('avatar-upload')?.click()}
                          >
                            {isUploadingAvatar ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Subiendo...
                              </>
                            ) : (
                              <>
                                <Upload className="mr-2 h-4 w-4" />
                                {avatarPreview ? 'Cambiar Foto' : 'Subir Foto'}
                              </>
                            )}
                          </Button>
                        </label>
                        <input
                          id="avatar-upload"
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handleAvatarUpload}
                          disabled={isUploadingAvatar}
                        />
                      </div>
                      <p className="text-xs text-gray-500">
                        PNG, JPG o GIF. Máximo 5MB.
                      </p>
                    </div>
                  </div>

                  {/* Name Fields */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="first_name">
                        Nombre <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="first_name"
                        {...registerProfile('first_name')}
                        disabled={isSavingProfile}
                      />
                      {profileErrors.first_name && (
                        <p className="text-sm text-red-500">{profileErrors.first_name.message}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="last_name">
                        Apellido <span className="text-red-500">*</span>
                      </Label>
                      <Input
                        id="last_name"
                        {...registerProfile('last_name')}
                        disabled={isSavingProfile}
                      />
                      {profileErrors.last_name && (
                        <p className="text-sm text-red-500">{profileErrors.last_name.message}</p>
                      )}
                    </div>
                  </div>

                  {/* Email (read-only) */}
                  <div className="space-y-2">
                    <Label htmlFor="profile_email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <Input
                        id="profile_email"
                        type="email"
                        value={user?.email || ''}
                        className="pl-10 bg-gray-50"
                        disabled
                      />
                    </div>
                    <p className="text-xs text-gray-500">
                      El email no puede ser modificado
                    </p>
                  </div>

                  {/* Phone & Job Info */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="profile_phone">Teléfono</Label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          id="profile_phone"
                          type="tel"
                          placeholder="+58 212 1234567"
                          className="pl-10"
                          {...registerProfile('phone')}
                          disabled={isSavingProfile}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="job_title">Cargo / Puesto</Label>
                      <div className="relative">
                        <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <Input
                          id="job_title"
                          placeholder="Ej: Gerente General"
                          className="pl-10"
                          {...registerProfile('job_title')}
                          disabled={isSavingProfile}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Department & Bio */}
                  <div className="space-y-2">
                    <Label htmlFor="department">Departamento</Label>
                    <Input
                      id="department"
                      placeholder="Ej: Administración"
                      {...registerProfile('department')}
                      disabled={isSavingProfile}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="bio">Biografía</Label>
                    <Textarea
                      id="bio"
                      placeholder="Cuéntanos sobre ti..."
                      rows={3}
                      {...registerProfile('bio')}
                      disabled={isSavingProfile}
                    />
                  </div>

                  {/* Notifications */}
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="receive_notifications"
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      {...registerProfile('receive_notifications')}
                      disabled={isSavingProfile}
                    />
                    <Label htmlFor="receive_notifications" className="flex items-center gap-2 cursor-pointer">
                      <Bell className="h-4 w-4 text-gray-600" />
                      Recibir notificaciones por email
                    </Label>
                  </div>

                  {/* Profile Actions */}
                  <div className="flex justify-end">
                    <Button type="submit" disabled={isSavingProfile} className="bg-blue-600 hover:bg-blue-700">
                      {isSavingProfile && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      <Save className="mr-2 h-4 w-4" />
                      Guardar Perfil
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </form>
            </TabsContent>

            {/* SECURITY TAB */}
            <TabsContent value="security">
            <form onSubmit={handleSubmitPassword(onPasswordSubmit)}>
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-slate-900">
                    <Lock className="h-5 w-5 text-blue-600" />
                    Cambiar Contraseña
                  </CardTitle>
                  <CardDescription className="text-slate-600">
                    Actualiza tu contraseña para mayor seguridad
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Password Success/Error Messages */}
                  {passwordSuccess && (
                    <Alert className="bg-green-50 border-green-200">
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                      <AlertDescription className="text-green-800">
                        {passwordSuccess}
                      </AlertDescription>
                    </Alert>
                  )}
                  {passwordError && (
                    <Alert variant="destructive">
                      <AlertDescription>{passwordError}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="current_password">Contraseña Actual</Label>
                    <Input
                      id="current_password"
                      type="password"
                      {...registerPassword('current_password')}
                      disabled={isChangingPassword}
                    />
                    {passwordErrors.current_password && (
                      <p className="text-sm text-red-500">{passwordErrors.current_password.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="new_password">Nueva Contraseña</Label>
                    <Input
                      id="new_password"
                      type="password"
                      {...registerPassword('new_password')}
                      disabled={isChangingPassword}
                    />
                    {passwordErrors.new_password && (
                      <p className="text-sm text-red-500">{passwordErrors.new_password.message}</p>
                    )}
                    <p className="text-xs text-gray-500">
                      Mínimo 8 caracteres
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm_password">Confirmar Nueva Contraseña</Label>
                    <Input
                      id="confirm_password"
                      type="password"
                      {...registerPassword('confirm_password')}
                      disabled={isChangingPassword}
                    />
                    {passwordErrors.confirm_password && (
                      <p className="text-sm text-red-500">{passwordErrors.confirm_password.message}</p>
                    )}
                  </div>

                  <div className="flex justify-end">
                    <Button type="submit" disabled={isChangingPassword} className="bg-blue-600 hover:bg-blue-700">
                      {isChangingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      <Lock className="mr-2 h-4 w-4" />
                      Cambiar Contraseña
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </form>
            </TabsContent>

            {/* BUSINESS TAB */}
            <TabsContent value="business">
            <form onSubmit={handleSubmit(onSubmit)}>
              {/* Business Information */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-slate-900">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    Información del Negocio
                  </CardTitle>
                  <CardDescription className="text-slate-600">
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

                  {/* Currency Settings */}
                  <div className="pt-4 border-t">
                    <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                      <DollarSign className="h-4 w-4 text-green-600" />
                      Configuración de Moneda
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="default_currency">Moneda Predeterminada</Label>
                        <select
                          id="default_currency"
                          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          {...register('default_currency')}
                          disabled={isSaving}
                        >
                          <option value="USD">US Dollar ($)</option>
                          <option value="DOP">Dominican Peso (RD$)</option>
                          <option value="EUR">Euro (€)</option>
                          <option value="GBP">British Pound (£)</option>
                        </select>
                        {errors.default_currency && (
                          <p className="text-sm text-red-500">{errors.default_currency.message}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="currency_symbol">Símbolo de Moneda</Label>
                        <Input
                          id="currency_symbol"
                          placeholder="$"
                          maxLength={10}
                          {...register('currency_symbol')}
                          disabled={isSaving}
                        />
                        {errors.currency_symbol && (
                          <p className="text-sm text-red-500">{errors.currency_symbol.message}</p>
                        )}
                        <p className="text-xs text-gray-500">
                          Ej: $, RD$, €, £
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Address Information */}
              <Card className="border-slate-200 shadow-sm mt-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-slate-900">
                    <MapPin className="h-5 w-5 text-blue-600" />
                    Dirección
                  </CardTitle>
                  <CardDescription className="text-slate-600">
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

              {/* Subscription Info (Read-only) */}
              {tenant && (
                <Card className="border-slate-200 shadow-sm mt-6">
                  <CardHeader>
                    <CardTitle className="text-slate-900">Información de Suscripción</CardTitle>
                    <CardDescription className="text-slate-600">
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
              <div className="flex justify-end gap-3 mt-6">
                <Link href="/dashboard">
                  <Button type="button" variant="outline" disabled={isSaving}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isSaving} className="bg-blue-600 hover:bg-blue-700">
                  {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Guardar Información del Negocio
                </Button>
              </div>
            </form>
            </TabsContent>

            {/* APPEARANCE TAB */}
            <TabsContent value="appearance">
            <form onSubmit={handleSubmit(onSubmit)}>
              {/* Branding */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-slate-900">
                    <Palette className="h-5 w-5 text-blue-600" />
                    Personalización
                  </CardTitle>
                  <CardDescription className="text-slate-600">
                    Personaliza la apariencia de tu tenant
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Logo Section */}
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <ImageIcon className="h-4 w-4" />
                      Logo de la Empresa
                    </Label>

                    {/* Logo Preview */}
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center gap-4">
                      {logoPreview ? (
                        <div className="relative">
                          <img
                            src={logoPreview}
                            alt="Logo"
                            className="max-w-xs max-h-32 object-contain"
                          />
                          {!isUploadingLogo && (
                            <Button
                              type="button"
                              variant="destructive"
                              size="sm"
                              className="absolute -top-2 -right-2"
                              onClick={handleLogoRemove}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center gap-2 text-gray-400">
                          <ImageIcon className="h-12 w-12" />
                          <p className="text-sm">No hay logo</p>
                        </div>
                      )}

                      {/* Upload Button */}
                      <div className="flex gap-2">
                        <label htmlFor="logo-upload">
                          <Button
                            type="button"
                            variant="outline"
                            disabled={isUploadingLogo}
                            onClick={() => document.getElementById('logo-upload')?.click()}
                          >
                            {isUploadingLogo ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Subiendo...
                              </>
                            ) : (
                              <>
                                <Upload className="mr-2 h-4 w-4" />
                                {logoPreview ? 'Cambiar Logo' : 'Subir Logo'}
                              </>
                            )}
                          </Button>
                        </label>
                        <input
                          id="logo-upload"
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={handleLogoUpload}
                          disabled={isUploadingLogo}
                        />
                      </div>

                      <p className="text-xs text-gray-500 text-center">
                        PNG, JPG o GIF. Máximo 5MB.
                      </p>
                    </div>
                  </div>

                  {/* Color Section */}
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

              {/* Actions */}
              <div className="flex justify-end gap-3 mt-4">
                <Link href="/dashboard">
                  <Button type="button" variant="outline" disabled={isSaving || isUploadingLogo}>
                    Cancelar
                  </Button>
                </Link>
                <Button type="submit" disabled={isSaving || isUploadingLogo} className="bg-blue-600 hover:bg-blue-700">
                  {(isSaving || isUploadingLogo) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  <Save className="mr-2 h-4 w-4" />
                  Guardar Apariencia
                </Button>
              </div>
            </form>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
