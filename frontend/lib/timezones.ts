/**
 * Zonas horarias para la configuración del tenant.
 *
 * El backend valida contra la base IANA; aquí mostramos primero las zonas más
 * usadas por las financieras y después todas las que conoce el navegador.
 */

export const DEFAULT_TIMEZONE = 'America/New_York';

export const COMMON_TIMEZONES: { value: string; label: string }[] = [
  { value: 'America/New_York', label: 'Nueva York (Este de EE. UU.)' },
  { value: 'America/Santo_Domingo', label: 'Santo Domingo (República Dominicana)' },
  { value: 'America/Puerto_Rico', label: 'San Juan (Puerto Rico)' },
  { value: 'America/Chicago', label: 'Chicago (Centro de EE. UU.)' },
  { value: 'America/Denver', label: 'Denver (Montaña de EE. UU.)' },
  { value: 'America/Los_Angeles', label: 'Los Ángeles (Pacífico de EE. UU.)' },
  { value: 'America/Mexico_City', label: 'Ciudad de México' },
  { value: 'America/Bogota', label: 'Bogotá' },
  { value: 'America/Lima', label: 'Lima' },
  { value: 'America/Caracas', label: 'Caracas' },
  { value: 'America/Santiago', label: 'Santiago de Chile' },
  { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires' },
  { value: 'Europe/Madrid', label: 'Madrid' },
  { value: 'UTC', label: 'UTC' },
];

/** Desfase actual de una zona, p. ej. "UTC−05:00". */
export function utcOffsetLabel(timeZone: string, at: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      timeZoneName: 'longOffset',
    }).formatToParts(at);
    const name = parts.find((p) => p.type === 'timeZoneName')?.value ?? 'GMT';
    const offset = name.replace('GMT', '') || '+00:00';
    return `UTC${offset.replace('-', '−')}`;
  } catch {
    return '';
  }
}

/** Opciones del selector: comunes primero, luego el resto (sin repetir). */
export function timezoneOptions(current?: string): { value: string; label: string }[] {
  const common = COMMON_TIMEZONES.map(({ value, label }) => ({
    value,
    label: `${label} · ${utcOffsetLabel(value)}`,
  }));
  const seen = new Set(common.map((o) => o.value));
  const all = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [];
  const rest = all
    .filter((tz) => !seen.has(tz))
    .map((tz) => ({ value: tz, label: `${tz.replace(/_/g, ' ')} · ${utcOffsetLabel(tz)}` }));
  if (current && !seen.has(current) && !all.includes(current)) {
    rest.unshift({ value: current, label: current });
  }
  return [...common, ...rest];
}
