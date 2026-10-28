import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const replace = vi.fn();
const push = vi.fn();
const refreshUser = vi.fn();
let currentUser: Record<string, unknown> | null = null;

vi.mock('@/lib/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    tenant: null,
    isAuthenticated: true,
    isLoading: false,
    refreshUser,
  }),
}));
vi.mock('@/lib/navigation', () => ({
  useRouter: () => ({ push, replace }),
}));
vi.mock('@/lib/navigation/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

const setup2FA = vi.fn();
const verify2FA = vi.fn();
vi.mock('@/lib/api/auth', () => ({
  authAPI: {
    setup2FA: () => setup2FA(),
    verify2FA: (code: string) => verify2FA(code),
  },
}));

import Setup2FAPage from '@/app/setup-2fa/page';

const QR = 'data:image/png;base64,iVBORw0KGgo=';

beforeEach(() => {
  replace.mockReset();
  push.mockReset();
  refreshUser.mockReset().mockResolvedValue(undefined);
  setup2FA.mockReset().mockResolvedValue({ secret: 'ABCDEFGHIJKLMNOP', qr_code: QR, provisioning_uri: 'otpauth://x' });
  verify2FA.mockReset().mockResolvedValue({ message: 'ok', backup_codes: ['AAAA1111', 'BBBB2222'] });
  currentUser = { id: 1, role: 'admin', is_tenant_owner: true, is_2fa_enabled: false };
});

describe('/setup-2fa', () => {
  it('explica por qué un dueño o administrador debe activar la 2FA', () => {
    render(<Setup2FAPage />);
    expect(screen.getByText(/tu cuenta es de dueño o administrador/i)).toBeInTheDocument();
    expect(screen.getByText(/autorizar reversos de pagos/i)).toBeInTheDocument();
  });

  it('muestra el QR de TwoFactorSetup al comenzar', async () => {
    const usuario = userEvent.setup();
    render(<Setup2FAPage />);
    await usuario.click(screen.getByRole('button', { name: /activar verificación en dos pasos/i }));
    await usuario.click(await screen.findByRole('button', { name: /comenzar/i }));
    const qr = await screen.findByAltText(/qr code for 2fa/i);
    expect(qr).toHaveAttribute('src', QR);
    expect(setup2FA).toHaveBeenCalledTimes(1);
  });

  it('al terminar refresca el usuario y va al dashboard', async () => {
    const usuario = userEvent.setup();
    render(<Setup2FAPage />);
    await usuario.click(screen.getByRole('button', { name: /activar verificación en dos pasos/i }));
    await usuario.click(await screen.findByRole('button', { name: /comenzar/i }));
    await screen.findByAltText(/qr code for 2fa/i);
    await usuario.click(screen.getByRole('button', { name: /siguiente/i }));
    await usuario.type(await screen.findByRole('textbox'), '123456');
    await usuario.click(screen.getByRole('button', { name: /^verificar$/i }));
    expect(verify2FA).toHaveBeenCalledWith('123456');
    // Códigos de respaldo (BackupCodesDisplay) y cierre
    await screen.findByText('AAAA1111');
    await usuario.click(screen.getByRole('button', { name: /he guardado mis codigos/i }));
    await waitFor(() => expect(refreshUser).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/dashboard'));
  });

  it('si ya tiene 2FA no ofrece activarla y enlaza al dashboard', () => {
    currentUser = { ...currentUser, is_2fa_enabled: true };
    render(<Setup2FAPage />);
    expect(screen.queryByRole('button', { name: /activar verificación en dos pasos/i })).toBeNull();
    expect(screen.getByRole('link', { name: /ir al panel/i })).toHaveAttribute('href', '/dashboard');
  });
});
