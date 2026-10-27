"""Genera los CSS del DS para el SPA (frontend/lib/design-system/cf/) desde la
misma paleta que usa el canvas (palette.py), para que claro y oscuro no tengan
dos fuentes.

El oscuro sólo aplica dentro de `.cf-root` (pantallas ya rehechas con el DS):
las pantallas viejas siguen con sus tokens V2 hasta que se rehagan.

uso: python3 design-prototypes/_tools/export_tokens.py   (o `npm run tokens` en frontend/)
"""
from palette import HERE, PALETTE, recolor_css, theme_vars, trip

DS = HERE.parent / 'ds'
OUT = HERE.parent.parent / 'frontend/lib/design-system/cf'
DARK_SCOPE = '.dark .cf-root'
HEADER = '/* Generado por design-prototypes/_tools/export_tokens.py — no editar a mano. */\n'


def base_tokens():
    """El :root de ds/tokens.css tal cual (espacios, radios, sombras, hairlines...)."""
    css = (DS / 'tokens.css').read_text()
    return css[css.index(':root'):].strip() + '\n'


def print_reset():
    light = ';'.join(f'--{r}-{n}:{trip(h)}' for r in ('bg', 'fg', 'bd') for n, h in PALETTE.items())
    return '@media print{' + DARK_SCOPE + '{color-scheme:light;' + light + '}}\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'tokens.css').write_text(HEADER + base_tokens() + theme_vars(':root', DARK_SCOPE) + print_reset())
    bundle = (DS / 'bundle.css').read_text() + '\n' + (DS / 'patterns.css').read_text()
    (OUT / 'bundle.css').write_text(HEADER + recolor_css(bundle))
    (OUT / 'print.css').write_text(HEADER + recolor_css((DS / 'print.css').read_text()))


if __name__ == '__main__':
    main()
