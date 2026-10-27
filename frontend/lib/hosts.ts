/**
 * Hosts sin subdominio de tenant.
 *
 * `HOSTS_SIN_TENANT` es el conjunto con el que `TenantHostGuard` decide qué rutas redirige a
 * `/select-tenant`; esa decisión no cambia aquí.
 *
 * `esHostGeneral` es sólo para textos: además del conjunto de dev, cuenta el host de
 * `VITE_APP_URL` (el `FRONTEND_URL` de producción, adonde redirige la confirmación de correo de
 * allauth sin revelar el tenant). Desde ese host la API no le envía enlaces a un usuario de
 * empresa, y las pantallas de enlaces lo avisan.
 */
export const HOSTS_SIN_TENANT: ReadonlySet<string> = new Set(['localhost:3000', 'localhost']);

/** Host de `VITE_APP_URL`, o null si falta o no es una URL válida. */
function hostDeAppUrl(): string | null {
  const valor = import.meta.env.VITE_APP_URL;
  if (!valor) return null;
  try {
    return new URL(valor).host || null;
  } catch {
    return null;
  }
}

/** True en el host general de la app (dev o el de `VITE_APP_URL`). Sólo para textos. */
export function esHostGeneral(host: string = window.location.host): boolean {
  return HOSTS_SIN_TENANT.has(host) || host === hostDeAppUrl();
}
