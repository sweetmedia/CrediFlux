/** Financieras usadas en este equipo (/select-tenant), en localStorage. */
const KEY = 'cf-recent-tenants';
const MAX = 5;
const VALIDO = /^[a-z0-9-]{1,63}$/;

function read(): string[] {
  try {
    const v = JSON.parse(window.localStorage.getItem(KEY) ?? '[]');
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string' && VALIDO.test(x)).slice(0, MAX) : [];
  } catch {
    return [];
  }
}

function add(sub: string): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify([sub, ...read().filter((x) => x !== sub)].slice(0, MAX)));
  } catch {
    /* almacenamiento bloqueado: no se recuerda */
  }
}

export const recentTenants = { read, add };
