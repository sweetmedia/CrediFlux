import { describe, expect, it } from 'vitest';
import { compareSortValues, parseSortValue } from './sort';

describe('parseSortValue', () => {
  it('lee montos y porcentajes como número', () => {
    expect(parseSortValue('RD$ 1,250.00', 'num')).toBe(1250);
    expect(parseSortValue('-3.5%', 'num')).toBe(-3.5);
  });

  it('los vacíos y la raya son null', () => {
    expect(parseSortValue('—', 'num')).toBeNull();
    expect(parseSortValue('-', 'num')).toBeNull();
    expect(parseSortValue('', 'text')).toBeNull();
  });

  it('lee fechas en español y en ISO', () => {
    expect(parseSortValue('10 abr 2026', 'date')).toBe(new Date(2026, 3, 10).getTime());
    expect(parseSortValue('2026-04-10', 'date')).toBe(Date.parse('2026-04-10'));
    expect(parseSortValue('ayer', 'date')).toBeNull();
  });

  it('el texto queda tal cual', () => {
    expect(parseSortValue('  Ana Ramírez ', 'text')).toBe('Ana Ramírez');
  });
});

describe('compareSortValues', () => {
  it('deja los null al final en ambos sentidos', () => {
    const vals = [3, null, 1, 2];
    expect([...vals].sort((a, b) => compareSortValues(a, b, 'asc'))).toEqual([1, 2, 3, null]);
    expect([...vals].sort((a, b) => compareSortValues(a, b, 'desc'))).toEqual([3, 2, 1, null]);
  });

  it('ordena texto con reglas del español', () => {
    expect(['Óscar', 'Ana', 'Ñoño', 'Nora'].sort((a, b) => compareSortValues(a, b, 'asc'))).toEqual([
      'Ana',
      'Nora',
      'Ñoño',
      'Óscar',
    ]);
  });
});
