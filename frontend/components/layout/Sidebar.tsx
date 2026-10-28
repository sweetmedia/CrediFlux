import { useEffect, useState } from 'react';
import Link from '@/lib/navigation/link';
import { usePathname, useRouter } from '@/lib/navigation';
import Image from '@/components/ui/image';
import { useAuth } from '@/lib/contexts/AuthContext';
import { getApiUrl } from '@/lib/api/client';
import { GlobalSearch } from '@/components/search';
import { ChevronDown, LogOut, Search } from 'lucide-react';
import { activeHref, NAV_GROUPS, visibleNavGroups } from './nav';
import { useCan } from '@/lib/permissions';

interface SidebarProps {
  /** En móvil es un cajón: cerrado sale del orden de tabulación (inert). */
  drawer?: boolean;
  isOpen?: boolean;
  onClose?: () => void;
}

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  manager: 'Gerente',
  loan_officer: 'Oficial de crédito',
  collector: 'Cobrador',
  collection_supervisor: 'Supervisor de cobros',
  accountant: 'Contador',
  cashier: 'Cajero',
  viewer: 'Solo lectura',
};

const COLLAPSED_KEY = 'cf-nav-collapsed';

function readCollapsed(): Record<string, boolean> {
  try {
    return JSON.parse(window.localStorage.getItem(COLLAPSED_KEY) ?? '{}');
  } catch {
    return {};
  }
}

export function Sidebar({ drawer = false, isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, tenant, logout } = useAuth();
  // URL firmada del logo que falló al cargar (p. ej. expirada): se usa el logo por defecto.
  const [failedLogo, setFailedLogo] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(readCollapsed);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      } else if (e.key === 'Escape' && drawer && isOpen) {
        onClose?.();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawer, isOpen, onClose]);

  const can = useCan();
  const groups = visibleNavGroups(NAV_GROUPS, can);
  const current = activeHref(pathname, groups.flatMap((g) => g.items.map((i) => i.href)));

  const isCollapsed = (id: string, byDefault?: boolean) => {
    // El grupo con la página actual siempre se ve.
    if (groups.find((g) => g.id === id)?.items.some((i) => i.href === current)) return false;
    return collapsed[id] ?? !!byDefault;
  };

  const toggle = (id: string, byDefault?: boolean) => {
    const next = { ...collapsed, [id]: !isCollapsed(id, byDefault) };
    setCollapsed(next);
    try {
      window.localStorage.setItem(COLLAPSED_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const initials = `${user?.first_name?.charAt(0) ?? ''}${user?.last_name?.charAt(0) ?? ''}`;

  return (
    <div className="cf-root">
      <aside
        id="app-sidebar"
        aria-label="Barra lateral"
        inert={drawer && !isOpen}
        className={`cf-shell-sidebar sidebar fixed left-0 top-0 z-50 flex h-[100dvh] w-[240px] flex-col transition-transform duration-slow ease-spring ${
          drawer && !isOpen ? '-translate-x-full' : 'translate-x-0'
        }`}
      >
        <div className="border-b border-white/[0.08] px-5 pb-4 pt-5">
          <div className="mb-4">
            {tenant?.logo && failedLogo !== tenant.logo ? (
              <img
                src={tenant.logo.startsWith('http') ? tenant.logo : `${getApiUrl()}${tenant.logo}`}
                alt={tenant.business_name}
                className="h-[22px] w-auto object-contain brightness-0 invert"
                onError={() => setFailedLogo(tenant.logo ?? null)}
              />
            ) : (
              <Image src="/logo-white.svg" alt="CrediFlux" width={110} height={22} className="h-[22px] w-auto" priority />
            )}
          </div>
          {tenant && (
            <div>
              <div className="font-display text-[14px] font-medium leading-[1.25] text-white">{tenant.business_name}</div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-widest text-white/40">{tenant.name}</div>
            </div>
          )}
        </div>

        <button type="button" className="sidebar-search" onClick={() => setIsSearchOpen(true)}>
          <span className="flex items-center gap-2">
            <Search className="h-[13px] w-[13px]" aria-hidden="true" />
            <span>Buscar</span>
          </span>
          <span className="kbd">⌘K</span>
        </button>
        <GlobalSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />

        <nav aria-label="Navegación principal" className="scrollbar-dark flex-1 overflow-y-auto px-3 py-5">
          {groups.map((g, gi) => {
            const closed = g.collapsible && isCollapsed(g.id, g.collapsedByDefault);
            const listId = `nav-group-${g.id}`;
            return (
              <div key={g.id} className={gi < groups.length - 1 ? 'mb-6' : undefined}>
                {g.collapsible ? (
                  <button
                    type="button"
                    className="nav-group-header"
                    aria-expanded={!closed}
                    aria-controls={listId}
                    onClick={() => toggle(g.id, g.collapsedByDefault)}
                  >
                    <span>{g.label}</span>
                    <ChevronDown className="nav-group-chevron h-2.5 w-2.5" strokeWidth={2.5} aria-hidden="true" />
                  </button>
                ) : (
                  <div className="nav-group-header">
                    <span>{g.label}</span>
                  </div>
                )}
                {!closed && (
                  <div id={listId} className="mt-1.5 space-y-[1px]">
                    {g.items.map(({ href, label, icon: Icon }) => (
                      <Link
                        key={href}
                        href={href}
                        className="nav-item"
                        aria-current={href === current ? 'page' : undefined}
                        onClick={drawer ? onClose : undefined}
                      >
                        <Icon className="h-[15px] w-[15px]" strokeWidth={1.75} aria-hidden="true" />
                        <span>{label}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="border-t border-white/[0.08] px-3 py-3">
          <div className="flex items-center gap-3 rounded px-2 py-1.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sage-500 font-mono text-[11px] font-medium tabular-nums text-white">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate font-display text-[13px] font-medium leading-tight text-white">{user?.full_name}</div>
              <div className="mt-0.5 truncate font-mono text-[9px] uppercase tracking-widest text-white/45">
                {user?.is_tenant_owner ? 'Dueño' : user?.role ? (ROLE_LABELS[user.role] ?? user.role) : ''}
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded p-1.5 text-white/35 transition-colors hover:text-white/90"
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
