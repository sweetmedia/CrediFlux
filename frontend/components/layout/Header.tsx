import { useState } from 'react';
import { Bell, Building, ChevronDown, Search } from 'lucide-react';
import Link from '@/lib/navigation/link';
import { usePathname } from '@/lib/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { GlobalSearch } from '@/components/search';
import { ThemeSwitch } from '@/lib/design-system/ThemeSwitch';
import { sectionFor } from './nav';
import { UserMenu } from './UserMenu';

/** Barra superior de escritorio (ShellV1): migas, empresa, búsqueda, tema (D3) y usuario. */
export function Header() {
  const pathname = usePathname();
  const { tenant } = useAuth();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const { group, item } = sectionFor(pathname);

  return (
    <header className="cf-root sticky top-0 z-30 border-b border-forest-900/10 bg-cream/85 backdrop-blur">
      <div className="flex h-14 items-center gap-3 pl-8 pr-6">
        <nav aria-label="Migas" className="flex min-w-0 flex-1 items-center gap-2 text-[12px] text-sage-500">
          <Link href="/dashboard" className="transition-colors hover:text-forest-900">
            Inicio
          </Link>
          {group && (
            <>
              <span className="text-[9px] leading-none text-sun-500" aria-hidden="true">●</span>
              <span>{group}</span>
            </>
          )}
          {item && item !== group && (
            <>
              <span aria-hidden="true">/</span>
              <span className="truncate text-forest-900">{item}</span>
            </>
          )}
        </nav>
        <div className="flex items-center gap-1">
          {tenant && (
            <span className="util-btn gap-1.5 px-2.5 text-[12px]">
              <Building className="h-[13px] w-[13px]" aria-hidden="true" />
              <span className="font-mono text-[10px] uppercase tracking-widest">{tenant.name}</span>
              <ChevronDown className="h-2.5 w-2.5" aria-hidden="true" />
            </span>
          )}
          <button type="button" className="util-btn util-btn--icon" aria-label="Búsqueda global" onClick={() => setIsSearchOpen(true)}>
            <Search className="h-[15px] w-[15px]" aria-hidden="true" />
          </button>
          <Link href="/collections/reminders" className="util-btn util-btn--icon" aria-label="Recordatorios">
            <Bell className="h-[15px] w-[15px]" aria-hidden="true" />
          </Link>
          <ThemeSwitch className="mx-1.5" />
          <UserMenu />
        </div>
      </div>
      <GlobalSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </header>
  );
}
