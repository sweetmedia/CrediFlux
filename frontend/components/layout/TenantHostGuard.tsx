import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

/**
 * Port del antiguo `middleware.ts` de Next.js.
 *
 * Multi-tenant por subdominio: en el host sin subdominio (`localhost:3000` o
 * `localhost`) sólo se permite el selector de tenant, las páginas públicas de
 * firma y `/verify-email` (y `/verify-email/resend`); todo lo demás va a `/select-tenant`. Los subdominios
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
    // Enlace de verificación de un usuario sin tenant: va a FRONTEND_URL (host público), y
    // desde ahí pide uno nuevo (la API sólo se lo envía desde ese host).
    pathname === '/verify-email' ||
    pathname === '/verify-email/resend'
  );
}

/**
 * True en el host sin subdominio de tenant (el de `FRONTEND_URL` en dev). Lo usan también las
 * pantallas que piden enlaces por correo: la API sólo envía a un usuario de tenant desde el host
 * de su tenant.
 */
export function esHostSinTenant(host: string = window.location.host): boolean {
  return HOSTS_SIN_TENANT.has(host);
}

export function TenantHostGuard({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  if (esHostSinTenant() && !rutaPermitidaSinTenant(pathname)) {
    return <Navigate to="/select-tenant" replace />;
  }
  return <>{children}</>;
}
