"""Paleta del DS y su versión oscura, compartida por build_canvas.py (canvas)
y export_tokens.py (frontend). Cada color se reescribe a una variable según el
papel que hace en la declaración (bg fondo, fg texto, bd borde), porque el
oscuro de un mismo color cambia según ese papel."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

PALETTE = {}
for name, hx in re.findall(r'--([a-z]+(?:-[a-z]+)?(?:-\d+)?):\s*(#[0-9a-fA-F]{6})', (HERE.parent / 'ds/tokens.css').read_text()):
    PALETTE.setdefault(name, hx.lower())

def trip(hx):
    hx = hx.lstrip('#')
    return f'{int(hx[0:2],16)} {int(hx[2:4],16)} {int(hx[4:6],16)}'

# Colores sueltos de los prototipos, fuera de la escala, que también cambian en oscuro.
EXTRA = {
    'tw-border': ('#e5e7eb', {'bd': '#2c3627', 'bg': '#2c3627'}),
    'paper-1': ('#f3f1e8', {'bg': '#12170f', 'bd': '#222b1e'}),
    'paper-2': ('#f8f4e9', {'bg': '#12170f', 'bd': '#222b1e'}),
    'paper-3': ('#f5f1e4', {'bg': '#12170f'}),
    'paper-4': ('#f0ece0', {'bg': '#171e14'}),
    'paper-5': ('#ece9df', {'bg': '#1e271a', 'bd': '#2c3627'}),
    'paper-6': ('#ece5dd', {'bg': '#1e271a'}),
    'ink-deep': ('#1d2a12', {'fg': '#e8efe1'}),
    'sun-ink': ('#5c4a00', {'fg': '#f0d860'}),
    'whatsapp-deep': ('#0e6b60', {'fg': '#4fc1b2'}),
}
for n, (h, _) in EXTRA.items():
    PALETTE[n] = h

SCALE = set(EXTRA) | {n for n in PALETTE if re.match(r'(forest|sage|sun|flame|neutral)-\d+$|(cream|warm-white|white)$', n)}
BY_TRIPLET = {}
for n in PALETTE:
    if n in SCALE:
        BY_TRIPLET.setdefault(trip(PALETTE[n]), n)

# Valores oscuros por papel. Lo que no aparece conserva el valor claro.
DARK = {
    'bg': {
        'white': '#151b12', 'cream': '#0e120c', 'warm-white': '#12170f',
        'neutral-50': '#151b12', 'neutral-100': '#1a2117', 'neutral-200': '#252d21', 'neutral-300': '#323b2d',
        'sage-50': '#171e14', 'sage-100': '#1e271a', 'sage-200': '#2a3425', 'sage-300': '#3a4733',
        'forest-50': '#152210', 'forest-100': '#1b2e12', 'forest-200': '#274018', 'forest-300': '#3d5c28',
        'forest-900': '#2f5c14', 'forest-950': '#070a05',
        'sun-100': '#2a260b', 'sun-200': '#3a3410', 'sun-300': '#5c5218',
        'flame-100': '#2e1a09', 'flame-200': '#45270c',
    },
    'fg': {
        'forest-950': '#f1f5ec', 'forest-900': '#e8efe1', 'forest-800': '#d3e3c6', 'forest-700': '#b3d39b',
        'forest-600': '#9bc77e', 'forest-500': '#8cbf6a', 'forest-400': '#7fb35e',
        'sage-700': '#c9d4c0', 'sage-600': '#b1bea6', 'sage-500': '#9cad90', 'sage-400': '#86987a',
        'sage-300': '#677760', 'sage-200': '#4a5743',
        'neutral-900': '#ece9e6', 'neutral-800': '#dedad6', 'neutral-700': '#cfcac6', 'neutral-600': '#b5afa9',
        'neutral-500': '#9a938d', 'neutral-400': '#7a746f',
        'flame-700': '#ffb37a', 'flame-600': '#ff9a4d',
    },
    'bd': {
        'white': '#151b12', 'cream': '#0e120c',
        'sage-50': '#1c2419', 'sage-100': '#222b1e', 'sage-200': '#2c3627', 'sage-300': '#3b4735',
        'neutral-100': '#222b1e', 'neutral-200': '#2a3226', 'neutral-300': '#36402f',
        'forest-100': '#24371a', 'forest-200': '#2f4a1f',
        'forest-900': '#e8efe1', 'forest-950': '#e8efe1',
    },
}

for n, (_, d) in EXTRA.items():
    for r, v in d.items():
        DARK[r][n] = v

def role(prop):
    p = prop.strip().lower()
    if 'background' in p:
        return 'bg'
    if 'border' in p or 'outline' in p or 'shadow' in p or p.startswith('--tw-ring') or 'divide' in p:
        return 'bd'
    return 'fg'

RGB = re.compile(r'rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)\s*(?:[,/]\s*([^)]+?))?\s*\)')
HEX = re.compile(r'#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\b|#([0-9a-fA-F]{3})\b')
VAR = re.compile(r'var\(--((?:color-)?[a-z]+(?:-[a-z]+)?(?:-\d+)?)\)')

def recolor(value, r):
    def rgb(m):
        t = f'{m.group(1)} {m.group(2)} {m.group(3)}'
        n = BY_TRIPLET.get(t)
        a = m.group(4)
        if not n:
            return m.group(0)
        return f'rgb(var(--{r}-{n}) / {a})' if a else f'rgb(var(--{r}-{n}))'
    def hx(m):
        h = m.group(1) or ''.join(c * 2 for c in m.group(3))
        n = BY_TRIPLET.get(trip(h))
        if not n:
            return m.group(0)
        # #rrggbbaa: el alfa se conserva sobre el color del tema.
        if m.group(2):
            return f'rgb(var(--{r}-{n}) / {int(m.group(2), 16) / 255:.3f})'
        return f'rgb(var(--{r}-{n}))'
    def var(m):
        n = m.group(1).removeprefix('color-')
        return f'rgb(var(--{r}-{n}))' if n in SCALE else m.group(0)
    return VAR.sub(var, HEX.sub(hx, RGB.sub(rgb, value)))

DECL = re.compile(r'(--[\w-]+|[a-zA-Z-]+)\s*:\s*([^;]+)')

def recolor_decls(text):
    def one(m):
        prop, val = m.group(1), m.group(2)
        if prop.startswith('--') and not prop.startswith('--tw-'):
            return m.group(0)  # definiciones de tokens
        return f'{prop}: {recolor(val, role(prop))}'
    return DECL.sub(one, text)

def recolor_css(css):
    return re.sub(r'\{([^{}]*)\}', lambda m: '{' + recolor_decls(m.group(1)) + '}', css)

def theme_vars(root=':root,.cf-root', dark='.cf-root[data-theme=dark]'):
    """Variables --bg-*/--fg-*/--bd-* en claro (root) y su oscuro (dark)."""
    light, dk = [], []
    for r in ('bg', 'fg', 'bd'):
        for n, h in PALETTE.items():
            light.append(f'--{r}-{n}:{trip(h)}')
            if n in DARK[r]:
                dk.append(f'--{r}-{n}:{trip(DARK[r][n])}')
    keep_ink = ';'.join(f'--fg-{n}:{trip(PALETTE[n])}' for n in ('forest-950', 'forest-900', 'forest-800', 'forest-700', 'sage-700', 'sage-600', 'sage-500', 'sun-ink'))
    return (
        root + '{' + ';'.join(light) + '}\n'
        + dark + '{color-scheme:dark;' + ';'.join(dk) + ';' + SEMANTIC_DARK + '}\n'
        # Las zonas que ya son oscuras en claro (barra lateral, masthead, bloques verde
        # oscuro) usan blanco translúcido encima: ahí el blanco sigue siendo blanco.
        + dark + ' :is(.sidebar,.masthead,[class*="bg-forest-9"],[class*="bg-forest-8"],.cf-sidebar)'
        '{--bg-white:255 255 255;--bd-white:255 255 255}\n'
        # El papel de un documento (vista previa de contrato, recibo) sigue claro en oscuro.
        + dark + ' :is(.tpl-paper,.cf-paper,.cf-doc),' + dark + ':is(.tpl-paper,.cf-paper,.cf-doc){color-scheme:light;'
        + ';'.join(light) + ';' + SEMANTIC_LIGHT + '}\n'
        # Sobre amarillo el texto sigue oscuro también en oscuro.
        + dark + ' :is(.bg-sun-400,.bg-sun-500,.cf-btn--sun,.m-btn--sun,.m-nav__cta,[style*="--bg-sun-400))"],[style*="--bg-sun-500))"]){' + keep_ink + '}\n'
    )

# Los mismos semánticos en claro, para el papel dentro del oscuro.
SEMANTIC_LIGHT = ';'.join([
    '--hairline:#16330014', '--hairline-strong:#1633001f', '--hairline-input:#16330026', '--hairline-control:#16330033',
    '--tint-hover:#1633000a', '--tint-active:#1633000f', '--surface-done:#f7f9f5',
    '--success:#2d6a2e', '--danger:#c0392b', '--info:#2980b9',
    '--color-success:#2d6a2e', '--color-danger:#c0392b', '--color-info:#2980b9',
])

SEMANTIC_DARK = ';'.join([
    '--hairline:#e8efe114', '--hairline-strong:#e8efe11f', '--hairline-input:#e8efe126', '--hairline-control:#e8efe133',
    '--tint-hover:#e8efe10a', '--tint-active:#e8efe10f', '--surface-done:#121a0f',
    '--color-tenant-primary:#0c1309', '--success:#6fbf70', '--danger:#ff7b6b', '--info:#6cb4e6',
    '--color-success:#6fbf70', '--color-danger:#ff7b6b', '--color-info:#6cb4e6',
])

