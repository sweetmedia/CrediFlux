'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import {
  DollarSign,
  LogOut,
  User,
  Building2,
  Settings,
} from 'lucide-react';

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, tenant, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const isActivePath = (path: string) => {
    return pathname === path;
  };

  const navLinkClass = (path: string) => {
    return isActivePath(path)
      ? "text-sm font-medium text-blue-600 border-b-2 border-blue-600 pb-1"
      : "text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors";
  };

  return (
    <header className="bg-white border-b shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {tenant?.logo ? (
              <img
                src={
                  tenant.logo.startsWith('http')
                    ? tenant.logo
                    : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${tenant.logo}`
                }
                alt={tenant.business_name}
                className="h-10 w-auto object-contain"
              />
            ) : (
              <Image
                src="/logo.svg"
                alt="CrediFlux"
                width={160}
                height={40}
                className="h-10 w-auto"
                priority
              />
            )}
            {tenant && (
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {tenant.business_name}
                </h1>
                <p className="text-sm text-gray-600 flex items-center gap-1">
                  <Building2 className="h-3 w-3" />
                  {tenant.schema_name}
                </p>
              </div>
            )}
          </div>

          <nav className="hidden md:flex items-center space-x-6">
            <Link href="/dashboard" className={navLinkClass('/dashboard')}>
              Dashboard
            </Link>
            <Link href="/loans" className={navLinkClass('/loans')}>
              Préstamos
            </Link>
            <Link href="/customers" className={navLinkClass('/customers')}>
              Clientes
            </Link>
            <Link href="/collections" className={navLinkClass('/collections')}>
              Cobranza
            </Link>
            <Link href="/payments" className={navLinkClass('/payments')}>
              Pagos
            </Link>
            {(user?.is_tenant_owner || user?.role === 'admin') && (
              <Link href="/users" className={navLinkClass('/users')}>
                Equipo
              </Link>
            )}
            {(user?.is_tenant_owner || user?.role === 'admin') && (
              <Link
                href="/settings"
                className={`${navLinkClass('/settings')} flex items-center gap-1`}
              >
                <Settings className="h-3 w-3" />
                Configuración
              </Link>
            )}
          </nav>

          <div className="flex items-center space-x-4">
            <div className="hidden md:block text-right">
              <p className="text-sm font-medium text-gray-900 flex items-center gap-1 justify-end">
                <User className="h-3 w-3" />
                {user?.full_name}
              </p>
              <p className="text-xs text-gray-600 capitalize">
                {user?.role.replace('_', ' ')}
              </p>
            </div>
            <Button onClick={handleLogout} variant="outline" size="sm">
              <LogOut className="h-4 w-4 mr-2" />
              Salir
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
