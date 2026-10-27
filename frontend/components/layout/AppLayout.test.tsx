import { fireEvent, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppearanceProvider } from '@/lib/design-system/AppearanceProvider';
import { AppLayout } from './AppLayout';

const auth = vi.hoisted(() => ({
  isAuthenticated: true,
  isLoading: false,
  user: { first_name: 'María', last_name: 'Fernández', full_name: 'María Fernández', role: 'admin', is_tenant_owner: false },
  tenant: { id: 1, name: 'coop-san-jose', business_name: 'Cooperativa San José', subscription_plan: 'basic', is_active: true },
  logout: vi.fn(),
}));

vi.mock('@/lib/contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('@/components/AIChatBubble', () => ({ AIChatBubble: () => null }));

let movil = false;

beforeEach(() => {
  movil = false;
  auth.isAuthenticated = true;
  vi.stubGlobal('matchMedia', (q: string) => ({
    matches: q.includes('max-width: 767px') ? movil : false,
    media: q,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => vi.unstubAllGlobals());

function montar(ruta: string) {
  const router = createMemoryRouter(
    [
      {
        path: '*',
        element: (
          <AppearanceProvider>
            <AppLayout>
              <label>
                Monto
                <input />
              </label>
            </AppLayout>
          </AppearanceProvider>
        ),
      },
    ],
    { initialEntries: [ruta] },
  );
  render(<RouterProvider router={router} />);
}

const barraInferior = () => screen.queryByRole('navigation', { name: 'Navegación inferior' });

describe('AppLayout en móvil', () => {
  beforeEach(() => {
    movil = true;
  });

  it('tiene barra inferior con Cobrar al centro hacia /payments/new', () => {
    montar('/dashboard');
    const nav = barraInferior();
    expect(nav).toBeInTheDocument();
    const enlaces = within(nav!).getAllByRole('link');
    expect(enlaces.map((a) => a.textContent)).toEqual(['Inicio', 'Clientes', 'Cobrar', 'Préstamos', 'Más']);
    expect(enlaces[2]).toHaveAttribute('href', '/payments/new');
    expect(enlaces[0]).toHaveAttribute('aria-current', 'page');
  });

  it('el switch de tema está en el menú de usuario, no en la barra superior', () => {
    montar('/dashboard');
    expect(screen.queryByRole('radiogroup', { name: 'Tema' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Menú de usuario' }));
    const menu = screen.getByRole('dialog', { name: 'Menú de usuario' });
    expect(within(menu).getByRole('radiogroup', { name: 'Tema' })).toBeInTheDocument();
    expect(within(menu).getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument();
  });

  it('la barra inferior se esconde mientras se escribe en un campo', () => {
    montar('/dashboard');
    fireEvent.focusIn(screen.getByRole('textbox', { name: 'Monto' }));
    expect(barraInferior()).not.toBeInTheDocument();
    fireEvent.focusOut(screen.getByRole('textbox', { name: 'Monto' }));
    expect(barraInferior()).toBeInTheDocument();
  });

  it.each(['/payments/new', '/loans/new'])('%s no lleva barra inferior (tiene su barra de acción)', (ruta) => {
    montar(ruta);
    expect(barraInferior()).not.toBeInTheDocument();
  });

  it('marca el layout para subir el asistente por encima de la barra inferior', () => {
    montar('/dashboard');
    expect(document.querySelector('[data-bottom-nav]')).toBeInTheDocument();
  });

  it('Más abre el menú completo', () => {
    montar('/dashboard');
    fireEvent.click(within(barraInferior()!).getByRole('link', { name: 'Más' }));
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeVisible();
  });
});

describe('AppLayout en escritorio', () => {
  it('el switch de tema va en la barra superior y no hay barra inferior', () => {
    montar('/customers');
    expect(within(screen.getByRole('banner')).getByRole('radiogroup', { name: 'Tema' })).toBeInTheDocument();
    expect(barraInferior()).not.toBeInTheDocument();
    expect(document.querySelector('[data-bottom-nav]')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Navegación principal' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Clientes' })).toHaveAttribute('aria-current', 'page');
  });
});

describe('páginas públicas', () => {
  it.each([
    ['/login', false],
    ['/login', true],
    ['/verify-email', false],
    ['/verify-email', true],
  ])('%s (móvil: %s) no pinta sidebar ni barra inferior', (ruta, esMovil) => {
    movil = esMovil;
    auth.isAuthenticated = false;
    montar(ruta);
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
  });
});
