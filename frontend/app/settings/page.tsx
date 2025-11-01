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
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/dashboard"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
        >
          <ChevronRight className="h-4 w-4 mr-1 rotate-180" />
          Volver al Dashboard
        </Link>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <SettingsIcon className="h-8 w-8" />
          Configuración
        </h1>
        <p className="text-muted-foreground mt-2">
          Administra la configuración de tu cuenta y organización
        </p>
      </div>

      {/* Settings Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {settingsSections.map((section, index) => (
          <Link key={index} href={section.href} className="group">
            <Card className="h-full transition-all hover:shadow-lg hover:border-primary cursor-pointer">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-muted group-hover:bg-primary/10 transition-colors">
                      {section.icon}
                    </div>
                    <div>
                      <CardTitle className="text-lg flex items-center gap-2">
                        {section.title}
                        {section.badge && (
                          <span className="text-xs font-normal bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            {section.badge}
                          </span>
                        )}
                      </CardTitle>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <CardDescription className="mt-2">{section.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Info */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <FileText className="h-4 w-4" />
            ¿Necesitas ayuda?
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <p>
            Si tienes problemas con la configuración o necesitas asistencia,{' '}
            <Link href="/support" className="text-primary hover:underline">
              contacta a nuestro equipo de soporte
            </Link>
            .
          </p>
        </CardContent>
      </Card>

      {/* User Info Footer */}
      {user && (
        <div className="text-xs text-muted-foreground text-center pt-4 border-t">
          Sesión iniciada como <span className="font-medium">{user.email}</span>
          {user.role && (
            <span className="ml-2">
              • Rol: <span className="font-medium capitalize">{user.role}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}