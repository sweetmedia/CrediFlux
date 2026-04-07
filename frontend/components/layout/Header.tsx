'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { getApiUrl } from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import {
  LogOut,
  User,
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
    return pathname === path || pathname.startsWith(path + '/');
  };

  const navLinkClass = (path: string) => {
    return isActivePath(path)
      ? "text-sm font-medium text-gray-900 pb-6"
      : "text-sm text-gray-500 hover:text-gray-900 transition-colors pb-6";
  };

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-20">
          {/* Logo & Tenant */}
          <div className="flex items-center gap-8">
            {tenant?.logo ? (
              <img
                src={
                  tenant.logo.startsWith('http')
                    ? tenant.logo
                    : `${getApiUrl()}${tenant.logo}`
                }
                alt={tenant.business_name}
                className="h-8 w-auto object-contain"
              />
            ) : (
              <Image
                src="/logo.svg"
                alt="CrediFlux"
                width={120}
                height={30}
                className="h-8 w-auto"
                priority
              />
            )}
            {tenant && (
              <div className="border-l border-gray-200 pl-8">
                <h1 className="text-sm font-medium text-gray-900">
                  {tenant.business_name}
                </h1>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-8">
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
              <Link href="/settings" className={navLinkClass('/settings')}>
                Configuración
              </Link>
            )}
          </nav>

          {/* User & Logout */}
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-3 text-right">
              <div className="h-8 w-8 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-medium">
                {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500 capitalize">
                  {user?.role.replace('_', ' ')}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
