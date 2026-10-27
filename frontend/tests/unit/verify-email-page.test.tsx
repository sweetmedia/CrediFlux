import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const post = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { post: (...args: unknown[]) => post(...args) } }));

import VerifyEmailPage from '@/app/verify-email/page';

const CONFIRM = '/api/users/auth/verify-email/confirm/';
const UID = 'MTIz';
const TOKEN = 'cz9k1a-0123456789abcdef0123456789abcdef';

function montar(ruta: string) {
  const router = createMemoryRouter(
    [
      { path: '/verify-email', element: <VerifyEmailPage /> },
      { path: '/login', element: <p>pantalla de login</p> },
    ],
    { initialEntries: [ruta] }
  );
  render(
    <StrictMode>
      <RouterProvider router={router} />
    </StrictMode>
  );
}

function enlaceLogin() {
  const enlace = screen.getByRole('link', { name: /iniciar sesi[oó]n/i });
  expect(enlace).toHaveAttribute('href', '/login');
  return enlace;
}

describe('página /verify-email', () => {
  const consola: ReturnType<typeof vi.spyOn>[] = [];

  beforeEach(() => {
    post.mockReset();
    for (const metodo of ['log', 'info', 'warn', 'error', 'debug'] as const) {
      consola.push(vi.spyOn(console, metodo).mockImplementation(() => {}));
    }
  });

  afterEach(() => {
    // La página nunca escribe el token (ni el uid) en la consola.
    for (const espia of consola) {
      for (const llamada of espia.mock.calls) {
        expect(JSON.stringify(llamada.map(String))).not.toContain(TOKEN);
      }
      espia.mockRestore();
    }
    consola.length = 0;
  });

  it('con uid y token confirma una sola vez (StrictMode) y muestra el éxito', async () => {
    post.mockResolvedValue({ message: 'ok' });
    montar(`/verify-email?uid=${UID}&token=${TOKEN}`);

    expect(await screen.findByText(/correo verificado/i)).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith(CONFIRM, { uid: UID, token: TOKEN });
    enlaceLogin();
  });

  it('muestra "confirmando" mientras espera la respuesta', async () => {
    post.mockReturnValue(new Promise(() => {}));
    montar(`/verify-email?uid=${UID}&token=${TOKEN}`);

    expect(await screen.findByText(/verificando tu correo/i)).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('si la API rechaza el enlace muestra el mensaje genérico de enlace inválido', async () => {
    post.mockRejectedValue({
      response: { status: 400, data: { token: ['Invalid or expired verification token.'] } },
    });
    montar(`/verify-email?uid=${UID}&token=${TOKEN}`);

    expect(await screen.findByText(/enlace inválido o vencido/i)).toBeInTheDocument();
    expect(screen.queryByText(/Invalid or expired/)).not.toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
    enlaceLogin();
  });

  it('un fallo de red también se muestra como enlace inválido', async () => {
    post.mockRejectedValue(new Error('Network Error'));
    montar(`/verify-email?uid=${UID}&token=${TOKEN}`);

    expect(await screen.findByText(/enlace inválido o vencido/i)).toBeInTheDocument();
  });

  it.each([
    ['sin token', `/verify-email?uid=${UID}`],
    ['sin uid', `/verify-email?token=${TOKEN}`],
    ['sin parámetros', '/verify-email'],
  ])('%s muestra el estado inválido sin llamar a la API', async (_caso, ruta) => {
    montar(ruta);

    expect(await screen.findByText(/enlace inválido o vencido/i)).toBeInTheDocument();
    expect(post).not.toHaveBeenCalled();
    enlaceLogin();
  });
});
