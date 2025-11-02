'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/contexts/AuthContext';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Loader2,
  Building2,
  CreditCard,
  User,
  Lock,
  Bell,
  Palette,
  DollarSign,
  FileText,
  Settings as SettingsIcon,
  ChevronRight,
} from 'lucide-react';

interface SettingsCard {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  badge?: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const settingsSections: SettingsCard[] = [
    {
      title: 'Información del Negocio',
      description: 'Configura la información de tu empresa, logo y personalización',
      icon: <Building2 className="h-6 w-6 text-blue-600" />,
      href: '/settings/general',
    },
    {
      title: 'Configuración de Préstamos',
      description: 'Tasas de interés, montos, plazos, métodos de pago y requisitos',
      icon: <DollarSign className="h-6 w-6 text-green-600" />,
      href: '/settings/loans',
      badge: 'Nuevo',
    },
    {
      title: 'Perfil de Usuario',
      description: 'Actualiza tu información personal y foto de perfil',
      icon: <User className="h-6 w-6 text-purple-600" />,
      href: '/settings/general#profile',
    },
    {
      title: 'Seguridad y Contraseña',
      description: 'Cambia tu contraseña y gestiona la seguridad de tu cuenta',
      icon: <Lock className="h-6 w-6 text-red-600" />,
      href: '/settings/general#security',
    },
    {
      title: 'Notificaciones',
      description: 'Configura tus preferencias de notificaciones y alertas',
      icon: <Bell className="h-6 w-6 text-yellow-600" />,
      href: '/settings/general#notifications',
    },
    {
      title: 'Apariencia',
      description: 'Personaliza los colores y el tema de la aplicación',
      icon: <Palette className="h-6 w-6 text-pink-600" />,
      href: '/settings/general#appearance',
    },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Configuración</h1>
            <p className="text-sm text-slate-600 mt-1">
              Administra la configuración de tu cuenta y organización
            </p>
          </div>
        </div>
      </div>

      {/* Settings Cards Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {settingsSections.map((section, index) => (
          <Link key={index} href={section.href} className="group">
            <Card className="h-full transition-all hover:shadow-lg border-slate-200 cursor-pointer">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-50 group-hover:bg-blue-50 transition-colors">
                      {section.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2 text-slate-900">
                        {section.title}
                        {section.badge && (
                          <span className="text-xs font-normal bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            {section.badge}
                          </span>
                        )}
                      </CardTitle>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-blue-600 transition-colors" />
                </div>
                <CardDescription className="mt-2 text-slate-600">{section.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Info */}
      <Card className="border-slate-200 border-dashed mt-6">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2 text-slate-900">
            <FileText className="h-4 w-4" />
            ¿Necesitas ayuda?
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          <p>
            Si tienes problemas con la configuración o necesitas asistencia,{' '}
            <Link href="/support" className="text-blue-600 hover:underline">
              contacta a nuestro equipo de soporte
            </Link>
            .
          </p>
        </CardContent>
      </Card>

      {/* User Info Footer */}
      {user && (
        <div className="text-xs text-slate-500 text-center pt-4 border-t border-slate-200 mt-6">
          Sesión iniciada como <span className="font-medium text-slate-900">{user.email}</span>
          {user.role && (
            <span className="ml-2">
              • Rol: <span className="font-medium capitalize text-slate-900">{user.role}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}