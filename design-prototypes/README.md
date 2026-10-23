# CrediFlux — Design prototypes

Standalone HTML prototypes for iterating on visual design **before** implementing
pages in the Next.js dashboard (`/opt/crediflux/frontend`). These are not
integrated into the real app — they are design targets.

Each prototype:
- Imports the real `tokens.css` from `../branding/tokens.css`
- Uses the real self-hosted fonts from `../branding/fonts/`
- Loads Tailwind via CDN (fine for prototypes; the real app uses PostCSS)
- Includes realistic Spanish content (no lorem ipsum)
- Uses the same color / spacing / font tokens the real implementation will use

## How to open

The prototypes load fonts via relative paths (`../branding/fonts/...`). Some
browsers block cross-directory font loading via `file://`. **Serve the repo root
with a local web server** — don't double-click the HTML files:

```bash
cd /opt/crediflux
python3 -m http.server 8765
```

Then visit:
- http://localhost:8765/design-prototypes/appshell.html — Variante 1 desktop (Editorial Operational Instrument)
- http://localhost:8765/design-prototypes/appshell-mobile.html — Variante 1 mobile
- http://localhost:8765/design-prototypes/appshell-saas.html — Variante 2 desktop (Modern SaaS / Soft Cards)
- http://localhost:8765/design-prototypes/appshell-tropical.html — Variante 3 desktop (Warm Caribbean / Brand-Forward)
- http://localhost:8765/design-prototypes/appshell-v4-calido.html — Variante 4 desktop (Editorial Cálido)
- http://localhost:8765/design-prototypes/appshell-v5-banca-lat.html — Variante 5 desktop (Banca Latinoamericana Moderna)

(Any port works; 8765 picked so it won't collide with Next 3000 or landing 3610.)

> **El ADN de cada variante** (no-negociables, paleta canónica, qué heredan
> entre sí) vive en `CONCEPT.md`. Léelo antes de construir páginas nuevas
> dentro de cualquier shell.

## Las 5 variantes de AppShell

Cinco direcciones distintas para presentar a los socios. Las 5 usan los mismos
`tokens.css` y fonts self-hosted, y comparten el mismo contenido (Cooperativa
San José, María Fernández, mismas KPIs y actividad) para que la comparación
sea justa — solo cambia el lenguaje visual.

| Variante | Archivo | Referencia | Apuesta |
|---|---|---|---|
| 1 — Editorial Operational Instrument | `appshell.html` | Bloomberg Terminal × Financial Times × Muji | "Esto es una herramienta de trabajo seria" |
| 2 — Modern SaaS / Soft Cards | `appshell-saas.html` | Linear × Vercel × Stripe | "Familiar, moderno, lo que la gente espera" |
| 3 — Warm Caribbean / Brand-Forward | `appshell-tropical.html` | Branding tropical + sun/flame protagonistas | "Esto es de aquí, tiene personalidad" |
| 4 — Editorial Cálido | `appshell-v4-calido.html` | FT Weekend Magazine × Apartamento × Kinfolk | "Restraint editorial, pero respira y tiene calidez" |
| 5 — Banca Latinoamericana Moderna | `appshell-v5-banca-lat.html` | Banco Popular Dominicano + BHD León + Banreservas | "Confiable e institucional, formal pero amable" |

### Variante 1 — `appshell.html` (Editorial Operational Instrument)

The canonical container every authenticated dashboard page will render inside.
Demonstrates:

- **Sidebar** (240px, tenant-primary colored) with editorial masthead, global
  search trigger (`⌘K`), 7 nav groups (1 active, 1 expanded collapsible, 4
  collapsed collapsibles, 2 flat), user profile footer with logout
- **Header** (sticky, cream, 56px) with breadcrumb + current page, data freshness
  pulse indicator, tenant switcher, search button, reminder bell with flame
  badge (3), user menu
- **Main content** — a realistic Dashboard page stub: page header with display
  heading, 4-KPI strip separated by vertical hairlines (NOT cards), activity
  feed with colored status rails, "Por cobrar hoy" sidebar panel with itemized
  list and mora tag
- **Dev-only tenant theme switcher** in the bottom-right corner — click any of
  the 5 color swatches to prove the entire shell re-themes via one CSS
  variable (`--color-tenant-primary`). Works across forest, burgundy, navy,
  teal, violet.
- Working collapsible groups (click any non-flat group header)
- Working `⌘K` keyboard shortcut (no-op in prototype, wired for demo)

### Variante 2 — `appshell-saas.html` (Modern SaaS / Soft Cards)

La opción "safe modern". El lenguaje visual al que cualquier usuario de Linear,
Notion, Stripe o Vercel está acostumbrado. Demuestra:

- **Sidebar blanca** con border-right gris cálido (no tenant-colored). El nav
  activo es una pill rellena en `var(--color-tenant-primary)` — la única
  variación de color en el sidebar.
- **Plus Jakarta Sans en TODO**, incluyendo títulos. ABC Whyte queda fuera —
  esta variante apuesta por la familiaridad sans, no por lo editorial.
- **Mono solo donde es tabular num real** (números de KPI, montos). Nada de
  IDs en mono ni timestamps tracked-out.
- **4 KPI cards reales** con shadow-sm, rounded-xl, icon chip arriba a la
  izquierda. Hover sube el shadow. Una de las cards (balance vencido) tiene
  border flame para señalizar urgencia sin gritar.
- **Activity feed dentro de un card grande** con tabs Hoy/Semana/Mes en el
  header. Cada item es una row con icon medallion + título + pill chip de tipo +
  monto a la derecha. Background hover sutil.
- **"Por cobrar hoy" como card lateral** con avatar circular para cada cliente.
- **Header con search pill** centralizado, tenant switcher pill, icon buttons
  rounded-lg, avatar dropdown.
- **Saludo "Hola, María 👋"** con emoji y subtitle de contexto operativo.
- **Sin paper texture, sin colophon editorial, sin pulse indicator** — todo
  el "extra" de la variante 1 se omite a propósito.

Es el shell más conservador. Lo elegimos si los socios quieren minimizar
el riesgo de "se ve raro" para usuarios nuevos.

### Variante 3 — `appshell-tropical.html` (Warm Caribbean / Brand-Forward)

La opción "stand out". Más color, más decoración, más identidad. Demuestra:

- **Sidebar tenant-colored** con dos esferas radiales decorativas (sun + flame)
  difuminadas en las esquinas, dándole un sense de "esto es nuestro brand,
  no un template".
- **Wordmark gigante** "Credi**flux**" con la "flux" en sun-500. ABC Whyte
  Black 900 a 22px. El brand grita.
- **Nav activo en sun-500 sólido sobre forest** con shadow warm — el contraste
  es máximo, el feedback es imposible de no ver.
- **Hero strip de saludo** con gradient radial sun→flame, "¡Buenos días, María!"
  donde "María" tiene un text gradient sun→flame, copy contextual con emoji
  tropical 🌴, y CTAs como pills (uno con gradient sun, otro forest gradient).
- **4 KPI cards con accent stripe arriba** en gradient (forest, sun, flame,
  sage) — cada KPI tiene su "personalidad" cromática. Hover sube las cards.
- **ABC Whyte Black 900 en TODOS los números grandes** (display font protagónica).
- **Activity feed con medallion icons en gradients warm** (good/sun/flame/sage).
  Cada row es más voluminosa, más "card-like".
- **Por cobrar hoy con header gradient sun→flame**, avatar circular para cada
  cliente, item de Mora con background flame muy sutil + avatar gradient flame.
- **Botón "Ver 2 más" en gradient sun** — la decoración es la regla, no la
  excepción.
- **Header con icon buttons circulares** (rounded-full) con border cream,
  badge sun→flame en el bell, y pill switcher de tenant.

Es el shell más brand-forward. Lo elegimos si los socios quieren que CrediFlux
se vea distinto a TODO lo demás en el mercado fintech latino.

### Variante 4 — `appshell-v4-calido.html` (Editorial Cálido)

Hereda todo el restraint editorial de la V1 — hairlines en lugar de cards,
mono en datos, paper texture, colophon — pero con la temperatura subida.
Demuestra:

- **Cream más saturado** (`#f8f4e9`) — el background tiene tono "warm paper"
  de revista, no el cream neutro de la V1.
- **Sun-500 como acento HABITUAL** (no la regla "3 puntos" de V1):
  subrayados de KPI, breadcrumb separator (sun bullet), eyebrows tinted,
  rail de activity, kbd, hover de nav. Sigue siendo decorativo, nunca text.
- **ABC Whyte Bold 700 a 44px** en heading "Buenos días, María." (no Black 900,
  no exclamación) con tracking más relajado — más respiración, menos shouty.
- **Logo CrediFlux real** (gradient SVG colored) en el masthead, sobre la
  cream sidebar — no white, no monochrome.
- **Sidebar cream** (`#f5f1e4`) con thin sun-500 left rail en el activo en
  lugar de fill. Hairline border, nada tenant-dark.
- **Section eyebrows estilo magazine**: small caps + sage-600 + dot bullets
  sun ("Sección II ● Movimientos").
- **KPI strip ruled** con divisores verticales y subrayado sun (24px) bajo
  cada figure — el sun actúa como underline editorial.
- **Editorial colophon** al pie con un hairline-sun (gradient sun→transparent).

Es el shell que toma "lo que le gusta al usuario" de la V1 y le baja la
gravedad: la misma seriedad editorial, pero más cálida y respirada. Punto
medio entre V1 (austera) y V3 (decorativa).

### Variante 5 — `appshell-v5-banca-lat.html` (Banca Latinoamericana Moderna)

Inspirado explícitamente en la banca institucional dominicana
(Banco Popular, BHD León, Banreservas) — formal pero amable, lo que un
cliente del BHD esperaría ver al login en su sucursal. Demuestra:

- **Sidebar deep forest** (`forest-900` con texture sutil de líneas
  diagonales 1.5%) con el wordmark **CrediFlux real** forzado a blanco vía
  `filter: brightness(0) invert(1)` — el SVG original con todos sus
  gradientes funciona sin tener que crear una versión monocromo.
- **Header generoso (72px)** con saludo institucional inline:
  "Hola, María — Cooperativa San José" donde el tenant actúa como
  identification, no como pill flotante.
- **Hero strip institucional** con gradient `forest-900 → forest-700 → sage-600`
  + glow radial sun sutil en la esquina, conteniendo la fecha en eyebrow sun
  + un mini-resumen cuantitativo destacado ("Recaudo de abril al **94%**
  de la meta") con CTAs blancos sobre el gradient. Es la "presencia
  institucional" del banco — el momento "estás en sucursal".
- **4 KPI cards horizontales** con icon en círculo lateral 52px (no top),
  border-left 3px en `var(--color-tenant-primary)` — el "stamp del banco" en
  cada card. Una card (balance vencido) tiene border flame.
- **Activity feed = tabla institucional** con header sticky, columnas
  alineadas (icon | operación | cliente/ref | monto | hora), alterna bg
  `#fafaf9` muy sutil. Es lo que un cajero bancario reconocería como
  "mis movimientos".
- **Por cobrar hoy con header forest sólido**, total al PIE (no al inicio)
  con border-top `forest-900` 2px, y un botón CTA full-width "Registrar pago"
  cosido al fondo del card. Avatar circular cream con iniciales forest, mora
  con bg flame muy sutil.
- **Tipografía**: Plus Jakarta Sans en TODO + ABC Whyte Bold 700 SOLO en KPI
  big numbers + page title del hero. Mono SOLO en montos.
- **Iconografía stroke-1.75** (más fina que default 2) — feeling de "banca
  seria", no de SaaS startup.
- **Sin emojis** — institucional. Nada de 👋 ni 🌴.
- **Footer regulatorio** al pie: "Cooperativa San José · Regulado por la
  Superintendencia de Bancos de la República Dominicana · Plataforma
  CrediFlux v2.0 · Términos · Privacidad · Soporte" — explícito, formal.

Es el shell más conservador-pero-confiado. Lo elegimos si los socios
priorizan que el producto se sienta como "banca real RD" y no como un
fintech startup. Punto medio entre V2 (SaaS familiar) y V3 (brand-forward).

### `appshell-mobile.html` — mobile AppShell (Variante 1)

Same app shell adapted for mobile. Rendered inside a faux phone frame (390×844)
so you can see it in context on a desktop browser. Demonstrates:

- **Top header bar** (tenant-colored, 56px) with hamburger on left, CrediFlux
  wordmark centered, bell + avatar on right
- **Sheet sidebar** — tap the hamburger to slide it in from the left; backdrop
  dims the content. Tap the backdrop or the X button to close.
- **Single-column content** — dashboard condensed: page header, 2×2 KPI grid
  with abbreviated RD$ values (12.45M, 1.84M, 284.6K, 347/412), "Por cobrar
  hoy" list
- Same tenant theme switcher as desktop

## Design decisions to discuss

Read the notes in the closing message that accompanied this prototype. The
"editorial operational instrument" direction is deliberate — we're leaving
generic SaaS aesthetics on the table and committing to something that looks
like a Bloomberg Terminal × The Economist × Dominican warmth. Specific
decisions to push back on or validate:

1. **Typography as structure** — mono in every piece of data (not just money)
2. **Hairline rules, not cards** — content hierarchy via dividers
3. **Active nav via typographic weight shift**, bar is secondary
4. **Sun-500 as narrative punctuation only** (3 places in the whole shell)
5. **Flame-500 on cream for bad numbers** — uses AA Large allowance
6. **Editorial masthead** at the top of the sidebar, not just a logo
7. **Paper texture** in the content bg (radial dots at 3% opacity)
8. **Pulse indicator** for data freshness (one of the only motion exceptions)
9. **Editorial colophon** at the bottom of the content area

Once we agree on the shell, we move to the customers cluster (list, profile,
new-customer flow) using the same vocabulary.

## Not designed yet

These will be added as separate prototypes during F3 design:

- `customers-list.html` — lista con KPIs + chips + tabla densa
- `customer-profile.html` — perfil 70/30 con 4 KPI cards de riesgo
- `customer-new.html` — flujo 2-pasos con lookup JCE
- `loans-list.html` — lista de préstamos con galería de garantías
- `loan-detail.html` — detalle con cronograma + garantías
- `loan-new-wizard.html` — wizard nuevo (reemplaza el jumbo de 2352 LOC)
- `payments-new.html` — registro rápido
