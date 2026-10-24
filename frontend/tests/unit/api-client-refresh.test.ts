import axios, { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const endSession = vi.fn();
vi.mock('@/lib/api/session', () => ({
  endSession: (...args: unknown[]) => endSession(...args),
  clearStoredSession: vi.fn(),
}));

import { apiClient } from '@/lib/api/client';

const REFRESH_URL = '/api/auth/token/refresh/';

function httpError(config: InternalAxiosRequestConfig, status: number, data: unknown) {
  return new AxiosError(`Request failed with status code ${status}`, String(status), config, null, {
    status,
    statusText: '',
    data,
    headers: {},
    config,
  });
}

/** Adaptador falso: 401 para cualquier petición de la API. */
const unauthorized: AxiosAdapter = (config) =>
  Promise.reject(httpError(config, 401, { detail: 'Token revocado.' }));

describe('apiClient: refresh rechazado', () => {
  beforeEach(() => {
    endSession.mockReset();
    localStorage.setItem('access_token', 'acceso-viejo');
    localStorage.setItem('refresh_token', 'refresh-viejo');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('un 401 del refresh cierra la sesión una sola vez aunque fallen varias peticiones', async () => {
    const refresh = vi.spyOn(axios, 'post').mockImplementation(async (url) => {
      expect(String(url)).toContain(REFRESH_URL);
      throw httpError({ headers: {} } as InternalAxiosRequestConfig, 401, {
        detail: 'Token revocado.',
        code: 'token_revoked',
      });
    });

    const results = await Promise.allSettled([
      apiClient.get('/api/loans/', { adapter: unauthorized }),
      apiClient.get('/api/customers/', { adapter: unauthorized }),
    ]);

    expect(results.every((r) => r.status === 'rejected')).toBe(true);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(endSession).toHaveBeenCalledTimes(1);
    expect(endSession).toHaveBeenCalledWith('token_revoked');
  });

  it('un 400 del refresh también cierra la sesión (sin aviso de contraseña)', async () => {
    vi.spyOn(axios, 'post').mockRejectedValue(
      httpError({ headers: {} } as InternalAxiosRequestConfig, 400, { refresh: ['Este campo es obligatorio.'] })
    );
    await expect(apiClient.get('/api/loans/', { adapter: unauthorized })).rejects.toBeTruthy();
    expect(endSession).toHaveBeenCalledTimes(1);
    expect(endSession).toHaveBeenCalledWith(undefined);
  });

  it('un error de red en el refresh no cierra la sesión', async () => {
    vi.spyOn(axios, 'post').mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'));
    await expect(apiClient.get('/api/loans/', { adapter: unauthorized })).rejects.toBeTruthy();
    expect(endSession).not.toHaveBeenCalled();
  });

  it('un 401 en la propia URL de refresh no dispara otro refresh', async () => {
    const refresh = vi.spyOn(axios, 'post');
    await expect(apiClient.post(REFRESH_URL, { refresh: 'x' }, { adapter: unauthorized })).rejects.toBeTruthy();
    expect(refresh).not.toHaveBeenCalled();
  });

  it('con refresh exitoso reintenta la petición con el token nuevo', async () => {
    vi.spyOn(axios, 'post').mockResolvedValue({ data: { access: 'acceso-nuevo', refresh: 'refresh-nuevo' } });
    const adapter: AxiosAdapter = (config) => {
      const auth = String(config.headers?.Authorization ?? '');
      if (auth === 'Bearer acceso-nuevo') {
        return Promise.resolve({ data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config });
      }
      return Promise.reject(httpError(config, 401, { detail: 'expirado' }));
    };
    await expect(apiClient.get('/api/loans/', { adapter })).resolves.toEqual({ ok: true });
    expect(localStorage.getItem('access_token')).toBe('acceso-nuevo');
    expect(localStorage.getItem('refresh_token')).toBe('refresh-nuevo');
    expect(endSession).not.toHaveBeenCalled();
  });
});
