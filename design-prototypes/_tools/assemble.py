"""Ensambla una página V1 sobre _tools/shell.html (sidebar + header + DS).
uso: python3 _tools/assemble.py salida.html "Título" crumbs.html main.html extra.html prestamos|clientes|calculadora|pagos"""
import sys
out, title, crumbs, main, extra, active = sys.argv[1:7]
s = open('_tools/shell.html', encoding='utf-8').read()
rd = lambda p: open(p, encoding='utf-8').read()
s = (s.replace('{{TITLE}}', title).replace('{{CRUMBS}}', rd(crumbs)).replace('    {{MAIN}}', rd(main))
      .replace('{{EXTRA}}', rd(extra))
      )
import re
s = re.sub(r'\{\{ACT_([A-Z]+)\}\}', lambda m: ' active" aria-current="page' if m.group(1) == active.upper() else '', s)
COB = {'mesa', 'gestiones', 'recordatorios', 'cobrador', 'reportescob'}
s = s.replace('{{GRP_COBRANZA}}', 'false' if active in COB else 'true')
CON = {'contratos', 'generar', 'plantillas', 'impresos'}
s = s.replace('{{GRP_CONTRATOS}}', 'false' if active in CON else 'true')
open(out, 'w', encoding='utf-8').write(s)
