import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import SelectTenantPage from '@/app/select-tenant/page';

const assign = vi.fn();

beforeEach(() => {
  window.localStorage.clear();
  assign.mockReset();
  vi.stubEnv('VITE_TENANT_BASE_DOMAIN', '');
  vi.stubGlobal('location', { ...new URL('http://localhost:3000/select-tenant'), host: 'localhost:3000', hostname: 'localhost', protocol: 'http:', port: '3000', assign });
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function montar() {
  const router = createMemoryRouter([{ path: '/select-tenant', element: <SelectTenantPage /> }], { initialEntries: ['/select-tenant'] });
  render(<RouterProvider router={router} />);
}

describe('/select-tenant', () => {
  it('no muestra ninguna lista fija de financieras', () => {
    montar();
    expect(screen.queryByText(/democompany|caproinsa|amsfin/i)).not.toBeInTheDocument();
    expect(screen.getByText(/no mostramos la lista de financieras por privacidad/i)).toBeInTheDocument();
  });

  it('escribir la dirección lleva al login de esa financiera y la recuerda', async () => {
    montar();
    fireEvent.change(screen.getByLabelText('Dirección de tu financiera'), { target: { value: 'Demo' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    });
    expect(assign).toHaveBeenCalledWith('http://demo.localhost:3000/login');
    expect(JSON.parse(window.localStorage.getItem('cf-recent-tenants')!)).toEqual(['demo']);
  });

  it('una dirección inválida muestra el error y no navega', async () => {
    montar();
    fireEvent.change(screen.getByLabelText('Dirección de tu financiera'), { target: { value: 'evil.com/x' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    });
    expect(assign).not.toHaveBeenCalled();
    expect(screen.getByText(/sólo letras, números y guiones/i)).toBeInTheDocument();
  });

  it('muestra las usadas en este equipo como enlaces', () => {
    window.localStorage.setItem('cf-recent-tenants', '["demo","coop-san-jose"]');
    montar();
    expect(screen.getByRole('link', { name: /coop-san-jose/ })).toHaveAttribute('href', 'http://coop-san-jose.localhost:3000/login');
  });
});
