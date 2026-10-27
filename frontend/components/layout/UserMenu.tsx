import { useEffect, useRef, useState } from 'react';
import { LogOut } from 'lucide-react';
import { useRouter } from '@/lib/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';
import { ThemeSwitch } from '@/lib/design-system/ThemeSwitch';
import { cn } from '@/lib/utils';
import { ROLE_LABELS } from './Sidebar';

interface UserMenuProps {
  /** D8: en móvil el switch de tema vive aquí; en escritorio está en la barra superior. */
  withTheme?: boolean;
  /** Botón compacto de la barra móvil (44 px). */
  compact?: boolean;
}

export function UserMenu({ withTheme = false, compact = false }: UserMenuProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const initials = `${user?.first_name?.charAt(0) ?? ''}${user?.last_name?.charAt(0) ?? ''}`;
  const role = user?.is_tenant_owner ? 'Dueño' : user?.role ? (ROLE_LABELS[user.role] ?? user.role) : '';

  const handleLogout = async () => {
    setOpen(false);
    try {
      await logout();
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Menú de usuario"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={cn(compact ? 'm-ic' : 'ml-1 flex h-8 items-center gap-2 rounded pl-1 pr-2 transition-colors hover:bg-forest-900/[0.04]')}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-sage-500 font-mono text-[10px] font-medium tabular-nums text-white">
          {initials}
        </span>
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Menú de usuario"
          className="absolute right-0 top-[calc(100%+6px)] z-50 w-64 rounded-lg border border-forest-900/10 bg-white p-3 shadow-lg"
        >
          <div className="px-1 pb-3">
            <div className="truncate font-display text-[14px] font-medium text-forest-900">{user?.full_name}</div>
            <div className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-sage-600">{role}</div>
          </div>
          {withTheme && (
            <div className="flex items-center justify-between border-t border-forest-900/10 px-1 py-3">
              <span className="text-[13px] text-forest-900">Tema</span>
              <ThemeSwitch />
            </div>
          )}
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded border-t border-forest-900/10 px-1 pt-3 text-[13px] text-sage-600 hover:text-forest-900"
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}
