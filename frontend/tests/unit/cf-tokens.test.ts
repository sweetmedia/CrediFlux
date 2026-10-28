import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const DIR = resolve(__dirname, '../../lib/design-system/cf');
const tokens = readFileSync(resolve(DIR, 'tokens.css'), 'utf8');
const bundle = readFileSync(resolve(DIR, 'bundle.css'), 'utf8');

/** Declaraciones `--x:r g b` de todos los bloques cuyo selector es exactamente `selector`. */
function block(selector: string): Record<string, [number, number, number]> {
  const out: Record<string, [number, number, number]> = {};
  let from = 0;
  for (;;) {
    const start = tokens.indexOf(`\n${selector}{`, from);
    if (start < 0) break;
    const body = tokens.slice(tokens.indexOf('{', start) + 1, tokens.indexOf('}', start));
    for (const m of body.matchAll(/--([\w-]+):(\d+) (\d+) (\d+)(?=;|$)/g)) {
      out[m[1]] = [Number(m[2]), Number(m[3]), Number(m[4])];
    }
    from = start + 1;
  }
  expect(Object.keys(out).length, `bloque ${selector}`).toBeGreaterThan(0);
  return out;
}

function luminance([r, g, b]: [number, number, number]) {
  const c = [r, g, b].map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}

function contrast(a: [number, number, number], b: [number, number, number]) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe('tokens del DS', () => {
  const light = block(':root');
  const dark = { ...light, ...block('.dark .cf-root') };

  it('el oscuro redefine los fondos, textos y bordes principales', () => {
    for (const v of ['bg-white', 'bg-cream', 'fg-forest-900', 'fg-sage-600', 'bd-sage-200']) {
      expect(block('.dark .cf-root')[v], v).toBeDefined();
      expect(block('.dark .cf-root')[v]).not.toEqual(light[v]);
    }
  });

  it.each([
    ['fg-forest-900', 'bg-cream'],
    ['fg-forest-900', 'bg-white'],
    ['fg-sage-600', 'bg-white'],
    ['fg-sage-600', 'bg-cream'],
  ])('%s sobre %s llega a 4.5:1 en claro y en oscuro', (fg, bg) => {
    expect(contrast(light[fg], light[bg])).toBeGreaterThanOrEqual(4.5);
    expect(contrast(dark[fg], dark[bg])).toBeGreaterThanOrEqual(4.5);
  });

  it('el papel vuelve a la paleta clara dentro del oscuro, también si es el propio cf-root', () => {
    const regla = tokens.match(/\.dark \.cf-root :is\(\.tpl-paper,\.cf-paper,\.cf-doc\),\.dark \.cf-root:is\(\.tpl-paper,\.cf-paper,\.cf-doc\)\{color-scheme:light;([^}]*)\}/);
    expect(regla, 'regla del papel').not.toBeNull();
    // Hairlines y colores de estado también en claro, no sólo la escala.
    expect(regla![1]).toContain('--hairline:#16330014');
    expect(regla![1]).toContain('--danger:#c0392b');
    expect(regla![1]).toContain('--surface-done:#f7f9f5');
  });

  it('el bundle no deja colores de la escala fijos', () => {
    expect(bundle).not.toMatch(/#e5e7eb/i);
    expect(bundle).not.toMatch(/var\(--(forest|sage|neutral)-\d+\)/);
    expect(bundle).toMatch(/rgb\(var\(--bg-forest-900\)\)/);
  });
});

describe('botón primario en oscuro', () => {
  it('no usa el casi negro del sidebar sino el verde de fondo del oscuro, con texto legible', () => {
    expect(tokens).toContain('.dark .cf-root .cf-btn--primary{background:rgb(var(--bg-forest-900))}');
    const dark = { ...block(':root'), ...block('.dark .cf-root') };
    expect(contrast(dark['bg-forest-900'], [255, 255, 255])).toBeGreaterThanOrEqual(4.5);
    expect(contrast(dark['bg-forest-900'], dark['bg-cream'])).toBeGreaterThan(1.5);
  });
});
