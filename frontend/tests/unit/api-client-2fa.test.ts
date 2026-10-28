import { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const goToTwoFactorSetup = vi.fn();
vi.mock('@/lib/api/session', () => ({
  endSession: vi.fn(),
  clearStoredSession: vi.fn(),
  goToTwoFactorSetup: () => goToTwoFactorSetup(),
}));

import { apiClient } from '@/lib/api/client';

function forbidden(data: unknown): AxiosAdapter {
  return (config: InternalAxiosRequestConfig) =>
    Promise.reject(
      new AxiosError('Request failed with status code 403', '403', config, null, {
        status: 403,
        statusText: '',
        data,
        headers: {},
        config,
      })
    );
}

describe('apiClient: 403 2fa_required', () => {
  const hrefOriginal = window.location.href;

  beforeEach(() => {
    goToTwoFactorSetup.mockReset();
    window.history.replaceState(null, '', '/loans');
  });

  afterEach(() => {
    window.history.replaceState(null, '', new URL(hrefOriginal).pathname);
  });

  it('manda a /setup-2fa y no a acceso denegado', async () => {
    const adapter = forbidden({
      detail: 'Activa la verificación en dos pasos para continuar.',
      code: '2fa_required',
    });
    await expect(apiClient.get('/api/loans/customers/', { adapter })).rejects.toBeTruthy();
    expect(goToTwoFactorSetup).toHaveBeenCalledTimes(1);
    expect(window.location.pathname).toBe('/loans'); // no pasó por /access-denied
  });

  it('un 403 de permiso normal no va a /setup-2fa', async () => {
    const adapter = forbidden({ detail: 'Sin permiso.', required_permission: 'loans.view' });
    await expect(apiClient.get('/api/loans/', { adapter })).rejects.toBeTruthy();
    expect(goToTwoFactorSetup).not.toHaveBeenCalled();
  });
});
