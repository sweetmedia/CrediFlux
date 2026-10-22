# CrediFlux V2 — Design Tokens

The token vocabulary for the V2 redesign. **Semantic, not brand-named.** Anything visual that recurs gets a token; raw values are a smell.

## Goals

- **Rebrand-friendly.** No `green`, `gold`, `forest` in token names. Swap a single theme file to repaint the app.
- **Density: comfortable.** More breathing room than V1, modern SaaS feel.
- **Light + dark first-class.** Both themes are designed, not auto-derived.
- **Tailwind-native.** Tokens are CSS variables; Tailwind utilities map to them. No hardcoded colors in `tailwind.config.ts`.

## Layered architecture

```
┌──────────────────────────────────────────────┐
│  3. Tailwind utilities (bg-surface, ...)     │  ← what components use
├──────────────────────────────────────────────┤
│  2. Semantic tokens (--color-surface, ...)   │  ← what designers reason about
├──────────────────────────────────────────────┤
│  1. Theme primitives (--ref-green-500, ...)  │  ← raw palette, swappable per brand
└──────────────────────────────────────────────┘
```

- **Layer 1 — Reference palette.** Numeric scales (50–950) for each hue in the brand. Lives in `themes/theme-default.css`. Never referenced directly by components.
- **Layer 2 — Semantic tokens.** What things *mean* (surface, fg, accent, danger). Reference Layer 1 via `var()`. Lives in `globals.css`.
- **Layer 3 — Tailwind utilities.** `bg-surface`, `text-fg-muted`, `border-border`, etc. Defined in `tailwind.config.ts`, mapped 1:1 to Layer 2 tokens.

Components only ever touch Layer 3. Rebranding = edit Layer 1.

---

## 1. Color tokens

### Surfaces (backgrounds, in stacking order)

| Token | Purpose |
|---|---|
| `--color-bg` | App background. The deepest layer. |
| `--color-surface` | Default container background (cards, panels). Sits on `bg`. |
| `--color-surface-raised` | Elevated surfaces (popovers, dropdowns, modals). Sits on `surface`. |
| `--color-surface-sunken` | Inset areas (code blocks, well panels). Recedes from `surface`. |
| `--color-surface-hover` | Hover state for interactive surfaces (list rows, menu items). |
| `--color-surface-active` | Pressed/selected state. |

### Foreground (text & icons)

| Token | Purpose | Approx contrast on `surface` |
|---|---|---|
| `--color-fg` | Primary text. Headings, body. | AAA |
| `--color-fg-muted` | Secondary text. Labels, descriptions. | AA |
| `--color-fg-subtle` | Tertiary text. Placeholders, captions, disabled. | AA Large |
| `--color-fg-on-accent` | Text on accent-filled surfaces. | AAA on accent |
| `--color-fg-on-status` | Text on status-filled surfaces (success/warn/danger/info bg). | AAA on each |

### Borders & dividers

| Token | Purpose |
|---|---|
| `--color-border` | Default 1px borders. Cards, inputs, dividers. |
| `--color-border-strong` | Higher-contrast borders. Focused inputs, table headers. |
| `--color-border-subtle` | Low-contrast dividers inside dense layouts. |

### Accent (the brand color, semantically)

| Token | Purpose |
|---|---|
| `--color-accent` | Primary brand action. Buttons, links, active nav. |
| `--color-accent-hover` | Hover state. |
| `--color-accent-active` | Pressed state. |
| `--color-accent-muted` | Tinted background (selected row, badge bg). |
| `--color-accent-fg` | Foreground when accent is the background. |

### Status (semantic states)

Each status has the same 4-token shape: `bg` (tinted background), `fg` (text/icon on neutral surface), `border` (outline), `solid` (filled background, paired with `--color-fg-on-status`).

| Family | Tokens |
|---|---|
| Success | `--color-success-bg`, `--color-success-fg`, `--color-success-border`, `--color-success-solid` |
| Warning | `--color-warn-bg`, `--color-warn-fg`, `--color-warn-border`, `--color-warn-solid` |
| Danger | `--color-danger-bg`, `--color-danger-fg`, `--color-danger-border`, `--color-danger-solid` |
| Info | `--color-info-bg`, `--color-info-fg`, `--color-info-border`, `--color-info-solid` |

### Focus & overlay

| Token | Purpose |
|---|---|
| `--color-focus-ring` | Focus outline color (uses accent at 40% in light, 60% in dark). |
| `--color-overlay` | Modal/dialog scrim. |

---

## 2. Spacing scale

4px base. Comfortable density means default paddings live in the 12–24px range, not 8–12px like V1.

| Token | Value | Common use |
|---|---|---|
| `--space-0` | 0 | — |
| `--space-px` | 1px | hairlines |
| `--space-0_5` | 2px | tight icon offsets |
| `--space-1` | 4px | icon ↔ text gap (compact) |
| `--space-1_5` | 6px | — |
| `--space-2` | 8px | inline gap |
| `--space-3` | 12px | compact padding |
| `--space-4` | 16px | **default gap** |
| `--space-5` | 20px | card body padding (compact) |
| `--space-6` | 24px | **default card padding** |
| `--space-8` | 32px | section gap |
| `--space-10` | 40px | — |
| `--space-12` | 48px | page section gap |
| `--space-16` | 64px | hero / page top padding |
| `--space-20` | 80px | — |
| `--space-24` | 96px | — |

**Rule:** No raw px in components. If a value isn't on the scale, either it should be, or you're doing something wrong.

---

## 3. Type scale

**Body font:** Inter (geometric sans, already in V1). Falls back to system sans.
**Mono font:** JetBrains Mono or Space Mono — for currency, IDs, code. **Tabular numerals always on** for numeric columns (`font-feature-settings: "tnum"`).

Comfortable density bumps base body to **15px** (V1 used 14px), so dense tables get a clear "use `body-sm`" signal.

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `--text-display-xl` | 48 / 56 | 600 | Marketing only (login/landing) |
| `--text-display-lg` | 36 / 44 | 600 | — |
| `--text-heading-xl` | 28 / 36 | 600 | Page title |
| `--text-heading-lg` | 22 / 30 | 600 | Section title |
| `--text-heading-md` | 18 / 26 | 600 | Card title |
| `--text-heading-sm` | 15 / 22 | 600 | Subsection / list group |
| `--text-body-lg` | 16 / 24 | 400 | Long-form text |
| `--text-body` | 15 / 22 | 400 | **Default body** |
| `--text-body-sm` | 13 / 20 | 400 | Dense tables, helper text |
| `--text-label` | 13 / 18 | 500 | Form labels, table headers (uppercase optional) |
| `--text-caption` | 12 / 16 | 400 | Timestamps, footnotes |
| `--text-mono` | 14 / 22 | 500 | Currency, IDs (tabular) |
| `--text-mono-sm` | 12 / 18 | 500 | Compact numeric |

Letter-spacing tokens:
- `--tracking-tight` = -0.01em (display + heading)
- `--tracking-normal` = 0
- `--tracking-wide` = 0.04em (uppercase labels)

---

## 4. Radii

Comfortable density pairs well with slightly larger radii. V1 used 6px globally; V2 uses 8px as the default and 12px for primary cards.

| Token | Value | Use |
|---|---|---|
| `--radius-none` | 0 | — |
| `--radius-sm` | 4px | badges, tags |
| `--radius-md` | 8px | **default** — buttons, inputs |
| `--radius-lg` | 12px | **default cards** |
| `--radius-xl` | 16px | hero cards, modals |
| `--radius-2xl` | 24px | large illustrations |
| `--radius-full` | 9999px | avatars, pill badges |

---

## 5. Elevation

V1 was almost entirely flat (`shadow-none` × 155). V2 keeps that as the default but defines a small ladder for genuinely raised UI: dropdowns, popovers, modals, drag previews. **Surfaces use borders, not shadows, until they need to escape the document flow.**

| Token | Use | Value |
|---|---|---|
| `--elevation-0` | Flat. Cards, inputs. | `none` |
| `--elevation-1` | Subtle lift (hover on draggable cards). | `0 1px 2px rgba(0,0,0,0.04), 0 1px 1px rgba(0,0,0,0.03)` |
| `--elevation-2` | Dropdowns, popovers. | `0 4px 12px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)` |
| `--elevation-3` | Modals, dialogs. | `0 16px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06)` |
| `--elevation-overlay` | Command palette, full-screen overlays. | `0 24px 64px rgba(0,0,0,0.18)` |

In dark mode, shadows are weakened and supplemented with a 1px top highlight (`box-shadow: ..., inset 0 1px 0 rgba(255,255,255,0.04)`).

---

## 6. Motion

Movement is small, fast, and consistent. Anything slower than 300ms feels heavy in a SaaS dashboard.

### Durations

| Token | Value | Use |
|---|---|---|
| `--duration-instant` | 0ms | reduced-motion fallback |
| `--duration-fast` | 120ms | hover, focus, color changes |
| `--duration-base` | 200ms | **default** — most transitions |
| `--duration-slow` | 320ms | modal/sheet enter-exit |
| `--duration-slower` | 480ms | route transitions, page-level |

### Easings

| Token | Value | Use |
|---|---|---|
| `--ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | **default** — most transitions |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | exits |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | enters |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | continuous (toggles, position) |
| `--ease-spring` | `cubic-bezier(0.5, 1.5, 0.5, 1)` | playful bounces (use sparingly) |

**Reduced motion:** When `prefers-reduced-motion: reduce`, all durations collapse to `--duration-instant` and easings to `linear`. Implemented in `globals.css`, not per-component.

---

## 7. Z-index scale

Named layers, no magic numbers.

| Token | Value | Use |
|---|---|---|
| `--z-base` | 0 | normal flow |
| `--z-dropdown` | 1000 | menus, selects |
| `--z-sticky` | 1100 | sticky headers |
| `--z-overlay` | 1200 | scrim |
| `--z-modal` | 1300 | dialog |
| `--z-popover` | 1400 | popovers above modals |
| `--z-toast` | 1500 | toasts always on top |
| `--z-tooltip` | 1600 | tooltips above everything |

---

## 8. Breakpoints

Tailwind defaults are fine. Documented for completeness.

| Token | Value |
|---|---|
| `sm` | 640px |
| `md` | 768px |
| `lg` | 1024px |
| `xl` | 1280px |
| `2xl` | 1536px |

Sidebar collapses below `lg`. Page padding scales: `--space-4` < `md`, `--space-6` < `lg`, `--space-8` ≥ `lg`.

---

## Naming rules

1. **Semantic over literal.** `--color-danger-fg`, not `--color-red-500`.
2. **No brand words in token names.** `--color-accent`, not `--color-green` or `--color-forest`.
3. **Purpose first, modifier second.** `--color-fg-muted`, not `--color-muted-fg`.
4. **Scales use shirt sizes or numeric multiples**, not vague words. `--space-4`, not `--space-md`. `--text-heading-lg`, not `--text-heading-big`.
5. **One way to do a thing.** If both `--color-fg-secondary` and `--color-fg-muted` would work, pick one and delete the other.

## What does NOT get a token

- One-off values used in a single component for a single reason. Inline them.
- Values derived from other tokens at runtime (e.g. `color-mix(in srgb, var(--color-accent) 20%, transparent)`). Compute, don't pre-bake.
- Component-specific dimensions (sidebar width, table row height). Those live as constants in the component file.

## File layout

```
frontend/
├── app/
│   └── globals.css                 ← Layer 2: semantic tokens (light + dark)
├── lib/design-system/
│   ├── TOKENS.md                   ← this file
│   └── themes/
│       ├── theme-default.css       ← Layer 1: brand reference palette
│       └── theme-default-dark.css  ← dark variant of the same palette
└── tailwind.config.ts              ← Layer 3: utilities → tokens
```

To add a new brand later: drop `themes/theme-acme.css` + `theme-acme-dark.css`, expose a brand selector alongside `AppearanceProvider`. No component code changes.
