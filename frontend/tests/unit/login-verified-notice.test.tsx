import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/contexts/AuthContext', () => ({
  useAuth: () => ({ login: vi.fn(), complete2FALogin: vi.fn() }),
}));
vi.mock('@/components/auth', () => ({ TwoFactorVerify: () => null }));
vi.mock('@/lib/api/session', () => ({ consumeSessionEndNotice: () => null }));

import LoginPage from '@/app/login/page';

function montar(ruta: string) {
  const router = createMemoryRouter([{ path: '/login', element: <LoginPage /> }], {
    initialEntries: [ruta],
  });
  return render(<RouterProvider router={router} />);
}

describe('/login con ?verified= (redirección de la confirmación de correo)', () => {
  it('?verified=invalid muestra un aviso de error genérico con enlace a pedir uno nuevo', async () => {
    montar('/login?verified=invalid');

    const aviso = await screen.findByText(/no pudimos verificar tu correo/i);
    expect(aviso).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /solicitar un enlace nuevo/i })).toHaveAttribute(
      'href',
      '/verify-email/resend'
    );
    expect(screen.queryByText(/verificado exitosamente/i)).not.toBeInTheDocument();
  });

  it('?verified=true sigue mostrando el aviso de éxito', async () => {
    montar('/login?verified=true');

    expect(await screen.findByText(/verificado exitosamente/i)).toBeInTheDocument();
    expect(screen.queryByText(/no pudimos verificar tu correo/i)).not.toBeInTheDocument();
  });

  it('sin parámetro no muestra ningún aviso de verificación', () => {
    montar('/login');

    expect(screen.queryByText(/verificado exitosamente/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/no pudimos verificar tu correo/i)).not.toBeInTheDocument();
  });
});
