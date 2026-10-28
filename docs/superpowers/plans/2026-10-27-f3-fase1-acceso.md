# F3 · Fase 1 — Acceso (login, registro, recuperar, verificar, financiera, 403)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar las pantallas de acceso al diseño aprobado del grupo 1 (canvas «01 · Acceso») sin cambiar su comportamiento de seguridad.

**Architecture:** Un marco común `AuthShell` (masthead de la financiera + panel de papel, como `login.html`) y cada página se rehace dentro de él con clases `cf-*` y la raíz `cf-root`. La lógica (llamadas a la API, manejo de errores, redirecciones, `esHostGeneral`) se conserva línea por línea; sólo cambia el marcado. Las páginas sin tests reciben primero un test de caracterización que fija su comportamiento actual. Lo que el prototipo muestra y el backend no sostiene se omite (lista en «Fuera de alcance»).

**Tech Stack:** React 19 + React Router 7 (vía `@/lib/navigation`), react-hook-form + zod, vitest + Testing Library, Playwright.

**Spec:** canvas https://claude.ai/artifact/8aZSCmXbzPq55DbWcxLTzT, página «01 · Acceso» (aprobada con 3 cambios: elegir financiera sin lista, requisitos de contraseña en vivo, 403 con el permiso exacto); prototipos `design-prototypes/login.html` (estados `default`, `error`, `2fa`), `register.html` (`go(1..5)`), `access.html` (`setState(estado, host)`), `access-denied.html`. Plan padre: `2026-10-27-f3-ui-implementacion.md`.

## Global Constraints

- Las del plan padre (rama `feat/f3-ui`, sin push, navegación por `@/lib/navigation`, `cf-*`, RD$, «listo» = claro + oscuro + 390 px + `npm test` + `tsc` + `build` + navegador).
- **Sin cambio de comportamiento** en `/verify-email`, `/verify-email/resend`, `lib/hosts.ts`, `TenantHostGuard`, `public-pages.ts`, el aviso de `/login?verified=invalid` y los mensajes genéricos de forgot-password. Sus tests (`tests/unit/{verify-email-page,verify-email-resend-page,login-verified-notice,forgot-password-page,hosts}.test.tsx`, `components/layout/{TenantHostGuard,public-pages}.test.*`) **no se editan** y siguen verdes.
- Los tests de verify-email exigen la clase `cf-surface-card` y prohíben `text-(green|red|blue|gray)-\d`, `bg-gradient` y `#e8eddf` en el HTML: el marco común no puede usar esas clases.
- Login y registro siguen el tema del equipo (D3): `AuthShell` no muestra switch.
- Cada página nueva lleva `cf-root` en su raíz (el oscuro del DS sólo aplica ahí).
- Textos en español; la contraseña nunca se muestra en logs ni en mensajes.

## Review Focus

- Enlace de reset con `uid`/`token` válidos pero vencidos: la API responde error de token y hoy se ve como alerta en línea; debe verse el estado «Enlace inválido» del prototipo, no un formulario que nunca funcionará — Task 4.
- Host general (`localhost:3000` o el de `VITE_APP_URL`) en `/select-tenant`: escribir `demo` debe llevar a `demo.<dominio base>` del entorno actual (en local `demo.localhost:<puerto>`), nunca a producción desde desarrollo — Task 6.
- Registro que responde 202 `{status: 'pending'}`: la pantalla final no puede decir «ya puedes entrar» — Task 5.
- 2FA con código de respaldo de 8 caracteres: las seis cajas no pueden impedir escribirlo — Task 2.
- Requisitos de contraseña en vivo: ninguno puede marcarse cumplido si el backend lo va a rechazar por esa misma regla (sólo se listan las reglas que el backend aplica) — Task 3.

## Fuera de alcance (el prototipo lo muestra, el backend no lo sostiene)

Intentos restantes y detalle del bloqueo en login; «No pedir código por 30 días»; «Mantener sesión iniciada»; ticker de estado de servicios; comprobación en vivo de subdominio disponible; elegir tema V1/V4 en el registro; fecha de «primer cobro»; correo del usuario en la pantalla de reset; «Tu rol», «Lo tienen» y nombre del administrador en el 403 (llegan con F2, Task 13 de ese plan). Si Juan quiere alguno, va a F2 o después.

---

## Archivos

- Create: `frontend/components/auth/AuthShell.tsx` (+ `AuthShell.test.tsx`), `frontend/components/auth/PasswordRequirements.tsx` (+ test), `frontend/components/auth/OtpInput.tsx` (+ test), `frontend/lib/tenant-url.ts` (+ test), `frontend/lib/recent-tenants.ts` (+ test).
- Modify: `.env.production.example`, `frontend/Dockerfile` (si pasa las `VITE_*`), `frontend/app/login/page.tsx`, `frontend/components/auth/TwoFactorVerify.tsx`, `frontend/app/register/page.tsx`, `frontend/app/forgot-password/page.tsx`, `frontend/app/reset-password/page.tsx`, `frontend/app/verify-email/page.tsx`, `frontend/app/verify-email/resend/page.tsx`, `frontend/app/select-tenant/page.tsx`, `frontend/app/access-denied/page.tsx`, `frontend/tests/e2e/rutas.spec.ts:44-46`.
- Tests nuevos: `frontend/tests/unit/{login-page,register-page,reset-password-page,select-tenant-page,access-denied-page}.test.tsx`.

### Task 1: AuthShell

**Interfaces:**
- Produces: `<AuthShell eyebrow?: string; title: string; children; aside?: ReactNode />`. Pinta el masthead (logo CrediFlux en blanco, «Estás entrando a» + `company_name` de `useConfig()` en host de tenant; en host general (`esHostGeneral()`) sólo el logo y «CrediFlux») y el panel `paper-bg` con el contenido. Raíz `<div class="cf-root ...">`. En < 768 px el masthead se reduce a la franja superior de `MobileLogin`.

- [ ] **Step 1: Test que falla** — `AuthShell.test.tsx`: con `useConfig` mockeado a `{company_name: 'Financiera Demo'}` y host `demo.localhost:3100` muestra «Financiera Demo»; con host `localhost:3000` no lo muestra; el HTML contiene `cf-root` y no coincide con `/text-(green|red|blue|gray)-\d|bg-gradient|#e8eddf/`; no hay `radiogroup` «Tema».
- [ ] **Step 2:** `npx vitest run components/auth/AuthShell.test.tsx` → FAIL (no existe).
- [ ] **Step 3:** Implementar desde `login.html:96-158` (aside `.masthead` y `main.paper-bg`), con Tailwind de la paleta por papel.
- [ ] **Step 4:** Test → PASS.
- [ ] **Step 5:** Commit `feat(auth): marco común de las pantallas de acceso`.

### Task 2: Login y 2FA

**Interfaces:**
- Consumes: `AuthShell`.
- Produces: `<OtpInput value onChange length={6} />` (seis cajas, pegar un código de 6 dígitos lo reparte, retroceso vuelve a la caja anterior) usado por `TwoFactorVerify` sólo en modo código; el modo «código de respaldo» sigue siendo un campo de texto de 8 caracteres.

- [ ] **Step 1: Tests que fallan**
  - `OtpInput.test.tsx`: pegar `123456` llena las 6 cajas y llama `onChange('123456')`; escribir una letra no avanza; `Backspace` en una caja vacía enfoca la anterior.
  - `login-page.test.tsx` (mock de `useAuth`, `useConfig`, `consumeSessionEndNotice`): el botón se llama **«Entrar»**; el campo de correo tiene label «Correo»; un 400 con `non_field_errors: ['x']` muestra `x` en `role="alert"`; si `login` resuelve `{requires_2fa: true}` aparece «Paso 2 de 2» y seis cajas; «Usar un código de respaldo» cambia a un campo que acepta `ABCD1234` y lo envía a `complete2FALogin` como `backup_code`.
- [ ] **Step 2:** Correr ambos → FAIL. Correr `tests/unit/login-verified-notice.test.tsx` → PASS (línea base).
- [ ] **Step 3:** Rehacer el JSX de `app/login/page.tsx` dentro de `AuthShell` (estados `default`/`error` y `2fa` de `login.html:160-256`), conservando `onSubmit`, el orden de lectura de errores (`:80-95`), el bloque `?verified=` (`:188-212`) con sus mismos textos y `consumeSessionEndNotice`. Cambiar el placeholder a `ej: maria@financiera.com.do` y actualizar `tests/e2e/rutas.spec.ts:44-46` para buscar por label «Correo» y botón «Entrar».
- [ ] **Step 4:** Tests nuevos + `login-verified-notice` → PASS.
- [ ] **Step 5:** Commit `feat(auth): login y verificación en dos pasos con el diseño F3`.

### Task 3: Requisitos de contraseña en vivo

**Interfaces:**
- Produces: `passwordChecks(password: string, ctx: { email?: string; names?: string[] }): { id: 'length' | 'not_numeric' | 'not_similar'; label: string; ok: boolean }[]` y `<PasswordRequirements password ctx />` (lista con `aria-live="polite"`). Las reglas son las de `AUTH_PASSWORD_VALIDATORS` (`backend/config/settings/base.py:159`): mínimo 8, no sólo números, no parecida al correo o al nombre. «No es una contraseña común» no se puede comprobar en el navegador: se muestra como texto fijo sin marca y, si el backend la rechaza, su mensaje aparece en el campo.

- [ ] **Step 1: Test que falla** — `PasswordRequirements.test.tsx`: `passwordChecks('12345678', {})` → `length` ok, `not_numeric` no; `passwordChecks('maria2026x', { email: 'maria@x.do' })` → `not_similar` no; `passwordChecks('Rio-Yaque-44', { email: 'maria@x.do', names: ['María', 'Pérez'] })` → todas ok. No existe ninguna regla de mayúscula ni de carácter especial.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar; `not_similar` = la contraseña en minúsculas sin acentos no contiene la parte local del correo ni ningún nombre de ≥ 3 letras.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(auth): requisitos de contraseña en vivo con las reglas del backend`.

### Task 4: Recuperar y restablecer contraseña

**Interfaces:** Consumes `AuthShell`, `PasswordRequirements`.

- [ ] **Step 1: Test que falla** — `reset-password-page.test.tsx` (mock de `usePasswordReset`): sin `uid`/`token` → «Enlace inválido» con enlace «Pedir un enlace nuevo» a `/forgot-password`; con ellos y `confirmReset` rechazando con `{token: ['...']}` o `{detail: '...'}` que mencione el enlace → también el estado «Enlace inválido» (no alerta en línea); un error de `new_password` → mensaje en el campo; éxito → «Contraseña restablecida» y `router.push('/login')` a los 5 s (fake timers). Se muestran los requisitos en vivo, sin «mayúscula» ni «carácter especial».
- [ ] **Step 2:** Este test y `forgot-password-page.test.tsx` (línea base, debe pasar) → el nuevo FAIL.
- [ ] **Step 3:** Rehacer `forgot-password` (estados `forgot`/`forgot-sent` de `access.html`; conservar textos «Email enviado», «Demasiados intentos», «No pudimos enviar la solicitud», «Email inválido» y el `aria-describedby="email-error"`) y `reset-password` (`reset`, `reset-done`, `reset-invalid`). Error de token de la API → estado inválido; contador 5 s con barra.
- [ ] **Step 4:** Ambos tests → PASS.
- [ ] **Step 5:** Commit `feat(auth): recuperar y restablecer contraseña con el diseño F3`.

### Task 5: Registro en cuatro pasos

**Interfaces:** Consumes `AuthShell`, `PasswordRequirements`; sigue llamando `authAPI.registerTenant` con el mismo payload que hoy (`register/page.tsx`) — sin campos nuevos.

- [ ] **Step 1: Test que falla** — `register-page.test.tsx` (mock de `authAPI`, `rncAPI`): pasos «Empresa», «Administrador», «Plan», «Confirmar»; «Continuar» no avanza con campos inválidos del paso; el paso 4 resume lo escrito y «Editar» vuelve al paso; sin aceptar términos «Crear cuenta» está deshabilitado; el payload enviado es igual al de hoy (snapshot de las claves); respuesta 201 → «Listo» con «Revisa tu correo para activar tu cuenta»; respuesta 202 `{status: 'pending'}` → «Estamos revisando tu solicitud» y ningún texto «ya puedes entrar»; error `owner_password: ['...']` → mensaje en el campo de contraseña (hoy cae al genérico).
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Rehacer en 4 pasos + pantalla final según `register.html`; mantener `rncAPI.validateRNC` para RNC y cédula, `formatRNC/formatCedula/cleanIDNumber` y la validación por paso con `trigger`. Plan: `basic`/`professional`/`enterprise` con los nombres Starter/Professional/Enterprise. Mapear errores de campo `owner_*` a su input.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(auth): registro en cuatro pasos con el diseño F3`.

### Task 6: Elegir financiera sin lista

**Interfaces:**
- Produces: `tenantUrl(sub: string, loc?: Location): string` en `lib/tenant-url.ts`: `https://<sub>.<VITE_TENANT_BASE_DOMAIN>/login` si esa variable existe (producción: `crediflux.com.do`, igual que `TENANT_BASE_DOMAIN` del backend en `.env.production.example:17`); si no, `<protocolo>//<sub>.<hostname actual>:<puerto actual>/login` (desarrollo). `sub` se pasa a minúsculas y debe cumplir `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$` o lanza `Error`; `recentTenants.read(): string[]`, `recentTenants.add(sub)` en `lib/recent-tenants.ts` (localStorage `cf-recent-tenants`, máx. 5, try/catch).

- [ ] **Step 1: Tests que fallan**
  - `tenant-url.test.ts`: sin la variable y en `http://localhost:3000` → `tenantUrl('demo')` = `http://demo.localhost:3000/login`; con `vi.stubEnv('VITE_TENANT_BASE_DOMAIN', 'crediflux.com.do')` → `https://demo.crediflux.com.do/login`; `tenantUrl('Demo')` → minúsculas; `tenantUrl('a.b')`, `tenantUrl('')`, `tenantUrl('-x')` y `tenantUrl('evil.com/x')` lanzan.
  - `recent-tenants.test.ts`: añade sin duplicar, el último va primero, máx. 5, localStorage que lanza → `[]`.
  - `select-tenant-page.test.tsx`: no hay ninguna lista fija (no aparecen `democompany`, `caproinsa`, `amsfin`); escribir `demo` y «Continuar» llama `window.location.assign(tenantUrl('demo'))` y `recentTenants.add('demo')`; «Usadas en este equipo» muestra las recientes como enlaces; texto «No mostramos la lista de financieras por privacidad».
- [ ] **Step 2:** → FAIL. `TenantHostGuard.test.tsx` → PASS (línea base).
- [ ] **Step 3:** Implementar según el estado `tenant` de `access.html`. Añadir `VITE_TENANT_BASE_DOMAIN=crediflux.com.do` a `.env.production.example` junto a `VITE_APP_URL` y al bloque de `ARG`/`ENV` de `frontend/Dockerfile` si allí se pasan las `VITE_*`.
- [ ] **Step 4:** → PASS, y `TenantHostGuard.test.tsx`/`public-pages.test.ts` siguen verdes sin tocarlos.
- [ ] **Step 5:** Commit `feat(auth): elegir financiera escribiendo su dirección, sin lista`.

### Task 7: Verificar correo y reenviar (sólo aspecto)

- [ ] **Step 1:** Correr `verify-email-page.test.tsx` y `verify-email-resend-page.test.tsx` → PASS (línea base; son el contrato).
- [ ] **Step 2:** Rehacer el JSX dentro de `AuthShell` con los estados `verify-wait`/`verify-ok`/`verify-bad`/`resend`/`resend-sent` de `access.html`, sin tocar efectos, `ref` anti doble envío, `router.replace`, `esHostGeneral` ni textos; mantener `cf-surface-card`, el `role="status"` y el `role="alert"` fuera de la región viva.
- [ ] **Step 3:** Los dos tests → PASS sin editarlos.
- [ ] **Step 4:** Commit `feat(auth): verificar correo con el diseño F3`.

### Task 8: Acceso denegado

- [ ] **Step 1: Test que falla** — `access-denied-page.test.tsx`: con `?reason=No%20puedes&permission=payments.void&returnUrl=/payments/9` muestra «Error 403», «No tienes permiso para esto», el código `payments.void` en «Permiso requerido», «Volver» con `href="/payments/9"` y «Ir al dashboard»; un `returnUrl` absoluto (`https://evil.example`) o que no empiece por `/` (o empiece por `//`) se ignora y «Volver» va a `/dashboard`.
- [ ] **Step 2:** → FAIL (al menos la validación de `returnUrl` y los textos).
- [ ] **Step 3:** Rehacer según `access-denied.html` dentro del shell (no es pública); sólo los datos disponibles (motivo, permiso, volver). Dejar el hueco de la etiqueta del permiso para F2 (Task 13 de ese plan).
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(auth): pantalla 403 con el permiso requerido`.

### Task 9: Verificación de la fase

- [ ] **Step 1:** `npm test`, `npx tsc --noEmit -p .`, `npm run build` en verde; `npm run test:e2e -- login.spec.ts rutas.spec.ts` contra `demo.localhost:3100` con `E2E_EMAIL`/`E2E_PASSWORD` de `DEMO_CREDENTIALS.local.md`.
- [ ] **Step 2:** En el navegador: cada estado en claro, oscuro (tema del equipo) y 390 px contra su artboard del canvas; `localhost:3000` (host general) para select-tenant y resend.
- [ ] **Step 3:** Memoria `project_f3_ui_implementacion.md` y tarea de ClickUp actualizadas.
