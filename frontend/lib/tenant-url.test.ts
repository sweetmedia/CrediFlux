import { afterEach, describe, expect, it, vi } from 'vitest';
import { tenantUrl } from './tenant-url';

const en = (href: string) => new URL(href) as unknown as Location;

afterEach(() => vi.unstubAllEnvs());

describe('tenantUrl', () => {
  it('en desarrollo usa el host y el puerto actuales', () => {
    vi.stubEnv('VITE_TENANT_BASE_DOMAIN', '');
    expect(tenantUrl('demo', en('http://localhost:3000/select-tenant'))).toBe('http://demo.localhost:3000/login');
  });

  it('en producción usa el dominio base de las financieras', () => {
    vi.stubEnv('VITE_TENANT_BASE_DOMAIN', 'crediflux.com.do');
    expect(tenantUrl('demo', en('https://app.crediflux.com.do/select-tenant'))).toBe('https://demo.crediflux.com.do/login');
  });

  it('pasa a minúsculas', () => {
    vi.stubEnv('VITE_TENANT_BASE_DOMAIN', '');
    expect(tenantUrl('Demo', en('http://localhost:3000/'))).toBe('http://demo.localhost:3000/login');
  });

  it.each(['', 'a.b', '-x', 'x-', 'evil.com/x', 'a b', 'ñu', 'a'.repeat(64)])('rechaza %j', (sub) => {
    vi.stubEnv('VITE_TENANT_BASE_DOMAIN', '');
    expect(() => tenantUrl(sub, en('http://localhost:3000/'))).toThrow();
  });
});
