/**
 * Sesión guardada en el navegador (tokens + usuario/tenant) y su cierre forzado.
 * Módulo aparte para que el cliente HTTP y `authAPI` compartan la misma limpieza.
 */

const SESSION_KEYS = ['access_token', 'refresh_token', 'user', 'tenant'] as const;
const NOTICE_KEY = 'session_end_notice';

export const SESSION_REVOKED_MESSAGE = 'Tu sesión fue cerrada por un cambio de contraseña.';

export function clearStoredSession(): void {
  if (typeof window === 'undefined') return;
  for (const key of SESSION_KEYS) localStorage.removeItem(key);
}

/**
 * Cierra la sesión local y manda al login. Si el backend dijo que el token fue
 * revocado (`token_revoked`), deja un aviso que el login muestra tras la recarga.
 */
export function endSession(code?: string): void {
  clearStoredSession();
  if (typeof window === 'undefined') return;
  if (code === 'token_revoked') {
    try {
      sessionStorage.setItem(NOTICE_KEY, SESSION_REVOKED_MESSAGE);
    } catch {
      // sin sessionStorage no hay aviso; el redirect sigue
    }
  }
  if (window.location.pathname !== '/login') window.location.href = '/login';
}

/** Devuelve (y borra) el aviso de cierre de sesión pendiente, si lo hay. */
export function consumeSessionEndNotice(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const notice = sessionStorage.getItem(NOTICE_KEY);
    if (notice) sessionStorage.removeItem(NOTICE_KEY);
    return notice;
  } catch {
    return null;
  }
}
