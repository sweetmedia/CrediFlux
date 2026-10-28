import type { ReactNode } from 'react';
import { useCan } from '@/lib/permissions';

/** Muestra `children` sólo si el usuario tiene el permiso; si no, `fallback`. */
export function PermissionGate({
  code,
  fallback = null,
  children,
}: {
  code: string;
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const can = useCan();
  return <>{can(code) ? children : fallback}</>;
}
