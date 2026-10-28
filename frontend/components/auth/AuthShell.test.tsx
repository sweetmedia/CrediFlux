import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthShell } from './AuthShell';

vi.mock('@/lib/contexts/ConfigContext', () => ({
  useConfig: () => ({ config: { company_name: 'Financiera Demo' }, isLoading: false }),
}));

afterEach(() => vi.unstubAllGlobals());

function enHost(host: string) {
  vi.stubGlobal('location', { ...window.location, host, hostname: host.split(':')[0] });
}

describe('AuthShell', () => {
  it('en el host de una financiera dice a cuál se entra', () => {
    enHost('demo.localhost:3100');
    render(<AuthShell title="Iniciar sesión"><p>formulario</p></AuthShell>);
    expect(screen.getByText('Estás entrando a')).toBeInTheDocument();
    expect(screen.getByText('Financiera Demo')).toBeInTheDocument();
    expect(screen.getByText('demo.localhost:3100')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    expect(screen.getByText('formulario')).toBeInTheDocument();
  });

  it('en el host general no muestra ninguna financiera', () => {
    enHost('localhost:3000');
    render(<AuthShell title="Elige tu financiera"><p>x</p></AuthShell>);
    expect(screen.queryByText('Estás entrando a')).not.toBeInTheDocument();
    expect(screen.queryByText('Financiera Demo')).not.toBeInTheDocument();
  });

  it('usa el DS, sin switch de tema ni clases prohibidas por los tests de verificación', () => {
    enHost('demo.localhost:3100');
    const { container } = render(<AuthShell eyebrow="Acceso" title="Hola"><p>x</p></AuthShell>);
    expect(container.querySelector('.cf-root')).not.toBeNull();
    expect(container.innerHTML).not.toMatch(/text-(green|red|blue|gray)-\d|bg-gradient|#e8eddf/);
    expect(screen.queryByRole('radiogroup', { name: 'Tema' })).not.toBeInTheDocument();
    expect(screen.getByText('Acceso')).toBeInTheDocument();
  });
});
