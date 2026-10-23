/**
 * Navegación de la app sobre React Router.
 *
 * Expone la misma forma que `next/navigation` (de donde vino el código antes
 * de migrar a Vite) para que las páginas no tengan que cambiar: `useRouter`,
 * `usePathname`, `useSearchParams` y `useParams`.
 */
import { useMemo } from 'react';
import {
  useLocation,
  useNavigate,
  useParams as useRouterParams,
  useSearchParams as useRouterSearchParams,
} from 'react-router';

export interface AppRouter {
  push: (href: string, options?: { scroll?: boolean }) => void;
  replace: (href: string, options?: { scroll?: boolean }) => void;
  back: () => void;
  forward: () => void;
  /** Vuelve a montar la ruta actual (equivalente a `router.refresh()`). */
  refresh: () => void;
}

export function useRouter(): AppRouter {
  const navigate = useNavigate();
  return useMemo(
    () => ({
      push: (href) => {
        void navigate(href);
      },
      replace: (href) => {
        void navigate(href, { replace: true });
      },
      back: () => {
        void navigate(-1);
      },
      forward: () => {
        void navigate(1);
      },
      refresh: () => {
        void navigate('.', { replace: true });
      },
    }),
    [navigate]
  );
}

export function usePathname(): string {
  return useLocation().pathname;
}

/** Parámetros de búsqueda de sólo lectura (como `ReadonlyURLSearchParams`). */
export function useSearchParams(): URLSearchParams {
  const [params] = useRouterSearchParams();
  return params;
}

/** Segmentos dinámicos de la ruta: `/loans/:id` → `{ id }`. */
export function useParams<
  T extends Record<string, string | undefined> = Record<string, string | undefined>,
>(): T {
  return useRouterParams() as T;
}
