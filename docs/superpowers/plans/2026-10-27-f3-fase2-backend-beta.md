# F3 · Fase 2 — Backend del beta (D4 cliente, D5 padrón JCE, D6 roles editables, revertir con TOTP)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar en el backend (y en el frontend sólo lo mínimo para usarlo) lo que las pantallas del beta necesitan: apodo, supervisor y «garante de otros» del cliente; el padrón JCE cargado y consultable con auditoría; roles editables por financiera con permisos granulares; revertir un pago con el código TOTP del dueño o de un administrador. Cierra con una ronda de auditoría de seguridad.

**Architecture:** Cuatro bloques independientes en este orden: A (D4) y B (D5) son pequeños y no se tocan entre sí; C (D6) reemplaza los chequeos de rol por un resolutor de permisos, protegido por una **matriz de autorización de caracterización** escrita antes de cambiar nada (mismo resultado por rol y endpoint antes y después); D (revertir) usa el permiso `payments.void` de C. Los roles viven en `apps.users` (esquema público, como `User`) con FK a la financiera; `User.role` sigue siendo la clave del rol, así la API actual no cambia.

**Tech Stack:** Django 5 + DRF + django-tenants, django-money, pyotp, Redis cache, pytest-django (Postgres real), vitest.

**Spec:** decisiones D4, D5, D6 del canvas https://claude.ai/artifact/8aZSCmXbzPq55DbWcxLTzT (página «00 · Decisiones») y artboards `SettingsRoles`, `RolesEdit`, `RolesSystem`, `RolesNew`, `RolesDelete`, `CustomerEdit`, `PaymentRevert`, `PaymentRevertError`; memorias `project_f3_design_prototypes.md` (D4–D6), `project_padron_jce_with_photos.md`, `project_revertir_pago_autorizacion.md`. Catálogo de permisos: los 47 códigos de `design-prototypes/settings-roles.html` + 3 que exigen chequeos existentes (Task 7). Plan padre: `2026-10-27-f3-ui-implementacion.md`.

## Global Constraints

- Las del plan padre (rama `feat/f3-ui`, sin push, RD$, español).
- Tests de backend en el worktree: `docker run --rm --network crediflux-v2_default --env-file ../CrediFlux-v2/.env -e DEFAULT_CURRENCY=DOP -e DATABASE_URL=postgres://crediflux_user:crediflux_pass@db:5432/crediflux_f3 -v "$PWD/backend:/app" -w /app crediflux-v2-backend:latest pytest …` (BD de prueba aparte `test_crediflux_f3`; `--create-db` tras cada migración nueva). Abreviado abajo como `PYTEST`.
- Toda migración debe funcionar en el esquema público y en cada tenant (`migrate_schemas`); los datos de financieras se tocan por esquema, nunca cruzando tenants.
- Ningún endpoint nuevo responde datos de otra financiera; `TenantMatches` sigue en `DEFAULT_PERMISSION_CLASSES`.
- Superusuario y dueño (`is_tenant_owner`) conservan todos los permisos; el rol `admin` tiene todos y no se puede editar (aprobado en grupo 2: «Administrador bloqueado»).
- Un 403 por permiso responde `{"detail": "...", "required_permission": "<código>"}` (el frontend ya lo lee en `lib/api/client.ts:160`).
- El padrón es dato personal: sólo lo consulta quien tenga `customers.create` o `customers.edit`, con throttle `cedula_lookup` y una entrada de auditoría por consulta.
- Revertir: además de `payments.void`, siempre el TOTP de un dueño o administrador con 2FA activa (aunque quien revierte sea admin); 3 fallos por autorizador lo bloquean 15 min.

## Review Focus

- Un usuario cuyo rol (clave en `User.role`) se borró o no existe en su financiera: debe quedar sin permisos (403), nunca con los de otro rol ni con los de `viewer` de otra financiera — Task 8.
- Dos financieras con un rol propio de la misma clave (`cobrador-norte`): editar los permisos en una no cambia la otra — Task 7.
- Cédula con o sin guiones (`001-2345111-0` vs `00123451110`) en cliente y garante: «garante de otros» debe encontrar el cruce igual — Task 2.
- El autorizador del reverso es el mismo usuario que revierte, está inactivo, es de otra financiera o tiene 2FA desactivada: rechazar sin gastar su contador de fallos — Task 14.
- Carga del padrón con un CSV a medias o mal formado: la tabla anterior queda intacta (la carga es todo o nada) — Task 4.

---

## Bloque A — D4: datos del cliente

### Task 1: Apodo y supervisor inmediato

**Files:** Modify `backend/apps/loans/models.py` (Customer), `backend/apps/loans/serializers.py` (`CustomerSerializer` :118, `CustomerListSerializer` :209); Create migración `loans/0023_customer_nickname_supervisor.py`; Test `backend/apps/loans/tests/test_customer_d4.py`.

**Interfaces:** Produces `Customer.nickname: CharField(80, blank)`, `supervisor_name: CharField(120, blank)`, `supervisor_phone: PhoneNumberField(blank)`; los tres en `CustomerSerializer` (lectura/escritura) y `nickname` en `CustomerListSerializer`; `nickname` en `search_fields` de `CustomerViewSet`.

- [ ] **Step 1: Test que falla** — `test_customer_d4.py` con `auth_client` y `customer_factory`: `PATCH /api/loans/customers/<id>/` con `{"nickname": "La Flaca", "supervisor_name": "Ramón Peña", "supervisor_phone": "+18095551234"}` → 200 y se guardan; `supervisor_phone: "123"` → 400 en ese campo; `GET /api/loans/customers/?search=flaca` encuentra al cliente; el listado incluye `nickname`.
- [ ] **Step 2:** `PYTEST apps/loans/tests/test_customer_d4.py` → FAIL.
- [ ] **Step 3:** Campos + migración (`makemigrations loans`) + serializers + `search_fields`.
- [ ] **Step 4:** `PYTEST --create-db apps/loans/tests/test_customer_d4.py` → PASS.
- [ ] **Step 5:** Commit `feat(customers): apodo y supervisor inmediato del cliente (D4)`.

### Task 2: Garante de otros clientes (calculado)

**Files:** Modify `backend/apps/loans/models_guarantors.py`, `backend/apps/loans/serializers.py`, `backend/apps/loans/views.py` (`CustomerViewSet`); Create migración `loans/0024_guarantor_id_digits.py`; Test `backend/apps/loans/tests/test_guarantor_of.py`.

**Interfaces:**
- Produces: `Guarantor.id_number_digits: CharField(20, db_index=True, editable=False)` rellenado en `save()` con `normalize_id_number(self.id_number)` (`serializers.py:25`; moverla a `apps/loans/utils_ids.py` y reimportarla) + `RunPython` que rellena los existentes.
- Produces: `guarantor_of(id_number: str, exclude_customer_id=None) -> list[dict]` en `apps/loans/services/guarantors.py` → `[{"loan_id", "loan_number", "customer_id", "customer_name", "status"}]` para garantes activos cuyo `id_number_digits` coincide (sólo dígitos), excluyendo préstamos del propio cliente.
- Produces: `CustomerSerializer.guarantor_of` (sólo lectura, en detalle) y `GET /api/loans/customers/guarantor-check/?id_number=` → `{"is_customer": bool, "customer_id": uuid|null, "guarantor_of": [...]}` (permiso: `customers.view` tras Task 9; antes, `IsAuthenticated` + `TenantMatches`).

- [ ] **Step 1: Test que falla** — con `loan_factory`: un garante `id_number="001-2345111-0"` en el préstamo de Juan y una cliente Carmen `id_number="00123451110"` → detalle de Carmen trae `guarantor_of == [{"loan_number": …, "customer_name": "Juan …", …}]`; un garante `status="released"` no aparece; el garante en un préstamo de la propia Carmen no aparece; `guarantor-check?id_number=001-2345111-0` → `is_customer: true` y la misma lista; con una cédula desconocida → `is_customer: false, guarantor_of: []`; con `id_number=` vacío → 400.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar; la consulta usa `id_number_digits` (índice), nunca `icontains`.
- [ ] **Step 4:** `PYTEST --create-db apps/loans/tests/test_guarantor_of.py` → PASS; `PYTEST apps/loans` sin regresiones.
- [ ] **Step 5:** Commit `feat(customers): «garante de otros clientes» calculado por cédula (D4)`.

## Bloque B — D5: padrón JCE

Ya existe `PadronJCE` (`backend/apps/core/models.py:81-111`, `managed=False`, tabla `padron_jce`) y `GET /api/validate-cedula/` (`apps/core/views.py:70-140`). Falta crear la tabla con las columnas del extracto, cargarla, y endurecer el endpoint.

### Task 3: Tabla del padrón en el esquema público

**Files:** Create `backend/apps/core/migrations/00xx_padron_jce_table.py`; Modify `backend/apps/core/models.py` (PadronJCE); Test `backend/apps/core/tests/test_padron_table.py`.

**Interfaces:** Produces la tabla `public.padron_jce(cedula char(11) PRIMARY KEY, nombres text, apellido1 text, apellido2 text, fecha_nacimiento date NULL, sexo char(1) NULL, estado_civil char(1) NULL, lugar_nacimiento text NULL)`; `PadronJCE` con `sexo`, `estado_civil`, `lugar_nacimiento` (sigue `managed=False`).

- [ ] **Step 1: Test que falla** — en `public_schema`: la tabla `public.padron_jce` existe con esas 8 columnas (consulta a `information_schema.columns`); en `tenant_schema` no existe una `padron_jce` propia del esquema `test`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Migración con `RunPython` que sólo actúa si `connection.schema_name == 'public'`: `CREATE TABLE IF NOT EXISTS public.padron_jce (...)` y `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para las 3 columnas nuevas (por si ya existe la tabla vieja de 5 columnas); reversa = no-op.
- [ ] **Step 4:** `PYTEST --create-db apps/core/tests/test_padron_table.py` → PASS.
- [ ] **Step 5:** Commit `feat(core): tabla del padrón JCE en el esquema público (D5)`.

### Task 4: Comando de carga

**Files:** Create `backend/apps/core/management/commands/load_padron_jce.py`, fixture `backend/apps/core/tests/fixtures/padron_sample.csv` (3 filas inventadas con el formato real, una con `Apellido2` = espacio, una sin fecha); Test `backend/apps/core/tests/test_load_padron.py`.

**Interfaces:** Produces `manage.py load_padron_jce <ruta> [--dry-run]`: archivo `|`-delimitado, sin cabecera, 8 columnas `Cedula|Nombres|Apellido1|Apellido2|FechaNacimiento|IdSexo|IdEstadoCivil|LugarNacimiento`. Carga en `public.padron_jce_staging` con `COPY ... FROM STDIN WITH (FORMAT csv, DELIMITER '|')`, valida (cédula = 11 dígitos, sexo ∈ {M,F,''}), y en una transacción hace `TRUNCATE padron_jce; INSERT INTO padron_jce SELECT ... FROM staging` (espacios recortados, `''` → NULL); imprime filas cargadas. `--dry-run` sólo valida y cuenta.

- [ ] **Step 1: Test que falla** — `call_command('load_padron_jce', sample)` en `public_schema` → 3 filas, `apellido2` NULL donde era espacio; con una tabla previa de 1 fila y un archivo con una línea de 7 columnas → el comando falla con `CommandError` y la fila previa sigue ahí; `--dry-run` no cambia la tabla.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar con `connection.cursor().copy_expert` (psycopg2) o `cursor.copy` (psycopg3; ver la versión en `uv.lock`), siempre con nombres calificados `public.`.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(core): comando load_padron_jce, carga todo o nada (D5)`. Anotar en `docs/deploy` (o el runbook de `f8b47fc`) cómo copiar `/opt/crediflux/data/padron_extract.csv` y correr el comando en producción.

### Task 5: Consulta de cédula endurecida y auditada

**Files:** Modify `backend/apps/core/views.py:49-140`, `backend/apps/audit/models.py` (ACTION_CHOICES :12-41), `frontend/lib/api/cedula.ts`, `frontend/app/customers/new/page.tsx:145-200`; Test `backend/apps/core/tests/test_cedula_lookup.py` (y mantener `test_security_rnc.py` verde).

**Interfaces:** Produces respuesta `{"found": bool, "cedula", "nombres", "apellido1", "apellido2", "nombre_completo", "fecha_nacimiento", "sexo", "estado_civil", "lugar_nacimiento"}`; acción de auditoría `cedula_lookup` con `extra_data={"cedula": <11 dígitos>, "found": bool}`.

- [ ] **Step 1: Test que falla** — con el sample cargado: `loan_officer` consulta una cédula existente → 200 con `sexo` y `lugar_nacimiento`, y queda un `AuditLog(action='cedula_lookup', user=…)`; cédula inexistente → 200 `found: false` y también se audita; tras la consulta, `connection` del request siguiente sigue en el esquema del tenant (la vista no deja `search_path = public`); un error de BD responde 500 con `{"detail": "No se pudo consultar el padrón."}` sin el texto de la excepción; `viewer` → 403.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Consultar `public.padron_jce` con nombre calificado (sin `SET search_path`); auditar con `AuditLog.log(tenant=request.tenant, user=request.user, action='cedula_lookup', model_name='PadronJCE', ip_address=get_client_ip(request), user_agent=get_user_agent(request), extra_data=…)`; en el frontend, al encontrar la cédula, autocompletar también `gender` desde `sexo`.
- [ ] **Step 4:** `PYTEST apps/core` → PASS; `npx vitest run` sin regresiones.
- [ ] **Step 5:** Commit `fix(core): consulta de cédula sin search_path pegado, auditada y con sexo/lugar de nacimiento (D5)`.

## Bloque C — D6: roles editables

### Task 6: Matriz de autorización actual (caracterización)

**Files:** Create `backend/tests/test_authz_matrix.py`, `backend/tests/authz_cases.py`.

**Interfaces:** Produces `CASES: list[tuple[str, str, str, dict]]` = (nombre, método, ruta-plantilla, cuerpo) — **un caso por cada chequeo de rol** de la tabla del inventario (los 32 del backend: `CanApproveLoan`, `CanManageLoans` en cliente/préstamo/garantía/plantilla/contrato/garante, `CanRegisterPayments`, `CanManageCollections`, `CanLookupCedula`, reverso, `CanManageCashOperations` + borrar caja, ajustes del tenant, auditoría (lista y stats), config IA, `CanManageBilling` + config ECF, `CanSendMessages`, `CanManageTasks`, gestión de usuarios y asignar `admin`) y `EXPECTED: dict[str, dict[str, set[int]]]` = caso → rol → códigos aceptados, para los 8 roles + dueño.

- [ ] **Step 1:** Escribir la matriz con el comportamiento **actual** (leer cada chequeo; un caso pasa si el código está en el conjunto: 403 vs no-403 es lo que importa; para escrituras basta un cuerpo inválido que dé 400 cuando el permiso deja pasar).
- [ ] **Step 2:** `PYTEST tests/test_authz_matrix.py` → PASS sobre el código de hoy (si falla, la matriz está mal, no el código).
- [ ] **Step 3:** Commit `test(authz): matriz de autorización por rol antes de los roles editables (D6)`.

### Task 7: Catálogo de permisos y modelo Role

**Files:** Create `backend/apps/users/permissions_catalog.py`, `backend/apps/users/models_roles.py` (importado en `models.py`), migraciones `users/00xx_role.py` (+ datos); Test `backend/apps/users/tests/test_roles_model.py`.

**Interfaces:**
- Produces: `MODULES: list[tuple[str, str, list[tuple[str, str]]]]` (clave, etiqueta, [(código, etiqueta)]) con los 47 códigos de `settings-roles.html` **más** `collections.supervise` («Ver visitas de todos los cobradores», chequeo de `views_geolocation.py:23`), `cashbox.registers` («Administrar cajas», borrar caja `cashbox/views.py:65`) y `billing.config` («Configurar proveedor e-CF», `billing/views.py:425`); `ALL_CODES: frozenset[str]`.
- Produces: `DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]]` para `admin, manager, loan_officer, collector, collection_supervisor, accountant, cashier, viewer` derivado **exactamente** de `EXPECTED` de Task 6 (las lecturas abiertas hoy a todo autenticado → `*.view` para los 8 roles; `settings.audit` sólo admin/manager; `admin` = `ALL_CODES`).
- Produces: `Role(tenant FK tenants.Tenant, key SlugField(50), name CharField(80), description, is_system bool, permissions JSONField(list))`, `unique_together (tenant, key)`, `clean()` rechaza códigos fuera de `ALL_CODES`; `ensure_system_roles(tenant) -> None` (crea los 8 si faltan, nunca pisa uno editado); migración de datos que lo llama para cada tenant existente; `User.role` deja de tener `choices` fijos (se valida contra los `Role` de su financiera en el serializer, Task 11).

- [ ] **Step 1: Test que falla** — `ensure_system_roles(tenant)` crea 8 roles con `DEFAULT_ROLE_PERMISSIONS`; llamarlo dos veces no duplica ni pisa un rol `manager` editado; `Role(permissions=['x.y'])` falla en `full_clean`; dos financieras con rol `cobrador-norte` son filas distintas y editar una no cambia la otra (Review Focus 2); `DEFAULT_ROLE_PERMISSIONS['admin'] == ALL_CODES`; los 50 códigos son únicos.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar; llamar `ensure_system_roles` también donde se crea/provisiona una financiera (`apps/tenants` registro y acción de provisionar del admin).
- [ ] **Step 4:** `PYTEST --create-db apps/users/tests/test_roles_model.py` → PASS.
- [ ] **Step 5:** Commit `feat(users): catálogo de permisos y roles por financiera (D6)`.

### Task 8: Resolutor de permisos

**Files:** Create `backend/apps/users/authz.py`; Test `backend/apps/users/tests/test_authz.py`.

**Interfaces:** Produces `user_permissions(user) -> frozenset[str]` (superusuario o dueño → `ALL_CODES`; si no, los del `Role(tenant=user.tenant, key=user.role)`; rol inexistente → `frozenset()`; memo en `user._cf_perms` por request); `has_perm(user, code) -> bool`; clase DRF `PermissionRequired` construida con `PermissionRequired.for_methods({'GET': 'customers.view', 'POST': 'customers.create', ...})` o `.for_actions({'approve': 'loans.approve', ...})`, cuyo 403 lleva `required_permission`.

- [ ] **Step 1: Test que falla** — dueño sin rol → todos; `loan_officer` → los de su rol; rol borrado → vacío y 403 con `required_permission` (Review Focus 1); usuario de la financiera A con `role='manager'` no toma el `manager` editado de B; el memo no persiste entre requests (dos requests del mismo usuario tras editar el rol ven el cambio).
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** → PASS.
- [ ] **Step 5:** Commit `feat(users): resolutor de permisos y PermissionRequired (D6)`.

### Task 9: Préstamos, clientes, pagos y cobranza sobre permisos

**Files:** Modify `backend/apps/loans/permissions.py` (reimplementar `CanApproveLoan`, `CanManageLoans`, `can_manage_loans()`, `CanRegisterPayments`, `CanManageCollections` sobre `has_perm` con el código por método/acción; mantener los nombres de clase), `backend/apps/loans/views.py` (reverso :1050 → `payments.void`; geolocalización `COLLECTOR_OVERSIGHT_ROLES` → `collections.supervise`), `backend/apps/loans/policy.py:241-245`, `backend/apps/loans/admin.py` (APPROVER_ROLES y las 12 llamadas a `can_manage_loans()`), `backend/apps/core/views.py` (`CanLookupCedula` → `customers.create` o `customers.edit`).

- [ ] **Step 1:** `PYTEST tests/test_authz_matrix.py` → PASS (línea base).
- [ ] **Step 2:** Cambiar los chequeos de esos archivos; mapeo: escrituras de cliente → `customers.create/edit/delete`, documentos → `customers.documents.*`, préstamo → `loans.create/edit`, aprobar/rechazar/desembolsar → `loans.approve/reject/disburse`, garantías/garantes/contratos/plantillas → `loans.edit`/`contracts.create`/`contracts.templates`, registrar pago → `payments.create`, confirmar/cancelar pago → `payments.create`, reverso → `payments.void`, recordatorios/contactos/teléfonos → `collections.reminders/contacts`.
- [ ] **Step 3:** `PYTEST tests/test_authz_matrix.py apps/loans apps/core` → PASS, la matriz sin un solo cambio.
- [ ] **Step 4:** Commit `refactor(loans): permisos por código en préstamos, clientes, pagos y cobranza (D6)`.

### Task 10: Caja, facturación, comunicaciones, auditoría, IA y ajustes sobre permisos

**Files:** Modify `backend/apps/cashbox/views.py:28-65`, `backend/apps/billing/permissions.py`, `backend/apps/billing/views.py:425`, `backend/apps/communications/permissions.py`, `backend/apps/audit/views.py:17,82` (→ `settings.audit`), `backend/apps/ai/views.py:283` (→ `settings.edit`), `backend/apps/tenants/views.py:483` (→ `settings.edit`).

- [ ] **Step 1:** Matriz → PASS (línea base).
- [ ] **Step 2:** Cambiar los chequeos (`cashbox.view/open/close/movements/registers`, `billing.*`/`billing.config`, `comms.whatsapp`/`comms.tasks`).
- [ ] **Step 3:** `PYTEST tests/test_authz_matrix.py apps/cashbox apps/billing apps/communications apps/audit apps/ai apps/tenants` → PASS, matriz sin cambios.
- [ ] **Step 4:** Commit `refactor(authz): permisos por código en caja, facturación, comunicaciones, auditoría, IA y ajustes (D6)`.

### Task 11: Equipo y asignación de roles

**Files:** Modify `backend/apps/users/models.py:151-175` (`is_admin`, `is_manager`, `can_manage_users()` → `team.*`; las dos propiedades sin uso se borran), `backend/apps/users/serializers.py:600-700`, `backend/apps/users/views.py:512-693`, `backend/apps/users/admin.py`.

**Interfaces:** `role` en el serializer de usuario valida contra `Role.objects.filter(tenant=…)`; asignar `admin` exige ser dueño o superusuario (igual que hoy); asignar cualquier otro rol exige `team.assign_roles`; las protecciones del dueño (:682, :693, :700) no cambian.

- [ ] **Step 1: Test que falla** — `backend/apps/users/tests/test_team_roles.py`: con `team.assign_roles` se asigna un rol propio `cobrador-norte` de la misma financiera; un rol de otra financiera → 400; un rol inexistente → 400; sin `team.assign_roles` → 403 con `required_permission`; un `admin` no puede asignar `admin` (sólo el dueño).
- [ ] **Step 2:** → FAIL; matriz → PASS.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Test nuevo + matriz + `PYTEST apps/users` → PASS.
- [ ] **Step 5:** Commit `refactor(users): equipo y asignación de roles por permisos (D6)`.

### Task 12: API de roles

**Files:** Create `backend/apps/users/views_roles.py`, `backend/apps/users/serializers_roles.py`; Modify `backend/apps/users/urls.py`, `backend/apps/users/serializers.py:89` (`UserSerializer.permissions`), `backend/apps/audit/models.py` (acción `role_change`); Test `backend/apps/users/tests/test_roles_api.py`.

**Interfaces:**
- `GET /api/users/permissions/catalog/` (nuevo `path` en `apps/users/urls.py`) → `[{"key", "label", "permissions": [{"code", "label"}]}]` (autenticado).
- `/api/users/roles/` (list/create/retrieve/update/destroy; lectura `team.view`, escritura `team.assign_roles`) → `{"key", "name", "description", "is_system", "permissions", "user_count"}`.
- Reglas: `admin` no se edita ni se borra; un rol de sistema no se borra (sí se editan sus permisos); `key` inmutable, se genera del nombre al crear (`slugify`, único en la financiera); borrar con `user_count > 0` → 409 con la cuenta; cada cambio de permisos → `AuditLog(action='role_change', changes={"added": [...], "removed": [...]})`.
- `UserSerializer.permissions` (sólo lectura) = `sorted(user_permissions(user))`; lo devuelve `ProfileView` (`/api/users/profile/`, `apps/users/urls.py:53`) y la respuesta de login que guarda `AuthContext`.

- [ ] **Step 1: Test que falla** — crear «Cobrador Norte» con `["collections.view", "payments.create"]` → 201 `key="cobrador-norte"`; un código inexistente → 400; editar `admin` → 403/400; borrar `manager` → 400; borrar un rol propio con un usuario → 409; sin usuarios → 204; quitar `payments.create` a un rol hace que su usuario reciba 403 en registrar pago en el request siguiente; `GET /api/users/profile/` trae `permissions`; queda `AuditLog` `role_change` con `added`/`removed`; otra financiera no ve ni edita estos roles.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** → PASS; matriz → PASS.
- [ ] **Step 5:** Commit `feat(users): API de roles y catálogo de permisos (D6)`.

### Task 13: Permisos en el frontend

**Files:** Create `frontend/lib/permissions.ts` (+ test), `frontend/components/auth/PermissionGate.tsx`; Modify `frontend/types/index.ts` (User.permissions), `frontend/lib/contexts/AuthContext.tsx`, `frontend/components/layout/nav.ts` (`adminOnly` → `permission` por ítem), `frontend/components/layout/Sidebar.tsx:61`, `frontend/app/loans/page.tsx:54-57`, `frontend/app/loans/[id]/page.tsx:61-66`, `frontend/app/payments/[id]/page.tsx:211`, `frontend/app/settings/general/page.tsx:736`, `frontend/app/audit/page.tsx:105,113`, `frontend/app/users/[id]/page.tsx:191-192,426,433`, `frontend/app/access-denied/page.tsx` (etiqueta del permiso).

**Interfaces:** Produces `useCan(): (code: string) => boolean` (lee `user.permissions`; dueño → todo), `<PermissionGate code fallback?>`, `permissionLabel(code): string` (de `GET /api/users/permissions/catalog/`, cacheado con TanStack Query).

- [ ] **Step 1: Test que falla** — `permissions.test.tsx`: `useCan()('loans.approve')` true/false según `user.permissions`; dueño → true; `PermissionGate` oculta su contenido sin el permiso; el menú muestra «Equipo» con `team.view` aunque el rol no sea `admin`, y lo oculta sin él; `access-denied` muestra «Anular pago» para `payments.void`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Reemplazar los 11 chequeos de rol del frontend por `useCan`.
- [ ] **Step 4:** `npm test`, `tsc`, `build` → verdes.
- [ ] **Step 5:** Commit `feat(frontend): permisos del usuario en vez de roles fijos (D6)`.

## Bloque D — Revertir con el código del dueño o administrador

### Task 14: Reverso autorizado por TOTP

**Files:** Modify `backend/apps/users/lockout.py` (`_increment(key, window=LOGIN_FAIL_WINDOW)`; nuevo `check_and_count_authorizer(authorizer) / reset_authorizer(authorizer)` con límite 3 y ventana 900 s, clave `revert_auth_fail:{pk}`), `backend/apps/loans/views.py:1040-1088`, `backend/apps/users/views.py` + `urls.py` (autorizadores), `frontend/lib/api/loans.ts:189-190`, `frontend/app/payments/[id]/page.tsx` (diálogo mínimo: elegir autorizador + código; el diseño final llega en F3); Test `backend/apps/loans/tests/test_payment_reverse_totp.py`.

**Interfaces:**
- `GET /api/users/authorizers/` → `[{"id", "full_name", "role_label"}]`: usuarios activos de la financiera que son dueño o rol `admin` con `is_2fa_enabled` (permiso `payments.void`).
- `POST /api/loans/payments/<id>/reverse/` con `{"reason", "authorizer_id", "code"}`. Orden: permiso `payments.void` → estado del pago (400 como hoy) → `reason` → autorizador válido (misma financiera, activo, dueño o `admin`, 2FA activa; si no → 400 `{"authorizer_id": [...]}` **sin contar fallo**) → bloqueo del autorizador (429 «Autorización bloqueada 15 minutos») → `verify_totp_once(authorizer, code)` (fallo → cuenta, 400 `{"code": ["Código incorrecto. Quedan N intentos."]}`) → éxito: `reset_authorizer`, reverso como hoy, y `_log_void` con `extra_data["authorized_by"] = authorizer.id` y nombre.
- `reversePayment(id, reason, authorizerId, code)` en el frontend.

- [ ] **Step 1: Test que falla** — `payments.void` + autorizador admin con 2FA y `code` válido (pyotp con su `totp_secret`) → 200, pago `reversed`, `AuditLog` con `authorized_by`; el mismo código otra vez → rechazado (anti-replay de `verify_totp_once`); 3 códigos malos → la 4.ª respuesta es 429 aun con código bueno, y a los 15 min (`cache.delete`/`freezegun` o `cache.touch`) vuelve a aceptar; autorizador = quien revierte **sí** se permite si es dueño/admin con 2FA (el código igual se pide); autorizador inactivo, sin 2FA, de rol `manager` o de otra financiera → 400 sin incrementar `revert_auth_fail:{pk}` (Review Focus 4); sin `payments.void` → 403 con `required_permission`; `/api/users/authorizers/` sólo lista dueño y admins con 2FA de la financiera.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar backend y el diálogo mínimo del frontend; actualizar el caso «reverso» de la matriz (Task 6) con un comentario: el cambio de permiso es intencional.
- [ ] **Step 4:** `PYTEST apps/loans apps/users tests/test_authz_matrix.py` + `npm test` → verdes.
- [ ] **Step 5:** Commit `feat(payments): revertir exige el código TOTP del dueño o un administrador`.

### Task 15: 2FA obligatoria para dueño y administradores

**Files:** Create `backend/apps/users/permissions_2fa.py`; Modify `backend/config/settings/base.py` (`DEFAULT_PERMISSION_CLASSES`), `frontend/lib/api/client.ts` (manejo del 403 `code: "2fa_required"`), Create `frontend/app/setup-2fa/page.tsx` (usa `components/auth/TwoFactorSetup` y `BackupCodesDisplay`); Test `backend/apps/users/tests/test_require_2fa.py`, `frontend/tests/unit/setup-2fa.test.tsx`.

**Interfaces:** `Require2FAForPrivileged` en `DEFAULT_PERMISSION_CLASSES`: si el usuario autenticado es dueño o rol `admin` y `not is_2fa_enabled`, responde 403 `{"detail": "…", "code": "2fa_required"}` salvo en la lista blanca: `/api/users/auth/logout/`, `/api/auth/token/refresh/`, `/api/users/profile/`, `/api/users/auth/2fa/{setup,verify,backup-codes}/`, `/api/config/`. El frontend, ante ese código, navega a `/setup-2fa`.

- [ ] **Step 1: Test que falla** — dueño sin 2FA: `GET /api/loans/customers/` → 403 `2fa_required`; `POST` de setup 2FA → no bloqueado; tras activar 2FA → 200; `manager` sin 2FA → no afectado; superusuario de la plataforma → no afectado. Front: un 403 `2fa_required` lleva a `/setup-2fa` y la página muestra el QR de `TwoFactorSetup`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** Implementar; añadir a la matriz (Task 6) que todos sus usuarios dueño/admin tienen 2FA en el fixture, para no confundir los resultados.
- [ ] **Step 4:** `PYTEST` completo + `npm test` → verdes. Revisar `DEMO_CREDENTIALS.local.md`: la cuenta demo (dueña) tendrá que activar 2FA en el primer ingreso; anotarlo.
- [ ] **Step 5:** Commit `feat(users): 2FA obligatoria para dueño y administradores`.

### Task 16: Auditoría de seguridad run-8 y cierre

- [ ] **Step 1:** Skill `security-audit` sobre el diff `f8b47fc..HEAD` del backend con foco en: escalada por roles propios (clave de rol de otra financiera, `admin` asignado por quien no es dueño), resolutor sin memo cruzado, endpoint de roles (IDOR entre financieras), padrón (PII, throttle, auditoría, inyección en la carga), reverso (fuerza bruta del TOTP, autorizador ajeno), 2FA obligatoria (endpoints que se escapan).
- [ ] **Step 2:** Cada hallazgo crítico/alto: test que lo reproduce (RED) → arreglo (GREEN) → commit `fix(security): …`.
- [ ] **Step 3:** `PYTEST --create-db` completo, `npm test`, `tsc`, `build` en verde; memoria `project_security_audit_run1.md` (run-8, nota) y `project_f3_ui_implementacion.md`; tarea de ClickUp actualizada.
