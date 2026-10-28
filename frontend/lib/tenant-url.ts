/**
 * Dirección del login de una financiera a partir de su subdominio.
 *
 * Producción: `https://<sub>.<VITE_TENANT_BASE_DOMAIN>/login` (el mismo dominio
 * que TENANT_BASE_DOMAIN del backend). Desarrollo, sin esa variable: el host y
 * el puerto actuales, `http://<sub>.localhost:3000/login`.
 */
const SUBDOMINIO = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

export function tenantUrl(sub: string, loc: Location = window.location): string {
  const s = sub.trim().toLowerCase();
  if (!SUBDOMINIO.test(s)) throw new Error('Subdominio inválido');
  const base = import.meta.env.VITE_TENANT_BASE_DOMAIN;
  if (base) return `https://${s}.${base}/login`;
  return `${loc.protocol}//${s}.${loc.hostname}${loc.port ? `:${loc.port}` : ''}/login`;
}

export function esSubdominioValido(sub: string): boolean {
  return SUBDOMINIO.test(sub.trim().toLowerCase());
}
