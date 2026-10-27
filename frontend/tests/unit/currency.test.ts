import { describe, expect, it } from 'vitest';
import { defaultConfig } from '@/lib/contexts/ConfigContext';
import { formatCurrency } from '@/lib/utils';

describe('moneda por defecto', () => {
  it('formatCurrency muestra RD$ si no se le pasa moneda', () => {
    expect(formatCurrency(1250)).toBe('RD$1,250.00');
  });

  it('respeta otra moneda cuando la financiera la elige', () => {
    expect(formatCurrency(1250, 'USD')).toContain('1,250.00');
    expect(formatCurrency(1250, 'USD')).not.toContain('RD$');
  });

  it('la configuración por defecto del tenant es DOP / RD$', () => {
    expect(defaultConfig.currency).toBe('DOP');
    expect(defaultConfig.currency_symbol).toBe('RD$');
  });
});
