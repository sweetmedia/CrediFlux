/**
 * `<Link href>` sobre React Router, con la misma API que usaba la app con
 * `next/link`. Las URLs externas (http, mailto, tel…) salen como `<a>`.
 */
import { forwardRef, type AnchorHTMLAttributes } from 'react';
import { Link as RouterLink } from 'react-router';

export interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  href: string | { pathname?: string; query?: Record<string, string | number> };
  replace?: boolean;
  /** Aceptados por compatibilidad; React Router no los necesita. */
  prefetch?: boolean;
  scroll?: boolean;
}

const EXTERNA = /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i;

function aTexto(href: LinkProps['href']): string {
  if (typeof href === 'string') return href;
  const query = href.query
    ? '?' + new URLSearchParams(Object.entries(href.query).map(([k, v]) => [k, String(v)]))
    : '';
  return `${href.pathname ?? ''}${query}`;
}

const Link = forwardRef<HTMLAnchorElement, LinkProps>(function Link(
  { href, replace, prefetch: _prefetch, scroll: _scroll, ...rest },
  ref
) {
  const destino = aTexto(href);
  if (EXTERNA.test(destino) || destino.startsWith('#')) {
    return <a ref={ref} href={destino} {...rest} />;
  }
  return <RouterLink ref={ref} to={destino} replace={replace} {...rest} />;
});

export default Link;
