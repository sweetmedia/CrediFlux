"""Convierte los volcados de dump.mjs en artboards .dc.html para el canvas de Claude Design.

Cada prototipo sale dos veces: claro y oscuro. El CSS de cada pantalla va en
project/css/<Nombre>.css y lo comparten las dos versiones. El modo oscuro no
toca el marcado: cada color de la paleta se reescribe a una variable según el
papel que hace en la declaración (fondo, texto o borde), y [data-theme=dark]
redefine esas variables.

uso: python3 _tools/build_canvas.py <dump_dir> <root> <logo_url>
"""
import json, re, sys
from pathlib import Path

DUMP, ROOT, LOGO_URL = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
PROJ = ROOT / 'project'
(PROJ / 'css').mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).resolve().parent

# --- Paleta -----------------------------------------------------------------
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

def theme_vars():
    light = []
    dark = []
    for r in ('bg', 'fg', 'bd'):
        for n, h in PALETTE.items():
            light.append(f'--{r}-{n}:{trip(h)}')
            if n in DARK[r]:
                dark.append(f'--{r}-{n}:{trip(DARK[r][n])}')
    keep_ink = ';'.join(f'--fg-{n}:{trip(PALETTE[n])}' for n in ('forest-950', 'forest-900', 'forest-800', 'forest-700', 'sage-700', 'sage-600', 'sage-500', 'sun-ink'))
    return (
        ':root,.cf-root{' + ';'.join(light) + '}\n'
        '.cf-root[data-theme=dark]{color-scheme:dark;' + ';'.join(dark) + ';' + SEMANTIC_DARK + '}\n'
        # Las zonas que ya son oscuras en claro (barra lateral, masthead, bloques verde
        # oscuro) usan blanco translúcido encima: ahí el blanco sigue siendo blanco.
        '.cf-root[data-theme=dark] :is(.sidebar,.masthead,[class*="bg-forest-9"],[class*="bg-forest-8"],.cf-sidebar)'
        '{--bg-white:255 255 255;--bd-white:255 255 255}\n'
        # Sobre amarillo el texto sigue oscuro también en oscuro.
        # El papel de un documento (vista previa de contrato, recibo) sigue claro en oscuro.
        '.cf-root[data-theme=dark] :is(.tpl-paper,.cf-paper,.cf-doc){color-scheme:light;' + ';'.join(light) + '}\n'
        '.cf-root[data-theme=dark] :is(.bg-sun-400,.bg-sun-500,.cf-btn--sun,.m-btn--sun,.m-nav__cta,[style*="--bg-sun-400))"],[style*="--bg-sun-500))"]){' + keep_ink + '}\n'
    )

SEMANTIC_DARK = ';'.join([
    '--hairline:#e8efe114', '--hairline-strong:#e8efe11f', '--hairline-input:#e8efe126', '--hairline-control:#e8efe133',
    '--tint-hover:#e8efe10a', '--tint-active:#e8efe10f', '--surface-done:#121a0f',
    '--color-tenant-primary:#0c1309', '--success:#6fbf70', '--danger:#ff7b6b', '--info:#6cb4e6',
    '--color-success:#6fbf70', '--color-danger:#ff7b6b', '--color-info:#6cb4e6',
])

FONTS = (
    ':root,.cf-root{--font-display:"ABC Whyte",system-ui,sans-serif;--font-mono:"ABC Whyte Mono",ui-monospace,monospace;'
    '--font-body:"Plus Jakarta Sans",system-ui,sans-serif}\n'
)
# ABC Whyte es trial: subida sólo a este canvas privado (decisión D1, 27-oct).
WHYTE = [('ABC Whyte', '3a45e0195eaaef454e0922998e43c3d1', '400'), ('ABC Whyte', '1d1e0aad6b6366b1c812dd497e5dbfd4', '500'),
         ('ABC Whyte', '182d44f23dcf501a858afc08911f69b9', '700'), ('ABC Whyte', '9721269690416fdcddc362445a1fd961', '900'),
         ('ABC Whyte Mono', '0df2d99d94a067988dea4cbdf7469828', '100 900')]
FONT_FACES = '\n'.join(f"@font-face{{font-family:'{f}';src:url(/_blob/{b}) format('woff2');font-weight:{w};font-style:normal;font-display:swap}}"
                        for f, b, w in WHYTE)

FONT_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400'
             '&amp;family=EB+Garamond:ital,wght@0,400;0,500;1,400&amp;family=Dancing+Script&amp;display=swap">')

SWITCH_CSS = """
.cf-theme-switch{display:inline-flex;gap:1px;border:1px solid rgb(var(--bd-sage-200));background:rgb(var(--bg-sage-50));border-radius:8px;padding:2px;margin:0 6px}
.cf-theme-switch button{display:grid;place-items:center;width:28px;height:24px;border-radius:6px;border:1px solid transparent;color:rgb(var(--fg-sage-500));background:transparent;cursor:pointer}
.cf-theme-switch button[aria-pressed=true]{background:rgb(var(--bg-white));border-color:rgb(var(--bd-sage-200));color:rgb(var(--fg-forest-900))}
.cf-root .fixed{position:absolute}
.cf-root .h-screen{height:100%}
.cf-root .min-h-screen{min-height:100%}
.cf-root[data-theme=dark] .perm-toggle:not(.on){background:#2c3627}
.cf-root[data-theme=dark] .cf-btn--destructive{background:#b03a2e;color:#fff}
"""

def switch(dark):
    def btn(label, svg, on):
        return (f'<button type="button" aria-label="{label}" aria-pressed="{"true" if on else "false"}">'
                f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
                f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{svg}</svg></button>')
    return ('<div class="cf-theme-switch" role="group" aria-label="Tema de la interfaz">'
            + btn('Tema claro', '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>', not dark)
            + btn('Tema oscuro', '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path>', dark)
            + btn('Tema automático', '<rect x="2" y="4" width="20" height="13" rx="2"></rect><path d="M8 21h8M12 17v4"></path>', False)
            + '</div>')

def clean_css(css):
    css = re.sub(r'@font-face\s*\{[^}]*\}', '', css)
    css = css.replace('100vh', '100%')
    def sel(m):
        t = m.group(1)
        if t.lstrip().startswith('@'):
            return m.group(0)
        return re.sub(r'(?<![\w.#-])(html|body)(?![\w-])', '.cf-root', t) + '{'
    css = re.sub(r'([^{};]+)\{', sel, css)
    return recolor_css(css)

TAG = re.compile(r'<([a-zA-Z][\w:-]*)((?:\s+[^\s=>/]+(?:="[^"]*")?)*)(\s*/?)>')
ATTR = re.compile(r'([^\s=>/]+)(?:="([^"]*)")?')
COLOR_ATTRS = {'fill': 'fill', 'stroke': 'stroke', 'stop-color': 'stop-color', 'color': 'color'}

def fix_markup(html, links):
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S)
    html = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', html, flags=re.S)
    # Los <style> del body ya vienen en el CSS volcado (document.styleSheets).
    html = re.sub(r'<style\b[^>]*>.*?</style>', '', html, flags=re.S)
    def tag(m):
        name, attrs, end = m.group(1), m.group(2), m.group(3)
        out, extra = [], []
        for a in ATTR.finditer(attrs):
            k, v = a.group(1), a.group(2)
            if k.lower().startswith('on'):
                continue
            if v is not None and k in COLOR_ATTRS and re.fullmatch(r'#[0-9a-fA-F]{3,6}', v.strip()):
                rv = recolor(v.strip(), 'bg' if False else 'fg')
                if rv != v.strip():
                    extra.append(f'{COLOR_ATTRS[k]}: {rv}')
            if v is not None and k == 'style':
                v = recolor_decls(v.replace('&quot;', '"')).replace('"', '&quot;')
            if v is not None and k in ('src', 'href'):
                if 'crediflux-logo' in v:
                    v = LOGO_URL
                elif v in links:
                    v = links[v]
                elif not v.startswith(('#', 'http', 'mailto:', 'tel:', '/_blob')):
                    v = '#'
            out.append(k if v is None else f'{k}="{v}"')
        if extra:
            i = next((j for j, s in enumerate(out) if s.startswith('style=')), None)
            if i is None:
                out.append('style="' + '; '.join(extra) + '"')
            else:
                out[i] = out[i][:-1].rstrip('; ') + '; ' + '; '.join(extra) + '"'
        return f'<{name}' + ''.join(' ' + s for s in out) + f'{end}>'
    html = TAG.sub(tag, html)
    return html.replace('{{', '{‍{').replace('}}', '}‍}')

PAGE_TPL = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
<link rel="stylesheet" href="./css/{css}.css">
</head>
<body>
<x-dc>
<helmet>
{font_link}
<style>body{{margin:0}}
{font_faces}</style>
</helmet>
<div class="cf-root {cls}"{theme} style="position: relative; width: {w}px; height: {h}px; overflow: hidden{style}">
{body}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
class Component extends DCLogic {{
renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
"""

def build(name, dark, links):
    d = json.loads((DUMP / f'{name}.json').read_text())
    body = fix_markup(d['body'], links)
    body = body.replace('<button class="flex items-center gap-2 h-8 pl-1 pr-2 ml-1 rounded',
                        switch(dark) + '<button class="flex items-center gap-2 h-8 pl-1 pr-2 ml-1 rounded', 1)
    cls = ' '.join(filter(None, [d['htmlClass'], d['bodyClass']]))
    style = recolor_decls(d['bodyStyle'])
    attrs = ''.join(f' {k}="{v}"' for k, v in {**d['htmlAttrs'], **d.get('bodyAttrs', {})}.items() if k.startswith('data-'))
    theme = attrs + (' data-theme="dark"' if dark else '')
    return PAGE_TPL.format(title=d['title'] + (' · oscuro' if dark else ''), css=name, font_link=FONT_LINK, font_faces=FONT_FACES,
                           cls=cls, theme=theme, h=d['height'], w=d.get('width', 1440), style=('; ' + style) if style else '', body=body)

if __name__ == '__main__':
    names = [p.stem for p in sorted(DUMP.glob('*.json'))]
    files = {}
    for n in names:
        files.setdefault(json.loads((DUMP / f'{n}.json').read_text())['file'], n)
    # Los enlaces van a la pantalla base de cada prototipo, no a uno de sus estados.
    files.update({'settings-roles.html': 'SettingsRoles', 'login.html': 'Main', 'access.html': 'AccessForgot',
                  'register.html': 'Register1', 'loan-new.html': 'LoanNew1',
                  'payment-detail.html': 'PaymentDetail', 'invoice-detail.html': 'InvoiceDetail'})
    links = {f: f'{n}.dc.html' for f, n in files.items()}
    NO_DARK = {n for n in names if n.startswith('Print')} | {'ShellV4', 'ShellV5'}
    for n in names:
        d = json.loads((DUMP / f'{n}.json').read_text())
        (PROJ / 'css' / f'{n}.css').write_text(theme_vars() + FONTS + clean_css(d['css']) + SWITCH_CSS)
        (PROJ / f'{n}.dc.html').write_text(build(n, False, links))
        if n not in NO_DARK:
            (PROJ / f'{n}Oscuro.dc.html').write_text(build(n, True, links))
        print(n, d['height'])
