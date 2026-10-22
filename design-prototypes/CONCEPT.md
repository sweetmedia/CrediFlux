# CrediFlux — Concept lock for AppShell variants

> **Para qué existe este archivo**: cuando se reinicia una sesión, esto es lo
> primero que debe leerse junto con el `README.md`. Aquí está el ADN visual
> de cada variante — los **no-negociables** que no pueden cambiar entre
> prototipos del mismo shell. Si construyes una página nueva (customers-list,
> loan-detail, etc.), debe respetar el ADN de la variante que el usuario
> haya elegido.

---

## Decisiones estratégicas (13-abr-2026)

### Themes finalistas: solo V1, V4, V5

V2 (Modern SaaS) y V3 (Warm Caribbean) quedan **descartados**. Los 3 themes
que se llevan a producción son:

| Theme | Archivo | Rol |
|---|---|---|
| V1 — Editorial Operational Instrument | `appshell.html` | **Default** |
| V4 — Editorial Cálido | `appshell-v4-calido.html` | **Default** (alternativa cálida) |
| V5 — Banca Latinoamericana Moderna | `appshell-v5-banca-lat.html` | Opción institucional |

Cada **tenant** elige su theme en configuración (`theme_preset` en modelo
tenant). Los defaults ofrecidos al crear un tenant son V1 y V4.

### KPIs personalizables por tenant

El dashboard NO tiene KPIs hardcoded. En producción:

- Existe un **catálogo de KPI widgets** disponibles (cartera activa, recaudado,
  balance vencido, clientes activos, mora %, próximos vencimientos, etc.).
  El catálogo está filtrado por los **módulos contratados** por el tenant.
- El admin del tenant **elige cuáles mostrar y en qué orden** desde un panel
  de configuración. Se persiste en un campo `dashboard_layout` (JSON) en el
  modelo del tenant o del usuario.
- Hay **defaults inteligentes** según el tipo de negocio (cooperativa,
  microfinanciera, prestamista).
- El KPI strip del frontend renderiza dinámicamente según esa config.

Esto se conecta con la modularización (F6): si un tenant no tiene el módulo
de Inventario, los KPIs de inventario no aparecen en su catálogo.

### Micro-iconos en KPIs: V4 hereda de V1

V1 tiene SVG inline micro-iconos contextuales en cada KPI (chevron-up verde
en cartera, triangle-alert flame en mora, users icon en clientes). V4 los
hereda — son parte del ADN editorial compartido entre V1 y V4.

---

## Contenido común a TODAS las variantes

Todo prototipo dentro del mismo shell DEBE usar exactamente los mismos
datos para que la comparación sea justa:

- **Tenant**: Cooperativa San José — slug `coop-san-jose · rd`
- **Usuario**: María Fernández — Oficial de Cobranza — avatar `MF` sage-500
- **Fecha**: Miércoles 10 · ABR · 2026
- **KPIs**:
  - Cartera activa: RD$ 12,450,000 · ↑ 4.2% vs mes anterior
  - Recaudado abril: RD$ 1,840,500 · 94% de meta RD$ 1,950,000
  - Balance vencido: RD$ 284,600 · 18 morosos
  - Clientes activos: 347 / 412 · +12 esta semana
- **Activity feed (5 items)**:
  1. Pago Juan Pérez · LN-2026-0142 · cuota 4/24 · efectivo · +RD$ 4,500 · hace 12 min
  2. Préstamo aprobado Rosa Mendoza · LN-2026-0156 · 24 cuotas · 2.5% · RD$ 75,000 · hace 34 min
  3. Recordatorio WhatsApp Carlos Díaz · vencido hace 5 días · RD$ 3,200 · hace 1 h
  4. Cliente registrado Ana Ramírez · padrón JCE confirmado · hace 2 h
  5. Visita cobrador Pedro Núñez · zona-norte · 8/10 visitados · RD$ 12,800 · hace 3 h
- **Por cobrar hoy** — total RD$ 28,400 · 7 cuotas:
  1. Miguel A. Santos · 09:00 · LN-142 · 4,500
  2. Luz Castillo · 10:30 · LN-089 · 6,200
  3. Francisco Ureña [MORA] · 11:15 · LN-201 · 3,800
  4. Elena Martínez · 14:00 · LN-178 · 5,100
  5. Ramón Torres · 16:30 · LN-067 · 8,800
  - + "Ver 2 más"
- **Nav** — 3 secciones:
  - General: Dashboard (active), Clientes (347), Préstamos (412), Pagos, Contratos
  - Operación: Comunicaciones (3), Reportes, Cobranza
  - Sistema: Configuración, Ayuda
- **Header**: breadcrumb Inicio › Dashboard, tenant pill `coop-san-jose`, búsqueda ⌘K, bell con badge 3, avatar
- **Dev banner** (bottom-right) con 5 swatches tenant: forest #163300, burgundy #3a0e1e, navy #0c1e38, teal #1a4d3a, violet #2d1b4e

Tokens compartidos: todos importan `../branding/tokens.css` y usan
`var(--color-tenant-primary)` para el accent del tenant.

---

## V1 — Editorial Operational Instrument · `appshell.html`

**Referencia**: Bloomberg Terminal × Financial Times × Muji
**Apuesta**: "Esto es una herramienta de trabajo seria"
**Estado**: ✅ construida — la favorita del founder

### ADN no-negociable

- **Tipografía como estructura**: mono (`ABC Whyte Mono`) en TODOS los datos —
  IDs, timestamps, tags, counts, kbd, no solo dinero.
- **Hairline rules en lugar de cards**: KPIs y activity feed se separan
  por dividers de 1px, NUNCA cards con shadow.
- **Display ABC Whyte Black 900 a 38px** en heading "Dashboard".
- **Sidebar tenant-colored** con masthead editorial (CrediFlux + tenant + slug
  mono uppercase).
- **Active nav por shift de weight** (no por bg fill); barra `sun-500` 2px
  como secundario.
- **Sun-500 como puntuación narrativa** — exactamente 3 lugares en todo
  el shell (barra nav activo + bullet breadcrumb + rail activity). Uso
  escasísimo, intencional.
- **Flame-500 sobre cream** para balance vencido (32px+, AA Large).
- **Paper texture**: radial dots 3% en background del contenido.
- **Pulse animation** en data freshness indicator (excepción a "no motion").
- **Colophon editorial** al pie (CrediFlux v2.0 · Santiago · Sesión 2h 14m).

---

## V2 — Modern SaaS / Soft Cards · `appshell-saas.html` — ❌ DESCARTADO

> Archivo conservado como referencia, no se lleva a producción.

---

## V3 — Warm Caribbean / Brand-Forward · `appshell-tropical.html` — ❌ DESCARTADO

> Archivo conservado como referencia, no se lleva a producción.

---

## V4 — Editorial Cálido · `appshell-v4-calido.html`

**Referencia**: V1 (Editorial) descongelada — FT Weekend Magazine × Apartamento × Kinfolk
**Apuesta**: "Misma seriedad editorial, pero respira más, tiene calidez sin perder gravitas"
**Estado**: 🚧 construyendo (10-abr-2026)

### ADN no-negociable

- **Hereda de V1**: hairline rules en lugar de cards, mono en datos,
  editorial colophon, restraint, paper texture (4% no 3% — un poco más
  presente), **micro-iconos SVG contextuales en KPIs** (chevron-up verde
  en cartera, triangle-alert flame en mora, users icon en clientes).
- **CAMBIA de V1**:
  - **Cream más saturado**: background base `#f8f4e9` (más amarillento que
    el `#faf8f2` neutro), genera el "warm paper" de revista.
  - **Sun-500 como acento HABITUAL** — no 3 puntos, sino: subrayados de KPI,
    section dividers tinted, callouts, breadcrumb separator. Sigue siendo
    decorativo (nunca text color), pero deja de ser raro verlo.
  - **Headings con ABC Whyte Bold 700** (no Black 900), tracking `-0.01em`
    en lugar de `-0.03em` — más respiración, menos "shouty".
  - **Sidebar cream** (no tenant-dark), con border-right hairline + un thin
    accent vertical sun-500 a la izquierda del activo (en lugar de fill).
  - **Logo CrediFlux real (gradient SVG colored)** en el masthead — el SVG
    radial sun→flame del isotipo aparece a tamaño moderado, integrado con
    el wordmark text.
  - **Section eyebrows** estilo magazine: small caps + sage-600 + leading
    doble (ej: "S Y N T H E S I S — RESUMEN OPERATIVO").
  - **Drop cap editorial** opcional en intros largas (no en este dashboard,
    pero declarado para páginas internas).
- **Display heading**: "Buenos días, María." (con punto, no exclamación —
  serio, cálido).

### Paleta canónica V4
| rol | token | hex |
|---|---|---|
| bg | warmer-cream | `#f8f4e9` |
| sidebar bg | cream-base | `#f5f1e4` |
| text primary | forest-900 | `#163300` |
| text secondary | sage-700 | `#4a5a3d` |
| hairlines | sage-200 con alpha | `rgba(168,184,156,0.55)` |
| accent | sun-500 | `#ffe026` (decorativo only) |
| danger | flame-600 | `#cc5e02` (texto AA Large) |

---

## V5 — Banca Latinoamericana Moderna · `appshell-v5-banca-lat.html`

**Referencia**: Banco Popular Dominicano + BHD León + Banreservas (online banking
de bancos institucionales RD modernos, no consumer fintech)
**Apuesta**: "Si Cooperativa San José fuera un cliente del BHD, esto es lo que
esperaría ver al login — institucional, confiable, formal pero amable"
**Estado**: 🚧 por construir

### ADN no-negociable

- **Sidebar deep forest** (`forest-900` con texture sutil), wordmark CrediFlux
  blanco (logo SVG real con `filter: brightness(0) invert(1)` para forzar
  blanco sobre dark). NUNCA texto-only — siempre el isotipo + wordmark.
- **Header blanco generoso** (72px alto, no 56), border-bottom hairline,
  con saludo institucional inline: "Hola, María — Cooperativa San José"
  donde "Cooperativa San José" actúa como tenant identification (no pill).
- **Hero strip institucional**: una banda forest→sage gradient debajo del
  header con `border-radius` solo bottom-corners, contiene la fecha en
  uppercase + un mini-resumen cuantitativo ("RD$ 1.84M recaudados de RD$ 1.95M
  meta — vamos al 94%"). Es la "presencia institucional" del banco.
- **4 KPI cards horizontales** — NO icon arriba, sino icon LATERAL izquierdo
  en círculo grande (48px), con number + delta a la derecha. Border-left
  3px en `var(--color-tenant-primary)` para "marca de banco". Background
  blanco, shadow muy sutil, rounded-md (no xl).
- **Activity feed = tabla institucional**: filas con padding generoso, alterna
  bg muy sutil (`#fafaf9`), columnas alineadas (icon | descripción | tipo |
  monto | hora). Header sticky. Es lo que un cajero bancario reconocería.
- **Por cobrar hoy en card lateral** con header solid forest, total al pie
  (no al principio), botón CTA "Registrar pago" abajo. Avatar circular cream
  con iniciales forest.
- **Tipografía**:
  - Plus Jakarta Sans en TODO el body
  - ABC Whyte Bold 700 SOLO en KPI big numbers + page title
  - Mono SOLO en tabular nums monetarios reales
- **Botones**: primary en `var(--color-tenant-primary)` solid, secondary outline
  forest-900, ambos rounded-md, padding generoso (h-11), font-weight 600.
- **Sin emojis** — institucional. Nada de 👋 ni 🌴.
- **Iconografía**: line icons stroke 1.75 (más finos que default 2),
  consistentes — feeling de "banca seria", no de SaaS startup.
- **Footer institucional bajo el contenido**: línea hairline + texto pequeño
  sage-600 con "Cooperativa San José · Regulado por la Superintendencia de
  Bancos · CrediFlux v2.0".

### Paleta canónica V5
| rol | token | hex |
|---|---|---|
| bg | neutral-50 | `#fafaf9` |
| sidebar bg | forest-900 | `#163300` |
| sidebar text | white | `#ffffff` |
| sidebar text muted | forest-200 | `#b5d4a0` |
| header bg | white | `#ffffff` |
| hero gradient | forest-900 → sage-600 | `#163300 → #5c6d4d` |
| card bg | white | `#ffffff` |
| card border | neutral-200 | `#e7e5e4` |
| text primary | forest-900 | `#163300` |
| text secondary | neutral-600 | `#57534e` |
| accent (border-l) | tenant-primary | `var(--color-tenant-primary)` |
| danger | flame-600 | `#cc5e02` |

### Inspiración explícita (lo que tomamos de cada banco)

- **Banco Popular Dominicano**: presencia del wordmark blanco grande sobre
  dark, hero strip institucional con datos cuantitativos resaltados, botones
  primary solid con shape rectangular generoso.
- **BHD León**: cards horizontales con icon lateral, alternancia sutil de
  filas en tablas, copy "Hola, [nombre]" sin emoji.
- **Banreservas**: footer regulatorio explícito, tipografía sans estricta sin
  display fonts decorativos, formalidad visual sin frialdad.

**Lo que NO tomamos**: ni los gradientes corporate over-the-top, ni la
densidad informática del banca empresarial, ni los popups intrusivos. Es
la versión "considerada" de banca RD moderna.

---

## Cómo trabajar con este documento

1. **Si construyes una página nueva** (customers-list, loan-detail, etc.):
   abre este archivo, elige la variante objetivo, y respeta el ADN
   no-negociable de esa variante.
2. **Si reabres una sesión sin contexto**: lee primero `README.md` para
   saber qué archivos existen, y este `CONCEPT.md` para saber qué representan.
3. **Si el founder cambia de opinión sobre una decisión** (ej: "ya no quiero
   sun como acento habitual en V4"): EDITA este archivo en el mismo commit
   que toca el HTML — el documento debe ser siempre la verdad.
4. **Si construyes una variante nueva (V6+)**: agrégala aquí con la misma
   estructura: referencia, apuesta, estado, ADN no-negociable, paleta.
