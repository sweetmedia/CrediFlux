import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { endSession } from './session';

/**
 * Get API URL based on current browser hostname
 * Supports multi-tenant subdomain routing
 *
 * @returns The API base URL for the current tenant
 */
export function getApiUrl(): string {
  // Server-side: use env variable
  if (typeof window === 'undefined') {
    return import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  // Client-side: detect from browser
  const hostname = window.location.hostname;
  const protocol = window.location.protocol; // http: or https:
  const backendPort = '8600'; // Backend mapped port (direct access)

  // If accessing via subdomain (e.g., democompany.localhost, caproinsa.localhost)
  // use the same subdomain for API calls, on the port VITE_API_URL points at
  // (8100 for the V2 Docker stack; 8000 is V1/other projects).
  if (hostname.includes('.localhost')) {
    let apiPort = '8000';
    try {
      apiPort = new URL(import.meta.env.VITE_API_URL || 'http://localhost:8000').port || '8000';
    } catch {
      // keep default
    }
    return `http://${hostname}:${apiPort}`;
  }

  // If accessing via a proper domain (e.g., app.crediflux.com.do, demo.crediflux.com.do)
  // nginx handles /api/ routing — use same origin, no port needed
  if (hostname.includes('.') && !hostname.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    return `${protocol}//${hostname}`;
  }

  // If accessing via IP (e.g., 23.95.73.125), use same host with backend port
  if (hostname !== 'localhost') {
    return `http://${hostname}:${backendPort}`;
  }

  // Default to localhost:8000 for regular localhost access
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
}

// Log initial configuration
if (typeof window !== 'undefined') {
  console.log('🔧 API Client Configuration:');
  console.log('  - Hostname:', window.location.hostname);
  console.log('  - VITE_API_URL:', import.meta.env.VITE_API_URL);
  console.log('  - API_URL (dynamic):', getApiUrl());
}

const REFRESH_PATH = '/api/auth/token/refresh/';

// Un solo refresh en vuelo: los 401 concurrentes esperan la misma promesa.
let refreshPromise: Promise<string> | null = null;

/**
 * Pide un access nuevo. El backend rota el refresh (el usado queda en lista
 * negra), así que se guardan ambos. Si el refresh es rechazado (401/400:
 * revocado, en lista negra, expirado) se cierra la sesión una sola vez; un
 * error de red o 5xx no cierra la sesión.
 * Usa `axios` directo (no la instancia), así que el refresh no pasa por el interceptor.
 */
function refreshAccessToken(refreshToken: string): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = withRefreshLock(() => doRefresh(refreshToken)).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

/**
 * Serializa el refresh entre pestañas con Web Locks cuando el navegador lo
 * soporta; sin Web Locks corre directo (la comparación de tokens en
 * `doRefresh` cubre la carrera igualmente).
 */
function withRefreshLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined;
  if (locks?.request) return locks.request('crediflux-token-refresh', fn) as Promise<T>;
  return fn();
}

/** Otra pestaña ya rotó el refresh: el que enviamos ya no es el guardado. */
function rotatedElsewhere(sent: string): string | null {
  const stored = localStorage.getItem('refresh_token');
  const access = localStorage.getItem('access_token');
  return stored && stored !== sent && access ? access : null;
}

async function doRefresh(sentRefresh: string): Promise<string> {
  // Con el lock, otra pestaña pudo terminar su refresh mientras esperábamos.
  const already = rotatedElsewhere(sentRefresh);
  if (already) return already;

  try {
    const response = await axios.post(`${getApiUrl()}${REFRESH_PATH}`, { refresh: sentRefresh });
    const { access, refresh } = response.data as { access: string; refresh?: string };
    localStorage.setItem('access_token', access);
    if (refresh) localStorage.setItem('refresh_token', refresh);
    return access;
  } catch (refreshError: unknown) {
    const status = axios.isAxiosError(refreshError) ? refreshError.response?.status : undefined;
    if (status === 401 || status === 400) {
      // Carrera entre pestañas: la otra ganó la rotación y el nuestro quedó en
      // lista negra. Usar sus tokens en vez de cerrar la sesión de todas.
      const winner = rotatedElsewhere(sentRefresh);
      if (winner) return winner;
      const data = axios.isAxiosError(refreshError) ? (refreshError.response?.data as { code?: string } | undefined) : undefined;
      endSession(data?.code === 'token_revoked' ? 'token_revoked' : undefined);
    }
    throw refreshError;
  }
}

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Calculate baseURL dynamically for each request
        config.baseURL = getApiUrl();

        // Get token from localStorage
        if (typeof window !== 'undefined') {
          const token = localStorage.getItem('access_token');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        // If error is 403 (Forbidden) - redirect to access denied page
        if (error.response?.status === 403) {
          const errorData = error.response.data as any;
          const reason = errorData?.detail || errorData?.error || 'No tienes permisos para acceder a este recurso.';
          const permission = errorData?.required_permission;

          // Get current URL for return
          const currentUrl = typeof window !== 'undefined' ? window.location.pathname : '/dashboard';

          // Build access denied URL with params
          const params = new URLSearchParams({
            reason,
            returnUrl: currentUrl,
          });

          if (permission) {
            params.append('permission', permission);
          }

          // Redirect to access denied page
          if (typeof window !== 'undefined') {
            window.location.href = `/access-denied?${params.toString()}`;
          }

          return Promise.reject(error);
        }

        // 401: intentar un refresh (una sola vez por petición, nunca sobre el propio refresh)
        if (
          error.response?.status === 401 &&
          originalRequest &&
          !originalRequest._retry &&
          !String(originalRequest.url ?? '').includes(REFRESH_PATH)
        ) {
          originalRequest._retry = true;

          const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;
          if (refreshToken) {
            try {
              const access = await refreshAccessToken(refreshToken);
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${access}`;
              }
              return this.client(originalRequest);
            } catch (refreshError) {
              return Promise.reject(refreshError);
            }
          }
          // Access guardado pero sin refresh: no hay forma de renovar, cerrar la sesión.
          if (typeof window !== 'undefined' && localStorage.getItem('access_token')) {
            endSession();
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }
}

export const apiClient = new APIClient();

// ---------------------------------------------------------------------------
// Mensajes de error para el usuario
// ---------------------------------------------------------------------------

const STATUS_MESSAGES: Record<number, string> = {
  400: 'Revisa los datos ingresados: la solicitud no es válida.',
  401: 'Tu sesión expiró. Inicia sesión de nuevo.',
  403: 'No tienes permiso para realizar esta acción.',
  404: 'No encontramos el recurso solicitado.',
  405: 'Esta acción no está permitida.',
  409: 'La operación entra en conflicto con el estado actual. Recarga e intenta de nuevo.',
  413: 'El archivo o los datos enviados son demasiado grandes.',
  429: 'Demasiadas solicitudes. Espera un momento e intenta de nuevo.',
  500: 'Error interno del servidor. Intenta de nuevo en unos minutos.',
  502: 'El servidor no está disponible. Intenta de nuevo en unos minutos.',
  503: 'El servicio no está disponible temporalmente. Intenta de nuevo en unos minutos.',
  504: 'El servidor tardó demasiado en responder. Intenta de nuevo.',
};

const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Revisa tu conexión e intenta de nuevo.';
const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Intenta de nuevo.';

// Mensajes estándar de DRF / simplejwt que pueden llegar en inglés.
const EXACT_TRANSLATIONS: Record<string, string> = {
  'This field is required.': 'Este campo es obligatorio.',
  'This field may not be blank.': 'Este campo no puede estar vacío.',
  'This field may not be null.': 'Este campo no puede estar vacío.',
  'A valid number is required.': 'Ingresa un número válido.',
  'A valid integer is required.': 'Ingresa un número entero válido.',
  'Enter a valid email address.': 'Ingresa un correo electrónico válido.',
  'Enter a valid date.': 'Ingresa una fecha válida.',
  'Not a valid string.': 'Ingresa un texto válido.',
  'Must be a valid boolean.': 'Selecciona un valor válido.',
  'Not found.': 'No encontramos el recurso solicitado.',
  'No Customer matches the given query.': 'No encontramos el cliente.',
  'No Loan matches the given query.': 'No encontramos el préstamo.',
  'Authentication credentials were not provided.': 'Tu sesión expiró. Inicia sesión de nuevo.',
  'Given token not valid for any token type': 'Tu sesión expiró. Inicia sesión de nuevo.',
  'Token is invalid or expired': 'Tu sesión expiró. Inicia sesión de nuevo.',
  'Incorrect authentication credentials.': 'Credenciales incorrectas.',
  'No active account found with the given credentials': 'Correo o contraseña incorrectos.',
  'Unable to log in with provided credentials.': 'Correo o contraseña incorrectos.',
  'You do not have permission to perform this action.': 'No tienes permiso para realizar esta acción.',
  'Invalid page.': 'La página solicitada no existe.',
  'Request was throttled.': 'Demasiadas solicitudes. Espera un momento e intenta de nuevo.',
  'A server error occurred.': STATUS_MESSAGES[500],
};

const PATTERN_TRANSLATIONS: Array<[RegExp, (m: RegExpMatchArray) => string]> = [
  [/^Ensure this field has no more than (\d+) characters\.$/, (m) => `Usa como máximo ${m[1]} caracteres.`],
  [/^Ensure this field has at least (\d+) characters\.$/, (m) => `Usa al menos ${m[1]} caracteres.`],
  [/^Ensure this value is greater than or equal to (.+)\.$/, (m) => `El valor debe ser mayor o igual a ${m[1]}.`],
  [/^Ensure this value is less than or equal to (.+)\.$/, (m) => `El valor debe ser menor o igual a ${m[1]}.`],
  [/^Ensure that there are no more than (\d+) digits in total\.$/, (m) => `Usa como máximo ${m[1]} dígitos en total.`],
  [/^Ensure that there are no more than (\d+) decimal places\.$/, (m) => `Usa como máximo ${m[1]} decimales.`],
  [/^"(.+)" is not a valid choice\.$/, (m) => `"${m[1]}" no es una opción válida.`],
  [/^Invalid pk "(.+)" - object does not exist\.$/, () => 'El registro seleccionado no existe.'],
  [/^Method "(.+)" not allowed\.$/, () => STATUS_MESSAGES[405]],
  [/^.+ with this .+ already exists\.$/, () => 'Ya existe un registro con ese valor.'],
  [/^Request was throttled\. Expected available in (\d+) seconds?\.$/, (m) => `Demasiadas solicitudes. Intenta de nuevo en ${m[1]} s.`],
];

const FIELD_LABELS: Record<string, string> = {
  amount: 'Monto',
  principal_amount: 'Monto del préstamo',
  opening_balance: 'Balance de apertura',
  closing_balance: 'Balance de cierre',
  interest_rate: 'Tasa de interés',
  term_months: 'Plazo',
  payment_date: 'Fecha de pago',
  payment_method: 'Método de pago',
  customer: 'Cliente',
  customer_name: 'Cliente',
  loan: 'Préstamo',
  register: 'Caja',
  session: 'Sesión de caja',
  category: 'Categoría',
  description: 'Descripción',
  reference: 'Referencia',
  reference_number: 'Referencia',
  email: 'Correo',
  password: 'Contraseña',
  first_name: 'Nombre',
  last_name: 'Apellido',
  phone: 'Teléfono',
  id_number: 'Cédula',
  notes: 'Notas',
};

function translateMessage(message: string): string {
  const trimmed = message.trim();
  if (EXACT_TRANSLATIONS[trimmed]) return EXACT_TRANSLATIONS[trimmed];
  for (const [pattern, build] of PATTERN_TRANSLATIONS) {
    const match = trimmed.match(pattern);
    if (match) return build(match);
  }
  return trimmed;
}

function fieldLabel(field: string): string {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field];
  const spaced = field.replace(/_/g, ' ');
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** Aplana un valor de error de DRF (string, lista o dict anidado) a mensajes. */
function flattenMessages(value: unknown): string[] {
  if (value == null) return [];
  if (typeof value === 'string') return [translateMessage(value)];
  if (Array.isArray(value)) return value.flatMap(flattenMessages);
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).flatMap(flattenMessages);
  return [String(value)];
}

function messageFromBody(data: unknown): string | null {
  if (!data) return null;
  if (typeof data === 'string') {
    // Páginas HTML de error (500 de Django, proxies) no sirven como mensaje.
    return data.trim().startsWith('<') || data.length > 300 ? null : translateMessage(data);
  }
  if (Array.isArray(data)) return flattenMessages(data).join(' ') || null;
  if (typeof data !== 'object') return null;

  const body = data as Record<string, unknown>;
  for (const key of ['detail', 'error', 'message']) {
    const msgs = flattenMessages(body[key]);
    if (msgs.length) return msgs.join(' ');
  }

  const nonField = flattenMessages(body.non_field_errors);
  if (nonField.length) return nonField.join(' ');

  const fieldMessages = Object.entries(body)
    .filter(([key]) => !['detail', 'error', 'message', 'non_field_errors', 'code', 'status'].includes(key))
    .map(([key, value]) => {
      const msgs = flattenMessages(value);
      return msgs.length ? `${fieldLabel(key)}: ${msgs.join(' ')}` : null;
    })
    .filter(Boolean);
  return fieldMessages.length ? fieldMessages.join(' · ') : null;
}

/**
 * Convierte cualquier error (axios, fetch, Error, string) en un mensaje en
 * español listo para mostrar. Prioriza el mensaje del backend (`detail`,
 * `error`, `non_field_errors`, errores por campo) y cae al código de estado.
 */
export function getApiErrorMessage(err: unknown, fallback?: string): string {
  if (axios.isAxiosError(err)) {
    if (!err.response) {
      if (err.code === 'ECONNABORTED' || err.code === 'ETIMEDOUT') return STATUS_MESSAGES[504];
      if (axios.isCancel(err)) return fallback || GENERIC_ERROR_MESSAGE;
      return NETWORK_ERROR_MESSAGE;
    }
    const { status, data } = err.response;
    const fromBody = status < 500 ? messageFromBody(data) : null;
    return fromBody || STATUS_MESSAGES[status] || (status >= 500 ? STATUS_MESSAGES[500] : fallback || GENERIC_ERROR_MESSAGE);
  }
  if (typeof err === 'string') return translateMessage(err);
  if (err instanceof Error) {
    if (/network|fetch/i.test(err.message) && err instanceof TypeError) return NETWORK_ERROR_MESSAGE;
    // Errores lanzados por nuestro propio código (lib/api/*) ya vienen en español;
    // los genéricos en inglés de librerías se sustituyen por el fallback.
    // TypeError/ReferenceError son bugs, no mensajes para el usuario.
    if (err.constructor === Error && err.message && !/^(Failed to|Request failed|Network Error|timeout)/i.test(err.message)) {
      return translateMessage(err.message);
    }
  }
  return fallback || GENERIC_ERROR_MESSAGE;
}
