# Remediación de la auditoría de seguridad (run-1) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar los 41 hallazgos confirmados y las 5 pistas de la auditoría run-1 del backend, de modo que una re-auditoría con el mismo método no encuentre ningún hallazgo alto ni crítico (calificación A).

**Architecture:** Cada hallazgo se cierra en su causa raíz: (1) un binding usuario↔tenant por request (middleware, permiso DRF por defecto y claim en el JWT) que resuelve a la vez el acceso cross-tenant, el registro anónimo, la desactivación de tenant inerte y la falta de revocación; (2) permisos por rol a nivel de viewset y `read_only_fields` en los serializers de estado, firmas e identidad fiscal, que cierran los bypass por rutas genéricas; (3) retirar las rutas paralelas de dj-rest-auth que duplican las propias con menos controles; (4) servir archivos privados sólo por URL firmada y con rutas por tenant; (5) endurecimientos puntuales (lockout, TOTP, validadores, RNC, PDF, CSV, SSRF, settings). Cada tarea trae un test de regresión en pytest que exige la respuesta correcta (403/400/404) y conserva el caso positivo del rol autorizado.

**Tech Stack:** Django 5 + DRF + django-tenants + simplejwt; pytest-django con las fixtures de `backend/conftest.py` (`tenant_schema`, `user_factory`, `api_client`, `auth_client`, `public_client`) y `apps/loans/tests/conftest.py` (`customer_factory`, `loan_factory`, `active_loan`). Se corre con `docker compose exec backend pytest` (Postgres real).

**Spec:** `~/security-audit-skill/CrediFlux/run-1/REPORT.md` (resumen y arreglo mínimo por hallazgo), `FINDINGS-DETAIL.md` (trazas) y `findings.json` (registros validados). Cada tarea cita la `fingerprint` del hallazgo que cierra.

## Global Constraints

- Ramas: trabajar en un worktree partiendo de `master` (skill `superpowers:using-git-worktrees`); un commit por tarea.
- No cambiar el contrato de la API que usa el frontend salvo donde la tarea lo diga (Task 22). El frontend usa `/api/tenants/login/`, `/api/auth/token/refresh/`, `/api/users/auth/*`, `/api/tenants/register/` y lee `document_file`, `pdf_file`, `certificate_file`, `photo`, `logo` como strings de URL.
- Tests: cada tarea añade `apps/<app>/tests/test_security_<tema>.py` y termina con ese archivo en verde y la suite completa sin regresiones (`docker compose exec backend pytest -q`).
- `config/settings/test.py` desactiva throttles y validadores de contraseña: los tests de throttle, lockout y validadores usan `override_settings`.
- Mensajes al usuario en español donde la vista ya está en español; identificadores de código en inglés como el resto del backend.
- Nunca imprimir ni loguear secretos. Quitar los `logger.warning` de depuración de `TenantAwareLoginSerializer.validate` que exponen email y tenant.
- Cada cambio de modelo trae su migración (`manage.py makemigrations <app>`); tras crearla, la suite se corre con `--create-db`.
- Fixture nueva compartida (Task 1): `other_tenant` en `backend/conftest.py`, un segundo `Tenant` con `Domain other.test.localhost` y `auto_create_schema = False` (sin schema; basta para probar el binding por host).

## Ya cerrado antes de este plan

- `loans.LoanPaymentViewSet.generic-write-routes-bypass-confirm-and-owner-reverse`: la Fase 0 (commit `a19ac98`) dejó `LoanPaymentViewSet.http_method_names = ['get','post','head','options']` y `CanRegisterPayments`. Task 5 añade el test de regresión que lo fija (PATCH/DELETE → 405).

## Review Focus

1. El superusuario de plataforma (`tenant=None`, `is_superuser=True`) debe seguir usando el admin en el host público y la API en cualquier host. Test en Task 1.
2. Un JWT emitido antes del despliegue no trae el claim `pwd_ts`: debe responder 401 limpio (fuerza un re-login), nunca 500. Test en Task 3.
3. Un `<img src>` del frontend no manda `Authorization`: las URLs firmadas de media deben abrir sin cabecera en el host del tenant y responder 403 en otro host o caducadas. Test en Task 17.
4. Los roles legítimos siguen operando: `loan_officer` crea clientes y préstamos, `collector` registra pagos y sus visitas, `cashier` mueve caja en sesión abierta, `accountant` emite e-CF, `admin` edita settings. Cada tarea de permisos incluye el caso positivo.
5. El flujo público de firma (`/sign/<token>`), los webhooks y los Celery tasks no tienen `request.user`: el binding de tenant y el helper de tenant del audit toleran usuario anónimo y `get_current_request()` igual a `None`. Tests en Task 1 y Task 14.

---

## Fase A — Identidad y binding al tenant

### Task 1: Binding usuario↔tenant en cada request (middleware + permiso DRF)

Cierra `tenant-isolation/request-credential-not-bound-to-host-tenant`, la parte de acceso de `apps.users.registration.open-signup-anonymous-principal-reaches-tenant-host-data`, la parte de request de `tenants.Tenant.is_active:login-serializer-only-no-request-refresh-session-enforcement`, `users.TeamMemberDetailView.get_object:tenant-none-equality-cross-principal-read` y el fallback de `TenantSettingsView`.

**Files:**
- Create: `backend/apps/core/permissions.py`
- Modify: `backend/apps/tenants/middleware.py`
- Modify: `backend/config/settings/base.py` (`REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']`)
- Modify: `backend/apps/users/views.py` (`TeamMemberDetailView.get_object`)
- Modify: `backend/apps/tenants/views.py` (`TenantSettingsView._get_effective_tenant` y sus llamadas)
- Modify: `backend/conftest.py` (fixture `other_tenant`)
- Test: `backend/apps/tenants/tests/test_security_tenant_binding.py`

**Interfaces:**
- Produces: `apps.core.permissions.user_matches_tenant(user, tenant) -> bool`: `True` si el usuario es superusuario con `tenant_id is None`; si no, exige `tenant` no nulo, `tenant.schema_name != 'public'`, `user.tenant_id == tenant.id`, `user.is_active` y `tenant.is_active`.
- Produces: `apps.core.permissions.TenantMatches(BasePermission)` con `message = 'Credenciales no válidas para esta organización.'`; `has_permission` devuelve `True` para usuarios no autenticados (lo decide `IsAuthenticated`) y `user_matches_tenant(request.user, getattr(request, 'tenant', None))` en el resto.
- Produces: fixture `other_tenant` (ver Global Constraints), scope `function`, depende de `db` y `public_schema`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/apps/tenants/tests/test_security_tenant_binding.py
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db
TENANT = "tenant.test.localhost"
OTHER = "other.test.localhost"

def bearer(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}

def test_token_of_tenant_user_is_rejected_on_other_host(tenant_schema, user_factory, other_tenant):
    user = user_factory(role="admin")
    assert APIClient(HTTP_HOST=OTHER).get("/api/users/profile/", **bearer(user)).status_code == 403

def test_token_of_tenant_user_is_accepted_on_own_host(tenant_schema, user_factory):
    user = user_factory(role="viewer")
    assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(user)).status_code == 200

def test_tenantless_non_superuser_is_rejected_on_tenant_host(tenant_schema, user_factory):
    user = user_factory(role="viewer", tenant=None)
    client = APIClient(HTTP_HOST=TENANT)
    assert client.get("/api/tenants/settings/", **bearer(user)).status_code == 403
    assert client.get("/api/loans/customers/", **bearer(user)).status_code == 403

def test_platform_superuser_is_allowed_on_tenant_and_public_hosts(tenant_schema, user_factory, public_client):
    su = user_factory(role="admin", tenant=None, is_superuser=True, is_staff=True)
    assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(su)).status_code == 200
    assert public_client.get("/api/users/profile/", **bearer(su)).status_code == 200

def test_users_of_inactive_tenant_are_rejected(tenant_schema, user_factory):
    user = user_factory(role="admin")
    tenant_schema.is_active = False
    tenant_schema.save(update_fields=["is_active"])
    try:
        assert APIClient(HTTP_HOST=TENANT).get("/api/users/profile/", **bearer(user)).status_code == 403
    finally:
        tenant_schema.is_active = True
        tenant_schema.save(update_fields=["is_active"])

def test_team_detail_requires_a_tenant(tenant_schema, user_factory, public_client):
    su = user_factory(role="admin", tenant=None, is_superuser=True, is_staff=True)
    viewer = user_factory(role="viewer", tenant=None)
    assert public_client.get(f"/api/users/team/{su.pk}/", **bearer(viewer)).status_code == 403

def test_session_user_is_rejected_on_other_host(tenant_schema, user_factory, other_tenant):
    user = user_factory(role="admin")
    client = APIClient(HTTP_HOST=OTHER)
    client.force_login(user)
    assert client.get("/api/users/profile/").status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose exec backend pytest apps/tenants/tests/test_security_tenant_binding.py -q`
Expected: FAIL (200 donde se espera 403; la fixture `other_tenant` no existe).

- [ ] **Step 3: Add the `other_tenant` fixture to `backend/conftest.py`** (crear el `Tenant` con `auto_create_schema = False` asignado en la instancia antes de `save()`, y su `Domain`).

- [ ] **Step 4: Implement `user_matches_tenant` and `TenantMatches` in `backend/apps/core/permissions.py`** (ver Interfaces).

- [ ] **Step 5: Add `'apps.core.permissions.TenantMatches'` after `IsAuthenticated` in `DEFAULT_PERMISSION_CLASSES`.** Las vistas con `permission_classes = [AllowAny]` propias (login, registro, webhooks, firma pública, health, validate-rnc) no heredan el default y no cambian.

- [ ] **Step 6: Apply the same rule to session requests in `TenantAccessControlMiddleware.__call__`**: para `request.user.is_authenticated` en todo path salvo `/admin/login/` y `/admin/logout/`, devolver `HttpResponseForbidden` si `not user_matches_tenant(request.user, getattr(request, 'tenant', None))`; después mantener la regla actual de `/admin/` por `is_staff`.

- [ ] **Step 7: Scope `TeamMemberDetailView.get_object`**: si `request.user.tenant_id is None` responder 403 `{'error': 'You do not belong to any tenant.'}`; buscar con `User.objects.get(pk=pk, tenant_id=request.user.tenant_id)`.

- [ ] **Step 8: Remove the schema fallback in `TenantSettingsView._get_effective_tenant(self, request)`**: devolver `request.user.tenant`; para un superusuario `tenant=None`, `request.tenant`; en cualquier otro caso `None` (la vista ya responde 403 cuando es `None`). Actualizar `get` y `_update_tenant` para pasar `request`.

- [ ] **Step 9: Run the tests and the whole suite**

Run: `docker compose exec backend pytest apps/tenants/tests/test_security_tenant_binding.py -q && docker compose exec backend pytest -q`
Expected: PASS, sin regresiones.

- [ ] **Step 10: Commit** `fix(security): bind authenticated requests to the host tenant (middleware + DRF permission)`

### Task 2: Retirar las rutas paralelas de dj-rest-auth y cerrar el registro abierto

Cierra la entrada de `apps.users.registration.open-signup-anonymous-principal-reaches-tenant-host-data`, `users.login.rest-auth-serializers-legacy-key-stock-login-no-2fa` y la puerta de `password/change` de `users.rest-auth-password-change.OLD_PASSWORD_FIELD_ENABLED-default-false.backup-codes-regenerate-mfa-defeat`; elimina la clave muerta `REST_AUTH_SERIALIZERS`.

**Files:**
- Modify: `backend/config/urls.py`, `backend/config/urls_public.py`
- Modify: `backend/config/settings/base.py` (`REST_AUTH`; borrar `REST_AUTH_SERIALIZERS`)
- Test: `backend/apps/users/tests/test_security_auth_routes.py`

**Interfaces:**
- Produces: en ambos URL confs sólo quedan de dj-rest-auth/simplejwt `path('api/auth/token/refresh/', TenantAwareTokenRefreshView.as_view())` (Task 3; hasta entonces `rest_framework_simplejwt.views.TokenRefreshView`) y `path('api/auth/token/verify/', TokenVerifyView.as_view())`. Se retiran los includes `dj_rest_auth.urls` y `dj_rest_auth.registration.urls`. Se conserva la `re_path` `account_confirm_email` que allauth necesita para construir el enlace del correo.
- Produces: `REST_AUTH['LOGIN_SERIALIZER'] = 'apps.users.serializers.TenantAwareLoginSerializer'` y `REST_AUTH['REGISTER_PERMISSION_CLASSES'] = ('rest_framework.permissions.IsAdminUser',)` como defensa si alguien vuelve a montar las rutas.

- [ ] **Step 1: Write the failing tests**

```python
# backend/apps/users/tests/test_security_auth_routes.py
import pytest
pytestmark = pytest.mark.django_db

@pytest.mark.parametrize("path", [
    "/api/auth/registration/", "/api/auth/login/", "/api/auth/password/change/",
    "/api/auth/password/reset/", "/api/auth/user/",
])
def test_parallel_dj_rest_auth_routes_are_gone(public_client, path):
    assert public_client.post(path, {}, format="json").status_code == 404

def test_token_refresh_route_is_still_mounted(api_client):
    assert api_client.post("/api/auth/token/refresh/", {"refresh": "x"}, format="json").status_code in (400, 401)

def test_legacy_rest_auth_serializers_key_is_gone(settings):
    assert not hasattr(settings, "REST_AUTH_SERIALIZERS")
    assert settings.REST_AUTH["LOGIN_SERIALIZER"] == "apps.users.serializers.TenantAwareLoginSerializer"
```

- [ ] **Step 2: Run the tests to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Replace the includes in both URL confs** por las dos rutas explícitas; conservar la `re_path` de confirmación de email.
- [ ] **Step 4: Update `REST_AUTH` and delete `REST_AUTH_SERIALIZERS`**; quitar los `logger.warning` de depuración de `TenantAwareLoginSerializer.validate`.
- [ ] **Step 5: Run the tests and the suite.** Expected: PASS.
- [ ] **Step 6: Commit** `fix(auth): remove dj-rest-auth login/registration/password routes; keep token refresh and verify`

### Task 3: JWT ligado al estado de la credencial y del tenant (revocación real)

Cierra `users.password-change-and-reset.no-refresh-token-revocation.OutstandingToken-not-blacklisted`, el resto de `tenants.Tenant.is_active:...` (refresh, completar 2FA) y `users.recovery-serializers.debug-gated-reset-token-in-response`.

**Files:**
- Modify: `backend/apps/users/models.py` (`password_changed_at`) + `backend/apps/users/migrations/0007_user_password_changed_at.py`
- Create: `backend/apps/users/tokens.py`
- Create: `backend/apps/users/authentication.py`
- Modify: `backend/apps/users/views.py` (`TenantAwareTokenRefreshView`, `TwoFactorLoginVerifyView.post`, vistas de reset/verificación con rama `DEBUG`)
- Modify: `backend/apps/users/serializers.py` (`PasswordResetConfirmSerializer.save`, `PasswordChangeSerializer.save`, `TwoFactorLoginSerializer.validate`, serializers de reset/verificación con rama `DEBUG`)
- Modify: `backend/apps/users/admin.py` (`reset_password_view`, `reset_password_action`: llamar a la revocación)
- Modify: `backend/apps/tenants/serializers.py` (`TenantLoginSerializer.validate` emite con `issue_tokens`)
- Create: `backend/apps/tenants/signals.py`; Modify: `backend/apps/tenants/apps.py` (`ready()` importa signals)
- Modify: `backend/config/settings/base.py` (`DEFAULT_AUTHENTICATION_CLASSES`), `backend/config/urls.py`, `backend/config/urls_public.py` (vista de refresh)
- Test: `backend/apps/users/tests/test_security_token_revocation.py`

**Interfaces:**
- Produces: `User.password_changed_at = models.DateTimeField(default=timezone.now)`.
- Produces: `apps.users.tokens.issue_tokens(user) -> RefreshToken`: `RefreshToken.for_user(user)` con `refresh['pwd_ts'] = int(user.password_changed_at.timestamp())`; el access derivado (`refresh.access_token`) hereda el claim.
- Produces: `apps.users.tokens.revoke_user_credentials(user) -> None`: fija `password_changed_at = timezone.now()`, guarda ese campo y crea `BlacklistedToken` para cada `OutstandingToken` del usuario.
- Produces: `apps.users.authentication.CrediFluxJWTAuthentication(JWTAuthentication)`: `get_user` lanza `AuthenticationFailed('Token revocado.', code='token_revoked')` si falta `pwd_ts`, no coincide con el usuario o el usuario está inactivo.
- Produces: `apps.users.views.TenantAwareTokenRefreshView(TokenRefreshView)` con `serializer_class = TenantAwareTokenRefreshSerializer` (en `apps/users/serializers.py`): carga el usuario del refresh, exige `is_active`, `pwd_ts` igual y `user_matches_tenant(user, request.tenant)`; responde `{'access': ..., 'refresh': ...}` emitidos con `issue_tokens` (misma forma que simplejwt para no tocar el frontend).
- Consumes: `user_matches_tenant` (Task 1).

- [ ] **Step 1: Write the failing tests**

```python
# backend/apps/users/tests/test_security_token_revocation.py
import pytest
pytestmark = pytest.mark.django_db
PASSWORD = "clave-de-prueba-123"

def login(client, user):
    r = client.post("/api/tenants/login/", {"email": user.email, "password": PASSWORD}, format="json")
    assert r.status_code == 200, r.content
    return r.json()

def test_password_change_invalidates_existing_tokens(api_client, user_factory):
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    hdr = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access_token']}"}
    assert api_client.get("/api/users/profile/", **hdr).status_code == 200
    body = {"current_password": PASSWORD, "new_password": "Nueva-Clave-456!", "confirm_password": "Nueva-Clave-456!"}
    assert api_client.post("/api/users/profile/change-password/", body, format="json", **hdr).status_code == 200
    assert api_client.get("/api/users/profile/", **hdr).status_code == 401
    assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401

def test_token_without_pwd_ts_claim_is_rejected(api_client, user_factory):
    from rest_framework_simplejwt.tokens import RefreshToken
    legacy = RefreshToken.for_user(user_factory()).access_token
    assert api_client.get("/api/users/profile/", HTTP_AUTHORIZATION=f"Bearer {legacy}").status_code == 401

def test_refresh_is_rejected_after_tenant_deactivation(api_client, user_factory, tenant_schema):
    user = user_factory(role="admin")
    tokens = login(api_client, user)
    tenant_schema.is_active = False
    tenant_schema.save()
    try:
        assert api_client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh_token"]}, format="json").status_code == 401
    finally:
        tenant_schema.is_active = True
        tenant_schema.save()

def test_reset_request_never_returns_token_material(public_client, user_factory, settings):
    settings.DEBUG = True
    user = user_factory(role="viewer", tenant=None)
    r = public_client.post("/api/users/auth/password-reset/request/", {"email": user.email}, format="json")
    assert r.status_code == 200
    assert not ({"token", "uid", "reset_token"} & set(r.json()))
```

- [ ] **Step 2: Run the tests to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Add `password_changed_at` and create the migration** (`makemigrations users`).
- [ ] **Step 4: Implement `tokens.py` and `authentication.py`**; registrar `CrediFluxJWTAuthentication` en `DEFAULT_AUTHENTICATION_CLASSES` en lugar de `JWTAuthentication`.
- [ ] **Step 5: Use `issue_tokens` wherever tokens are minted**: `TenantLoginSerializer.validate`, `TwoFactorLoginVerifyView.post` y la nueva vista de refresh; montarla en ambos URL confs.
- [ ] **Step 6: Call `revoke_user_credentials(user)` after every `set_password()`**: `PasswordResetConfirmSerializer.save`, `PasswordChangeSerializer.save` y las dos ramas de `UserAdmin.reset_password_view` (y `reset_password_action`).
- [ ] **Step 7: Tenant deactivation revokes**: en `apps/tenants/signals.py`, `pre_save` guarda el `is_active` anterior y `post_save` llama a `revoke_user_credentials` para cada usuario del tenant cuando pasa de activo a inactivo; conectar en `TenantsConfig.ready()`. En `TwoFactorLoginSerializer.validate`, rechazar si `not user.is_active` o `user.tenant and not user.tenant.is_active`.
- [ ] **Step 8: Remove the DEBUG token echo** de las respuestas de reset y verificación (serializers y vistas): el correo es el único canal.
- [ ] **Step 9: Run the tests with `--create-db` and the whole suite.** Expected: PASS.
- [ ] **Step 10: Commit** `fix(auth): bind JWTs to password_changed_at, tenant-aware refresh, revoke on password change and tenant deactivation`

### Task 4: Admin de Django acotado por tenant

Cierra `crediflux/apps.users.admin/UserAdmin.reset_password_view/unscoped-password-reset` (crítico), `crediflux/apps.users.admin/UserAdmin.fieldsets/is_superuser-tenant-fields-exposed`, `crediflux/apps.tenants.admin/generate_demo_data_view/is_staff-only-cross-tenant-write` y la parte admin de `tenants.registration.schema-name-no-reserved-name-guard` (schema_name editable deja schemas huérfanos).

**Files:**
- Modify: `backend/apps/users/admin.py` (`reset_password_view`, `reset_password_action`, nuevos `get_fieldsets`, `get_readonly_fields`, `has_delete_permission`)
- Modify: `backend/apps/tenants/admin.py` (`TenantAdminForm`, `readonly_fields`, `generate_demo_data_view`, `generate_demo_data_action`)
- Test: `backend/apps/users/tests/test_security_admin.py`

**Interfaces:**
- Produces: `UserAdmin._can_reset(request, target) -> bool`: superusuario `tenant=None`, o bien `request.user.can_manage_users()` y `target.tenant_id == request.user.tenant_id` y `not target.is_superuser`.
- Produces: para quien no sea superusuario `tenant=None`, `get_fieldsets` omite y `get_readonly_fields` incluye `is_superuser`, `is_staff`, `groups`, `user_permissions`, `tenant`, `is_tenant_owner`.
- Produces: `TenantAdmin.readonly_fields` incluye `schema_name` (quitar `EditableSchemaNameWidget`); `generate_demo_data_view` y `generate_demo_data_action` exigen superusuario `tenant=None` (`PermissionDenied`).

- [ ] **Step 1: Write the failing tests** (cliente `django.test.Client(HTTP_HOST='tenant.test.localhost')` con `force_login`; URLs vía `reverse('admin:users_user_reset_password', args=[pk])` y `reverse('admin:generate_demo_data')`):

```python
def test_tenant_admin_cannot_reset_a_superuser(...)          # POST → 403, contraseña intacta
def test_tenant_admin_cannot_reset_user_of_other_tenant(...) # POST generate_random → 403
def test_viewer_cannot_open_reset_view(...)                  # GET → 403
def test_change_form_ignores_privilege_fields(...)           # POST is_superuser/is_tenant_owner → siguen False
def test_demo_data_view_is_superuser_only(...)               # GET como admin de tenant → 403
def test_tenant_admin_can_reset_own_team_member(...)         # caso positivo → 302 y check_password True
```

- [ ] **Step 2: Run the tests to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement `_can_reset` and enforce it** al inicio de `reset_password_view` (`raise PermissionDenied`) y dentro de `reset_password_action` (saltar con `messages.error` los no permitidos).
- [ ] **Step 4: Implement `get_fieldsets`, `get_readonly_fields` and align `has_delete_permission` with `has_change_permission`.**
- [ ] **Step 5: `TenantAdmin`: `schema_name` read-only; superuser-only demo data.**
- [ ] **Step 6: Run the tests and the suite.** Expected: PASS.
- [ ] **Step 7: Commit** `fix(admin): tenant-scoped password reset, hidden privilege fields, read-only schema_name, superuser-only demo data`

## Fase B — Autorización en las APIs del tenant

### Task 5: Préstamos, clientes, documentos y contratos: rol por viewset y campos de estado read-only

Cierra `loans.viewsets.generic-crud-IsAuthenticated-no-role-gate`, `loans.LoanViewSet.partial_update.status-writable-bypasses-CanApproveLoan`, `loans.ContractViewSet.generic-update-and-sign_customer-ungated`, `loans.CustomerDocumentSerializer.verification_status-writable-bypasses-verify`, `loans.LoanSerializer.user-fks-unscoped-shared-users-table` y `crediflux.loans.contract-signature-token.cancel-does-not-revoke.public-sign-ignores-status`.

**Files:**
- Create: `backend/apps/loans/fields.py`
- Modify: `backend/apps/loans/permissions.py` (añadir `CanManageCollections`)
- Modify: `backend/apps/loans/views.py` (`CustomerViewSet`, `CustomerDocumentViewSet`, `LoanViewSet`, `CollateralViewSet`, `ContractTemplateViewSet`, `ContractViewSet`, `GuarantorViewSet`, `CustomerPhoneViewSet`, `CustomerEmailViewSet`, `CollectionReminderViewSet`, `CollectionContactViewSet`; acciones `ContractViewSet.sign_customer` y `ContractViewSet.cancel`; `public_contract_view`, `public_contract_sign`)
- Modify: `backend/apps/loans/serializers.py` (`LoanSerializer`, `LoanCreateSerializer`, `ContractSerializer`, `CustomerDocumentSerializer`)
- Modify: `backend/apps/loans/utils_contracts.py` (`regenerate_latest_loan_contract`)
- Test: `backend/apps/loans/tests/test_security_loans_authz.py`

**Interfaces:**
- Produces: `apps.loans.fields.TenantUserField(PrimaryKeyRelatedField)`: `get_queryset()` = `User.objects.filter(tenant_id=request.user.tenant_id, is_active=True)` (vacío sin tenant); `default_error_messages` únicos `'Usuario no válido para esta organización.'` para inexistente y foráneo.
- Produces: `apps.loans.permissions.CanManageCollections(BasePermission)`: SAFE_METHODS abiertos; escritura para `admin`, `manager`, `loan_officer`, `collector`, `collection_supervisor`, dueño y superusuario.
- Produces: `permission_classes = [IsAuthenticated, CanManageLoans]` en Customer, CustomerDocument, Loan, Collateral, ContractTemplate, Contract, Guarantor; `[IsAuthenticated, CanManageCollections]` en CustomerPhone, CustomerEmail, CollectionReminder, CollectionContact.
- Produces: `LoanSerializer.Meta.read_only_fields` += `status, approval_date, rejection_date, disbursement_date, maturity_date, approved_by, rejected_by, approval_notes`; `loan_officer = TenantUserField(required=False, allow_null=True)` en `LoanSerializer` y `LoanCreateSerializer`.
- Produces: `ContractSerializer.Meta.read_only_fields` += `content, status, customer_signed_at, customer_signature, officer_signed_at, officer_signature, witness_signature, witness_signed_at`.
- Produces: `CustomerDocumentSerializer.Meta.read_only_fields` += `verification_status, rejection_reason`.
- Produces: `sign_customer` lleva `permission_classes=[CanManageLoans]`; `ContractViewSet.cancel` marca `used_at = timezone.now()` en los `ContractSignatureToken` del contrato aún sin usar; `public_contract_view` y `public_contract_sign` responden 410 cuando `contract.status != 'pending_signature'` o `contract.is_archived`.
- Produces: `regenerate_latest_loan_contract` devuelve `None` sin escribir cuando el contrato ya tiene `customer_signed_at` u `officer_signed_at`.

- [ ] **Step 1: Write the failing tests** (fixtures locales `viewer_client`/`officer_client` = `APIClient(HTTP_HOST='tenant.test.localhost')` + `force_authenticate` con `user_factory(role=...)`):

```python
def test_viewer_cannot_create_customer_or_loan(...)                 # POST → 403 en ambos
def test_viewer_cannot_patch_loan(...)                              # PATCH /api/loans/<id>/ → 403
def test_officer_patch_keeps_status_and_approved_by(...)            # PATCH status/approved_by → 200, BD sin cambios
def test_officer_cannot_assign_user_of_other_tenant_as_officer(...) # PATCH loan_officer foráneo → 400 con clave 'loan_officer'
def test_viewer_cannot_sign_customer_nor_patch_contract(...)        # 403 en ambos
def test_officer_patch_cannot_change_signatures_or_content(...)     # 200, campos intactos
def test_verification_status_is_read_only_on_generic_routes(...)    # viewer 403; officer 200 y sigue 'pending'
def test_cancel_revokes_tokens_and_public_view_is_gone(...)         # tras cancel, GET público del token → 410
def test_regenerate_skips_signed_contract(...)                      # content intacto
def test_officer_can_create_customer_and_loan(...)                  # caso positivo 201
def test_payment_generic_writes_stay_closed(...)                    # PATCH y DELETE de un pago → 405 (fijado en Fase 0)
```

- [ ] **Step 2: Run the tests to verify they fail.** Run: `docker compose exec backend pytest apps/loans/tests/test_security_loans_authz.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement `TenantUserField`, `CanManageCollections`, the `permission_classes` and the `read_only_fields` changes.**
- [ ] **Step 4: Gate `sign_customer`, revoke tokens in `cancel`, check status in the public views, guard `regenerate_latest_loan_contract`.**
- [ ] **Step 5: Run the tests and the suite.** Expected: PASS (los tests existentes de loans usan `auth_client` con admin).
- [ ] **Step 6: Commit** `fix(loans): role gates on all viewsets, read-only workflow and signature fields, tenant-scoped user FKs, token revocation on cancel`

### Task 6: Facturación fiscal (e-CF): rol, estado, totales e identidad protegidos

Cierra `crediflux.billing.views.fiscal-workflow-IsAuthenticated-only-writable-state-totals-sequence`.

**Files:**
- Create: `backend/apps/billing/permissions.py`
- Modify: `backend/apps/billing/views.py` (`DigitalCertificateViewSet`, `FiscalSequenceViewSet`, `InvoiceViewSet` y sus acciones `generate_ecf`, `sign_ecf`, `submit_to_dgii`, `check_dgii_status`; `ECFProviderViewSet`; `DGIIReportViewSet`)
- Modify: `backend/apps/billing/serializers.py` (`InvoiceDetailSerializer`, `FiscalSequenceSerializer`)
- Modify: `backend/apps/billing/models.py` (`FiscalSequence.get_next_encf`, `Invoice.recalculate_totals`)
- Test: `backend/apps/billing/tests/test_security_billing.py`

**Interfaces:**
- Produces: `apps.billing.permissions.CanManageBilling(BasePermission)`: `allowed_roles = ('admin', 'accountant')`, dueño y superusuario pasan; SAFE_METHODS abiertos salvo para `view.action in ('generate_ecf', 'sign_ecf', 'submit_to_dgii', 'check_dgii_status', 'submit_invoice', 'query_invoice')`.
- Produces: `InvoiceDetailSerializer.Meta.read_only_fields` += `status, encf_number, fiscal_sequence, certificate, security_code, emisor_rnc, emisor_razon_social, comprador_rnc, comprador_razon_social, subtotal, total_itbis, total_discount, total`; `FiscalSequenceSerializer.Meta.read_only_fields` += `current_number`.
- Produces: `Invoice.recalculate_totals() -> None` (suma `InvoiceItem`), llamado en `generate_ecf` antes de construir el XML; `InvoiceViewSet.perform_update`/`perform_destroy` lanzan `ValidationError('Solo facturas en borrador pueden modificarse')` si `status != 'draft'`; `sign_ecf` sólo acepta certificados `is_active=True` y no vencidos; `environment` sale de `connection.tenant.dgii_environment or 'testecf'`, nunca del request; `get_next_encf` corre en `transaction.atomic()` con `select_for_update()`.

- [ ] **Step 1: Write the failing tests** (viewer y accountant; factura draft con un ítem de 5000.00):

```python
def test_viewer_cannot_create_sequence_or_edit_invoice(...)      # 403
def test_accountant_patch_keeps_status_and_total(...)            # 200; status 'draft', total == suma de ítems
def test_issued_invoice_cannot_be_deleted(...)                   # status 'generated' → DELETE 400
def test_sign_rejects_inactive_certificate(...)                  # 400
def test_submit_uses_tenant_environment(...)                     # mock DGIIClient; kwarg environment == tenant.dgii_environment
def test_accountant_can_create_sequence_and_invoice(...)         # caso positivo 201
```

- [ ] **Step 2: Run to verify they fail.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run the tests and the suite. Expected: PASS.**
- [ ] **Step 5: Commit** `fix(billing): role gate, read-only fiscal state and totals, active certificate, tenant environment, atomic e-NCF`

### Task 7: Caja: movimientos sólo en sesión abierta y con monto positivo

Cierra `crediflux.cashbox.CashMovement.no-open-session-check-closed-ledger-mutable`.

**Files:**
- Modify: `backend/apps/cashbox/serializers.py` (`CashMovementCreateSerializer.validate_session`, `validate_amount`)
- Modify: `backend/apps/cashbox/views.py` (`CashMovementViewSet.perform_update`, `perform_destroy`)
- Test: `backend/apps/cashbox/tests/test_security_cashbox.py`

- [ ] **Step 1: Tests**: con `cashier`, sesión abierta + movimiento 500 + cierre; luego POST en la sesión cerrada → 400 (`'La sesión de caja no está abierta.'`); POST con `amount` `-100.00` → 400 (`'El monto debe ser mayor que cero.'`); PATCH y DELETE del movimiento de la sesión cerrada → 400; movimiento en sesión abierta → 201.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(cashbox): movements only in open sessions and with positive amounts`

### Task 8: WhatsApp: envío con rol y destinatario ligado; webhook con `phone_number_id` único y por entrada

Cierra `crediflux.communications.whatsapp-send.no-role-gate.arbitrary-recipient`, `crediflux.communications.whatsapp-webhook.tenant-by-body-phone-number-id.non-unique-newest-wins` y la pista `crediflux.communications.whatsapp-webhook.multi-entry-payload-bound-to-entry0-tenant`.

**Files:**
- Create: `backend/apps/communications/permissions.py`
- Modify: `backend/apps/communications/views_whatsapp.py` (`send`)
- Modify: `backend/apps/tenants/models.py` (`whatsapp_phone_id` → `unique=True`) + migración que normaliza `''` a `NULL` antes del `AlterField`
- Modify: `backend/apps/tenants/serializers.py` (`TenantUpdateSerializer.validate_whatsapp_phone_id`)
- Modify: `backend/apps/communications/webhooks/utils.py` (`find_tenant_by_phone_id`), `backend/apps/communications/webhooks/handlers.py` (`WhatsAppWebhookHandler.process`)
- Test: `backend/apps/communications/tests/test_security_whatsapp.py`

**Interfaces:**
- Produces: `apps.communications.permissions.CanSendMessages`: roles `admin, manager, loan_officer, collector, collection_supervisor`, dueño y superusuario.
- Produces: `send` requiere `CanSendMessages` y resuelve el destino sólo si existe `WhatsAppMessage` con ese `conversation_id` o un `Customer` del tenant con ese teléfono; si no, 404.
- Produces: `validate_whatsapp_phone_id` normaliza vacío a `None` y rechaza con `'Este phone_number_id ya está en uso.'` si otro tenant lo tiene; `find_tenant_by_phone_id` devuelve `None` (y loguea `error`) si hay 0 o más de 1 coincidencias; `process` salta y loguea cada `change` cuyo `value.metadata.phone_number_id` no coincide con `self.tenant.whatsapp_phone_id`.

- [ ] **Step 1: Tests**: viewer POST send → 403; collector send a un número sin conversación ni cliente → 404; collector send a conversación existente → 202/200 (task mockeada); settings PATCH de tenant B con el phone_id de A → 400; handler de A con payload de dos entradas (A y B) encola sólo la de A (mock de la task).
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement + migration.**  - [ ] **Step 4: Run tests (`--create-db`) + suite → PASS.**
- [ ] **Step 5: Commit** `fix(communications): role-gated send bound to conversations, unique phone_number_id, per-entry webhook check`

### Task 9: IA: conversaciones con dueño, clave por request y rol en la configuración

Cierra `apps.ai.views.ChatView.post:conversation_id-unbound-to-user`, `apps.ai.views.apply_tenant_ai_config:process-global-provider-key` y `crediflux/apps.ai/AIConfigView.put/is_staff-write-gate-weaker-than-tenant-settings`; acota `calcular_prestamo` (variante del hallazgo del calculador).

**Files:**
- Modify: `backend/apps/ai/views.py` (`apply_tenant_ai_config` → `build_tenant_agent`, `ChatView.post`, `AIConfigView.put`)
- Modify: `backend/apps/ai/agents.py` (hook de proveedor por instancia)
- Modify: `backend/apps/ai/tools.py` (`calcular_prestamo`)
- Test: `backend/apps/ai/tests/test_security_ai.py`

**Interfaces:**
- Produces: `ChatView.post`: con `conversation_id`, lo parsea como UUID (400 si no) y exige `Conversation.objects.filter(id=cid, metadata__user_id=request.user.pk).exists()` (404 si no); sin `conversation_id`, `agent.start_conversation(metadata={'user_id': request.user.pk, 'schema': connection.schema_name})`.
- Produces: la clave del tenant deja de escribirse en `os.environ`: los agentes de `apps/ai/agents.py` aceptan `provider_config: ProviderConfig | None` y sobreescriben el método de `Promptable` que hoy hace `registry.get(name)` (`djangosdk/agents/mixins/promptable.py`, ~línea 60) para devolver `LiteLLMProvider(provider_config=self.provider_config)` cuando está puesto. `build_tenant_agent(agent_class, ai_config)` construye esa `ProviderConfig(name=provider, api_key=key, default_model=model)`.
- Produces: `AIConfigView.put` exige `user.is_tenant_owner or user.role == 'admin' or user.is_superuser` (igual que `TenantSettingsView`), nunca `is_staff`.
- Produces: `calcular_prestamo` rechaza `plazo_meses` fuera de `1..600` con un mensaje al modelo.

- [ ] **Step 1: Tests** (con `litellm.completion` parcheado y `AI_ENABLED=True`): segundo usuario con el `conversation_id` del primero → 404 y sin `Message` nuevo; `conversation_id` malformado → 400; tras una petición de un tenant con clave propia, `os.environ` no contiene esa clave y el proveedor recibió `api_key` de la clave del tenant (inspeccionar los kwargs del mock); viewer PUT config → 403; admin PUT → 200.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(ai): conversation ownership, per-request provider key, role gate on config, bounded loan tool`

### Task 10: Política de originación del tenant y límite de usuarios aplicados

Cierra `tenants.Tenant.loan-origination-policy:no-enforcement-in-loans` y `tenants.Tenant.max_users:no-enforcement-on-team-create`.

**Files:**
- Create: `backend/apps/loans/policy.py`
- Modify: `backend/apps/loans/serializers.py` (`LoanCreateSerializer.validate`, `LoanSerializer.validate`)
- Modify: `backend/apps/loans/views.py` (`LoanViewSet.approve`, `LoanViewSet.disburse`)
- Modify: `backend/apps/loans/admin.py` (`approve_loans`, `disburse_loans`)
- Modify: `backend/apps/tenants/serializers.py` (`TenantUpdateSerializer.validate` cruzado: `min_* <= max_*`, montos no negativos, `max_active_loans_per_customer >= 1`)
- Modify: `backend/apps/users/serializers.py` (`TeamMemberCreateSerializer.validate`), `backend/apps/users/views.py` (`TeamMemberCreateView.post` en `transaction.atomic()` con `select_for_update` del tenant)
- Test: `backend/apps/loans/tests/test_security_loan_policy.py`, `backend/apps/users/tests/test_security_team_limits.py`

**Interfaces:**
- Produces: `apps.loans.policy.validate_origination(attrs, customer, request=None)`, `validate_approval(loan, request=None)`, `validate_disbursement(loan, user, request=None)`: leen el tenant de `connection.tenant` (fallback `request.user.tenant`) y lanzan `serializers.ValidationError` con la regla incumplida (rango de monto, tasa y plazo; `max_active_loans_per_customer` contando `pending/approved/active`; `require_id_document`; garante/colateral por umbral; `require_credit_score`/`minimum_credit_score`; `require_disbursement_approval`: quien desembolsa no es `approved_by` salvo admin/dueño).
- Produces: `TeamMemberCreateSerializer.validate` rechaza con `'Límite de usuarios del plan alcanzado.'` cuando `User.objects.filter(tenant=tenant, is_active=True).count() >= tenant.max_users`.

- [ ] **Step 1: Tests**: con política ajustada por el dueño (monto máximo 50000, tasa máxima 20, plazo máximo 12, `require_guarantor`, `require_disbursement_approval`, `max_active_loans_per_customer=1`): POST de préstamo fuera de rango → 400 con claves `principal_amount`, `interest_rate`, `term_months`; aprobar sin garante → 400; mismo manager aprueba y desembolsa → 400; segundo préstamo del mismo cliente → 400; préstamo dentro de política → 201/200. Con `max_users=1` y un usuario activo, `team/create/` → 400; con `max_users=2` → 201.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `feat(policy): enforce tenant loan-origination limits and max_users`

### Task 11: Cobradores: visitas y ubicaciones acotadas al propio cobrador

Cierra `loans.collector-geolocation-and-visits.no-object-scoping`.

**Files:**
- Modify: `backend/apps/loans/views_geolocation.py` (`CollectorVisitViewSet.get_queryset`, `perform_create`, `permission_classes`; `CollectorLocationViewSet.get_queryset`)
- Test: `backend/apps/loans/tests/test_security_geolocation.py`

**Interfaces:**
- Produces: `get_queryset` filtra por `collector=request.user` salvo que `request.user.role in ('admin', 'manager', 'collection_supervisor')` o sea dueño; `perform_create` fuerza `collector=request.user`; `permission_classes = [IsAuthenticated, CanManageCollections]`.

- [ ] **Step 1: Tests**: cobrador B no ve ni edita la visita de cobrador A (404 en GET/PATCH); supervisor sí la ve; viewer no crea visitas (403); cobrador crea la suya (201) y el `collector` guardado es él aunque mande otro id.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(loans): scope collector visits and locations to the collector or supervisors`

## Fase C — Endurecimiento de autenticación

### Task 12: Límite de intentos de login y validadores de contraseña en todas las rutas

Cierra `crediflux.auth.anonymous-login-no-per-account-attempt-limit-or-lockout`.

**Files:**
- Create: `backend/apps/users/lockout.py`
- Modify: `backend/apps/tenants/serializers.py` (`TenantLoginSerializer.validate`, `TenantRegistrationSerializer.validate_owner_password`)
- Modify: `backend/apps/users/serializers.py` (`TeamMemberCreateSerializer`, `PasswordResetConfirmSerializer`, `PasswordChangeSerializer`: validación de fortaleza; `TenantAwareLoginSerializer.validate` usa el mismo contador)
- Modify: `backend/apps/users/admin.py` (`reset_password_view`: `validate_password` en vez de `len < 8`)
- Modify: `backend/config/urls.py`, `backend/config/urls_public.py` (login del admin envuelto con `django_ratelimit`)
- Modify: `backend/config/settings/development.py` (quitar `AUTH_PASSWORD_VALIDATORS = []`)
- Test: `backend/apps/users/tests/test_security_lockout.py`

**Interfaces:**
- Produces: `apps.users.lockout.check_and_count(email, request) -> None` y `reset(email)`: contador en caché `login_fail:{email.lower()}` y `login_fail_ip:{ip}` con `LOGIN_FAIL_LIMIT = 5` y `LOGIN_FAIL_WINDOW = 300`; `check_and_count` lanza `serializers.ValidationError('Demasiados intentos. Intenta de nuevo en unos minutos.')` al superar el límite; el serializer lo llama antes de `authenticate()`, incrementa tras un fallo y llama a `reset` tras un éxito.
- Produces: `apps.users.lockout.validate_strength(password, user=None)`: envuelve `django.contrib.auth.password_validation.validate_password` y convierte `DjangoValidationError` en `serializers.ValidationError(list(exc.messages))`; usado en los cuatro serializers y en el admin.
- Produces: `admin.site.login` envuelto en `ratelimit(key='post:username', rate='5/5m', method='POST', block=True)` en ambos URL confs.

- [ ] **Step 1: Tests** (`override_settings(AUTH_PASSWORD_VALIDATORS=<los de base.py>)` y caché `locmem` limpia por test): sexto intento fallido en `/api/tenants/login/` → 400 con el mensaje de bloqueo aunque la contraseña sea correcta; tras `reset` del contador el login correcto → 200; `team/create/` con contraseña `password1` → 400; `change-password` a `12345678` → 400; `development.py` ya no define la lista vacía (`assert settings.AUTH_PASSWORD_VALIDATORS` con `DJANGO_ENVIRONMENT=development` importando el módulo).
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(auth): per-account login lockout, password strength on every path, rate-limited admin login`

### Task 13: TOTP de un solo uso y códigos de respaldo con segundo factor

Cierra `users.TwoFactorLoginSerializer.totp-verify-no-used-step-state-replay` y el lado de códigos de respaldo de `users.rest-auth-password-change...backup-codes-regenerate-mfa-defeat`.

**Files:**
- Create: `backend/apps/users/totp.py`
- Modify: `backend/apps/users/serializers.py` (`TwoFactorLoginSerializer`, `TwoFactorVerifySerializer`, `TwoFactorDisableSerializer`, `BackupCodesRegenerateSerializer`)
- Test: `backend/apps/users/tests/test_security_totp.py`

**Interfaces:**
- Produces: `apps.users.totp.verify_totp_once(user, code) -> bool`: `pyotp.TOTP(user.totp_secret).verify(code)` y además rechaza si el paso actual (`int(time.time()) // 30`) ya está guardado en caché `totp_last_step_{user.pk}` (TTL 90 s); guarda el paso al aceptar. Usado por los tres serializers.
- Produces: `BackupCodesRegenerateSerializer` exige `password` y `code` (TOTP vigente) y responde `{'code': 'Código de verificación inválido.'}` si falla.

- [ ] **Step 1: Tests**: con dos `temp_token` pendientes del mismo usuario, el mismo código TOTP acepta la primera vez (200) y rechaza la segunda (400) dentro del mismo paso; regenerar códigos con contraseña pero sin `code` → 400; con contraseña y TOTP válido → 200 con 10 códigos.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(2fa): one-time TOTP steps and TOTP-protected backup code regeneration`

### Task 14: Audit log sin secretos, con tenant para modelos de schema y sin estado global

Cierra `crediflux/apps.audit/EXCLUDED_FIELDS/tenant-secret-plaintext-tracked-and-role-readable` y `apps.audit.signals._pre_save_instances:tenant-models-never-popped-unbounded-retention`; de paso los modelos de caja y facturación quedan auditados (hardening de Fase B).

**Files:**
- Modify: `backend/apps/audit/signals.py` (`TRACKED_MODELS`, `EXCLUDED_FIELDS`, `get_tenant_for_instance`, `audit_pre_save`, `audit_post_save`, `audit_post_delete`)
- Test: `backend/apps/audit/tests/test_security_audit_log.py`

**Interfaces:**
- Produces: `EXCLUDED_FIELDS` += todos los campos secretos de `Tenant` (`smtp_password`, `imap_password`, `whatsapp_access_token`, `whatsapp_app_secret`, `whatsapp_verify_token`, `ai_api_key`, `nexconnect_api_key`, `certificate_password` y cualquier otro campo cuyo nombre contenga `password`, `secret`, `token` o `api_key`; implementar como conjunto más una comprobación por sufijo en `get_changes`).
- Produces: `TRACKED_MODELS` += `CashSession`, `CashMovement`, `Invoice`, `FiscalSequence`, `DigitalCertificate`, y la clave de `Contract` corregida a `apps.loans.models_contracts.Contract`.
- Produces: `get_tenant_for_instance` cae a `request.tenant` (de `get_current_request()`) y luego a `django.db.connection.tenant` cuando el modelo no tiene FK a tenant; devuelve `None` sólo si tampoco hay conexión de tenant.
- Produces: el snapshot pre-save vive en `instance._audit_old_instance` (no hay dict de módulo); `audit_post_save` lo consume con `instance.__dict__.pop(...)` antes de cualquier `return`; `audit_pre_save` no consulta la BD si no se puede resolver tenant.

- [ ] **Step 1: Tests**: PATCH de settings con `smtp_password` por un admin → el `AuditLog` creado no contiene la clave en `changes` (ni old ni new); un movimiento de caja y una factura generan `AuditLog` con el tenant del schema; tras N PATCH de clientes distintos, `apps.audit.signals` no tiene atributo `_pre_save_instances` y `tracemalloc` no crece con N (o simplemente `hasattr` False y el snapshot no queda en la instancia tras el save).
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(audit): never log tenant secrets, resolve tenant from schema, drop module-level pre-save cache`

### Task 15: Registro de tenants: throttle propio, nombres reservados y errores genéricos

Cierra `tenants.registration.schema-name-no-reserved-name-guard` (parte API), `tenants.registration.TenantRegistrationView.sync-schema-migration-no-cap-no-reclaim` y `crediflux.tenants.registration-validators-account-tenant-existence-oracle`.

**Files:**
- Modify: `backend/apps/tenants/views.py` (`TenantRegistrationView`: `throttle_classes`, manejo de errores)
- Modify: `backend/apps/tenants/serializers.py` (`TenantRegistrationSerializer.validate_tenant_name`, `validate_subdomain`, `validate_owner_email`, `create`)
- Modify: `backend/config/settings/base.py` (`DEFAULT_THROTTLE_RATES['tenant_registration']`, `MAX_TENANTS_PER_DAY`)
- Test: `backend/apps/tenants/tests/test_security_registration.py`

**Interfaces:**
- Produces: `TenantRegistrationThrottle(AnonRateThrottle)` con `scope = 'tenant_registration'` y tasa `config('DRF_THROTTLE_TENANT_REGISTRATION', default='3/hour')`; además un tope global `MAX_TENANTS_PER_DAY = config(..., default=20, cast=int)` comprobado en `create` contra `Tenant.objects.filter(created_on__gte=now-1d).count()`.
- Produces: `RESERVED_TENANT_NAMES = {'public','pg-catalog','pg-toast','information-schema','www','admin','api','app','mail','ftp','localhost','test'}` y rechazo de `tenant_name` cuyo `schema_name` derivado exista en `Tenant.schema_name` o en PostgreSQL (`django_tenants.utils.schema_exists`), re-comprobado dentro de la transacción de `create`.
- Produces: los tres validadores de existencia devuelven el mismo mensaje genérico `'No se pudo completar el registro con estos datos.'` (sin distinguir email, nombre o subdominio); la vista responde 400 genérico ante `IntegrityError`/excepciones internas en vez de `str(e)`.

- [ ] **Step 1: Tests** (`override_settings` para activar el throttle): cuarto registro desde la misma IP en una hora → 429; `tenant_name='public'` y `tenant_name` igual al schema `test` existente → 400; email/nombre/subdominio existentes devuelven el mismo mensaje que entre sí y distinto de 201; registro válido → 201.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(tenants): registration throttle and daily cap, reserved and existing schema guard, uniform validation errors`

### Task 16: Consulta de RNC en O(1), sin scraping anónimo y con throttle propio

Cierra `crediflux.core.rnc_lookup.RNCLookupService.full-registry-json-per-anonymous-request` y `core.validate_cedula_view.IsAuthenticated-any-role-registry-lookup`.

**Files:**
- Modify: `backend/apps/core/services/rnc_lookup.py` (`lookup`, `is_database_loaded`, `_cache_scraped_result`, `validate`)
- Modify: `backend/apps/core/management/commands/update_rnc_database.py` y `backend/apps/core/tasks.py` (carga por claves)
- Modify: `backend/apps/core/views.py` (`validate_rnc_view`, `rnc_database_status`, `validate_cedula_view`)
- Modify: `backend/config/settings/base.py` (`DEFAULT_THROTTLE_RATES['validate_rnc']`)
- Test: `backend/apps/core/tests/test_security_rnc.py`

**Interfaces:**
- Produces: registro en caché por clave `dgii_rnc:{rnc}` (valor: dict del registro) escrito con `cache.set_many` en lotes de 5000 por ambos cargadores; `is_database_loaded()` lee sólo `dgii_rnc_database_meta`; `lookup` hace un `cache.get` por clave; `_cache_scraped_result` escribe una clave.
- Produces: `validate_rnc(rnc, allow_scrape: bool)`; la vista pasa `allow_scrape=request.user.is_authenticated`; `validate_rnc_view` y `rnc_database_status` llevan `ScopedRateThrottle` con `throttle_scope = 'validate_rnc'` y tasa `config('DRF_THROTTLE_VALIDATE_RNC', default='10/minute')`; el formato se valida antes de tocar la caché.
- Produces: `validate_cedula_view` exige rol `admin, manager, loan_officer, collector, collection_supervisor` (reutilizar `CanManageCollections`).

- [ ] **Step 1: Tests** (caché `locmem`): con 1000 registros cargados, una consulta hace exactamente 1 `cache.get` del registro (envolver `cache.get`); formato inválido no toca la caché; anónimo con RNC inexistente no invoca el scraper (mock) y autenticado sí; `validate_cedula_view` con viewer → 403.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `perf(core): per-key RNC cache, authenticated-only scraping, dedicated throttle, role-gated cedula lookup`

## Fase D — Superficie anónima, archivos y configuración

### Task 17: Archivos privados por URL firmada y rutas por tenant

Cierra `media-debug-static-serve-unauthenticated-blob-read` y `media-s3-public-read-acl-blob-overreach`.

**Files:**
- Create: `backend/apps/core/storage.py` (`tenant_upload_to`), `backend/apps/core/media.py` (`signed_media_url`, `SignedFileField`), `backend/apps/core/media_views.py` (`SignedMediaView`)
- Modify: `backend/config/urls.py`, `backend/config/urls_public.py` (ruta `media/s/<signed>/`; quitar `static(settings.MEDIA_URL, ...)`, conservar `static(STATIC_URL)`)
- Modify: `backend/config/settings/production.py` (`AWS_DEFAULT_ACL = 'private'`, `AWS_QUERYSTRING_AUTH = True`)
- Modify: todos los `upload_to=` de `apps/*/models*.py` (usar `tenant_upload_to('<prefijo actual>')`) + migraciones `AlterField`
- Modify: serializers que exponen archivos (`CustomerDocumentSerializer`, `ContractSerializer`, `DigitalCertificateUploadSerializer`, `CustomerSerializer.photo`, `TenantSerializer.logo`, `GuarantorSerializer`, `CollateralSerializer`, geolocation): campo de archivo → `SignedFileField`
- Test: `backend/apps/core/tests/test_security_media.py`

**Interfaces:**
- Produces: `tenant_upload_to(prefix)` devuelve un callable `f'{connection.schema_name}/{prefix}/{secrets.token_urlsafe(16)}/{filename}'`.
- Produces: `signed_media_url(name, schema) -> str`: `TimestampSigner(salt='media').sign(f'{schema}|{name}')` en `reverse('signed-media', args=[value])`; `SignedFileField(serializers.FileField)` cuyo `to_representation` devuelve esa URL (o `None`).
- Produces: `SignedMediaView` (sin autenticación): `unsign(max_age=settings.MEDIA_SIGNED_URL_MAX_AGE, default 3600)`, exige `schema == request.tenant.schema_name` (o superusuario autenticado por sesión en el host público), responde `FileResponse` del `default_storage`; 403 en firma inválida, caducada o de otro tenant; 404 si no existe.

- [ ] **Step 1: Tests**: con `DEBUG=True` forzado y las URL confs recargadas, `GET /media/<ruta>` anónimo → 404 (ya no hay ruta); la URL firmada que devuelve el serializer abre sin cabecera en el host del tenant (200, bytes iguales); la misma URL en `other.test.localhost` → 403; una firma con `max_age` vencido → 403; un `CustomerDocument` nuevo se guarda bajo `test/customer_documents/...`.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement + migrations.**  - [ ] **Step 4: Run tests (`--create-db`) + suite → PASS.**
- [ ] **Step 5: Commit** `fix(media): signed tenant-bound file URLs, per-tenant upload paths, no anonymous MEDIA_ROOT, private S3 ACL`

### Task 18: Settings: credenciales de BD sin default, `DATABASE_URL` leído, `NUM_PROXIES`, bootstrap sin contraseña fija

Cierra `backend/config/settings/base.py:DATABASES.default:hardcoded-default-credentials`, `crediflux.settings.REST_FRAMEWORK.NUM_PROXIES-unset-xff-throttle-identity` y `backend/setup_initial_tenant.py:create_superuser:hardcoded-password-admin`.

**Files:**
- Modify: `backend/config/settings/base.py` (`DATABASES`, `REST_FRAMEWORK['NUM_PROXIES']`)
- Modify: `backend/config/settings/production.py` (fallo cerrado si falta la contraseña)
- Modify: `backend/setup_initial_tenant.py`
- Modify: `.env.example`, `docker-compose.yml` (variables `DB_*` o `DATABASE_URL` coherentes con lo que lee Django)
- Test: `backend/tests/test_security_settings.py`

**Interfaces:**
- Produces: `DATABASES['default']` = `dj_database_url.parse(DATABASE_URL, engine='django_tenants.postgresql_backend')` si `DATABASE_URL` existe; si no, `DB_*` sin default para `DB_PASSWORD` (en `base.py` `config('DB_PASSWORD', default='')`); `production.py` lanza `ImproperlyConfigured('DB_PASSWORD or DATABASE_URL is required')` si queda vacío.
- Produces: `REST_FRAMEWORK['NUM_PROXIES'] = config('DRF_NUM_PROXIES', default=1, cast=int)`.
- Produces: `setup_initial_tenant.py` lee `INITIAL_SUPERUSER_PASSWORD` del entorno o genera una con `get_random_string(16)` y la imprime una sola vez; nunca `admin2026`.

- [ ] **Step 1: Tests** (importando `config.settings.base` con `os.environ` manipulado vía `monkeypatch` e `importlib.reload`): con `DATABASE_URL=postgres://u:p@h:5/d` y sin `DB_*`, `DATABASES['default']['USER'] == 'u'` y `['HOST'] == 'h'`; sin ninguna variable, `PASSWORD == ''`; `NUM_PROXIES == 1`; `grep` del repo sin `admin2026` (test que lee el archivo).
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(settings): read DATABASE_URL, no default DB password, NUM_PROXIES, no hardcoded bootstrap password`

### Task 19: PDF de contratos sin markup inyectable y CSV 607 sin fórmulas

Cierra `loans-contract-pdf-paragraph-unescaped-markup-injection` y `billing-dgii607-csv-formula-injection-id-number`.

**Files:**
- Modify: `backend/apps/loans/utils_pdf.py` (párrafos de `contract.content`, `special_terms`)
- Modify: `backend/apps/billing/reports_dgii.py` (`csv_safe`, `normalize_tax_id`, ambos `generate_csv`)
- Modify: `backend/apps/loans/serializers.py` (`CustomerSerializer.validate` para `id_number`)
- Test: `backend/apps/loans/tests/test_security_pdf.py`, `backend/apps/billing/tests/test_security_csv.py`

**Interfaces:**
- Produces: en `utils_pdf.py`, el texto del contrato pasa por `html.escape()` antes de `Paragraph(...)` (los `\n` → `<br/>` se añaden después del escape); `reportlab.rl_config.trustedSchemes = ['file']` se deja fuera: fijar `trustedSchemes = []` y `trustedHosts = []` al cargar el módulo.
- Produces: `csv_safe(value) -> str` antepone `'` cuando la celda empieza por `=`, `+`, `-`, `@`, tab, CR o LF; `normalize_tax_id(raw)` deja sólo alfanuméricos; ambos writers envuelven cada celda.
- Produces: `CustomerSerializer.validate` exige `id_number` alfanumérico con guiones/espacios y, por `id_type`, 11 dígitos para cédula y 9 para RNC.

- [ ] **Step 1: Tests**: un contrato cuyo contenido incluye una etiqueta `<img>` produce un PDF (bytes no vacíos) y la cadena escapada aparece como texto (buscar `&lt;img` en el flujo o comprobar que `Paragraph` recibió texto escapado vía mock); 607 con un cliente cuyo `id_number` empieza por `=` sale con `'=` en la celda; crear cliente con `id_number='=HYPERLINK(1)'` → 400.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(reports): escape contract markup in PDFs, neutralize CSV formulas, validate id_number`

### Task 20: Actualización del RNC: URL fija y disparo sólo para superusuarios; calculador acotado

Cierra `core-rnc-update-ssrf-constance-fetch-url` y `crediflux.loans.LoanCalculatorInputSerializer.term-no-upper-bound`.

**Files:**
- Modify: `backend/apps/core/management/commands/update_rnc_database.py` (`_download_rnc_file`)
- Modify: `backend/apps/core/admin.py` (`update_rnc_database_view`)
- Modify: `backend/apps/loans/serializers.py` (`LoanCalculatorInputSerializer.term`)
- Test: `backend/apps/core/tests/test_security_rnc_update.py`, ampliar `backend/apps/loans/tests/test_security_loans_authz.py`

**Interfaces:**
- Produces: `ALLOWED_RNC_HOSTS = {'dgii.gov.do', 'www.dgii.gov.do'}`; `_download_rnc_file` rechaza con `ValueError` toda URL que no sea `https` en esos hosts y llama a `requests.get(..., allow_redirects=False)`.
- Produces: `update_rnc_database_view` exige superusuario `tenant=None` (`PermissionDenied`) y encola `apps.core.tasks.update_rnc_database.delay()` en vez de ejecutar el comando en la request; el mensaje al usuario no incluye la excepción.
- Produces: `term = serializers.IntegerField(min_value=1, max_value=600)`.

- [ ] **Step 1: Tests**: con `DGII_RNC_DATABASE_URL` apuntando a `http://127.0.0.1:1/x.zip`, el comando lanza `ValueError` antes de `requests.get` (mock); POST a la vista como admin de tenant → 403; como superusuario → 302 y la task encolada (mock `delay`); calculador con `term=601` → 400.
- [ ] **Step 2: Run → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: Run tests + suite → PASS.**
- [ ] **Step 5: Commit** `fix(core): allow-listed DGII URL, superuser-only async RNC refresh, bounded calculator term`

### Task 21: Cosas pendientes de documentación de despliegue (needs validation)

Cierra el lado de código de las 5 pistas `needs_validation` que no quedaron cubiertas arriba: deja constancia en `docs/deployment/README.md` de (a) `NUM_PROXIES` y que el edge debe sobrescribir `X-Forwarded-For`, (b) no publicar el puerto de Postgres fuera de `127.0.0.1` en los compose, (c) el modelo de Meta App por tenant para WhatsApp. Sin tests; es documentación.

- [ ] **Step 1: Edit `docs/deployment/README.md`** con una sección "Supuestos de red que el código asume" con esos tres puntos y la variable `DRF_NUM_PROXIES`.
- [ ] **Step 2: Change the Postgres port mapping in `docker-compose.yml` to `127.0.0.1:5433:5432`.**
- [ ] **Step 3: Commit** `docs(deploy): network assumptions behind the security fixes; bind Postgres port to loopback`

### Task 22: Frontend: dos ajustes de contrato

**Files:**
- Modify: `frontend/lib/api/auth.ts` (`regenerateBackupCodes` envía `{ password, code }`)
- Modify: la página de seguridad del perfil que llama a esa función (añadir el campo de código TOTP)
- Modify: `frontend/lib/api/auth.ts` o `client.ts`: al recibir 401 con `code: 'token_revoked'` en el refresh, limpiar sesión y mandar al login (ya existe el manejo de 401; comprobar que no entra en bucle)
- Test: `frontend/tests/unit/` test de `regenerateBackupCodes` con vitest (payload incluye `code`)

- [ ] **Step 1: Write the failing vitest test.**  - [ ] **Step 2: Run `cd frontend && npm test` → FAIL.**  - [ ] **Step 3: Implement.**  - [ ] **Step 4: `npm test` y `npm run typecheck` → PASS.**
- [ ] **Step 5: Commit** `feat(frontend): TOTP code when regenerating backup codes; clean logout on revoked token`

### Task 23: Verificación final

- [ ] **Step 1: `docker compose exec backend pytest --create-db -q`** → toda la suite en verde.
- [ ] **Step 2: `docker compose exec backend python manage.py makemigrations --check --dry-run`** → sin migraciones pendientes.
- [ ] **Step 3: `cd frontend && npm run typecheck && npm test`** → verde.
- [ ] **Step 4: Smoke manual en Docker**: login en `tenant.localhost`, ver clientes, crear préstamo como `loan_officer`, abrir un documento (URL firmada), registrar pago como `cashier`.
- [ ] **Step 5: Re-auditoría**: correr `/security-audit` en modo `standard` sobre `backend/` indicando `~/security-audit-skill/CrediFlux/run-1/` como run previo (el skill lee su `coverage-ledger.json` y `findings.json` y revalida cada `confirmed`). La calificación A exige que ningún registro `confirmed` quede en alto o crítico.
- [ ] **Step 6: Merge** de la rama a `master` tras la revisión.
