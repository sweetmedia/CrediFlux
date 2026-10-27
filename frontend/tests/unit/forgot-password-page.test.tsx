import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const post = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { post: (...args: unknown[]) => post(...args) } }));

import ForgotPasswordPage from '@/app/forgot-password/page';

function montar() {
  const router = createMemoryRouter([{ path: '/forgot-password', element: <ForgotPasswordPage /> }], {
    initialEntries: ['/forgot-password'],
  });
  const cliente = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={cliente}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

async function enviar() {
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText(/email/i), 'cajero@acme.test');
  await usuario.click(screen.getByRole('button', { name: /enviar instrucciones/i }));
}

describe('página /forgot-password', () => {
  beforeEach(() => {
    post.mockReset();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.mocked(console.error).mockRestore();
  });

  it('un 429 muestra un aviso genérico de demasiados intentos, sin el texto de la API', async () => {
    post.mockRejectedValue(
      Object.assign(new Error('Request failed with status code 429'), {
        response: { status: 429, data: { detail: 'Request was throttled. Expected available in 3599 seconds.' } },
      })
    );
    montar();

    await enviar();

    expect(await screen.findByText(/demasiados intentos/i)).toBeInTheDocument();
    expect(screen.queryByText(/throttled|status code 429/)).not.toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('un 200 sigue mostrando la confirmación', async () => {
    post.mockResolvedValue({ message: 'ok' });
    montar();

    await enviar();

    expect(await screen.findByText(/email enviado/i)).toBeInTheDocument();
  });

  // Ronda 33.1 M4: nunca el texto de la API (detail / email[0]), como en /verify-email/resend.
  it.each([
    ['un 400 con email[0]', { response: { status: 400, data: { email: ['Enter a valid email address.'] } } }],
    ['un 500 con detail', { response: { status: 500, data: { detail: 'Internal server error' } } }],
    ['un fallo de red', {}],
  ])('%s muestra un error genérico en español', async (_caso, extra) => {
    post.mockRejectedValue(Object.assign(new Error('Request failed'), extra));
    montar();

    await enviar();

    expect(await screen.findByRole('alert')).toHaveTextContent(/no pudimos enviar la solicitud/i);
    expect(screen.queryByText(/Enter a valid|Internal server|Request failed/)).not.toBeInTheDocument();
  });

  it('la validación del campo sigue siendo de zod y queda enlazada con aria-describedby', async () => {
    montar();
    const usuario = userEvent.setup();
    await usuario.type(screen.getByLabelText(/email/i), 'no-es-un-correo');
    await usuario.click(screen.getByRole('button', { name: /enviar instrucciones/i }));

    const error = await screen.findByText(/email inválido/i);
    const campo = screen.getByLabelText(/email/i);
    expect(post).not.toHaveBeenCalled();
    expect(error.id).not.toBe('');
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(campo.getAttribute('aria-describedby')?.split(' ')).toContain(error.id);
  });
});
