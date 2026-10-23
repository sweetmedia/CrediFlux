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

  it.each(['/select-tenant', '/sign/abc123', '/api'])('deja pasar %s sin tenant', (ruta) => {
    expect(rutaPermitidaSinTenant(ruta)).toBe(true);
  });

  it('en localhost:3000 manda /dashboard al selector de tenant', () => {
    vi.stubGlobal('location', { ...window.location, host: 'localhost:3000' });
    montar('/dashboard');
    expect(screen.getByText('selector')).toBeInTheDocument();
  });

  it('en un subdominio de tenant muestra la página', () => {
    vi.stubGlobal('location', { ...window.location, host: 'caproinsa.localhost:3100' });
    montar('/dashboard');
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });
});
