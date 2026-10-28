import { afterEach, describe, expect, it, vi } from 'vitest';
import { consumeSessionEndNotice, endSession, SESSION_REVOKED_MESSAGE } from '@/lib/api/session';

describe('endSession', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
    sessionStorage.clear();
  });

  function stubLocation() {
    const location = { pathname: '/loans', href: 'http://demo.localhost:3100/loans' };
    vi.stubGlobal('location', location);
    return location;
  }

  it('borra tokens y datos guardados y manda al login', () => {
    const location = stubLocation();
    for (const k of ['access_token', 'refresh_token', 'user', 'tenant']) localStorage.setItem(k, 'x');
    endSession();
    expect(localStorage.length).toBe(0);
    expect(location.href).toBe('/login');
    expect(consumeSessionEndNotice()).toBeNull();
  });

  it('con token_revoked deja un aviso que se consume una sola vez', () => {
    stubLocation();
    endSession('token_revoked');
    expect(consumeSessionEndNotice()).toBe(SESSION_REVOKED_MESSAGE);
    expect(consumeSessionEndNotice()).toBeNull();
  });
});

describe('goToTwoFactorSetup', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  async function cargar() {
    vi.resetModules();
    return import('@/lib/api/session');
  }

  it('manda a /setup-2fa una sola vez aunque fallen varias peticiones', async () => {
    const { goToTwoFactorSetup } = await cargar();
    const location = { pathname: '/loans', href: 'http://demo.localhost:3100/loans' };
    vi.stubGlobal('location', location);
    goToTwoFactorSetup();
    expect(location.href).toBe('/setup-2fa');
    location.href = 'sin-cambio';
    goToTwoFactorSetup();
    expect(location.href).toBe('sin-cambio');
  });

  it('estando ya en /setup-2fa no redirige (sin bucles)', async () => {
    const { goToTwoFactorSetup } = await cargar();
    const location = { pathname: '/setup-2fa', href: 'http://demo.localhost:3100/setup-2fa' };
    vi.stubGlobal('location', location);
    goToTwoFactorSetup();
    expect(location.href).toBe('http://demo.localhost:3100/setup-2fa');
  });

  it('no borra la sesión', async () => {
    const { goToTwoFactorSetup } = await cargar();
    vi.stubGlobal('location', { pathname: '/loans', href: '' });
    localStorage.setItem('access_token', 'x');
    goToTwoFactorSetup();
    expect(localStorage.getItem('access_token')).toBe('x');
    localStorage.clear();
  });
});
