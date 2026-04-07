# CrediFlux

Multi-tenant loan management SaaS. Django REST backend + Next.js frontend, orchestrated via Docker Compose.

## Stack

**Backend** (`backend/`)
- Django + Django REST Framework, `django-tenants` (schema-per-tenant multi-tenancy)
- PostgreSQL 16, Redis 7, Celery + Celery Beat
- Auth: `dj-rest-auth` + `allauth` + `rest_framework_simplejwt`
- Admin: Django Unfold (+ Constance for runtime config)
- Other: `djmoney`, `phonenumber_field`, `drf-yasg`, `django-filters`, custom `djangosdk` AI integration
- Settings split: `config/settings/{base,development,production}.py`
- Two URL confs: `config/urls.py` (tenant) and `config/urls_public.py` (public schema)

**Frontend** (`frontend/`)
- Next.js 16 (App Router) + React 19 + TypeScript
- TailwindCSS + Radix UI + shadcn-style components (`components.json`)
- TanStack Query + TanStack Table, `react-hook-form` + `zod`
- `axios` for API calls, `recharts` for charts, `sonner` for toasts
- `middleware.ts` handles auth/tenant routing

## Apps

- `apps.core` — shared base models/utilities
- `apps.tenants` — tenant management (public schema)
- `apps.users` — custom user model (shared, required by allauth)
- `apps.audit` — audit trail system
- `apps.loans` — loans (tenant-specific, also in shared for public access)
- `apps.communications` — notifications/messaging
- `apps.billing` — billing/subscriptions
- `apps.cashbox` — cash register / payments
- `apps.ai` — AI integrations via `djangosdk`

`SHARED_APPS` vs `TENANT_APPS` split is in `backend/config/settings/base.py`. Tenant apps are duplicated in shared so they exist in the public schema for single-tenant dev.

## Running

```bash
# Full stack
docker compose up

# Services: db (5432), redis (6379), mailhog (1025/8025),
#           backend (8000), celery, celery-beat, frontend (3000), docs (3001)
```

Frontend talks to backend via `NEXT_PUBLIC_API_URL=http://localhost:8000`. Mailhog UI at `localhost:8025` for dev email.

## Frontend routes (`frontend/app/`)

App Router with route groups: `(auth)`, `dashboard`, `loans`, `customers`, `payments`, `cashbox`, `collections`, `collector`, `billing`, `communications`, `contracts`, `contract-templates`, `schedules`, `tasks`, `users`, `settings`, `ai`, `audit`, `calculator`, `sign`, `select-tenant`, `login`, `register`, `forgot-password`, `reset-password`, `access-denied`.

## Conventions / gotchas

- Multi-tenancy is **schema-based** (`django-tenants`). Be aware whether code runs in public vs tenant schema. New models in tenant apps must also work when the app is loaded in `SHARED_APPS`.
- `apps.users` is in `SHARED_APPS` only — required because allauth needs the user model in the public schema.
- Two `urls.py` files — pick `urls_public.py` for routes that should be reachable on the public schema (signup, tenant creation), `urls.py` for tenant routes.
- Reference docs in repo root: `API_AUTHENTICATION.md`, `API_TENANT_LOGIN.md`, `API_TENANT_REGISTRATION.md`, `PAYMENT_DISTRIBUTION.md`, `CONSTANCE_CONFIG.md`, `MODELO_CONTRATO_INTIMACION.md` (all in `backend/`); `FRONTEND_INTEGRATION.md`, `CONTEXTO.md`, `SESSION_CONTEXT.md` at root.
- CSRF cookie domain was recently fixed for localhost dev (commit 36fc33a) — check `backend/config/settings/development.py` before tweaking cookie/CORS settings.
- Spanish-language product (variable names, docs, and UI strings frequently in Spanish).
