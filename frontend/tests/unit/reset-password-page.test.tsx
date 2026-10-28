import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const confirmReset = vi.hoisted(() => vi.fn());
vi.mock('@/hooks/usePasswordReset', () => ({
  usePasswordReset: () => ({ confirmReset, isConfirming: false }),
}));

import ResetPasswordPage from '@/app/reset-password/page';

function montar(ruta: string) {
  const router = createMemoryRouter(
    [
      { path: '/reset-password', element: <ResetPasswordPage /> },
      { path: '/login', element: <p>login</p> },
    ],
    { initialEntries: [ruta] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

async function guardar(pw = 'Rio-Yaque-44', pw2 = pw) {
  fireEvent.change(screen.getByLabelText('Contraseña nueva'), { target: { value: pw } });
  fireEvent.change(screen.getByLabelText('Repite la contraseña'), { target: { value: pw2 } });
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /restablecer contraseña/i }));
  });
}

const invalido = () => screen.findByRole('heading', { name: 'Enlace inválido' });

beforeEach(() => {
  confirmReset.mockReset();
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.useRealTimers();
  vi.mocked(console.error).mockRestore();
});

describe('/reset-password', () => {
  it('sin uid o token muestra el enlace inválido con salida a pedir otro', async () => {
    montar('/reset-password?uid=MQ');
    await invalido();
    expect(screen.getByRole('link', { name: /pedir un enlace nuevo/i })).toHaveAttribute('href', '/forgot-password');
    expect(confirmReset).not.toHaveBeenCalled();
  });

  it.each([
    ['token', { token: ['Invalid or expired reset token.'] }],
    ['uid', { uid: ['Invalid value'] }],
  ])('un error de %s de la API también lleva al enlace inválido', async (_k, data) => {
    confirmReset.mockRejectedValue({ response: { status: 400, data } });
    montar('/reset-password?uid=MQ&token=abc');
    await guardar();
    await invalido();
  });

  it('un error de la contraseña sale en el campo', async () => {
    confirmReset.mockRejectedValue({ response: { status: 400, data: { new_password: ['Esta contraseña es demasiado común.'] } } });
    montar('/reset-password?uid=MQ&token=abc');
    await guardar();
    const msg = await screen.findByText('Esta contraseña es demasiado común.');
    expect(screen.getByLabelText('Contraseña nueva').getAttribute('aria-describedby')?.split(' ')).toContain(msg.id);
  });

  it('no inventa requisitos que el backend no aplica', () => {
    montar('/reset-password?uid=MQ&token=abc');
    expect(screen.queryByText(/mayúscula|carácter especial/i)).not.toBeInTheDocument();
    expect(screen.getByText(/al menos 8 caracteres/i)).toBeInTheDocument();
  });

  it('al guardar muestra la confirmación y lleva al login a los 5 segundos', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    confirmReset.mockResolvedValue({});
    const router = montar('/reset-password?uid=MQ&token=abc');
    await guardar();
    expect(confirmReset).toHaveBeenCalledWith({ uid: 'MQ', token: 'abc', new_password: 'Rio-Yaque-44', confirm_password: 'Rio-Yaque-44' });
    expect(screen.getByRole('heading', { name: 'Contraseña restablecida' })).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(4900);
    });
    expect(router.state.location.pathname).toBe('/reset-password');
    await act(async () => {
      vi.advanceTimersByTime(200);
    });
    expect(router.state.location.pathname).toBe('/login');
  });
});
