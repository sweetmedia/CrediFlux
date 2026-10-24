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
