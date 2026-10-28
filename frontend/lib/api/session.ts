/**
 * Sesión guardada en el navegador (tokens + usuario/tenant) y su cierre forzado.
 * Módulo aparte para que el cliente HTTP y `authAPI` compartan la misma limpieza.
 */

const SESSION_KEYS = ['access_token', 'refresh_token', 'user', 'tenant'] as const;
const NOTICE_KEY = 'session_end_notice';

// Neutro: token_revoked cubre cambio de contraseña, usuario inactivo y tenant distinto.
export const SESSION_REVOKED_MESSAGE = 'Tu sesión fue cerrada. Inicia sesión de nuevo.';

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

/** Página donde un dueño o administrador sin 2FA la activa (Task 15). */
export const SETUP_2FA_PATH = '/setup-2fa';

let yendoA2fa = false;

/**
 * La API respondió 403 `2fa_required`: el usuario es dueño o administrador y
 * todavía no activó la verificación en dos pasos. Lo manda a `/setup-2fa` sin
 * tocar la sesión, una sola vez aunque fallen varias peticiones a la vez y
 * nunca estando ya ahí (las llamadas del shell en esa página no hacen bucle).
 */
export function goToTwoFactorSetup(): void {
  if (typeof window === 'undefined') return;
  if (yendoA2fa || window.location.pathname === SETUP_2FA_PATH) return;
  yendoA2fa = true;
  window.location.href = SETUP_2FA_PATH;
}
