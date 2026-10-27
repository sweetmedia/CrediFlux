import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppearanceProvider } from './AppearanceProvider';
import { ThemeSwitch } from './ThemeSwitch';

let sistemaOscuro = false;

beforeEach(() => {
  sistemaOscuro = false;
  window.localStorage.clear();
  document.documentElement.className = '';
  vi.stubGlobal('matchMedia', (q: string) => ({
    matches: q.includes('dark') ? sistemaOscuro : false,
    media: q,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => vi.unstubAllGlobals());

function montar() {
  return render(
    <AppearanceProvider>
      <ThemeSwitch />
    </AppearanceProvider>,
  );
}

describe('ThemeSwitch', () => {
  it('ofrece claro, oscuro y sistema como un grupo de radios', () => {
    montar();
    expect(screen.getByRole('radiogroup', { name: 'Tema' })).toBeInTheDocument();
    expect(screen.getAllByRole('radio').map((r) => r.getAttribute('aria-label'))).toEqual([
      'Claro',
      'Oscuro',
      'Sistema',
    ]);
    expect(screen.getByRole('radio', { name: 'Sistema' })).toHaveAttribute('aria-checked', 'true');
  });

  it('Oscuro marca el radio, lo guarda y pone la clase dark', () => {
    montar();
    fireEvent.click(screen.getByRole('radio', { name: 'Oscuro' }));
    expect(screen.getByRole('radio', { name: 'Oscuro' })).toHaveAttribute('aria-checked', 'true');
    expect(window.localStorage.getItem('cf-appearance')).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('Sistema sigue al equipo cuando está en oscuro', () => {
    sistemaOscuro = true;
    window.localStorage.setItem('cf-appearance', 'light');
    montar();
    fireEvent.click(screen.getByRole('radio', { name: 'Sistema' }));
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('las flechas mueven la selección', () => {
    window.localStorage.setItem('cf-appearance', 'light');
    montar();
    const claro = screen.getByRole('radio', { name: 'Claro' });
    fireEvent.keyDown(claro, { key: 'ArrowRight' });
    expect(screen.getByRole('radio', { name: 'Oscuro' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: 'Oscuro' })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('radio', { name: 'Oscuro' }), { key: 'ArrowLeft' });
    expect(claro).toHaveAttribute('aria-checked', 'true');
  });

  it('con oscuro guardado no quita la clase dark al montar (sin destello)', async () => {
    window.localStorage.setItem('cf-appearance', 'dark');
    document.documentElement.classList.add('dark'); // lo que pone el script de index.html
    const registros: MutationRecord[] = [];
    const obs = new MutationObserver((rs) => registros.push(...rs));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'], attributeOldValue: true });
    montar();
    await act(async () => {});
    registros.push(...obs.takeRecords());
    obs.disconnect();
    // Cada registro guarda la clase anterior: tras el primero, ninguna puede venir sin dark.
    expect(registros.slice(1).map((r) => r.oldValue)).not.toContain('');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });
});
