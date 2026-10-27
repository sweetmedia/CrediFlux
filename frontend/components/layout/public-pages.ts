/**
 * Páginas que se ven sin sesión y sin sidebar (`AppLayout`). `/verify-email` es el destino del
 * enlace de verificación de correo, que el backend arma con el dominio del tenant, y
 * `/verify-email/resend` pide uno nuevo.
 */
export const PUBLIC_PAGES = [
  '/',
  '/login',
  '/register',
  '/forgot-password',
  '/select-tenant',
  '/reset-password',
  '/verify-email',
  '/verify-email/resend',
  '/v2-probe',
];

export function esPaginaPublica(pathname: string): boolean {
  return PUBLIC_PAGES.includes(pathname);
}
