'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { getApiUrl } from '@/lib/api/client';
import { GlobalSearch } from '@/components/search';
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
  ChevronDown,
  Building2,
  FileSignature,
  ScrollText,
  MessageSquare,
  CheckSquare,
  ClipboardList,
  Search,
  Receipt,
  Shield,
  Hash,
  Calculator,
} from 'lucide-react';

interface NavItem {
  href: string;
  icon: any;
  label: string;
  subItems?: { href: string; icon: any; label: string }[];
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, tenant, logout } = useAuth();
  const [expandedItems, setExpandedItems] = useState<string[]>(['contracts']);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

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

  const toggleExpanded = (href: string) => {
    setExpandedItems((prev) =>
      prev.includes(href) ? prev.filter((item) => item !== href) : [...prev, href]
    );
  };

  const navItems: NavItem[] = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/loans', icon: FileText, label: 'Préstamos' },
    { href: '/calculator', icon: Calculator, label: 'Calculadora' },
    {
      href: 'contracts',
      icon: FileSignature,
      label: 'Contratos',
      subItems: [
        { href: '/contracts', icon: FileSignature, label: 'Lista de Contratos' },
        { href: '/contract-templates', icon: ScrollText, label: 'Plantillas' },
      ],
    },
    { href: '/customers', icon: Users, label: 'Clientes' },
    { href: '/collections', icon: Phone, label: 'Cobranza' },
    { href: '/payments', icon: DollarSign, label: 'Pagos' },
    {
      href: 'billing',
      icon: Receipt,
      label: 'Facturación',
      subItems: [
        { href: '/billing', icon: Receipt, label: 'Facturas e-CF' },
        { href: '/billing/sequences', icon: Hash, label: 'Secuencias e-NCF' },
        { href: '/billing/certificates', icon: Shield, label: 'Certificados' },
      ],
    },
    { href: '/communications', icon: MessageSquare, label: 'Comunicaciones' },
    { href: '/tasks', icon: CheckSquare, label: 'Tareas' },
  ];

  const adminNavItems = [
    { href: '/users', icon: UsersRound, label: 'Equipo' },
    { href: '/audit', icon: ClipboardList, label: 'Auditoria' },
    { href: '/settings', icon: Settings, label: 'Configuracion' },
  ];

  const isAnySubItemActive = (subItems?: { href: string }[]) => {
    if (!subItems) return false;
    return subItems.some((subItem) => isActive(subItem.href));
  };

  const initials = `${user?.first_name?.charAt(0) ?? ''}${user?.last_name?.charAt(0) ?? ''}`;

  return (
    <aside
      className="flex flex-col h-screen fixed left-0 top-0 z-40"
      style={{ width: 240, backgroundColor: '#163300' }}
    >
      {/* Logo & Tenant */}
      <div className="px-5 py-5 border-b border-white/10">
        {tenant?.logo ? (
          <img
            src={
              tenant.logo.startsWith('http')
                ? tenant.logo
                : `${getApiUrl()}${tenant.logo}`
            }
            alt={tenant.business_name}
            className="h-7 w-auto object-contain mb-3 brightness-0 invert"
          />
        ) : (
          <Image
            src="/logo.svg"
            alt="CrediFlux"
            width={130}
            height={32}
            className="h-7 w-auto mb-3 brightness-0 invert"
            priority
          />
        )}
        {tenant && (
          <div className="flex items-center gap-1.5 text-xs text-white/40 mt-2">
            <Building2 className="h-3 w-3 shrink-0" />
            <span className="truncate">{tenant.business_name}</span>
          </div>
        )}

        {/* Search */}
        <button
          onClick={() => setIsSearchOpen(true)}
          className="mt-4 w-full flex items-center justify-between px-3 py-2 rounded-md text-xs text-white/50 bg-white/5 hover:bg-white/10 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5" />
            <span>Buscar...</span>
          </div>
          <kbd className="px-1.5 py-0.5 bg-white/10 rounded text-white/40" style={{ fontSize: 10 }}>⌘K</kbd>
        </button>
      </div>

      <GlobalSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <div className="space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const hasSubItems = item.subItems && item.subItems.length > 0;
            const isExpanded = expandedItems.includes(item.href);
            const active = !hasSubItems && isActive(item.href);
            const anySubActive = isAnySubItemActive(item.subItems);

            return (
              <div key={item.href}>
                {hasSubItems ? (
                  <>
                    <button
                      onClick={() => toggleExpanded(item.href)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors ${
                        anySubActive
                          ? 'text-white bg-white/10'
                          : 'text-white/60 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4 shrink-0" />
                        <span>{item.label}</span>
                      </div>
                      <ChevronDown
                        className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </button>

                    {isExpanded && (
                      <div className="mt-0.5 ml-3 pl-3 border-l border-white/10 space-y-0.5">
                        {item.subItems?.map((subItem) => {
                          const SubIcon = subItem.icon;
                          const subActive = isActive(subItem.href);
                          return (
                            <Link
                              key={subItem.href}
                              href={subItem.href}
                              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                                subActive
                                  ? 'text-white bg-white/10'
                                  : 'text-white/50 hover:text-white hover:bg-white/5'
                              }`}
                            >
                              <SubIcon className="h-3.5 w-3.5 shrink-0" />
                              <span>{subItem.label}</span>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </>
                ) : (
                  <Link
                    href={item.href}
                    className={`relative flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                      active
                        ? 'text-white bg-white/10'
                        : 'text-white/60 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {active && (
                      <span
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-[#FFE026]"
                      />
                    )}
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                )}
              </div>
            );
          })}
        </div>

        {/* Admin Section */}
        {(user?.is_tenant_owner || user?.role === 'admin') && (
          <div className="mt-6">
            <p className="px-3 mb-1.5 text-[10px] font-semibold text-white/30 uppercase tracking-widest">
              Administración
            </p>
            <div className="space-y-0.5">
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`relative flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                      active
                        ? 'text-white bg-white/10'
                        : 'text-white/60 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-[#FFE026]" />
                    )}
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </nav>

      {/* User Profile */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2 mb-2">
          <div className="h-8 w-8 rounded-full bg-[#738566] flex items-center justify-center text-white text-xs font-semibold shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate leading-tight">
              {user?.full_name}
            </p>
            <p className="text-xs text-white/40 capitalize truncate">
              {user?.role.replace('_', ' ')}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-white/50 hover:text-white hover:bg-white/5 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
}
