import { useState } from 'react';
import { FileText, LayoutDashboard, Menu, MoreHorizontal, Plus, Search, Users } from 'lucide-react';
import Link from '@/lib/navigation/link';
import { usePathname } from '@/lib/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { GlobalSearch } from '@/components/search';
import { activeHref } from './nav';
import { UserMenu } from './UserMenu';

/** Barra superior móvil (ShellMobile): menú, empresa, búsqueda y usuario con el tema dentro (D8). */
export function MobileTopBar({ onMenu }: { onMenu: () => void }) {
  const { tenant } = useAuth();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  return (
    <header className="cf-root m-top">
      <button type="button" className="m-ic" aria-label="Abrir menú" aria-controls="app-sidebar" onClick={onMenu}>
        <Menu className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
      </button>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[14px] font-semibold text-forest-900">{tenant?.business_name}</div>
        <div className="font-mono text-[9px] uppercase tracking-widest text-sage-500">{tenant?.name}</div>
      </div>
      <button type="button" className="m-ic" aria-label="Buscar" onClick={() => setIsSearchOpen(true)}>
        <Search className="h-[19px] w-[19px]" strokeWidth={1.75} aria-hidden="true" />
      </button>
      <UserMenu withTheme compact />
      <GlobalSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </header>
  );
}

const TABS = [
  { href: '/dashboard', label: 'Inicio', icon: LayoutDashboard },
  { href: '/customers', label: 'Clientes', icon: Users },
  { href: '/loans', label: 'Préstamos', icon: FileText },
];

/** Barra inferior: Inicio, Clientes, Cobrar (central), Préstamos, Más. */
export function MobileNav({ onMore }: { onMore: () => void }) {
  const pathname = usePathname();
  const current = activeHref(pathname, [...TABS.map((t) => t.href), '/payments/new']);
  const tab = ({ href, label, icon: Icon }: (typeof TABS)[number]) => (
    <Link key={href} href={href} aria-current={current === href ? 'page' : undefined}>
      <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
      {label}
    </Link>
  );
  return (
    <nav aria-label="Navegación inferior" className="cf-root m-nav">
      {tab(TABS[0])}
      {tab(TABS[1])}
      <Link href="/payments/new" aria-current={current === '/payments/new' ? 'page' : undefined}>
        <span className="m-nav__cta" aria-hidden="true">
          <Plus className="h-[22px] w-[22px]" strokeWidth={2} />
        </span>
        Cobrar
      </Link>
      {tab(TABS[2])}
      <a
        href="#menu"
        aria-controls="app-sidebar"
        onClick={(e) => {
          e.preventDefault();
          onMore();
        }}
      >
        <MoreHorizontal className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
        Más
      </a>
    </nav>
  );
}
