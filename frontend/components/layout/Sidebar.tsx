'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { getApiUrl } from '@/lib/api/client';
import {
  LayoutDashboard,
  FileText,
  Users,
  Phone,
  DollarSign,
  UsersRound,
  Settings,
  LogOut,
  ChevronRight,
  Building2,
  FileSignature,
  ScrollText,
} from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, tenant, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const isActive = (path: string) => {
    return pathname === path || pathname.startsWith(path + '/');
  };

  const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/loans', icon: FileText, label: 'Préstamos' },
    { href: '/contracts', icon: FileSignature, label: 'Contratos' },
    { href: '/contract-templates', icon: ScrollText, label: 'Plantillas' },
    { href: '/customers', icon: Users, label: 'Clientes' },
    { href: '/collections', icon: Phone, label: 'Cobranza' },
    { href: '/payments', icon: DollarSign, label: 'Pagos' },
  ];

  const adminNavItems = [
    { href: '/users', icon: UsersRound, label: 'Equipo' },
    { href: '/settings', icon: Settings, label: 'Configuración' },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0">
      {/* Logo & Tenant */}
      <div className="p-6 border-b border-slate-800">
        {tenant?.logo ? (
          <img
            src={
              tenant.logo.startsWith('http')
                ? tenant.logo
                : `${getApiUrl()}${tenant.logo}`
            }
            alt={tenant.business_name}
            className="h-8 w-auto object-contain mb-3 brightness-0 invert"
          />
        ) : (
          <Image
            src="/logo.svg"
            alt="CrediFlux"
            width={140}
            height={35}
            className="h-8 w-auto mb-3 brightness-0 invert"
            priority
          />
        )}
        {tenant && (
          <div className="mt-3 pt-3 border-t border-slate-800">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Building2 className="h-3 w-3" />
              <span className="truncate">{tenant.business_name}</span>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-6 overflow-y-auto">
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                  ${active
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                {active && <ChevronRight className="h-4 w-4" />}
              </Link>
            );
          })}
        </div>

        {/* Admin Section */}
        {(user?.is_tenant_owner || user?.role === 'admin') && (
          <div className="mt-8">
            <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Administración
            </p>
            <div className="space-y-1">
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`
                      flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                      ${active
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </div>
                    {active && <ChevronRight className="h-4 w-4" />}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-slate-800">
        <div className="flex items-center gap-3 mb-3">
          <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-sm font-semibold">
            {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {user?.full_name}
            </p>
            <p className="text-xs text-slate-400 capitalize truncate">
              {user?.role.replace('_', ' ')}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-all"
        >
          <LogOut className="h-4 w-4" />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
}
