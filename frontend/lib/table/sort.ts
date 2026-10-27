/**
 * Orden de las tablas del DS (contrato de design-prototypes/ds/datatable.js):
 * montos y porcentajes como número, fechas "10 abr 2026" o ISO, vacíos ("—")
 * siempre al final, texto con reglas del español.
 */

export type SortType = 'text' | 'num' | 'date';
export type SortValue = string | number | null;

const MESES: Record<string, number> = {
  ene: 0, feb: 1, mar: 2, abr: 3, may: 4, jun: 5, jul: 6, ago: 7, sep: 8, oct: 9, nov: 10, dic: 11,
};

export function parseSortValue(raw: string, type: SortType): SortValue {
  const s = (raw ?? '').trim();
  if (!s || s === '—' || s === '-') return null;
  if (type === 'num') {
    const n = parseFloat(s.replace(/[^0-9.-]/g, ''));
    return Number.isNaN(n) ? null : n;
  }
  if (type === 'date') {
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) return Date.parse(s);
    const m = s.toLowerCase().match(/(\d{1,2})\D+([a-z]{3})\D+(\d{4})/);
    if (m && m[2] in MESES) return new Date(Number(m[3]), MESES[m[2]], Number(m[1])).getTime();
    return null;
  }
  return s;
}

export function compareSortValues(a: SortValue, b: SortValue, dir: 'asc' | 'desc'): number {
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  const r = typeof a === 'number' && typeof b === 'number' ? a - b : String(a).localeCompare(String(b), 'es');
  return dir === 'asc' ? r : -r;
}
