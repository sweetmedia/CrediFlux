# F3 — Implementación de la UI aprobada (hoja de ruta + Fase 0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar al SPA (`frontend/`) y al backend las pantallas y decisiones aprobadas en el canvas de F3 (D1–D8, grupos 1–8), empezando por la base visual común (Fase 0) y cortando un beta demostrable al cliente.

**Architecture:** Este documento es el plan padre. Fija el orden de las fases, qué entra al beta y la Fase 0 con tareas detalladas. Cada fase siguiente tiene su propio plan detallado (`2026-10-xx-f3-<fase>.md`), que se escribe al empezarla, contra el código que haya en ese momento. Toda la UI usa las clases `cf-*` y los tokens del DS portados desde `design-prototypes/ds/`; el tema oscuro es la paleta D2 que ya genera `design-prototypes/_tools/build_canvas.py`.

**Tech Stack:** Vite 8 + React 19 + React Router 7 + TanStack Query/Table + Tailwind; Django/DRF + django-tenants + Postgres 16; vitest/jsdom, Playwright, pytest.

**Spec:** Canvas Claude Design https://claude.ai/artifact/8aZSCmXbzPq55DbWcxLTzT (v59; cada artboard claro/oscuro y su nota de aprobación), prototipos en `design-prototypes/*.html`, DS en `design-prototypes/ds/`, decisiones en la memoria `project_f3_design_prototypes.md`.

## Global Constraints

- Rama propia en worktree desde `master` = `f8b47fc` (no en el checkout compartido); commits pequeños por pantalla o grupo; **sin push** hasta que Juan lo pida.
- Páginas: navegación sólo con `@/lib/navigation` y `@/lib/navigation/link`; imágenes con `@/components/ui/image`; nunca `next/*` ni `react-router` directo en páginas.
- Estilo: clases `cf-*` del DS y sus tokens; nada de hex sueltos en componentes. Toda tabla de datos se ordena por cabecera.
- Seguridad sin cambio de comportamiento: `/verify-email`, `/verify-email/resend`, `lib/hosts.ts`, `TenantHostGuard`, `public-pages.ts`, el aviso de `/login?verified=invalid` y los mensajes genéricos de forgot-password pueden cambiar de aspecto pero no de lógica; sus tests en `frontend/tests/unit/` y `components/layout/*.test.*` siguen verdes sin editarlos.
- Moneda: todo monto en RD$ (DOP) salvo que la financiera diga otra cosa; `USD` por defecto es bug.
- Tema: claro / oscuro / sistema, persistido en `localStorage['cf-appearance']`. Switch en el topbar de la app (D3); login y registro siguen el sistema; en móvil el switch va en el menú de usuario (D8).
- Papel (`.cf-paper`, `.cf-doc`, `.tpl-paper`: contratos, recibos, plantillas) se ve claro también en oscuro.
- Fuentes ABC Whyte trial: ya están en `frontend/app/fonts/`; no publicarlas fuera del repo privado.
- Revertir un pago exige el código TOTP de un Dueño o Administrador (`verify_totp_once`), 3 fallos bloquean 15 min.
- "Listo" por pantalla: igual al prototipo en claro, oscuro y 390 px; `npm test`, `npx tsc --noEmit -p .`, `npm run build` (Node 24.22.1) y `docker compose exec backend pytest` en verde; vista en el navegador con el stack de Docker.

## Review Focus

- Sistema en oscuro y la página cargada en claro: el script anti-flash de `index.html` y el `AppearanceProvider` deben dar el mismo tema en el primer pintado (sin destello) — Task 3.
- Montos y fechas en tablas ordenables: `RD$ 1,250.00`, `—`, `10 abr 2026` deben ordenar como número/fecha, con los vacíos al final y la fila de totales fija — Task 4.
- Pantalla de 390 px con el teclado abierto o menú de usuario abierto: la barra inferior no tapa el botón primario del formulario — Task 5.
- Páginas públicas (login, registro, verify-email, select-tenant) no muestran sidebar ni barra inferior a ningún ancho — Task 5.
- Papel dentro de una pantalla oscura (vista previa de contrato o recibo) conserva tinta oscura sobre fondo claro — Task 2.

---

## Hoja de ruta

| Fase | Contenido | Beta |
|---|---|---|
| **F0 Fundación UI** | Tokens claro/oscuro, bundle `cf-*`, switch de tema, DataTable ordenable, AppShell escritorio + móvil, RD$ por defecto. Detallada abajo. | Sí |
| **F1 Acceso** | Login (+2FA), registro, forgot/reset (checklist en vivo), verify-email (+resend, host general), select-tenant sin lista, access-denied. Sólo aspecto. | Sí |
| **F2 Backend del beta** | D4: `nickname`, `supervisor_name`, `supervisor_phone` en Customer; "garante de otros" por cédula contra `Guarantor.id_number` (índice). D5: padrón JCE en el esquema público (comando de carga del CSV, tabla, endpoint por cédula con throttle + auditoría). D6: modelo `Role` + ~62 permisos en 11 módulos, roles propios, migración de los 8 roles, reemplazo de los chequeos de rol del backend, 403 con el permiso que falta, `PermissionGate` en el frontend. Revertir pago con TOTP de dueño/admin y 2FA obligatorio en esos roles. Ronda de auditoría de seguridad (run-8) al cerrar. | Sí |
| **F3 Pantallas núcleo** | Dashboard; clientes (lista, detalle, nuevo con búsqueda JCE, editar); préstamos (lista, detalle, nuevo en 6 pasos, mora); pagos (registrar, lista, detalle, revertir con TOTP); calculadora; sus versiones móviles (login, inicio, clientes, cliente, préstamo, cobrar). | Sí |
| **F4 Equipo y configuración** | Equipo, usuario nuevo/detalle, roles (editar, sistema, nuevo, borrar); índice de configuración, general, políticas de préstamo, e-CF. | Parcial: equipo + roles |
| **F5 Cobranza y reportes** | Mesa de cobranza, gestiones (+nueva), recordatorios (+nuevo, en lote), cuotas vencidas, cobrador móvil, centro de reportes + cartera y cobros (molde único para los 9), reportes programados. | No |
| **F6 Documentos y fiscal** | Contratos (lista, detalle, generar, firmar), plantillas (lista, nueva inactiva, detalle con versiones, variable `company_rnc`, modelos CrediFlux), facturación (lista, nueva, detalle, rechazada, certificados, secuencias), compras (recibidas desde NexConnect `GET /v1/received`, detalle, proveedores, cuentas por pagar, 606). | No |
| **F7 Resto** | Caja, comunicaciones, tareas, auditoría, asistente IA, impresos (recibo, térmico, estado de cuenta, amortización, cierre, contrato, intimación). | No |

**Corte del beta:** F0 + F1 + F2 + F3 + equipo y roles de F4. F2 cierra con la auditoría de seguridad antes de mostrarlo.

**Pendientes externos que no bloquean F0–F3:** ITBIS sobre interés y mora (los prototipos cobran 18 %; el contador debe confirmar si está exento) antes de F6; el prototipo viejo de `billing-list` muestra e-NCF de 14 caracteres (son 13) — se corrige al implementar F6.

**Paralelismo:** F1 y F2 no comparten archivos y pueden correr a la vez cuando F0 esté en la rama; F3 necesita F0 y los endpoints de F2 (cliente, JCE, revertir).

---

## Fase 0 — Fundación UI

### Archivos

- Create: `design-prototypes/_tools/export_tokens.py` — genera los CSS de tokens del frontend desde `ds/tokens.css` y los diccionarios `DARK`/`EXTRA` de `build_canvas.py` (fuente única de la paleta).
- Create: `frontend/lib/design-system/cf/tokens.css` (generado, `:root` claro + `.dark` oscuro), `frontend/lib/design-system/cf/bundle.css` (copia de `ds/bundle.css` + `ds/patterns.css`), `frontend/lib/design-system/cf/print.css`.
- Modify: `frontend/app/globals.css` (importa los tres; las variables HSL semánticas existentes apuntan a los tokens `cf`).
- Create: `frontend/lib/design-system/ThemeSwitch.tsx` (3 segmentos). `AppearanceToggle.tsx` deja de usarse.
- Create: `frontend/lib/table/sort.ts`, `frontend/components/ui/data-table.tsx`.
- Modify: `frontend/components/layout/AppLayout.tsx`, `Sidebar.tsx`, `Header.tsx`; Create: `frontend/components/layout/MobileNav.tsx`, `frontend/components/layout/UserMenu.tsx`.
- Modify (RD$): `backend/config/settings/base.py:755`, `backend/apps/loans/models_collections.py:151` (+ migración), `frontend/lib/utils.ts:8`, `frontend/lib/contexts/ConfigContext.tsx:17-18`, `frontend/app/settings/general/page.tsx:219-220`, `frontend/app/settings/loans/page.tsx:188`, `frontend/app/customers/[id]/edit/page.tsx:547`.
- Tests: `frontend/tests/unit/cf-tokens.test.ts`, `frontend/lib/design-system/ThemeSwitch.test.tsx`, `frontend/lib/table/sort.test.ts`, `frontend/components/ui/data-table.test.tsx`, `frontend/components/layout/AppLayout.test.tsx`, `frontend/tests/unit/currency.test.ts`, `backend/apps/loans/tests/test_default_currency.py`, `frontend/tests/e2e/theme.spec.ts`.

### Task 0: Worktree

- [ ] **Step 1:** `git worktree add ../CrediFlux-v2-f3-ui -b feat/f3-ui f8b47fc`; `cd ../CrediFlux-v2-f3-ui/frontend && nvm use && npm ci`.
- [ ] **Step 2:** Copiar a la rama sólo lo que la Fase 0 lee de `design-prototypes/` (`ds/*`, `_tools/build_canvas.py`) desde el checkout compartido y commitear: `chore(design): DS y build_canvas de los prototipos F3`.
- [ ] **Step 3:** Línea base: `npm test && npx tsc --noEmit -p . && npm run build` en verde; anotar fallas previas si las hay.

### Task 1: Tokens claro/oscuro

**Interfaces:**
- Produces: variables CSS `--forest-50…950`, `--sage-*`, `--sun-*`, `--flame-*`, `--neutral-*`, `--cream`, `--warm-white`, `--white` y las `EXTRA`, definidas en `:root` y redefinidas bajo `.dark`; las consume todo `bundle.css`.

- [ ] **Step 1: Test que falla** — `cf-tokens.test.ts` lee `lib/design-system/cf/tokens.css` y comprueba:
  - toda variable de `:root` existe también bajo `.dark`;
  - contraste ≥ 4.5 de `--forest-900` sobre `--cream` en claro y de su valor oscuro sobre el `--cream` oscuro (los pares texto/fondo del DS);
  - no queda ningún `#e5e7eb` (borde por defecto de Tailwind) sin mapear.
- [ ] **Step 2:** `npx vitest run tests/unit/cf-tokens.test.ts` → FAIL (archivo no existe).
- [ ] **Step 3:** `export_tokens.py` importa `PALETTE`, `DARK`, `EXTRA` de `build_canvas.py` y escribe `tokens.css`; `npm run tokens` en `package.json` lo corre (`python3 ../design-prototypes/_tools/export_tokens.py`).
- [ ] **Step 4:** Test → PASS.
- [ ] **Step 5:** Commit `feat(ds): tokens claro/oscuro del DS generados desde la paleta del canvas`.

### Task 2: Bundle `cf-*` y regla del papel

**Interfaces:**
- Consumes: tokens de Task 1.
- Produces: clases `cf-btn`, `cf-input`, `cf-field`, `cf-label`, `cf-table`, `cf-sort`, `cf-kpi*`, `cf-page-header*`, `cf-card`, `cf-mono`, `cf-amount`, `cf-paper`… disponibles globalmente; `.cf-paper, .cf-doc, .tpl-paper` re-declaran los tokens claros dentro de `.dark`.

- [ ] **Step 1: Test e2e que falla** — `theme.spec.ts`: en una página de prueba de desarrollo `/__ds` (sólo `import.meta.env.DEV`, fuera del build de producción) con un `.cf-btn--primary` y un `.cf-paper`, con `html.dark` el botón tiene `background-color` distinto que en claro y el `.cf-paper` tiene el mismo color de fondo y de texto en ambos temas.
- [ ] **Step 2:** `npm run test:e2e -- theme.spec.ts` → FAIL.
- [ ] **Step 3:** Copiar `bundle.css`, `patterns.css`, `print.css` a `lib/design-system/cf/`; añadir el bloque del papel; importar en `globals.css` antes de `@tailwind utilities`; ruta `/__ds` en `app/__ds/page.tsx` protegida por `import.meta.env.DEV`.
- [ ] **Step 4:** Test → PASS; `npm run build` no incluye `/__ds`.
- [ ] **Step 5:** Commit `feat(ds): bundle cf-* en el SPA, papel claro en tema oscuro`.

### Task 3: Switch de tema de 3 segmentos

**Interfaces:**
- Consumes: `useAppearance()` → `{ mode: AppearanceMode, setMode(m: AppearanceMode) }` de `AppearanceProvider.tsx` (ya existen).
- Produces: `<ThemeSwitch className? />` — `role="radiogroup"` con tres `role="radio"` etiquetados "Claro", "Oscuro", "Sistema".

- [ ] **Step 1: Test que falla** — `ThemeSwitch.test.tsx`: al pulsar "Oscuro" → `aria-checked="true"` en ese radio, `localStorage['cf-appearance'] === 'dark'`, `document.documentElement.classList.contains('dark')`; con "Sistema" y `matchMedia('(prefers-color-scheme: dark)')` mockeado a `true`, `html` también queda `dark`; flechas izquierda/derecha mueven la selección.
- [ ] **Step 2:** `npx vitest run lib/design-system/ThemeSwitch.test.tsx` → FAIL.
- [ ] **Step 3:** Implementar con el aspecto del topbar de `appshell.html` (segmentos con iconos Sun/Moon/Monitor de lucide y texto oculto visualmente).
- [ ] **Step 4:** Test → PASS; comprobar que el script anti-flash de `index.html` lee la misma clave y los mismos valores.
- [ ] **Step 5:** Commit `feat(ds): switch de tema claro/oscuro/sistema`.

### Task 4: DataTable ordenable

**Interfaces:**
- Produces: `parseSortValue(raw: string, type: 'text' | 'num' | 'date'): string | number | null` en `lib/table/sort.ts`; `<DataTable<T> columns={ColumnDef<T>[]} data={T[]} footer?={ReactNode} initialSort?={SortingState} />` en `components/ui/data-table.tsx`, con `meta.type` por columna y `<tfoot>` para totales (no se ordena).

- [ ] **Step 1: Tests que fallan** — `sort.test.ts`:
  - `parseSortValue('RD$ 1,250.00', 'num') === 1250`; `parseSortValue('-3.5%', 'num') === -3.5`;
  - `parseSortValue('—', 'num') === null`, `parseSortValue('', 'text') === null`;
  - `parseSortValue('10 abr 2026', 'date') === new Date(2026, 3, 10).getTime()`; `parseSortValue('2026-04-10', 'date') === Date.parse('2026-04-10')`.
  `data-table.test.tsx`: clic en "Monto" ordena ascendente y pone `aria-sort="ascending"`, segundo clic descendente; las filas con `null` quedan al final en ambos sentidos; el pie no se mueve.
- [ ] **Step 2:** `npx vitest run lib/table components/ui/data-table.test.tsx` → FAIL.
- [ ] **Step 3:** Implementar sobre `@tanstack/react-table` con `sortingFn` que usa `parseSortValue` y deja `null` al final; marcado `cf-table` / `cf-sort` / `cf-num` igual a `ds/datatable.js`.
- [ ] **Step 4:** Tests → PASS.
- [ ] **Step 5:** Commit `feat(ds): DataTable ordenable por cabecera`.

### Task 5: AppShell escritorio y móvil

**Interfaces:**
- Consumes: `ThemeSwitch` (Task 3), `esPaginaPublica` de `public-pages.ts` (sin cambios).
- Produces: `AppLayout` que en ≥ 768 px pinta sidebar V1 + topbar (con `ThemeSwitch`) y en < 768 px pinta topbar compacto + `MobileNav` (Inicio, Clientes, **Cobrar** central → `/payments/new`, Préstamos, Más) y `UserMenu` con `ThemeSwitch` dentro.

- [ ] **Step 1: Test que falla** — `AppLayout.test.tsx` (usuario autenticado mockeado):
  - con `matchMedia('(max-width: 767px)')` → `true`: existe `nav[aria-label="Navegación principal"]` con el enlace "Cobrar" a `/payments/new`; el topbar no contiene `ThemeSwitch`; al abrir el menú de usuario sí aparece el radiogroup "Tema";
  - a ancho de escritorio: el `ThemeSwitch` está en el topbar y no existe la barra inferior;
  - en `/login` y `/verify-email` no se pinta ni sidebar ni barra inferior a ningún ancho.
- [ ] **Step 2:** `npx vitest run components/layout/AppLayout.test.tsx` → FAIL.
- [ ] **Step 3:** Rehacer `Sidebar.tsx`/`Header.tsx` con las clases de `appshell.html` (ShellV1, grupos Cobranza/Contratos/Facturación como en `_tools/shell.html`); crear `MobileNav.tsx` y `UserMenu.tsx`; el contenido lleva `padding-bottom` igual a la altura de la barra en móvil. No tocar la lógica de redirección de `AppLayout` ni `TenantHostGuard`.
- [ ] **Step 4:** Test → PASS; `npx vitest run tests/unit components/layout` completo en verde (los de seguridad incluidos, sin editarlos).
- [ ] **Step 5:** Commit `feat(layout): AppShell V1 y navegación móvil con Cobrar`.

### Task 6: RD$ por defecto

- [ ] **Step 1: Tests que fallan**
  - `currency.test.ts`: `formatCurrency(1250) === 'RD$1,250.00'`; `formatCurrency(1250, 'USD')` sigue mostrando dólares; el `defaultConfig` de `ConfigContext` tiene `currency: 'DOP'` y `currency_symbol: 'RD$'`.
  - `test_default_currency.py`: `settings.DEFAULT_CURRENCY == 'DOP'` y `CollectionContact._meta.get_field('promise_amount').default_currency == 'DOP'`.
- [ ] **Step 2:** Correr ambos → FAIL.
- [ ] **Step 3:** `formatCurrency(amount, currency = 'DOP')` con locale `es-DO`; `DEFAULT_CURRENCY` default `'DOP'` y `CURRENCIES = ('DOP', 'USD', 'EUR')`; `default_currency='DOP'` + `makemigrations loans`; los tres selects del frontend con DOP preseleccionado.
- [ ] **Step 4:** `npx vitest run tests/unit/currency.test.ts` y `docker compose exec backend pytest apps/loans/tests/test_default_currency.py --create-db` → PASS.
- [ ] **Step 5:** Commit `fix(money): RD$ por defecto en backend y frontend`.

### Task 7: Verificación de la fase

- [ ] **Step 1:** `npm test && npx tsc --noEmit -p . && npm run build` y `docker compose exec backend pytest` en verde.
- [ ] **Step 2:** Con el stack de Docker, en el navegador: dashboard y una lista existente en claro, oscuro y 390 px; capturas comparadas con `ShellV1`/`ShellMobile` del canvas.
- [ ] **Step 3:** Anotar en memoria y en la nota compartida qué quedó; escribir el plan detallado de F1 y F2.
