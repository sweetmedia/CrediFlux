import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({ login: vi.fn(), complete2FALogin: vi.fn() }));
vi.mock('@/lib/contexts/AuthContext', () => ({ useAuth: () => auth }));
vi.mock('@/lib/api/session', () => ({ consumeSessionEndNotice: () => null }));

import LoginPage from '@/app/login/page';

function montar() {
  const router = createMemoryRouter(
    [
      { path: '/login', element: <LoginPage /> },
      { path: '/dashboard', element: <p>tablero</p> },
    ],
    { initialEntries: ['/login'] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

async function entrar() {
  fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'maria@demo.do' } });
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'secreta-123' } });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /^entrar/i }));
  });
}

beforeEach(() => {
  auth.login.mockReset();
  auth.complete2FALogin.mockReset();
});

describe('/login', () => {
  it('pide correo y contraseña y entra al tablero', async () => {
    auth.login.mockResolvedValue({ user: {} });
    const router = montar();
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    await entrar();
    expect(auth.login).toHaveBeenCalledWith({ email: 'maria@demo.do', password: 'secreta-123' });
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'));
  });

  it('muestra el error de la API en un alert', async () => {
    auth.login.mockRejectedValue({ response: { data: { non_field_errors: ['Credenciales incorrectas.'] } } });
    montar();
    await entrar();
    expect(await screen.findByRole('alert')).toHaveTextContent('Credenciales incorrectas.');
  });

  it('con 2FA pasa al paso 2 con seis cajas y acepta un código de respaldo', async () => {
    auth.login.mockResolvedValue({ requires_2fa: true, temp_token: 'tmp' });
    auth.complete2FALogin.mockResolvedValue({});
    montar();
    await entrar();
    expect(await screen.findByText('Paso 2 de 2')).toBeInTheDocument();
    expect(screen.getAllByRole('textbox', { name: /dígito/i })).toHaveLength(6);

    fireEvent.click(screen.getByRole('button', { name: 'Usar un código de respaldo' }));
    fireEvent.change(screen.getByLabelText('Código de respaldo'), { target: { value: 'abcd1234' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /verificar y entrar/i }));
    });
    expect(auth.complete2FALogin).toHaveBeenCalledWith('ABCD1234', 'tmp', true);
  });
});
