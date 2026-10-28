import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const reversePayment = vi.fn();
const getReverseAuthorizers = vi.fn();
vi.mock('@/lib/api/loans', () => ({
  paymentsAPI: {
    reversePayment: (...args: unknown[]) => reversePayment(...args),
    getReverseAuthorizers: () => getReverseAuthorizers(),
  },
}));

import { ReversePaymentDialog } from '@/components/payments/ReversePaymentDialog';

function renderDialog(overrides: Partial<React.ComponentProps<typeof ReversePaymentDialog>> = {}) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    paymentId: 'pago-1',
    onReversed: vi.fn(),
    ...overrides,
  };
  render(<ReversePaymentDialog {...props} />);
  return props;
}

async function llenar(usuario: ReturnType<typeof userEvent.setup>, codigo = '123456') {
  await screen.findByRole('option', { name: /ana dueña · dueño/i });
  await usuario.type(screen.getByLabelText(/motivo del reverso/i), 'Pago duplicado');
  await usuario.selectOptions(screen.getByLabelText(/^autoriza$/i), '7');
  await usuario.type(screen.getByLabelText(/código de verificación/i), codigo);
}

beforeEach(() => {
  reversePayment.mockReset();
  getReverseAuthorizers.mockReset().mockResolvedValue([
    { id: 7, full_name: 'Ana Dueña', role_label: 'Dueño' },
    { id: 9, full_name: 'Luis Admin', role_label: 'Administrador' },
  ]);
});

describe('diálogo de reverso con autorización TOTP', () => {
  it('envía motivo, autorizador y código, y cierra al terminar', async () => {
    reversePayment.mockResolvedValue({ message: 'ok' });
    const usuario = userEvent.setup();
    const props = renderDialog();

    const confirmar = screen.getByRole('button', { name: /revertir pago/i });
    expect(confirmar).toBeDisabled();
    await llenar(usuario);
    expect(confirmar).toBeEnabled();
    await usuario.click(confirmar);

    await waitFor(() =>
      expect(reversePayment).toHaveBeenCalledWith('pago-1', 'Pago duplicado', 7, '123456')
    );
    await waitFor(() => expect(props.onReversed).toHaveBeenCalled());
    expect(props.onOpenChange).toHaveBeenCalledWith(false);
  });

  it('el código sólo admite 6 dígitos', async () => {
    const usuario = userEvent.setup();
    renderDialog();
    await llenar(usuario, '12a34');
    expect(screen.getByLabelText(/código de verificación/i)).toHaveValue('1234');
    expect(screen.getByRole('button', { name: /revertir pago/i })).toBeDisabled();
  });

  it('muestra los intentos que quedan y sigue abierto', async () => {
    reversePayment.mockRejectedValue({
      response: { status: 400, data: { code: ['Código incorrecto. Quedan 2 intentos.'] } },
    });
    const usuario = userEvent.setup();
    const props = renderDialog();
    await llenar(usuario);
    await usuario.click(screen.getByRole('button', { name: /revertir pago/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Código incorrecto. Quedan 2 intentos.');
    expect(props.onOpenChange).not.toHaveBeenCalledWith(false);
    expect(props.onReversed).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/código de verificación/i)).toHaveValue('');
  });

  it('muestra el bloqueo de 15 minutos (429)', async () => {
    reversePayment.mockRejectedValue({
      response: {
        status: 429,
        data: { detail: 'Autorización bloqueada 15 minutos por intentos fallidos.' },
      },
    });
    const usuario = userEvent.setup();
    renderDialog();
    await llenar(usuario);
    await usuario.click(screen.getByRole('button', { name: /revertir pago/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/bloqueada 15 minutos/i);
  });

  it('avisa cuando nadie puede autorizar', async () => {
    getReverseAuthorizers.mockResolvedValue([]);
    renderDialog();
    expect(await screen.findByText(/nadie puede autorizar todavía/i)).toBeInTheDocument();
  });
});
