import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

let currentUser: Record<string, unknown> = {};
vi.mock('@/lib/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    tenant: null,
    isAuthenticated: true,
    isLoading: false,
    refreshTenant: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));
vi.mock('@/lib/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));
vi.mock('@/lib/navigation/link', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock('@/lib/api/auth', () => ({ authAPI: { get2FAStatus: vi.fn().mockResolvedValue({}) } }));
vi.mock('@/lib/api/tenants', () => ({
  tenantsAPI: {
    getSettings: vi.fn().mockResolvedValue({ id: 1, name: 'Acme', logo: 'https://x.test/logo.png' }),
  },
}));

import SettingsGeneralPage from '@/app/settings/general/page';

const base = { id: 1, role: 'viewer', is_tenant_owner: false };

async function abrir(tab: RegExp) {
  render(<SettingsGeneralPage />);
  const usuario = userEvent.setup();
  await usuario.click(await screen.findByRole('tab', { name: tab }));
}

beforeEach(() => {
  currentUser = {};
});

describe('configuración general según settings.edit', () => {
  it('un visualizador ve el negocio en sólo lectura, sin guardar', async () => {
    currentUser = { ...base, permissions: ['settings.view'] };
    await abrir(/negocio/i);
    await waitFor(() => expect(document.querySelector('fieldset')).not.toBeNull());
    expect(document.querySelector('fieldset')?.disabled).toBe(true);
    expect(screen.queryByRole('button', { name: /guardar información del negocio/i })).toBeNull();
  });

  it('un visualizador no ve las acciones del logo', async () => {
    currentUser = { ...base, permissions: ['settings.view'] };
    await abrir(/apariencia/i);
    await screen.findByText(/logo de la empresa/i);
    expect(screen.queryByRole('button', { name: /cambiar logo|subir logo/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /guardar apariencia/i })).toBeNull();
  });

  it('con settings.edit ve guardar y las acciones del logo', async () => {
    currentUser = { ...base, role: 'admin', permissions: ['settings.view', 'settings.edit'] };
    await abrir(/apariencia/i);
    expect(await screen.findByRole('button', { name: /cambiar logo/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /guardar apariencia/i })).toBeTruthy();
    expect(document.querySelector('fieldset')?.disabled).toBe(false);
  });
});
