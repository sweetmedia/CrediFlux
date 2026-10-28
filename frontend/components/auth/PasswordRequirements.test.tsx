import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PasswordRequirements, passwordChecks } from './PasswordRequirements';

const estado = (pw: string, ctx = {}) => Object.fromEntries(passwordChecks(pw, ctx).map((c) => [c.id, c.ok]));

describe('passwordChecks', () => {
  it('sólo números cumple el largo pero no la regla numérica', () => {
    expect(estado('12345678')).toEqual({ length: true, not_numeric: false, not_similar: true });
  });

  it('parecida al correo no cumple', () => {
    expect(estado('maria2026x', { email: 'maria@x.do' }).not_similar).toBe(false);
  });

  it('parecida al nombre, aun con acentos, no cumple', () => {
    expect(estado('perez-2026!', { names: ['María', 'Pérez'] }).not_similar).toBe(false);
  });

  it('una buena contraseña cumple todo', () => {
    expect(estado('Rio-Yaque-44', { email: 'maria@x.do', names: ['María', 'Pérez'] })).toEqual({
      length: true,
      not_numeric: true,
      not_similar: true,
    });
  });

  it('vacía no marca ninguna como cumplida', () => {
    expect(Object.values(estado(''))).toEqual([false, false, false]);
  });

  it('no inventa reglas que el backend no aplica', () => {
    const labels = passwordChecks('x', {}).map((c) => c.label.toLowerCase()).join(' ');
    expect(labels).not.toMatch(/mayúscula|especial|minúscula/);
  });
});

describe('PasswordRequirements', () => {
  it('anuncia los cambios y avisa de las contraseñas comunes sin marcarlas', () => {
    render(<PasswordRequirements password="Rio-Yaque-44" ctx={{}} />);
    expect(screen.getByRole('list')).toHaveAttribute('aria-live', 'polite');
    expect(screen.getByText(/al menos 8 caracteres/i).closest('li')).toHaveAttribute('data-ok', 'true');
    expect(screen.getByText(/contraseña común/i).closest('li')).not.toHaveAttribute('data-ok');
  });
});
