import { afterEach, describe, expect, it, vi } from 'vitest';
import { esHostGeneral, HOSTS_SIN_TENANT } from '@/lib/hosts';

// Ronda 33.2 R1: el texto para el host general (sin tenant) también cubre el de VITE_APP_URL.
describe('esHostGeneral', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it.each([...HOSTS_SIN_TENANT])('%s (host sin subdominio de dev) es general', (host) => {
    vi.stubEnv('VITE_APP_URL', 'https://app.crediflux.com.do');
    expect(esHostGeneral(host)).toBe(true);
  });

  it('el host de VITE_APP_URL es general; un subdominio de tenant no', () => {
    vi.stubEnv('VITE_APP_URL', 'https://app.crediflux.com.do');

    expect(esHostGeneral('app.crediflux.com.do')).toBe(true);
    expect(esHostGeneral('acme.crediflux.com.do')).toBe(false);
    expect(esHostGeneral('caproinsa.localhost:3100')).toBe(false);
  });

  it('respeta el puerto de VITE_APP_URL', () => {
    vi.stubEnv('VITE_APP_URL', 'http://staging.crediflux.test:8080');

    expect(esHostGeneral('staging.crediflux.test:8080')).toBe(true);
    expect(esHostGeneral('staging.crediflux.test')).toBe(false);
  });

  it.each([
    ['vacía', ''],
    ['inválida', 'no es una url'],
    ['sin esquema', 'app.crediflux.com.do'],
  ])('con VITE_APP_URL %s no falla y sólo cuenta el conjunto de dev', (_caso, valor) => {
    vi.stubEnv('VITE_APP_URL', valor);

    expect(() => esHostGeneral('app.crediflux.com.do')).not.toThrow();
    expect(esHostGeneral('app.crediflux.com.do')).toBe(false);
    expect(esHostGeneral('localhost:3000')).toBe(true);
  });

  it('sin argumento usa el host de la ventana', () => {
    vi.stubEnv('VITE_APP_URL', 'https://app.crediflux.com.do');
    vi.stubGlobal('location', { ...window.location, host: 'app.crediflux.com.do' });
    try {
      expect(esHostGeneral()).toBe(true);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
