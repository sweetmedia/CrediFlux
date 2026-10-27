/**
 * Rutas de la app, generadas desde la estructura de `app/` (la convención que
 * venía de Next.js App Router):
 *
 *   app/page.tsx                   → /
 *   app/loans/[id]/page.tsx        → /loans/:id
 *   app/(auth)/login/page.tsx      → /login   (los grupos `(x)` no cuentan)
 *   app/docs/[...slug]/page.tsx    → /docs/*
 *
 * Cada página se carga en diferido (un chunk por ruta). Para añadir una ruta
 * basta con crear su `page.tsx`.
 */
import type { ComponentType } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import RootLayout from './layout';
import NotFound from './not-found';

type PageModule = { default: ComponentType };

const pages = import.meta.glob<PageModule>('./**/page.tsx');

/** `./loans/[id]/page.tsx` → `/loans/:id` */
export function rutaDesdeArchivo(file: string): string {
  const segmentos = file
    .replace(/^\.\//, '')
    .replace(/(^|\/)page\.tsx$/, '')
    .split('/')
    .filter((s) => s && !/^\(.*\)$/.test(s))
    .map((s) => {
      const resto = s.match(/^\[\.\.\.(.+)\]$/);
      if (resto) return '*';
      const dinamico = s.match(/^\[(.+)\]$/);
      return dinamico ? `:${dinamico[1]}` : s;
    });
  return '/' + segmentos.join('/');
}

const rutas: RouteObject[] = Object.entries(pages).map(([file, load]) => ({
  path: rutaDesdeArchivo(file),
  lazy: async () => ({ Component: (await load()).default }),
}));

// Vitrina del DS sólo en desarrollo (las pruebas e2e del tema la usan); fuera
// del layout para no pasar por la sesión. En build la rama se elimina.
const rutasDev: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/__ds', lazy: async () => ({ Component: (await import('./__dev/ds')).default }) }]
  : [];

export const router = createBrowserRouter([
  ...rutasDev,
  {
    element: <RootLayout />,
    // Primera carga mientras llega el chunk de la página.
    HydrateFallback: () => null,
    children: [...rutas, { path: '*', Component: NotFound }],
  },
]);
