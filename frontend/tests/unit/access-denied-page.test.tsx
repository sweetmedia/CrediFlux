import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import AccessDeniedPage from '@/app/access-denied/page';

function montar(ruta: string) {
  const router = createMemoryRouter([{ path: '/access-denied', element: <AccessDeniedPage /> }], { initialEntries: [ruta] });
  render(<RouterProvider router={router} />);
}

describe('/access-denied', () => {
  it('dice qué permiso falta y vuelve a donde estaba', () => {
    montar('/access-denied?reason=No%20puedes%20anular%20pagos&permission=payments.void&returnUrl=/payments/9');
    expect(screen.getByText('Error 403')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'No tienes permiso para esto' })).toBeInTheDocument();
    expect(screen.getByText('No puedes anular pagos')).toBeInTheDocument();
    expect(screen.getByText('payments.void')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /volver/i })).toHaveAttribute('href', '/payments/9');
    expect(screen.getByRole('link', { name: /ir al dashboard/i })).toHaveAttribute('href', '/dashboard');
  });

  it.each(['https://evil.example', '//evil.example/x', 'javascript:alert(1)', 'payments/9', '/\\evil.example', '/\t/evil.example', '/\n/evil.example'])(
    'ignora un returnUrl externo o relativo (%s)',
    (url) => {
      montar(`/access-denied?returnUrl=${encodeURIComponent(url)}`);
      expect(screen.getByRole('link', { name: /volver/i })).toHaveAttribute('href', '/dashboard');
    },
  );

  it('sin permiso en la URL no muestra la fila del permiso', () => {
    montar('/access-denied');
    expect(screen.queryByText('Permiso requerido')).not.toBeInTheDocument();
    expect(screen.getByText(/no tienes permisos para acceder a esta página/i)).toBeInTheDocument();
  });
});
