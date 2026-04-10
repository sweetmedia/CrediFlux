# CrediFlux Design System

Source of truth for how CrediFlux looks, moves, and communicates visually
across the **landing**, the **dashboard**, and the **WordPress-headless
blog**. Read this before building or reviewing any UI.

Companion files in this same directory:
- `tokens.css` — the machine-readable version of everything documented here.
- `fonts/LICENSE.md` — licensing status of ABC Whyte.
- `VOICE.md` — copy tone and voice rules (not visual, but equally binding).

---

## 1. Core principle

CrediFlux is a financial tool for real people in small and mid-sized
financieras in the Dominican Republic. Its UI has to be:

1. **Trustworthy** — numbers are the product; typography, alignment, and
   contrast must leave no doubt about what a figure means.
2. **Calm** — gestores work with this software 8 hours a day. Motion,
   colors, and density are tuned to reduce fatigue, not to impress.
3. **Dominican in spirit** — warm (cream background instead of stark
   white), rooted in the brand's forest/sage/sun/flame palette, never
   "generic Silicon Valley SaaS".

If a design choice violates any of these three, it loses. Everything else
in this document is in service of them.

---

## 2. Color

### 2.1 Palette

Five named families, documented in `tokens.css`. Anchors from the logo:

| Family | Anchor | Hex | Role |
|---|---|---|---|
| **forest** | 900 | `#163300` | Primary text, dark UI, icon arc dark |
| **sage** | 500 | `#738566` | Secondary text, muted states, icon arc light |
| **sun** | 500 | `#FFE026` | Decorative only — badges, highlights, chart accent |
| **flame** | 500 | `#FF7503` | Warnings, overdue, warm accents |
| **cream** | — | `#FAF8F2` | Warm background alternative to white |

Each family (except cream and sun) has a 50–950 scale in `tokens.css`.

### 2.2 Usage rules

- **Text on light bg** uses `forest-900` or `sage-500`. Never sun or flame.
- **Text on dark bg** uses `cream`, `sage-100`, or pure white. Never sun.
- **Sun is decorative only**. `#FFE026` on white has contrast ratio 1.4:1
  — fails WCAG AA for any text. Use it for the shadow glow behind a
  highlighted CTA, the fill of a badge with dark text inside, chart dots,
  or a radial gradient behind a hero. Never as a word color.
- **Flame for danger/warning only**. Not a general accent.
- **Tenant primary** (`--color-tenant-primary`) defaults to forest-900 and
  is overridable at runtime by ConfigContext → `<html style="--color-tenant-primary: #..."`.
  Sidebar, primary buttons, focus rings, progress bars, and brand chrome
  all resolve through this variable.

### 2.3 Contrast table

Minimum ratios required:

| Pair | Minimum | Use |
|---|---|---|
| Body text vs background | **4.5:1** (WCAG AA) | Enforced |
| Large text (≥ 24px or 18px bold) vs bg | **3.0:1** | Enforced |
| Non-text UI (icons, borders) | **3.0:1** | Enforced |
| Decorative (backgrounds, illustrations) | no minimum | — |

Verified pairs:
- `forest-900` on `cream` — 16.1:1 ✅
- `sage-500` on `cream` — 4.7:1 ✅
- `sage-500` on white — 4.9:1 ✅
- `sun-500` on forest-900 — 13.2:1 ✅ (sun CAN be text here)
- `flame-500` on cream — 3.5:1 ⚠️ large text only
- `forest-900` on sun-500 — 13.2:1 ✅ (the classic "dark text on sun CTA" combo)

---

## 3. Typography

### 3.1 Font families

Three families, all declared in `tokens.css` and self-hosted from
`/branding/fonts/`. See `fonts/LICENSE.md` for Dinamo trial status.

| Role | Family | Source | Notes |
|---|---|---|---|
| **Display** | ABC Whyte | Dinamo (trial) | Headings, UI labels, CTAs |
| **Body** | Plus Jakarta Sans | Google Fonts (self-hosted) | Paragraphs, readable at small sizes |
| **Mono** | ABC Whyte Mono Inktrap Variable | Dinamo (trial) | Numbers, tables, code |

**Why two Dinamo fonts and one free font?** The display face is the most
visible part of the brand — it's what the user feels first. We invest
there. Body text is read more than seen; Plus Jakarta Sans is free, solid,
and familiar — no reason to pay for something users barely notice. Mono
for numbers is non-negotiable: financial tables need tabular alignment,
and the Inktrap variant traps ink at weight joins so numbers stay legible
even at small sizes on low-res screens.

### 3.2 Scale

Ten steps, values in `tokens.css` as `--font-size-*`:

| Token | px | Typical use |
|---|---|---|
| `xs` | 12 | Captions, badges, footnotes |
| `sm` | 14 | Body small, labels, sidebar items |
| `base` | 16 | Body default |
| `md` | 18 | Body emphasized, large lists |
| `lg` | 20 | H5 |
| `xl` | 24 | H4 |
| `2xl` | 30 | H3 |
| `3xl` | 36 | H2 |
| `4xl` | 48 | H1 dashboard |
| `5xl` | 60 | Hero on landing |

### 3.3 Weights

Four weights from ABC Whyte:

| Token | Name | Use |
|---|---|---|
| `regular` (400) | Regular | Body |
| `medium` (500) | Medium | UI labels, emphasis, sidebar active |
| `bold` (700) | Bold | Headings, CTA labels |
| `black` (900) | Black | Hero/display only |

**Do not use italic** unless the designer explicitly asks for it. Italic
variants are not in the initial bundle and require a PR.

### 3.4 Line height and tracking

| Token | Value | Use |
|---|---|---|
| `tight` | 1.15 | Display hero, large numbers |
| `snug` | 1.3 | Headings |
| `normal` | 1.5 | Body |
| `relaxed` | 1.7 | Long reading (blog posts, legal) |

| Token | Value | Use |
|---|---|---|
| `letter-spacing-tight` | -0.02em | Headings ≥ 36px |
| `letter-spacing-normal` | 0 | Everything else |
| `letter-spacing-wide` | 0.03em | Uppercase small labels, section titles |

### 3.5 Numbers

**Always use `font-variant-numeric: tabular-nums`** for money, counts,
dates, and any aligned figures. ABC Whyte Mono has tabular by default;
Plus Jakarta Sans needs the feature enabled via CSS.

Dashboard has a utility `.cf-mono-number` that applies `font-family: var(--font-mono)`
+ `font-variant-numeric: tabular-nums`. Use it for any monetary cell.

---

## 4. Spacing

4-pixel base grid. Named steps in `tokens.css`:

| Token | px | Common use |
|---|---|---|
| `space-1` | 4 | Tight inline gap |
| `space-2` | 8 | Inline gap, small padding |
| `space-3` | 12 | Compact padding |
| `space-4` | 16 | Default body padding, card padding |
| `space-6` | 24 | Section padding |
| `space-8` | 32 | Block separation |
| `space-12` | 48 | Major section gap |
| `space-16` | 64 | Hero padding |
| `space-24` | 96 | Marketing section breathing room |

**Do not use arbitrary pixel values in components**. Use the scale. If a
design requires `5px` or `11px`, it's a design bug — round to the nearest
step and document why if the deviation is justified.

---

## 5. Elevation (shadows)

Shadows are **tinted with forest-900 alpha** so they harmonize with the
warm palette. A neutral black shadow would look dirty on cream.

| Token | Use |
|---|---|
| `shadow-xs` | Subtle separation (table rows on hover) |
| `shadow-sm` | Cards, inputs on focus |
| `shadow-md` | Elevated panels, dropdowns |
| `shadow-lg` | Modals, floating actions |
| `shadow-xl` | Overlays, tooltips over content |
| `shadow-focus` | Focus ring — sage-500 alpha glow, accessibility critical |

Rules:
- **Never stack shadows**. If you feel you need two, you need one bigger one.
- **Modal backdrop is a separate shadow** (`rgba(0,0,0,0.4)`), not from this list.
- **Sidebar has no shadow** — use a `border-right` instead.

---

## 6. Radius

| Token | px | Use |
|---|---|---|
| `radius-sm` | 4 | Inputs, chips, small tags |
| `radius-md` | 8 | Buttons, cards, most containers |
| `radius-lg` | 12 | Modals, panels, feature cards |
| `radius-xl` | 16 | Heroes, image thumbnails |
| `radius-2xl` | 24 | Marketing sections, CTAs in landing |
| `radius-full` | 9999px | Pills, avatars, icon-only buttons |

**Do not mix radii aggressively**. A button inside a card should either
match the card's radius exactly or be noticeably smaller (at least 2
steps down). Never 1 step different — that looks unintentional.

---

## 7. States

Every interactive element has six states. Define them explicitly:

| State | What changes |
|---|---|
| **default** | Base styles |
| **hover** | Subtle bg tint (`forest-50` or `sage-50`), or shadow elevation up one step. Duration: `fast` (150ms) |
| **focus** | `shadow-focus` ring + 2px forest-900 outline. Never removed without replacement. |
| **active/pressed** | Scale(0.98) + shadow one step down. Duration: `fast` |
| **disabled** | Opacity 0.5, cursor not-allowed, all transitions killed |
| **loading** | Skeleton or inline spinner, not ghosting the whole element |

Specific components have extra states (e.g., form inputs add `error`,
`success`; buttons add `destructive`) — these extend, not replace, the six.

---

## 8. Empty states

Every list, table, or data container has an empty state. It includes:

1. **An icon** — from Lucide React (dashboard) or the Lucide via CDN
   (landing/blog). Size: 48px. Color: `sage-400`.
2. **A heading** — one line, display font, 18–20px, explains what's missing.
3. **A subtext** — one or two lines, body font, 14px, explains why or
   what to do.
4. **A primary action button** (if applicable) — the most likely next
   step for the user in this context.

Do NOT just show "No data". That's lazy and anxiety-inducing.

Example for `/customers` when there are no customers:

> 🧑‍🤝‍🧑 (users icon)
>
> **Aún no hay clientes en el sistema**
>
> Agregar un cliente es el primer paso antes de otorgar préstamos.
> Puedes importarlos en lote o crear uno manualmente.
>
> [ + Agregar cliente ]   [ Importar CSV ]

---

## 9. Loading states

Two patterns, both documented here because misusing them is common:

### 9.1 Skeleton screens
For content the user already knows the shape of (tables, cards, profiles).
Skeletons are silhouettes of the content that will appear. Generated via
the `boneyard` adoption (see F2 of the overhaul plan).

- Animation: subtle shimmer (1.5s loop). GSAP, not CSS keyframes, for
  consistency.
- Color: `sage-100` → `sage-50` → `sage-100` shimmer.
- **Match the final layout** — if the loaded card has 3 lines of text and
  an avatar, the skeleton should show 3 lines and a circle.
- Do not skeleton for more than 2 seconds — if the fetch is that slow,
  show progressive data or an explicit "Loading for a while..." message.

### 9.2 Inline spinners
For actions the user just triggered (submit buttons, "Refresh", etc.).
Small, inside the button, replaces the label.

- Use Lucide's `Loader2` with `animate-spin` (dashboard) or equivalent
  in landing.
- Always paired with the verb form of what's happening: "Guardando...",
  "Validando...", "Enviando..."
- Duration: show immediately on click, keep visible until response.

**Do not** spin a full-screen overlay for a user action. That's a modal
progress dialog and has different rules.

---

## 10. Motion

**GSAP is the only animation library.** Framer Motion is removed from
the landing in F1. No CSS keyframes for anything beyond the skeleton
shimmer.

### 10.1 Tokens

Durations and easings are declared in `tokens.css`:

| Token | Value | Use |
|---|---|---|
| `motion-duration-fast` | 150ms | Hover, press, toggle |
| `motion-duration-base` | 300ms | Modal open/close, drawer, sheet |
| `motion-duration-slow` | 500ms | Page transitions, hero reveals |
| `motion-duration-slower` | 750ms | Full-section reveals on scroll |

| Token | cubic-bezier | GSAP equivalent |
|---|---|---|
| `ease-out` | (0.16, 1, 0.3, 1) | `power3.out` |
| `ease-in` | (0.7, 0, 0.84, 0) | `power3.in` |
| `ease-in-out` | (0.87, 0, 0.13, 1) | `power3.inOut` |
| `ease-back-out` | (0.34, 1.56, 0.64, 1) | `back.out(1.7)` |

### 10.2 Patterns

**Entrance (element appearing)**:
```js
gsap.from(element, {
  y: 20, opacity: 0,
  duration: 0.3, ease: 'power3.out'
});
```

**Exit (element disappearing)**:
```js
gsap.to(element, {
  y: -10, opacity: 0,
  duration: 0.15, ease: 'power3.in',
  onComplete: () => element.remove()
});
```

**Scroll reveal (landing sections)**:
```js
gsap.registerPlugin(ScrollTrigger);
gsap.from('.section', {
  y: 40, opacity: 0,
  duration: 0.5, ease: 'power3.out',
  stagger: 0.08,
  scrollTrigger: {
    trigger: '.section',
    start: 'top 80%',  // fires when top of section hits 80% down viewport
    toggleActions: 'play none none reverse'
  }
});
```

**Page transition (Next.js dashboard)**:
```js
// See components/ds/PageTransition.tsx — wraps children, fades + slides.
<PageTransition>{children}</PageTransition>
```

**Number counter (stats on hero)**:
```js
gsap.from({ val: 0 }, {
  val: 1250,
  duration: 1.2, ease: 'power2.out',
  onUpdate: function() {
    el.textContent = Math.round(this.targets()[0].val).toLocaleString('es-DO');
  },
  scrollTrigger: { trigger: el, start: 'top 90%' }
});
```

### 10.3 Rules

- **Honor `prefers-reduced-motion`**. `tokens.css` already zeroes out
  durations at the CSS variable level, but GSAP tweens must also check
  `gsap.matchMedia` or `window.matchMedia('(prefers-reduced-motion: reduce)').matches`
  and set `duration: 0` for those users.
- **Never animate layout properties that trigger reflow** (width, height,
  top, left). Use `transform` (translate, scale) and `opacity` only,
  except for height when explicitly collapsing/expanding with GSAP's
  FLIP helpers.
- **Never autoplay loops.** No always-on carousel, no blinking badges,
  no spinning progress where no progress is happening. Motion must be
  tied to user action or scroll position.
- **Durations are capped**. Nothing on the interaction path (click →
  feedback) should exceed 300ms. Marketing reveals can go up to 750ms,
  but only for scroll-triggered sections users are actively watching.

---

## 11. Z-index

Stacking scale in `tokens.css` (`--z-*`). Use only these values:

```
base       →    0
dropdown   → 1000
sticky     → 1100
drawer     → 1200
modal      → 1300
popover    → 1400
toast      → 1500
tooltip    → 1600
```

**Never write raw z-index numbers in components.** If you need a new
layer, add it to the scale here first.

---

## 12. Dark mode

**Parqueado — not in this overhaul.** The backing CSS variables exist
in `tokens.css` but no component currently supports the `.dark` class
state. Any `.dark` styles in existing components are pre-overhaul
artifacts that will be audited in Backlog B3.

Do not add new dark-mode styles. Do not remove existing ones unless
they break light mode.

---

## 13. Responsive breakpoints

Follow Tailwind defaults in both apps:

| Name | Min width | Typical device |
|---|---|---|
| `sm` | 640px | Large phone / phablet |
| `md` | 768px | Tablet portrait |
| `lg` | 1024px | Tablet landscape / small laptop |
| `xl` | 1280px | Desktop |
| `2xl` | 1536px | Large desktop |

**Mobile-first**. Default styles target small screens. `md:` and up
progressively enhance.

**Dashboard target**: works down to `md` (768px). Below that, show a
"use desktop" message — the financial workflows are not productive on a
phone anyway.

**Landing target**: works down to `sm` (640px). Hero adapts with fluid
type. Below 640px things still work but aren't optimized.

**Cobrador móvil app** (future, F4): dedicated mobile-first UI, separate
breakpoint strategy, not covered here.

---

## 14. Accessibility checklist

Every component and page must pass:

- [ ] Contrast ratio ≥ 4.5:1 for normal text, ≥ 3.0:1 for large text
- [ ] Focus ring visible on every interactive element (see § 7)
- [ ] Keyboard navigable end-to-end (tab, shift+tab, enter, escape)
- [ ] Screen reader labels on icon-only buttons (`aria-label`)
- [ ] Form inputs have `<label>` with `htmlFor`
- [ ] Semantic HTML (nav, main, aside, section, button, not div on click)
- [ ] `prefers-reduced-motion` respected (durations zeroed)
- [ ] Language attribute on `<html lang="es">` (or `lang="en"` on `/en/*`)

Enforced in F1+ via `eslint-plugin-jsx-a11y` and manual axe runs before
every PR.

---

## 15. File naming + organization

Components are organized by feature, not by type:

```
components/
├── ds/               # Design system primitives, this doc's first-class citizens
│   ├── PageHeader.tsx
│   ├── DataTable.tsx
│   ├── EmptyState.tsx
│   ├── Skeleton.tsx
│   ├── Reveal.tsx    # GSAP wrapper
│   └── ...
├── layout/           # Shell, header, sidebar, footer
├── customers/        # Feature-specific components
├── loans/
└── ...
```

- One component per file. No barrel re-exports unless there's a strict
  convention (design system can barrel `ds/index.ts`, nothing else).
- File name = component name in PascalCase.
- Styles live with the component (Tailwind classes + tokens), not in
  separate `.css` files. The exceptions are `globals.css` and
  `tokens.css` (imported from branding).

---

## 16. Changelog

Document major design system decisions here. Append-only.

- **2026-04-09** — v1 written as part of F0 of the v2.0 overhaul. Palette
  locked (forest/sage/sun/flame/cream). Fonts: ABC Whyte + Plus Jakarta
  Sans + ABC Whyte Mono. Motion library: GSAP only.
