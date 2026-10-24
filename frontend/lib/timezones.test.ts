import { describe, expect, it } from 'vitest';

import { COMMON_TIMEZONES, DEFAULT_TIMEZONE, timezoneOptions, utcOffsetLabel } from './timezones';

describe('timezones', () => {
  it('Nueva York es la zona por defecto y la primera opción', () => {
    expect(DEFAULT_TIMEZONE).toBe('America/New_York');
    expect(timezoneOptions()[0].value).toBe('America/New_York');
  });

  it('muestra el desfase y respeta el horario de verano', () => {
    expect(utcOffsetLabel('America/New_York', new Date('2026-02-10T12:00:00Z'))).toBe('UTC−05:00');
    expect(utcOffsetLabel('America/New_York', new Date('2026-07-10T12:00:00Z'))).toBe('UTC−04:00');
    expect(utcOffsetLabel('America/Santo_Domingo', new Date('2026-07-10T12:00:00Z'))).toBe('UTC−04:00');
  });

  it('no repite las zonas comunes y conserva una zona guardada desconocida', () => {
    const values = timezoneOptions('Legacy/Zone').map((o) => o.value);
    for (const { value } of COMMON_TIMEZONES) {
      expect(values.filter((v) => v === value)).toHaveLength(1);
    }
    expect(values).toContain('Legacy/Zone');
  });
});
