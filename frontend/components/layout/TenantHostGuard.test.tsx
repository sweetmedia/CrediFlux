import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { rutaPermitidaSinTenant, TenantHostGuard } from './TenantHostGuard';

function montar(ruta: string) {
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <TenantHostGuard>
            <p>contenido</p>
          </TenantHostGuard>
        ),
      },
      { path: '/select-tenant', element: <p>selector</p> },
    ],
    { initialEntries: [ruta] }
  );
  render(<RouterProvider router={router} />);
}

describe('TenantHostGuard', () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(['/select-tenant', '/sign/abc123', '/api', '/verify-email', '/verify-email/resend'])('deja pasar %s sin tenant', (ruta) => {
    expect(rutaPermitidaSinTenant(ruta)).toBe(true);
  });

  it('en localhost:3000 manda /dashboard al selector de tenant', () => {
    vi.stubGlobal('location', { ...window.location, host: 'localhost:3000' });
    montar('/dashboard');
    expect(screen.getByText('selector')).toBeInTheDocument();
  });

  it('en localhost:3000 muestra /verify-email (enlace de un usuario sin tenant)', () => {
    vi.stubGlobal('location', { ...window.location, host: 'localhost:3000' });
    montar('/verify-email?uid=MQ&token=abc');
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('en un subdominio de tenant muestra /verify-email', () => {
    vi.stubGlobal('location', { ...window.location, host: 'caproinsa.localhost:3100' });
    montar('/verify-email?uid=MQ&token=abc');
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it.each(['caproinsa.localhost:3100', 'localhost:3000'])(
    'en %s muestra /verify-email/resend (la API sólo envía desde el host del usuario)',
    (host) => {
      vi.stubGlobal('location', { ...window.location, host });
      montar('/verify-email/resend');
      expect(screen.getByText('contenido')).toBeInTheDocument();
    }
  );

  it('en un subdominio de tenant muestra la página', () => {
    vi.stubGlobal('location', { ...window.location, host: 'caproinsa.localhost:3100' });
    montar('/dashboard');
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });

  it('el host de VITE_APP_URL no cambia la decisión del guard (sólo afecta textos, 33.2 R1)', () => {
    vi.stubEnv('VITE_APP_URL', 'https://app.crediflux.com.do');
    vi.stubGlobal('location', { ...window.location, host: 'app.crediflux.com.do' });
    try {
      montar('/dashboard');
      expect(screen.getByText('contenido')).toBeInTheDocument();
    } finally {
      vi.unstubAllEnvs();
    }
  });
});
