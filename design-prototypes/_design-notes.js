/* ================================================================
 * CrediFlux — Design Notes Panel
 * Self-contained injector. Add via:
 *   <script src="_design-notes.js"></script>
 * before </body>. Detects current variant by filename, mounts a
 * floating "Notas de diseño" button bottom-left + slide-in panel
 * from the right with the variant's full design rationale.
 *
 * To remove: delete the single <script> tag from the HTML file.
 * No other dependencies. Styles are self-contained inside a
 * #cf-notes-root scope so they cannot leak into the prototype.
 * ================================================================ */
(function () {
  'use strict';

  // ── Variant data — sourced from CONCEPT.md, condensed for panel ──
  const VARIANTS = {
    'appshell.html': {
      key: 'v1',
      name: 'V1 — Editorial Operational Instrument',
      tagline: 'Esto es una herramienta de trabajo seria',
      reference: 'Bloomberg Terminal × Financial Times × Muji',
      status: '✅ Construida — favorita del founder',
      summary: 'La opción "instrumento operativo". Restraint editorial radical: hairlines en lugar de cards, mono en TODOS los datos, sun como puntuación narrativa solo en 3 lugares de toda la pantalla. Es la antítesis del SaaS genérico.',
      nonNegotiables: [
        '<b>Tipografía como estructura</b>: mono (ABC Whyte Mono) en TODOS los datos — IDs, timestamps, tags, counts, kbd. No solo dinero.',
        '<b>Hairline rules en lugar de cards</b>: KPIs y activity feed se separan por dividers de 1px, NUNCA cards con shadow.',
        '<b>Display ABC Whyte Black 900 a 38px</b> en heading "Dashboard".',
        '<b>Sidebar tenant-colored</b> con masthead editorial (CrediFlux + tenant + slug mono uppercase).',
        '<b>Active nav por shift de weight</b> (no por bg fill); barra sun-500 2px como secundario.',
        '<b>Sun-500 como puntuación narrativa</b> — exactamente 3 lugares en todo el shell. Uso escasísimo, intencional.',
        '<b>Flame-500 sobre cream</b> para balance vencido (32px+, AA Large allowance).',
        '<b>Paper texture</b>: radial dots 3% en background del contenido.',
        '<b>Pulse animation</b> en data freshness indicator (única excepción a "no motion").',
        '<b>Colophon editorial</b> al pie (CrediFlux v2.0 · Santiago · Sesión 2h 14m).',
      ],
      palette: [
        ['#faf8f2', 'cream'],
        ['#163300', 'forest-900'],
        ['#738566', 'sage-500'],
        ['#ffe026', 'sun-500 (decorative only)'],
        ['#cc5e02', 'flame-600 (overdue)'],
      ],
    },
    'appshell-mobile.html': {
      key: 'v1m',
      name: 'V1 mobile — Editorial Operational Instrument',
      tagline: 'Same DNA, condensed for the phone',
      reference: 'V1 desktop adaptado a 390×844',
      status: '✅ Construida',
      summary: 'Mobile shell renderizado dentro de un faux phone frame para verlo en contexto desde un browser desktop. Mantiene el ADN editorial de V1: mono en datos, hairline rules, masthead editorial, sun como puntuación.',
      nonNegotiables: [
        '<b>Top header bar</b> tenant-colored (56px) con hamburger izquierda, wordmark centrado, bell + avatar derecha.',
        '<b>Sheet sidebar</b> que entra desde la izquierda al tap del hamburger, con backdrop dim.',
        '<b>Single-column content</b>: page header, 2×2 KPI grid con valores abreviados (12.45M, 1.84M, 284.6K, 347/412), "Por cobrar hoy" en lista.',
        '<b>Mismo lenguaje visual</b> que V1 desktop — no es una variante distinta, es la versión responsive.',
      ],
      palette: [
        ['#faf8f2', 'cream'],
        ['#163300', 'forest-900'],
        ['#738566', 'sage-500'],
        ['#ffe026', 'sun-500'],
        ['#cc5e02', 'flame-600'],
      ],
    },
    'appshell-saas.html': {
      key: 'v2',
      name: 'V2 — Modern SaaS / Soft Cards',
      tagline: 'Familiar y moderno — lo que la gente espera',
      reference: 'Linear × Vercel × Stripe × Notion',
      status: '✅ Construida',
      summary: 'La opción "safe modern". El lenguaje visual al que cualquier usuario de Linear, Notion, Stripe está acostumbrado. La elegimos si los socios quieren minimizar el riesgo de "se ve raro" para usuarios nuevos.',
      nonNegotiables: [
        '<b>Sidebar blanca</b> con border-right neutral, NO tenant-colored.',
        '<b>Plus Jakarta Sans en TODO</b>, incluyendo títulos. ABC Whyte queda fuera — esta variante apuesta por la familiaridad sans.',
        '<b>Cards con shadow-sm + rounded-xl</b> son la unidad atómica de layout. Hover sube el shadow.',
        '<b>Mono solo para tabular nums reales</b> (montos, KPI big numbers). Nada de IDs en mono ni timestamps tracked-out.',
        '<b>Active nav = pill rellena</b> en var(--color-tenant-primary).',
        '<b>KPI cards</b> con icon chip 36×36 arriba a la izquierda. Una card (balance vencido) tiene border flame-200 para señalizar urgencia sin gritar.',
        '<b>Activity feed dentro de un card grande</b> con tabs Hoy/Semana/Mes.',
        '<b>Saludo "Hola, María 👋"</b> con emoji.',
        '<b>Sin paper texture, sin colophon, sin pulse</b> — todo el "extra" de V1 se omite a propósito.',
      ],
      palette: [
        ['#fafafa', 'neutral-50'],
        ['#ffffff', 'card white'],
        ['#163300', 'forest-900 text'],
        ['#e7e5e4', 'neutral-200 border'],
        ['#ff7503', 'flame-500 accent'],
      ],
    },
    'appshell-tropical.html': {
      key: 'v3',
      name: 'V3 — Warm Caribbean / Brand-Forward',
      tagline: 'Esto es de aquí, tiene personalidad',
      reference: 'Branding tropical CrediFlux con sun + flame protagónicos',
      status: '✅ Construida',
      summary: 'La opción "stand out". Más color, más decoración, más identidad. La elegimos si los socios quieren que CrediFlux se vea distinto a TODO lo demás en el mercado fintech latino.',
      nonNegotiables: [
        '<b>Sidebar tenant-colored</b> con DOS esferas radiales decorativas (sun + flame) difuminadas en las esquinas.',
        '<b>Wordmark gigante</b> "Credi<b>flux</b>" con la "flux" en sun-500. ABC Whyte Black 900 a 22px.',
        '<b>Active nav en sun-500 sólido sobre forest</b> con shadow warm — contraste máximo.',
        '<b>Hero strip de saludo</b> con gradient radial sun→flame, "¡Buenos días, María!" con text gradient sun→flame, copy con emoji 🌴.',
        '<b>4 KPI cards con accent stripe arriba</b> en gradient (forest, sun, flame, sage).',
        '<b>ABC Whyte Black 900 en TODOS los números grandes</b> — display font protagónica.',
        '<b>Activity feed con medallion icons en gradients warm</b> — rows voluminosas, card-like.',
        '<b>Por cobrar hoy con header gradient sun→flame</b>, item de Mora con bg flame sutil.',
        '<b>Botones en gradient sun</b>, decoración es la regla.',
      ],
      palette: [
        ['#163300', 'forest-900 sidebar'],
        ['#ffe026', 'sun-500 protagonist'],
        ['#ff7503', 'flame-500 protagonist'],
        ['#738566', 'sage-500 supporting'],
        ['#faf8f2', 'cream content bg'],
      ],
    },
    'appshell-v4-calido.html': {
      key: 'v4',
      name: 'V4 — Editorial Cálido',
      tagline: 'Restraint editorial pero respira y tiene calidez',
      reference: 'FT Weekend Magazine × Apartamento × Kinfolk',
      status: '🆕 Construida 11-abr-2026',
      summary: 'V1 descongelada. Misma seriedad editorial pero con la temperatura subida. Hereda hairlines + mono + colophon, pero el cream es más saturado, sun-500 deja de ser raro y las headings pesan menos. Punto medio entre V1 (austera) y V3 (decorativa).',
      heredaCambia: {
        hereda: [
          'Hairline rules en lugar de cards (KPI strip ruled, no shadow).',
          'Mono en TODOS los datos — IDs, timestamps, tags, counts.',
          'Editorial colophon al pie con hairline-sun.',
          'Paper texture (radial dots, ahora 4% en lugar de 3%).',
          'Section eyebrows estilo magazine.',
        ],
        cambia: [
          '<b>Cream más saturado</b>: <code>#f8f4e9</code> (vs neutro de V1) → "warm paper" de revista.',
          '<b>Sun-500 como acento HABITUAL</b> (no la regla 3-puntos): subrayados de KPI, breadcrumb separator, eyebrows tinted, rail de activity, kbd, hover de nav.',
          '<b>ABC Whyte Bold 700 a 44px</b> (no Black 900) con tracking <code>-0.012em</code> → más respiración, menos shouty.',
          '<b>Sidebar cream</b> (<code>#f5f1e4</code>) con thin sun-500 left rail en el activo, NO tenant-dark.',
          '<b>Logo CrediFlux real</b> (gradient SVG colored) en el masthead, sobre la sidebar cream.',
          '<b>Heading "Buenos días, María."</b> con punto, no exclamación — serio y cálido.',
        ],
      },
      palette: [
        ['#f8f4e9', 'warmer-cream bg'],
        ['#f5f1e4', 'sidebar cream'],
        ['#163300', 'forest-900 text'],
        ['#ffe026', 'sun-500 (acento habitual)'],
        ['#cc5e02', 'flame-600 (overdue)'],
      ],
    },
    'appshell-v5-banca-lat.html': {
      key: 'v5',
      name: 'V5 — Banca Latinoamericana Moderna',
      tagline: 'Si Coop. San José fuera cliente del BHD, esto vería',
      reference: 'Banco Popular Dominicano + BHD León + Banreservas',
      status: '🆕 Construida 11-abr-2026',
      summary: 'Inspirado explícitamente en la banca institucional dominicana. Formal pero amable, lo que un cliente del BHD esperaría ver al login en su sucursal. Punto medio entre V2 (SaaS familiar) y V3 (brand-forward).',
      nonNegotiables: [
        '<b>Sidebar deep forest</b> (forest-900) con texture sutil de líneas diagonales 1.5%, wordmark CrediFlux <b>blanco</b> via <code>filter: brightness(0) invert(1)</code> sobre el SVG original.',
        '<b>Header generoso (72px)</b> con saludo institucional inline: "Hola, María — Cooperativa San José".',
        '<b>Hero strip institucional</b>: gradient forest-900 → sage-600 con glow radial sun, fecha en eyebrow sun + mini-resumen cuantitativo destacado ("Recaudo de abril al <b>94 %</b> de la meta").',
        '<b>4 KPI cards horizontales</b> con icon en círculo lateral 52px (no top), border-left 3px en var(--color-tenant-primary) — el "stamp del banco".',
        '<b>Activity feed = tabla institucional</b> con header sticky, columnas alineadas, alterna bg #fafaf9 sutil.',
        '<b>Por cobrar lateral</b> con header forest sólido, total al PIE (no al inicio), border-top forest-900 2px, CTA full-width "Registrar pago" cosido al fondo.',
        '<b>Tipografía</b>: Plus Jakarta Sans en TODO + ABC Whyte Bold 700 SOLO en KPI big numbers + page title del hero. Mono SOLO en montos.',
        '<b>Iconografía stroke-1.75</b> (más fina que default 2) — feeling de "banca seria", no de SaaS startup.',
        '<b>Sin emojis</b> — institucional. Nada de 👋 ni 🌴.',
        '<b>Footer regulatorio</b>: "Cooperativa San José · Regulado por la Superintendencia de Bancos de la República Dominicana · Plataforma CrediFlux v2.0".',
      ],
      inspiracion: {
        'Banco Popular': 'Wordmark blanco grande sobre dark, hero strip institucional con datos cuantitativos resaltados, botones primary solid rectangular generoso.',
        'BHD León': 'Cards horizontales con icon lateral, alternancia sutil de filas, copy "Hola, [nombre]" sin emoji.',
        'Banreservas': 'Footer regulatorio explícito, tipografía sans estricta sin display fonts decorativos, formalidad sin frialdad.',
      },
      palette: [
        ['#163300', 'forest-900 sidebar'],
        ['#fafaf9', 'neutral-50 content'],
        ['#ffffff', 'card white'],
        ['#5c6d4d', 'sage-600 (gradient stop)'],
        ['#cc5e02', 'flame-600 (danger)'],
      ],
    },
  };

  // ── Detect current variant ──
  const filename = window.location.pathname.split('/').pop() || 'appshell.html';
  const variant = VARIANTS[filename];
  if (!variant) return; // unknown file, do nothing

  // ── Build markup as a single HTML string ──
  const palette = (variant.palette || [])
    .map(
      ([hex, label]) =>
        `<div class="cf-notes-swatch"><span style="background:${hex}"></span><div><div class="cf-notes-swatch-hex">${hex}</div><div class="cf-notes-swatch-label">${label}</div></div></div>`
    )
    .join('');

  let body = '';
  body += `<p class="cf-notes-summary">${variant.summary}</p>`;

  if (variant.nonNegotiables) {
    body += `<h3 class="cf-notes-h3">No-negociables</h3><ul class="cf-notes-list">`;
    body += variant.nonNegotiables.map((n) => `<li>${n}</li>`).join('');
    body += `</ul>`;
  }

  if (variant.heredaCambia) {
    body += `<h3 class="cf-notes-h3">Hereda de V1</h3><ul class="cf-notes-list">`;
    body += variant.heredaCambia.hereda.map((n) => `<li>${n}</li>`).join('');
    body += `</ul>`;
    body += `<h3 class="cf-notes-h3">Cambia de V1</h3><ul class="cf-notes-list">`;
    body += variant.heredaCambia.cambia.map((n) => `<li>${n}</li>`).join('');
    body += `</ul>`;
  }

  if (variant.inspiracion) {
    body += `<h3 class="cf-notes-h3">Inspiración explícita</h3><dl class="cf-notes-dl">`;
    Object.entries(variant.inspiracion).forEach(([k, v]) => {
      body += `<dt>${k}</dt><dd>${v}</dd>`;
    });
    body += `</dl>`;
  }

  body += `<h3 class="cf-notes-h3">Paleta canónica</h3><div class="cf-notes-palette">${palette}</div>`;

  body += `<h3 class="cf-notes-h3">Cómo presentar</h3>`;
  body += `<p class="cf-notes-summary" style="margin-top:6px;">Elige esta variante si buscas: <i>"${variant.tagline}"</i>. Compárala con las otras 4 en <a href="/" class="cf-notes-link">design.crediflux.com.do</a>.</p>`;

  const root = document.createElement('div');
  root.id = 'cf-notes-root';
  root.innerHTML = `
    <style>
      #cf-notes-root, #cf-notes-root * { box-sizing: border-box; }
      #cf-notes-root {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      }
      .cf-notes-fab {
        position: fixed;
        bottom: 16px;
        left: 16px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        height: 40px;
        padding: 0 16px;
        background: #163300;
        color: #ffffff;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border: 1px solid #163300;
        border-radius: 6px;
        cursor: pointer;
        z-index: 9998;
        box-shadow: 0 8px 24px rgba(22,51,0,0.18);
        transition: transform 150ms ease, background 150ms ease;
      }
      .cf-notes-fab:hover { background: #2d5a10; transform: translateY(-1px); }
      .cf-notes-fab svg { width: 14px; height: 14px; }
      .cf-notes-fab .cf-notes-fab-key {
        margin-left: 4px;
        font-size: 9px;
        font-weight: 600;
        padding: 2px 5px;
        background: rgba(255,224,38,0.22);
        color: #ffe026;
        border-radius: 3px;
        letter-spacing: 0.05em;
      }
      .cf-notes-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(22,51,0,0.42);
        backdrop-filter: blur(2px);
        z-index: 9998;
        opacity: 0;
        pointer-events: none;
        transition: opacity 220ms ease;
      }
      .cf-notes-panel {
        position: fixed;
        top: 0;
        right: 0;
        width: 460px;
        max-width: 100vw;
        height: 100vh;
        background: #faf8f2;
        border-left: 1px solid rgba(168,184,156,0.55);
        box-shadow: -20px 0 40px rgba(22,51,0,0.16);
        z-index: 9999;
        transform: translateX(100%);
        transition: transform 280ms cubic-bezier(0.16, 1, 0.3, 1);
        display: flex;
        flex-direction: column;
        color: #163300;
      }
      #cf-notes-root.is-open .cf-notes-panel { transform: translateX(0); }
      #cf-notes-root.is-open .cf-notes-backdrop { opacity: 1; pointer-events: auto; }
      .cf-notes-header {
        flex-shrink: 0;
        padding: 22px 26px 18px;
        border-bottom: 1px solid rgba(168,184,156,0.45);
        background: #f5f1e4;
      }
      .cf-notes-eyebrow {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #5c6d4d;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .cf-notes-eyebrow .dot {
        width: 6px;
        height: 6px;
        background: #ffe026;
      }
      .cf-notes-title {
        font-size: 20px;
        font-weight: 800;
        line-height: 1.15;
        margin-top: 8px;
        letter-spacing: -0.01em;
      }
      .cf-notes-tagline {
        font-size: 13px;
        color: #4a5a3d;
        font-style: italic;
        margin-top: 6px;
      }
      .cf-notes-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 6px 12px;
        margin-top: 12px;
        font-size: 11px;
      }
      .cf-notes-meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 9px;
        background: rgba(255,255,255,0.7);
        border: 1px solid rgba(168,184,156,0.6);
        border-radius: 4px;
        color: #4a5a3d;
        font-weight: 600;
      }
      .cf-notes-close {
        position: absolute;
        top: 18px;
        right: 18px;
        width: 32px;
        height: 32px;
        background: rgba(22,51,0,0.06);
        border: 1px solid rgba(168,184,156,0.5);
        border-radius: 6px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #163300;
        transition: all 150ms ease;
      }
      .cf-notes-close:hover { background: rgba(22,51,0,0.12); }
      .cf-notes-body {
        flex: 1;
        overflow-y: auto;
        padding: 22px 26px 30px;
        scrollbar-width: thin;
        scrollbar-color: #a8b89c transparent;
      }
      .cf-notes-body::-webkit-scrollbar { width: 6px; }
      .cf-notes-body::-webkit-scrollbar-thumb { background: #c8d4be; border-radius: 3px; }
      .cf-notes-summary {
        font-size: 13.5px;
        line-height: 1.55;
        color: #2d5a10;
        margin: 0 0 18px;
      }
      .cf-notes-h3 {
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #5c6d4d;
        margin: 22px 0 10px;
        padding-bottom: 6px;
        border-bottom: 1px solid rgba(168,184,156,0.45);
      }
      .cf-notes-h3:first-child { margin-top: 0; }
      .cf-notes-list {
        margin: 0;
        padding: 0;
        list-style: none;
      }
      .cf-notes-list li {
        position: relative;
        padding: 8px 0 8px 18px;
        font-size: 12.5px;
        line-height: 1.55;
        color: #2d5a10;
        border-bottom: 1px dashed rgba(168,184,156,0.4);
      }
      .cf-notes-list li:last-child { border-bottom: none; }
      .cf-notes-list li::before {
        content: '';
        position: absolute;
        left: 0;
        top: 16px;
        width: 8px;
        height: 1px;
        background: #ffe026;
      }
      .cf-notes-list li b {
        font-weight: 700;
        color: #163300;
      }
      .cf-notes-list li code,
      .cf-notes-summary code {
        font-family: 'ABC Whyte Mono', ui-monospace, 'SF Mono', monospace;
        font-size: 11px;
        background: rgba(255,224,38,0.22);
        padding: 1px 5px;
        border-radius: 3px;
        color: #163300;
      }
      .cf-notes-dl {
        margin: 0;
      }
      .cf-notes-dl dt {
        font-size: 11px;
        font-weight: 800;
        color: #163300;
        margin-top: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .cf-notes-dl dt:first-child { margin-top: 0; }
      .cf-notes-dl dd {
        margin: 4px 0 12px;
        font-size: 12.5px;
        line-height: 1.5;
        color: #2d5a10;
      }
      .cf-notes-palette {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .cf-notes-swatch {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .cf-notes-swatch span {
        flex-shrink: 0;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        border: 1px solid rgba(22,51,0,0.12);
      }
      .cf-notes-swatch-hex {
        font-family: 'ABC Whyte Mono', ui-monospace, 'SF Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        color: #163300;
        letter-spacing: 0.04em;
      }
      .cf-notes-swatch-label {
        font-size: 11px;
        color: #5c6d4d;
        margin-top: 1px;
      }
      .cf-notes-link {
        color: #cc5e02;
        text-decoration: underline;
        text-decoration-color: #ffe026;
        text-decoration-thickness: 2px;
        text-underline-offset: 2px;
        font-weight: 600;
      }
      .cf-notes-link:hover { color: #163300; }
      @media (max-width: 600px) {
        .cf-notes-panel { width: 100vw; }
        .cf-notes-fab { bottom: 12px; left: 12px; height: 36px; padding: 0 12px; font-size: 11px; }
      }
    </style>

    <button class="cf-notes-fab" type="button" aria-label="Abrir notas de diseño">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="9" y1="13" x2="15" y2="13"/>
        <line x1="9" y1="17" x2="13" y2="17"/>
      </svg>
      Notas de diseño
      <span class="cf-notes-fab-key">N</span>
    </button>

    <div class="cf-notes-backdrop"></div>

    <aside class="cf-notes-panel" role="dialog" aria-label="Notas de diseño">
      <header class="cf-notes-header">
        <div class="cf-notes-eyebrow"><span>${variant.key.toUpperCase()}</span><span class="dot"></span><span>Notas de diseño</span></div>
        <div class="cf-notes-title">${variant.name}</div>
        <div class="cf-notes-tagline">"${variant.tagline}"</div>
        <div class="cf-notes-meta">
          <span class="cf-notes-meta-pill">📐 ${variant.reference}</span>
          <span class="cf-notes-meta-pill">${variant.status}</span>
        </div>
        <button class="cf-notes-close" type="button" aria-label="Cerrar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </header>
      <div class="cf-notes-body">${body}</div>
    </aside>
  `;

  document.body.appendChild(root);

  // ── Behavior ──
  const fab = root.querySelector('.cf-notes-fab');
  const closeBtn = root.querySelector('.cf-notes-close');
  const backdrop = root.querySelector('.cf-notes-backdrop');

  function open() { root.classList.add('is-open'); }
  function close() { root.classList.remove('is-open'); }
  function toggle() { root.classList.toggle('is-open'); }

  fab.addEventListener('click', open);
  closeBtn.addEventListener('click', close);
  backdrop.addEventListener('click', close);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
    if (e.key.toLowerCase() === 'n' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      const tag = (document.activeElement && document.activeElement.tagName) || '';
      if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
        e.preventDefault();
        toggle();
      }
    }
  });
})();
