'use client';

/**
 * V2 Token probe — visual smoke test for the design system foundation.
 *
 * Visit /v2-probe (no auth required, see AppLayout PUBLIC_PAGES).
 * Every token in TOKENS.md should render correctly in both light and dark
 * mode. If anything looks wrong here, the bug is in tokens/themes/Tailwind,
 * not in any one component.
 *
 * Delete or keep as a living style guide.
 */

import * as React from 'react';
import { AppearanceToggle } from '@/lib/design-system/AppearanceToggle';
import { useAppearance } from '@/lib/design-system/AppearanceProvider';

// ----------------------------------------------------------------------
// Section primitive (probe-only — not part of the design system)
// ----------------------------------------------------------------------

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-border pt-8 pb-12">
      <div className="mb-6">
        <h2 className="text-heading-lg text-fg">{title}</h2>
        {description && (
          <p className="text-body-sm text-fg-muted mt-1">{description}</p>
        )}
      </div>
      {children}
    </section>
  );
}

// ----------------------------------------------------------------------
// Color swatch
// ----------------------------------------------------------------------

function Swatch({
  name,
  twClass,
  textClass = 'text-fg',
}: {
  name: string;
  twClass: string;
  textClass?: string;
}) {
  return (
    <div className="rounded-md overflow-hidden border border-border">
      <div className={`${twClass} h-16 flex items-center justify-center`}>
        <span className={`text-mono-sm ${textClass}`}>{name}</span>
      </div>
      <div className="bg-surface px-3 py-2 text-mono-sm text-fg-muted">
        {twClass}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// Page
// ----------------------------------------------------------------------

const SPACING_TOKENS = [
  ['space-0_5',  '2px'],
  ['space-1',    '4px'],
  ['space-1_5',  '6px'],
  ['space-2',    '8px'],
  ['space-3',   '12px'],
  ['space-4',   '16px'],
  ['space-5',   '20px'],
  ['space-6',   '24px'],
  ['space-8',   '32px'],
  ['space-10',  '40px'],
  ['space-12',  '48px'],
  ['space-16',  '64px'],
  ['space-20',  '80px'],
  ['space-24',  '96px'],
] as const;

const RADIUS_TOKENS = [
  ['rounded-none', 'radius-none', '0'],
  ['rounded-sm',   'radius-sm',   '4px'],
  ['rounded-md',   'radius-md',   '8px'],
  ['rounded-lg',   'radius-lg',   '12px'],
  ['rounded-xl',   'radius-xl',   '16px'],
  ['rounded-2xl',  'radius-2xl',  '24px'],
  ['rounded-full', 'radius-full', '9999px'],
] as const;

const ELEVATION_TOKENS = [
  'shadow-elevation-0',
  'shadow-elevation-1',
  'shadow-elevation-2',
  'shadow-elevation-3',
  'shadow-elevation-overlay',
] as const;

// Static class lookup — Tailwind cannot detect dynamic `bg-${s}-bg` strings,
// so each status family gets its full class names spelled out.
const STATUS_CLASSES = {
  success: {
    tinted: 'bg-success-bg text-success-fg border border-success-border',
    solid: 'bg-success-solid text-fg-on-status',
    outline: 'bg-surface border border-success-border',
    text: 'text-success-fg',
  },
  warn: {
    tinted: 'bg-warn-bg text-warn-fg border border-warn-border',
    solid: 'bg-warn-solid text-fg-on-status',
    outline: 'bg-surface border border-warn-border',
    text: 'text-warn-fg',
  },
  danger: {
    tinted: 'bg-danger-bg text-danger-fg border border-danger-border',
    solid: 'bg-danger-solid text-fg-on-status',
    outline: 'bg-surface border border-danger-border',
    text: 'text-danger-fg',
  },
  info: {
    tinted: 'bg-info-bg text-info-fg border border-info-border',
    solid: 'bg-info-solid text-fg-on-status',
    outline: 'bg-surface border border-info-border',
    text: 'text-info-fg',
  },
} as const;

// Same problem for duration utilities
const DURATION_CLASSES = {
  fast: 'duration-fast',
  base: 'duration-base',
  slow: 'duration-slow',
  slower: 'duration-slower',
} as const;

const TYPE_TOKENS = [
  ['text-display-xl',  'Display XL — 48/56'],
  ['text-display-lg',  'Display LG — 36/44'],
  ['text-heading-xl',  'Heading XL — 28/36'],
  ['text-heading-lg',  'Heading LG — 22/30'],
  ['text-heading-md',  'Heading MD — 18/26'],
  ['text-heading-sm',  'Heading SM — 15/22'],
  ['text-body-lg',     'Body large — 16/24'],
  ['text-body',        'Body default — 15/22'],
  ['text-body-sm',     'Body small — 13/20'],
  ['text-label',       'LABEL — 13/18'],
  ['text-caption',     'Caption — 12/16'],
] as const;

export default function V2ProbePage() {
  const { mode, resolved } = useAppearance();

  return (
    <div className="min-h-screen bg-bg text-fg">
      {/* ----------------------------------------------------------------
          Header
          ---------------------------------------------------------------- */}
      <header className="sticky top-0 z-sticky bg-surface/80 backdrop-blur border-b border-border">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-heading-md text-fg">V2 Token Probe</h1>
            <p className="text-caption text-fg-muted mt-0.5">
              Foundation smoke test · mode:{' '}
              <span className="font-mono">{mode}</span> · resolved:{' '}
              <span className="font-mono">{resolved}</span>
            </p>
          </div>
          <AppearanceToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-24">
        {/* ============================================================
            Surfaces
            ============================================================ */}
        <Section
          title="Surfaces"
          description="The stacking layers a screen is built from. bg sits at the bottom; surface-raised floats above surface."
        >
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Swatch name="bg" twClass="bg-bg" />
            <Swatch name="surface" twClass="bg-surface" />
            <Swatch name="surface-raised" twClass="bg-surface-raised" />
            <Swatch name="surface-sunken" twClass="bg-surface-sunken" />
            <Swatch name="surface-hover" twClass="bg-surface-hover" />
            <Swatch name="surface-active" twClass="bg-surface-active" />
          </div>
        </Section>

        {/* ============================================================
            Foreground
            ============================================================ */}
        <Section
          title="Foreground"
          description="Text and icons on neutral surfaces. fg-muted is for secondary content; fg-subtle for tertiary (placeholders, captions)."
        >
          <div className="bg-surface rounded-lg border border-border p-6 space-y-3">
            <p className="text-fg text-body-lg">
              fg — Primary text. Headings and body content live here.
            </p>
            <p className="text-fg-muted text-body">
              fg-muted — Secondary text. Labels, descriptions, supporting copy.
            </p>
            <p className="text-fg-subtle text-body-sm">
              fg-subtle — Tertiary text. Placeholders, timestamps, disabled states.
            </p>
            <div className="bg-accent text-accent-fg rounded-md px-4 py-3 text-body-sm font-medium inline-block">
              accent-fg — Foreground on accent surfaces
            </div>
          </div>
        </Section>

        {/* ============================================================
            Borders
            ============================================================ */}
        <Section title="Borders">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-surface rounded-md border border-border p-4">
              <div className="text-mono-sm text-fg-muted">border</div>
              <div className="text-body-sm text-fg mt-1">Default 1px outline</div>
            </div>
            <div className="bg-surface rounded-md border border-border-strong p-4">
              <div className="text-mono-sm text-fg-muted">border-strong</div>
              <div className="text-body-sm text-fg mt-1">Higher contrast</div>
            </div>
            <div className="bg-surface rounded-md border border-border-subtle p-4">
              <div className="text-mono-sm text-fg-muted">border-subtle</div>
              <div className="text-body-sm text-fg mt-1">Low-contrast divider</div>
            </div>
          </div>
        </Section>

        {/* ============================================================
            Accent
            ============================================================ */}
        <Section title="Accent" description="The brand action color, semantically.">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Swatch name="accent" twClass="bg-accent" textClass="text-accent-fg" />
            <Swatch name="accent-hover" twClass="bg-accent-hover" textClass="text-accent-fg" />
            <Swatch name="accent-active" twClass="bg-accent-active" textClass="text-accent-fg" />
            <Swatch name="accent-muted" twClass="bg-accent-muted" />
            <div className="rounded-md overflow-hidden border border-border">
              <div className="bg-surface h-16 flex items-center justify-center">
                <span className="text-mono-sm text-accent">text-accent</span>
              </div>
              <div className="bg-surface px-3 py-2 text-mono-sm text-fg-muted">
                text-accent
              </div>
            </div>
          </div>
        </Section>

        {/* ============================================================
            Status families
            ============================================================ */}
        <Section
          title="Status"
          description="Success, warning, danger, info — each with bg/fg/border/solid variants."
        >
          <div className="space-y-4">
            {(['success', 'warn', 'danger', 'info'] as const).map((s) => {
              const cls = STATUS_CLASSES[s];
              return (
                <div key={s} className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div className={`${cls.tinted} rounded-md p-4`}>
                    <div className="text-mono-sm opacity-70">{s}-bg + {s}-fg</div>
                    <div className="text-body-sm font-medium mt-1 capitalize">
                      Tinted {s} message
                    </div>
                  </div>
                  <div className={`${cls.solid} rounded-md p-4`}>
                    <div className="text-mono-sm opacity-80">{s}-solid</div>
                    <div className="text-body-sm font-medium mt-1 capitalize">Solid {s}</div>
                  </div>
                  <div className={`${cls.outline} rounded-md p-4`}>
                    <div className="text-mono-sm text-fg-muted">{s}-border only</div>
                    <div className={`text-body-sm font-medium mt-1 ${cls.text} capitalize`}>
                      {s} outline
                    </div>
                  </div>
                  <div className="bg-surface border border-border rounded-md p-4">
                    <div className="text-mono-sm text-fg-muted">{s}-fg on surface</div>
                    <div className={`text-body-sm font-medium mt-1 ${cls.text} capitalize`}>
                      {s} text
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Section>

        {/* ============================================================
            Type scale
            ============================================================ */}
        <Section
          title="Type scale"
          description="Inter for UI, JetBrains Mono for numerics. Body default is 15/22."
        >
          <div className="bg-surface rounded-lg border border-border p-6 space-y-4">
            {TYPE_TOKENS.map(([cls, label]) => (
              <div key={cls} className="flex items-baseline gap-6 border-b border-border-subtle pb-3 last:border-0 last:pb-0">
                <div className="text-mono-sm text-fg-subtle w-32 shrink-0">{cls}</div>
                <div className={`${cls} text-fg`}>{label}</div>
              </div>
            ))}
            <div className="flex items-baseline gap-6 pt-3 border-t border-border-subtle">
              <div className="text-mono-sm text-fg-subtle w-32 shrink-0">font-mono tabular</div>
              <div className="font-mono text-mono text-fg tabular-nums">
                RD$ 1,234,567.89 · 12.50% · 2026-04-07
              </div>
            </div>
          </div>
        </Section>

        {/* ============================================================
            Spacing
            ============================================================ */}
        <Section
          title="Spacing scale"
          description="4px base. Bars are width = token. The page itself uses these for padding and gaps."
        >
          <div className="bg-surface rounded-lg border border-border p-6 space-y-2">
            {SPACING_TOKENS.map(([name, px]) => (
              <div key={name} className="flex items-center gap-4">
                <div className="text-mono-sm text-fg-subtle w-24 shrink-0">{name}</div>
                <div className="text-mono-sm text-fg-muted w-12 shrink-0">{px}</div>
                <div
                  className="h-3 bg-accent rounded-sm"
                  style={{ width: px }}
                  aria-hidden
                />
              </div>
            ))}
          </div>
        </Section>

        {/* ============================================================
            Radii
            ============================================================ */}
        <Section title="Radii">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {RADIUS_TOKENS.map(([cls, name, px]) => (
              <div key={cls} className="flex flex-col items-center gap-2">
                <div className={`${cls} bg-accent-muted border border-border w-20 h-20`} />
                <div className="text-mono-sm text-fg">{name}</div>
                <div className="text-mono-sm text-fg-subtle">{px}</div>
              </div>
            ))}
          </div>
        </Section>

        {/* ============================================================
            Elevation
            ============================================================ */}
        <Section
          title="Elevation"
          description="Default state is flat (elevation-0). Each step is for genuinely raised UI: popovers, modals, drag previews."
        >
          <div className="bg-bg p-8 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
              {ELEVATION_TOKENS.map((cls) => (
                <div key={cls} className="flex flex-col items-center gap-3">
                  <div className={`${cls} bg-surface border border-border rounded-lg w-24 h-24`} />
                  <div className="text-mono-sm text-fg text-center">{cls.replace('shadow-', '')}</div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* ============================================================
            Motion
            ============================================================ */}
        <Section
          title="Motion"
          description="Hover the buttons. All use ease-standard but different durations."
        >
          <div className="flex flex-wrap gap-3">
            {(['fast', 'base', 'slow', 'slower'] as const).map((d) => (
              <button
                key={d}
                type="button"
                className={
                  'px-5 py-2.5 rounded-md ' +
                  'bg-surface border border-border text-fg text-body-sm ' +
                  'hover:bg-accent hover:text-accent-fg hover:border-accent ' +
                  'hover:-translate-y-0.5 ' +
                  'transition-all ease-standard ' +
                  DURATION_CLASSES[d] + ' ' +
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus'
                }
              >
                duration-{d}
              </button>
            ))}
          </div>
          <p className="text-body-sm text-fg-muted mt-4">
            Easings:{' '}
            <code className="font-mono text-mono-sm text-fg">ease-standard</code>,{' '}
            <code className="font-mono text-mono-sm text-fg">ease-in</code>,{' '}
            <code className="font-mono text-mono-sm text-fg">ease-out</code>,{' '}
            <code className="font-mono text-mono-sm text-fg">ease-in-out</code>,{' '}
            <code className="font-mono text-mono-sm text-fg">ease-spring</code>.
          </p>
        </Section>

        {/* ============================================================
            Focus ring
            ============================================================ */}
        <Section title="Focus ring" description="Tab through these to verify the focus token.">
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="px-5 py-2.5 rounded-md bg-accent text-accent-fg text-body-sm font-medium hover:bg-accent-hover transition-colors duration-fast ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              Primary action
            </button>
            <button
              type="button"
              className="px-5 py-2.5 rounded-md bg-surface border border-border text-fg text-body-sm font-medium hover:bg-surface-hover transition-colors duration-fast ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            >
              Secondary
            </button>
            <input
              type="text"
              placeholder="Focus me"
              className="px-3 py-2 rounded-md bg-surface border border-border text-fg text-body-sm placeholder:text-fg-subtle focus:outline-none focus:border-border-strong focus:ring-2 focus:ring-focus/40"
            />
          </div>
        </Section>

        {/* ============================================================
            Done
            ============================================================ */}
        <div className="border-t border-border pt-8 mt-4">
          <p className="text-body-sm text-fg-muted">
            Phase 0 complete when this page renders correctly in both light and
            dark mode. Toggle with the button in the header.
          </p>
        </div>
      </main>
    </div>
  );
}
