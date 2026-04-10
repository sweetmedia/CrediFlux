# Contributing to CrediFlux

This document is the **hard contract** for any code landing in
`/opt/crediflux` during and after the v2.0 overhaul. If a PR violates
any of these rules, CI blocks it or a human rejects it — no exceptions
unless documented inline with the reason.

Read the companion files before contributing:
- `branding/DESIGN_SYSTEM.md` — visual rules (colors, typography,
  spacing, motion)
- `branding/VOICE.md` — copy and voice rules
- `/root/.claude/plans/prancy-hugging-dewdrop.md` — the overhaul plan
  (fases F−1 through F6)

This repo is polyglot: Django backend in `backend/`, Next.js dashboard
in `frontend/`, marketing landing as a submodule at `apps/landing`.
Rules below apply to frontend and apps/landing unless marked
"(backend only)".

---

## 1. Size limits (enforced by `eslint` in F0+)

| Artifact | Max lines | What to do if exceeded |
|---|---|---|
| **React component** | 500 LOC | Split into sub-components or extract hooks |
| **Page (`app/**/page.tsx`)** | 300 LOC | Move logic to feature components and hooks |
| **Hook (`use*.ts`)** | 150 LOC | Split into smaller hooks |
| **API client file (`lib/api/*.ts`)** | 250 LOC | Split by resource domain |
| **CSS module / tailwind classes per file** | no hard cap, but if one component uses > 40 classes inline, extract a `@layer components` utility |

**Why**: the overhaul starts with 6 jumbo files above 900 LOC
(loans/new 2352, settings/general 2113, settings/loans 1190,
contracts/[id] 953, communications 913, customers/new 881) that are
impossible to review and almost as hard to refactor. The hard cap
keeps the codebase safe from regressing into that state.

When splitting, prefer **feature-local composition** (components that
belong to the same page live in `app/<feature>/_components/` or
`components/<feature>/`) over a shared `components/common/` dumping
ground.

---

## 2. Type safety (enforced by `eslint`)

### 2.1 `any` is banned in new code

```ts
// ❌ blocked
function doStuff(data: any) { ... }

// ✅ accepted
function doStuff(data: unknown) {
  if (!isExpected(data)) throw new Error('unexpected shape');
  // narrowed
}
```

**Why**: we already have 217 `any`s in the dashboard. Every new one is
a future bug. Use `unknown` + a type guard, or define the real type.

**Exception**: third-party libraries without types. Declare a minimal
ambient type in `types/<lib>.d.ts` and `any` goes there, isolated.

### 2.2 `@ts-ignore` and `@ts-expect-error` require justification

```ts
// ❌ blocked
// @ts-ignore
const x = weirdLib();

// ✅ accepted (the lint rule is `ts-expect-error-allow-with-description`)
// @ts-expect-error Library types are wrong for this signature — see
// https://github.com/example/lib/issues/123
const x = weirdLib();
```

### 2.3 `// TODO` and `// FIXME` require a context

```ts
// ❌ blocked — drive-by debt with no owner
// TODO: fix this

// ✅ accepted
// TODO(juan, 2026-05): replace with new padron endpoint after F3.
```

---

## 3. Logging (enforced by `eslint-plugin-no-console`)

### 3.1 `console.*` is banned in source files

**Use `lib/logger.ts`** instead:

```ts
import { logger } from '@/lib/logger';

logger.debug('payload', payload);   // stripped in production
logger.info('user logged in');       // kept
logger.warn('retrying request');     // kept, tagged
logger.error('api call failed', err); // kept, sent to Sentry in F5
```

**Why**: we have 112 `console.*` in the dashboard, half of which leak
sensitive data (tokens, customer names, amounts). `logger` has a
structured format, respects environment, and has an opt-in sink for
production errors.

**Exception**: `logger.ts` itself can use `console.*` internally. No
other file can.

### 3.2 No `debugger` statements in committed code

Same rule as console. Use breakpoints in your editor.

---

## 4. Data fetching — React Query only

### 4.1 Every new fetch uses React Query

```tsx
// ❌ blocked in new code — inline state fetch
function Customers() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch('/api/customers/').then(r => r.json()).then(setData);
  }, []);
  ...
}

// ✅ accepted
function Customers() {
  const { data, isLoading, error } = useCustomers();
  ...
}
```

`useCustomers` lives in `lib/api/queries/useCustomers.ts` and wraps
`queryClient` with proper keys, stale time, and invalidation rules.

### 4.2 Query keys follow the convention

`[<resource>, <tenant>?, <filters>?]`:

```ts
// ✅
['customers', tenant.id, { status: 'active' }]
['loan', loanId]
['config']

// ❌
['customersActive']  // key-as-string — loses cache granularity
```

### 4.3 Mutations invalidate explicitly

```ts
const mutation = useMutation({
  mutationFn: createCustomer,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['customers'] });
  },
});
```

Don't rely on React Query's automatic refetching — be explicit about
what to invalidate.

### 4.4 Grandfather clause

Existing code using inline `fetch` or `axios` in `useEffect` is not
banned; it just cannot grow. If you touch a file that does it, migrate
that file to React Query as part of the PR — not in a separate cleanup
pass that never happens.

---

## 5. i18n — every string goes to a message file

### 5.1 No hardcoded user-facing strings

```tsx
// ❌ blocked
<button>Guardar cliente</button>

// ✅ accepted — dashboard (next-intl)
import { useTranslations } from 'next-intl';
const t = useTranslations('customers.form');
<button>{t('save')}</button>

// ✅ accepted — landing (react-i18next)
import { useTranslation } from 'react-i18next';
const { t } = useTranslation('customers');
<button>{t('form.save')}</button>
```

### 5.2 Strings live in `messages/{es,en}/<namespace>.json`

```json
// messages/es/customers.json
{
  "form": {
    "save": "Guardar cliente",
    "cancel": "Cancelar"
  }
}
```

```json
// messages/en/customers.json
{
  "form": {
    "save": "Save customer",
    "cancel": "Cancel"
  }
}
```

**English translations are not blocking** (see overhaul plan decision:
F1 ships in Spanish only, EN loaded later via LLM). But the key must
exist in both files — an empty string is OK as a placeholder:

```json
// messages/en/customers.json — OK for F1
{
  "form": {
    "save": "",
    "cancel": ""
  }
}
```

The missing-translation runtime falls back to `es`.

### 5.3 VOICE.md checklist runs on new strings

Any PR that adds to `messages/es/*.json` is checked by `lint-copy.sh`
for the banned terms in `branding/VOICE.md` § 3.1. SaaS, multi-tenant,
plataforma, and the rest of the ban list block the build.

---

## 6. Animations — GSAP only

### 6.1 `framer-motion` is not an accepted dependency

```json
// ❌ blocked in package.json
"framer-motion": "^11.0.0"
```

### 6.2 Use the DS `<Reveal>` wrapper for common patterns

```tsx
import { Reveal } from '@/components/ds/Reveal';

<Reveal y={20} duration={0.3} delay={0.1}>
  <Card>...</Card>
</Reveal>
```

For one-off animations, write GSAP directly inside the component using
`useGsapContext` (or the equivalent hook in the landing). Durations and
easings **must** come from the design system tokens:

```tsx
import gsap from 'gsap';

const ctx = useGsapContext(ref, () => {
  gsap.from('.thing', {
    y: 20, opacity: 0,
    duration: 0.3,         // matches --motion-duration-base
    ease: 'power3.out',    // matches --motion-ease-out
  });
});
```

See `branding/DESIGN_SYSTEM.md` § 10 for patterns.

### 6.3 `prefers-reduced-motion` is always honored

`tokens.css` zeroes out the CSS duration variables, but GSAP tweens
must also check via `gsap.matchMedia` or `window.matchMedia`:

```ts
const mm = gsap.matchMedia();
mm.add('(prefers-reduced-motion: no-preference)', () => {
  gsap.from('.hero', { y: 40, opacity: 0, duration: 0.5 });
});
mm.add('(prefers-reduced-motion: reduce)', () => {
  gsap.set('.hero', { y: 0, opacity: 1 });
});
```

---

## 7. CSS and styling

### 7.1 Tokens only

```tsx
// ❌ blocked — raw hex
<div className="bg-[#163300]">...</div>

// ✅ accepted — design token
<div className="bg-forest-900">...</div>

// ✅ accepted — CSS variable directly
<div style={{ backgroundColor: 'var(--color-forest-900)' }}>...</div>
```

The full token list is in `branding/tokens.css`, synced into each app's
`branding/` folder by `scripts/sync-tokens.sh`.

### 7.2 Tailwind utilities > inline styles > custom CSS

- **First choice**: Tailwind utility classes that map to design tokens.
- **Second choice**: inline `style={{ ... }}` for values that are
  computed at runtime (e.g., tenant-specific colors from ConfigContext).
- **Last resort**: a CSS class in `globals.css` or a `<style>` block.
  Only when Tailwind can't express it.

### 7.3 No inline color or spacing values

```tsx
// ❌ blocked
<div className="mt-[17px]">...</div>
<div style={{ color: '#FF7503' }}>...</div>

// ✅ accepted
<div className="mt-4">...</div>
<div className="text-flame-500">...</div>
```

If a design truly needs a non-standard value, it's a design system bug.
Add the token first, then use it.

---

## 8. Backend (Django) — rules specific to `backend/`

### 8.1 Tenant isolation is sacred

- **Never** query across tenants unless the view is explicitly a
  public/admin endpoint.
- All tenant-aware queries go through `request.tenant` set by
  `TenantMainMiddleware`.
- New models that hold tenant data go in `apps/<feature>/` and are
  listed in `TENANT_APPS` in `config/settings/base.py`.
- Shared models (User, Tenant itself, core catalog) stay in
  `SHARED_APPS`.

If in doubt, the test is: "Could a malicious user from tenant A ever
see data from tenant B through this endpoint?" The answer must be no.

### 8.2 New endpoints use DRF ViewSets, not function views

```python
# ✅
class CustomerViewSet(TenantAwareMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

# ❌ in new code
@api_view(['GET'])
def customer_list(request):
    ...
```

Grandfather clause: existing function views stay until their file is
touched for other reasons.

### 8.3 Migrations

- **One migration per PR** when feasible. Conflicting migrations between
  branches are a nightmare to resolve.
- **Never edit a committed migration** — squash or add a new one.
- **Data migrations are separate** from schema migrations when possible,
  and labeled clearly: `0042_data_backfill_customer_phones.py`.

### 8.4 Async work goes through Celery

```python
# ❌ blocked in new code — blocks the request
def send_reminder(request):
    send_whatsapp_message(...)  # takes 2 seconds
    return Response(...)

# ✅ accepted
def send_reminder(request):
    send_whatsapp_message.delay(...)
    return Response(...)
```

Exception: operations that must be transactional with the HTTP response
(e.g., charging a card and returning the result). Document why in a
comment above the call.

---

## 9. Tests

### 9.1 No hard test requirement yet

F5 (Hardening) of the overhaul plan is where we add meaningful test
coverage. Until then, tests are **encouraged** but not **required**
for most PRs.

### 9.2 Exception: security-adjacent code

If your PR touches authentication, authorization, tenant isolation,
payment processing, or the padrón JCE validation, **it must include a
test** that exercises the happy path and at least one failure path.
No exceptions. This is the only hard test rule during the overhaul.

### 9.3 When you write tests, they hit real databases

Integration tests use a real Postgres (via `pytest-django` + the
`TENANT_TEST_RUNNER`), not mocked ORM calls. Mocked tests that drift
from production have bitten us before — prefer slow and real over fast
and fake.

---

## 10. Commit messages

### 10.1 Conventional Commits

```
<type>: <short imperative summary>

<optional body explaining the why>

<optional footer for breaking changes, co-authors, etc.>
```

Types used in this repo:
- `feat:` — new user-facing feature
- `fix:` — bug fix
- `refactor:` — internal cleanup, no behavior change
- `chore:` — tooling, config, deps
- `docs:` — documentation only
- `test:` — tests only
- `perf:` — performance improvement
- `style:` — code formatting (rarely a full commit on its own)
- `security:` — security fix (prefer this over `fix:` for audit trails)

### 10.2 Subject line

- Imperative mood: "add login" not "added login" or "adds login"
- ≤ 72 characters
- No trailing period
- Lowercase after the colon unless it's a proper noun or code

### 10.3 Body (optional but encouraged)

- Wrap at 72 characters
- Explain **why**, not **what** — the diff shows what
- Reference the overhaul plan or an issue if relevant

### 10.4 Co-author trailer for AI-assisted commits

```
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

## 11. Branches and PRs

### 11.1 Branch naming

- **`v2.0`** — the overhaul branch. All F0–F6 work commits here.
- **`main`** — current production. Don't touch during the overhaul
  except for hotfixes.
- **`hotfix/<short>`** — production fixes, branched from `main`.
- **`feat/<short>`** — feature branches off `v2.0`, merged back via PR.
- **`fix/<short>`** — bug fix branches off `v2.0`.

Never commit directly to `main` during the overhaul. Never merge `v2.0`
into `main` until the whole overhaul is done and the cutover plan is
approved.

### 11.2 PR requirements

A PR can merge when:

- [ ] CI is green (lint, typecheck, build, tests if any)
- [ ] At least one human review for anything touching the backend,
      auth, billing, or tenant isolation. For pure frontend polish
      self-merge is OK.
- [ ] The PR description includes "Why" (not just "What")
- [ ] The overhaul plan line item (e.g., "F0: tokens") is referenced
      in the PR title or body when applicable

### 11.3 Never `--force push` to `v2.0` or `main`

Force-push to your own feature branch is fine. Force-push to shared
branches is grounds for a very awkward conversation.

---

## 12. Dependencies

### 12.1 Adding a new dep

Before running `npm install <pkg>`, answer these three:

1. **Can we do it without a new dep?** Often yes.
2. **Does it fit our token / DS / motion constraints?** If it ships its
   own animation library, its own color scheme, or its own icon set, it
   probably doesn't.
3. **Is it actively maintained?** Last commit < 6 months, > 1k weekly
   downloads on npm, no major open CVEs.

If all three check out, the PR adding the dep must say why in the
description and link to the package's home page.

### 12.2 Deps we will not add

- **`framer-motion`** — banned (see § 6)
- **`moment`** — use `date-fns` or `Intl.DateTimeFormat`
- **`lodash`** entire — use modern JS methods or import from
  `lodash/<fn>` individually
- **`styled-components`, `emotion`** — we're Tailwind-only
- **`classnames`, `clsx`** — already have a `cn()` helper

### 12.3 Updating deps

Minor/patch bumps: self-merge if tests pass. Major bumps: separate PR
with a clear migration note, and review from at least one human.

---

## 13. Environment and secrets

### 13.1 `.env` is never committed

The `.env.example` file is committed with empty values and documentation.
Your local `.env` inherits the example and adds secrets.

### 13.2 Secrets never appear in error messages, logs, or frontend bundles

```ts
// ❌ blocked
logger.error('API key failed', process.env.STRIPE_KEY);

// ✅ accepted
logger.error('API key validation failed for tenant', { tenantId });
```

Frontend code only accesses `NEXT_PUBLIC_*` env vars (Next.js convention).
Anything sensitive stays backend-only.

---

## 14. Changelog

- **2026-04-09** — v1 written as part of F0 of the v2.0 overhaul.
  Rules cover size limits, typing, logging, fetching, i18n, motion,
  styling, backend tenant isolation, commits, branches, deps, secrets.
