import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const post = vi.fn();
vi.mock('@/lib/api/client', () => ({ apiClient: { post: (...args: unknown[]) => post(...args) } }));

import ResendVerificationPage from '@/app/verify-email/resend/page';

const SEND = '/api/users/auth/verify-email/send/';
const CORREO = 'cajero@acme.test';

function montar() {
  const router = createMemoryRouter(
    [
      { path: '/verify-email/resend', element: <ResendVerificationPage /> },
      { path: '/login', element: <p>pantalla de login</p> },
    ],
    { initialEntries: ['/verify-email/resend'] }
  );
  const { container } = render(<RouterProvider router={router} />);
  return { router, container };
}

async function enviar(correo = CORREO) {
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText(/correo/i), correo);
  await usuario.click(screen.getByRole('button', { name: /enviar enlace/i }));
}

function rechazo(status: number, data: unknown = {}) {
  return Object.assign(new Error(`Request failed with status code ${status}`), {
    isAxiosError: true,
    response: { status, data },
  });
}

describe('página /verify-email/resend', () => {
  beforeEach(() => {
    post.mockReset();
  });

  it('pide el enlace una sola vez por envío y muestra el mensaje genérico', async () => {
    post.mockResolvedValue({ message: 'If an account with this email needs verification, ...' });
    montar();

    await enviar();

    expect(await screen.findByText(/si tu cuenta necesita verificación/i)).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith(SEND, { email: CORREO });
    // No repite el texto de la API (en inglés) ni dice si la cuenta existe.
    expect(screen.queryByText(/If an account/)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /iniciar sesi[oó]n/i })).toHaveAttribute('href', '/login');
  });

  it('el mensaje no cambia con el cuerpo de la respuesta 200', async () => {
    post.mockResolvedValueOnce({ message: 'uno' });
    const primero = montar();
    await enviar();
    await screen.findByText(/si tu cuenta necesita verificación/i);
    const htmlPrimero = primero.container.innerHTML;
    primero.container.remove();

    post.mockResolvedValueOnce({ message: 'otro distinto', email: CORREO });
    const segundo = montar();
    await enviar();
    await screen.findByText(/si tu cuenta necesita verificación/i);

    expect(segundo.container.innerHTML).toBe(htmlPrimero);
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('un 429 muestra el aviso genérico de demasiados intentos', async () => {
    post.mockRejectedValue(rechazo(429, { detail: 'Request was throttled. Expected available in 3599 seconds.' }));
    montar();

    await enviar();

    expect(await screen.findByText(/demasiados intentos/i)).toBeInTheDocument();
    expect(screen.queryByText(/throttled|3599/)).not.toBeInTheDocument();
    expect(screen.queryByText(/si tu cuenta necesita verificación/i)).not.toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['un fallo de red', () => new Error('Network Error')],
    ['un 500', () => rechazo(500, { detail: 'Server Error' })],
    ['un 400 de la API', () => rechazo(400, { email: ['Enter a valid email address.'] })],
  ])('%s muestra un error genérico', async (_caso, error) => {
    post.mockRejectedValue(error());
    montar();

    await enviar();

    expect(await screen.findByText(/no pudimos enviar la solicitud/i)).toBeInTheDocument();
    expect(screen.queryByText(/Network Error|Server Error|valid email/)).not.toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(1);
  });

  it('tras un error se puede volver a enviar, y cada envío llama una vez', async () => {
    post.mockRejectedValueOnce(rechazo(429)).mockResolvedValueOnce({ message: 'ok' });
    montar();

    await enviar();
    await screen.findByText(/demasiados intentos/i);
    await userEvent.setup().click(screen.getByRole('button', { name: /enviar enlace/i }));

    expect(await screen.findByText(/si tu cuenta necesita verificación/i)).toBeInTheDocument();
    expect(post).toHaveBeenCalledTimes(2);
  });

  it('un correo mal escrito no llama a la API', async () => {
    montar();

    await enviar('no-es-un-correo');

    expect(await screen.findByText(/correo inválido/i)).toBeInTheDocument();
    await waitFor(() => expect(post).not.toHaveBeenCalled());
  });

  it('usa tokens y clases del DS, sin colores crudos ni degradado fijo', async () => {
    post.mockResolvedValue({ message: 'ok' });
    const { container } = montar();
    expect(container.innerHTML).toContain('cf-surface-card');

    await enviar();
    await screen.findByText(/si tu cuenta necesita verificación/i);

    expect(container.innerHTML).not.toMatch(/text-(green|red|blue|gray)-\d|bg-gradient|#e8eddf/);
    expect(container.innerHTML).toContain('cf-surface-card');
  });
});
