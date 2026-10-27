import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

/**
 * Port del antiguo `middleware.ts` de Next.js.
 *
 * Multi-tenant por subdominio: en el host sin subdominio (`localhost:3000` o
 * `localhost`) sólo se permite el selector de tenant, las páginas públicas de
 * firma y `/verify-email`; todo lo demás va a `/select-tenant`. Los subdominios
 * (`democompany.localhost`, `caproinsa.localhost`…) pasan siempre.
 *
 * Ahora corre en el navegador: es una redirección de UX, no una barrera de
 * seguridad (la autorización real es del backend), igual que antes.
 */
const HOSTS_SIN_TENANT = new Set(['localhost:3000', 'localhost']);

export function rutaPermitidaSinTenant(pathname: string): boolean {
  return (
    pathname === '/select-tenant' ||
    pathname === '/api' ||
    pathname.startsWith('/static') ||
    pathname.startsWith('/sign/') ||
    // Enlace de verificación de un usuario sin tenant: va a FRONTEND_URL (host público).
    pathname === '/verify-email'
  );
}

export function TenantHostGuard({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  if (HOSTS_SIN_TENANT.has(window.location.host) && !rutaPermitidaSinTenant(pathname)) {
    return <Navigate to="/select-tenant" replace />;
  }
  return <>{children}</>;
}
