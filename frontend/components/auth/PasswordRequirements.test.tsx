import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PasswordRequirements, passwordChecks } from './PasswordRequirements';

const estado = (pw: string) => Object.fromEntries(passwordChecks(pw).map((c) => [c.id, c.ok]));

describe('passwordChecks', () => {
  it('sólo números cumple el largo pero no la regla numérica', () => {
    expect(estado('12345678')).toEqual({ length: true, not_numeric: false });
  });

  it('cuenta caracteres como el backend, no unidades UTF-16', () => {
    expect(estado('😀😀😀😀').length).toBe(false);
  });

  it('vacía no marca ninguna como cumplida', () => {
    expect(Object.values(estado(''))).toEqual([false, false]);
  });

  it('no inventa reglas que el backend no aplica', () => {
    const labels = passwordChecks('x').map((c) => c.label.toLowerCase()).join(' ');
    expect(labels).not.toMatch(/mayúscula|especial|minúscula/);
  });
});

describe('PasswordRequirements', () => {
  it('las reglas que sólo comprueba el servidor nunca se marcan como cumplidas', () => {
    render(<PasswordRequirements password="Rio-Yaque-44" />);
    expect(screen.getByText(/al menos 8 caracteres/i).closest('li')).toHaveAttribute('data-ok', 'true');
    expect(screen.getByText(/contraseña común/i).closest('li')).not.toHaveAttribute('data-ok');
    expect(screen.getByText(/se parezca a tu correo/i).closest('li')).not.toHaveAttribute('data-ok');
  });

  it('no repite toda la lista en cada tecla: sólo el resumen es región viva', () => {
    const { container } = render(<PasswordRequirements password="abc" id="req" />);
    expect(container.querySelector('ul')).not.toHaveAttribute('aria-live');
    expect(container.querySelector('#req')).not.toBeNull();
  });
});
