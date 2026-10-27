# CrediFlux

Multi-tenant loan management SaaS. Django REST backend + Vite/React SPA frontend, orchestrated via Docker Compose.

## Stack

**Backend** (`backend/`)
- Django + Django REST Framework, `django-tenants` (schema-per-tenant multi-tenancy)
- PostgreSQL 16, Redis 7, Celery + Celery Beat
- Auth: `dj-rest-auth` + `allauth` + `rest_framework_simplejwt`
- Admin: Django Unfold (+ Constance for runtime config)
- Other: `djmoney`, `phonenumber_field`, `drf-yasg`, `django-filters`, custom `djangosdk` AI integration
- Settings split: `config/settings/{base,development,production,test}.py`
- Dependencias con **uv**: `backend/pyproject.toml` + `uv.lock` (Python 3.11). `uv add <pkg>` / `uv lock`; en Docker el entorno vive en `/opt/venv` (fuera del bind mount) y ya está en el PATH
- Two URL confs: `config/urls.py` (tenant) and `config/urls_public.py` (public schema)

**Frontend** (`frontend/`)
- Vite 8 + React 19 + TypeScript, SPA con React Router 7 (sin SSR)
- Rutas generadas desde `app/**/page.tsx` (convención heredada de Next App Router) en `app/router.tsx`: `[id]` → `:id`, grupos `(x)` ignorados. Cada página es un chunk diferido
- Navegación: `@/lib/navigation` (`useRouter`, `usePathname`, `useSearchParams`, `useParams`, misma forma que `next/navigation`) y `@/lib/navigation/link`; imágenes con `@/components/ui/image`. No importar `next/*` ni `react-router` directo en páginas
- TailwindCSS + Radix UI + shadcn-style components (`components.json`)
- TanStack Query + TanStack Table, `react-hook-form` + `zod`
- `axios` for API calls, `recharts` for charts, `sonner` for toasts
- `components/layout/TenantHostGuard.tsx` (antes `middleware.ts`) manda el host sin subdominio a `/select-tenant`
- Metadatos y script anti-flash de apariencia en `index.html`; fuentes en `app/fonts.css`
- Env: `VITE_API_URL`, `VITE_APP_URL` (`import.meta.env`, se incrustan en build)
- Producción: `frontend/Dockerfile` construye `dist/` y lo sirve nginx (`frontend/nginx.conf`, fallback a index.html)

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

Frontend talks to backend via `VITE_API_URL` (V2 en Docker: `http://localhost:8100`; ver `lib/api/client.ts`, que la deduce del host). Mailhog UI at `localhost:8025` for dev email.

## Tests

Mismo esquema que NexConnect/NexFacturas.

```bash
# Backend: pytest + pytest-django contra Postgres real (django-tenants necesita schemas)
docker compose exec backend pytest                 # --reuse-db por defecto
docker compose exec backend pytest --create-db     # tras cambiar migraciones
docker compose exec backend pytest --cov

# Backend fuera de Docker: cd backend && uv run pytest

# Frontend (Node 24.22.1, ver frontend/.nvmrc; Node 20 no tiene parche para CVE-2026-111497)
cd frontend && npm test            # vitest + jsdom
cd frontend && npm run test:e2e    # Playwright contra localhost:3100
# con sesión (barre todas las rutas autenticadas):
# E2E_EMAIL=admin@crediflux.com E2E_PASSWORD=<password> npm run test:e2e
cd frontend && npm run typecheck
```

- Settings de test: `config/settings/test.py` (cache/correo en memoria, Celery eager, sin throttling).
- `backend/conftest.py` crea una vez por sesión el tenant público (`localhost`) y un tenant `test` (`tenant.test.localhost`). Fixtures: `tenant_schema`, `public_schema`, `user_factory`, `admin_user`, `api_client`, `auth_client`, `public_client`. Fábricas en `backend/tests/factories.py`.
- Tests backend: `apps/<app>/tests/test_*.py` o `backend/tests/`. Frontend: `*.test.ts(x)` junto al código o en `frontend/tests/unit/`; e2e en `frontend/tests/e2e/`.
- CI: `.github/workflows/backend-ci.yml` y `frontend-ci.yml`. Ruff completo y `tsc` aún son informativos (deuda previa).

## Frontend routes (`frontend/app/`)

Carpetas de páginas (cada `page.tsx` es una ruta): `(auth)`, `dashboard`, `loans`, `customers`, `payments`, `cashbox`, `collections`, `collector`, `billing`, `communications`, `contracts`, `contract-templates`, `schedules`, `tasks`, `users`, `settings`, `ai`, `audit`, `calculator`, `sign`, `select-tenant`, `login`, `register`, `forgot-password`, `reset-password`, `access-denied`.

## Conventions / gotchas

- Multi-tenancy is **schema-based** (`django-tenants`). Be aware whether code runs in public vs tenant schema. New models in tenant apps must also work when the app is loaded in `SHARED_APPS`.
- `apps.users` is in `SHARED_APPS` only — required because allauth needs the user model in the public schema.
- Two `urls.py` files — pick `urls_public.py` for routes that should be reachable on the public schema (signup, tenant creation), `urls.py` for tenant routes.
- Reference docs in repo root: `API_AUTHENTICATION.md`, `API_TENANT_LOGIN.md`, `API_TENANT_REGISTRATION.md`, `PAYMENT_DISTRIBUTION.md`, `CONSTANCE_CONFIG.md`, `MODELO_CONTRATO_INTIMACION.md` (all in `backend/`); `FRONTEND_INTEGRATION.md`, `CONTEXTO.md`, `SESSION_CONTEXT.md` at root.
- CSRF cookie domain was recently fixed for localhost dev (commit 36fc33a) — check `backend/config/settings/development.py` before tweaking cookie/CORS settings.
- Spanish-language product (variable names, docs, and UI strings frequently in Spanish).
