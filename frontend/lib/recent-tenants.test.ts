import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { recentTenants } from './recent-tenants';

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe('recentTenants', () => {
  it('el último usado va primero, sin duplicados y con máximo cinco', () => {
    ['a', 'b', 'c', 'a', 'd', 'e', 'f'].forEach(recentTenants.add);
    expect(recentTenants.read()).toEqual(['f', 'e', 'd', 'a', 'c']);
  });

  it('si el almacenamiento falla devuelve una lista vacía y no lanza', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    expect(recentTenants.read()).toEqual([]);
    expect(() => recentTenants.add('demo')).not.toThrow();
  });

  it('ignora basura guardada', () => {
    window.localStorage.setItem('cf-recent-tenants', '{"x":1}');
    expect(recentTenants.read()).toEqual([]);
    window.localStorage.setItem('cf-recent-tenants', '["ok","no válido",3]');
    expect(recentTenants.read()).toEqual(['ok']);
  });
});
