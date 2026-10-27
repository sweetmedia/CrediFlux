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

from palette import *  # noqa: F401,F403 — PALETTE, DARK, recolor*, theme_vars

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
