import { describe, expect, it } from 'vitest';
import { esPaginaPublica } from './public-pages';

describe('páginas públicas (sin sesión ni sidebar)', () => {
  it.each(['/login', '/forgot-password', '/reset-password', '/verify-email'])('%s es pública', (ruta) => {
    expect(esPaginaPublica(ruta)).toBe(true);
  });

  it.each(['/dashboard', '/loans', '/verify-email/otra'])('%s no es pública', (ruta) => {
    expect(esPaginaPublica(ruta)).toBe(false);
  });
});
