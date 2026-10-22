import { describe, expect, it } from 'vitest';
import { rutaDesdeArchivo } from './router';

describe('rutaDesdeArchivo', () => {
  it.each([
    ['./page.tsx', '/'],
    ['./dashboard/page.tsx', '/dashboard'],
    ['./loans/[id]/page.tsx', '/loans/:id'],
    ['./contract-templates/[id]/edit/page.tsx', '/contract-templates/:id/edit'],
    ['./(auth)/login/page.tsx', '/login'],
    ['./docs/[...slug]/page.tsx', '/docs/*'],
  ])('%s → %s', (archivo, ruta) => {
    expect(rutaDesdeArchivo(archivo)).toBe(ruta);
  });

  it('no hay dos páginas que resuelvan a la misma ruta', () => {
    const archivos = Object.keys(import.meta.glob('./**/page.tsx'));
    const rutas = archivos.map(rutaDesdeArchivo);
    expect(new Set(rutas).size).toBe(rutas.length);
    expect(rutas).toContain('/dashboard');
  });
});
