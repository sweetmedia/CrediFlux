# API de Autenticación y Gestión de Usuarios - CrediFlux

Este documento describe todos los endpoints de autenticación y gestión de usuarios disponibles en la plataforma CrediFlux.

## Tabla de Contenidos

1. [Verificación de Email](#verificación-de-email)
2. [Recuperación de Contraseña](#recuperación-de-contraseña)
3. [Logout](#logout)
4. [Gestión de Perfil](#gestión-de-perfil)
5. [Gestión de Equipo](#gestión-de-equipo)

---

## Verificación de Email

### 1. Enviar Email de Verificación

**Endpoint:** `POST /api/users/auth/verify-email/send/`

**Autenticación:** No requerida (endpoint público)

**Descripción:** Envía un email con un link de verificación al usuario.

#### Request Body

```json
{
  "email": "user@example.com"
}
```

#### Response (200 OK)

```json
{
  "email": "user@example.com",
  "message": "Verification email sent successfully.",
  "uid": "MQ",
  "token": "abcdef123456"
}
```

**Nota:** Los campos `uid` y `token` se incluyen para desarrollo/testing. En producción, estos solo se envían por email.

#### Errores

- **400 Bad Request** - Email no existe o ya está verificado

```json
{
  "email": ["User with this email does not exist."]
}
```

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/auth/verify-email/send/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

---

### 2. Confirmar Verificación de Email

**Endpoint:** `POST /api/users/auth/verify-email/confirm/`

**Autenticación:** No requerida (endpoint público)

**Descripción:** Verifica el email del usuario usando el token enviado por email.

#### Request Body

```json
{
  "uid": "MQ",
  "token": "abcdef123456"
}
```

#### Response (200 OK)

```json
{
  "message": "Email verified successfully.",
  "email": "user@example.com",
  "email_verified": true
}
```

#### Errores

- **400 Bad Request** - Token inválido o expirado

```json
{
  "token": ["Invalid or expired verification token."]
}
```

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/auth/verify-email/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "MQ",
    "token": "abcdef123456"
  }'
```

---

## Recuperación de Contraseña

### 1. Solicitar Recuperación de Contraseña

**Endpoint:** `POST /api/users/auth/password-reset/request/`

**Autenticación:** No requerida (endpoint público)

**Descripción:** Envía un email con un link para restablecer la contraseña.

#### Request Body

```json
{
  "email": "user@example.com"
}
```

#### Response (200 OK)

```json
{
  "message": "If an account exists with this email, a password reset link has been sent.",
  "uid": "MQ",
  "token": "xyz789abc123"
}
```

**Nota de Seguridad:** El mensaje siempre es el mismo, exista o no el usuario, para no revelar información sobre cuentas existentes.

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/auth/password-reset/request/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

---

### 2. Confirmar Recuperación de Contraseña

**Endpoint:** `POST /api/users/auth/password-reset/confirm/`

**Autenticación:** No requerida (endpoint público)

**Descripción:** Restablece la contraseña del usuario con una nueva.

#### Request Body

```json
{
  "uid": "MQ",
  "token": "xyz789abc123",
  "new_password": "NewSecurePass123!",
  "confirm_password": "NewSecurePass123!"
}
```

#### Response (200 OK)

```json
{
  "message": "Password has been reset successfully. You can now login with your new password.",
  "email": "user@example.com"
}
```

#### Errores

- **400 Bad Request** - Contraseñas no coinciden

```json
{
  "confirm_password": ["Passwords do not match."]
}
```

- **400 Bad Request** - Token inválido

```json
{
  "token": ["Invalid or expired reset token."]
}
```

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "MQ",
    "token": "xyz789abc123",
    "new_password": "NewSecurePass123!",
    "confirm_password": "NewSecurePass123!"
  }'
```

---

## Logout

**Endpoint:** `POST /api/users/auth/logout/`

**Autenticación:** Requerida (Bearer Token)

**Descripción:** Cierra sesión del usuario agregando el refresh token a la blacklist.

### Request Body

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Response (200 OK)

```json
{
  "message": "Successfully logged out."
}
```

### Errores

- **400 Bad Request** - Token inválido

```json
{
  "refresh_token": ["Invalid or expired token: ..."]
}
```

### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/auth/logout/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

---

## Gestión de Perfil

### 1. Ver Perfil

**Endpoint:** `GET /api/users/profile/`

**Autenticación:** Requerida (Bearer Token)

**Descripción:** Obtiene la información del perfil del usuario autenticado.

### Response (200 OK)

```json
{
  "id": 4,
  "email": "jane@democompany.com",
  "username": "jane",
  "first_name": "Jane",
  "last_name": "Smith",
  "full_name": "Jane Smith",
  "phone": "+1234567890",
  "avatar": null,
  "bio": "Senior Loan Officer",
  "job_title": "Loan Officer",
  "department": "Lending",
  "role": "admin",
  "tenant": 7,
  "tenant_name": "democompany",
  "is_tenant_owner": true,
  "is_staff": true,
  "is_superuser": false,
  "email_verified": true,
  "receive_notifications": true,
  "created_at": "2025-10-28 21:49:02",
  "last_login_at": "2025-10-28 22:04:27"
}
```

### Ejemplo cURL

```bash
curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 2. Actualizar Perfil

**Endpoint:** `PUT /api/users/profile/update/` (actualización completa)
**Endpoint:** `PATCH /api/users/profile/update/` (actualización parcial)

**Autenticación:** Requerida (Bearer Token)

**Descripción:** Actualiza la información del perfil del usuario autenticado.

#### Request Body (Ejemplo Parcial)

```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "phone": "+1234567890",
  "bio": "Senior Loan Officer with 10 years of experience",
  "job_title": "Senior Loan Officer",
  "department": "Lending",
  "receive_notifications": true
}
```

#### Response (200 OK)

Retorna el perfil completo actualizado (mismo formato que GET /profile/)

### Ejemplo cURL

```bash
curl -X PATCH http://localhost:8000/api/users/profile/update/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "job_title": "Senior Loan Officer",
    "bio": "10 years of experience"
  }'
```

---

### 3. Cambiar Contraseña

**Endpoint:** `POST /api/users/profile/change-password/`

**Autenticación:** Requerida (Bearer Token)

**Descripción:** Cambia la contraseña del usuario autenticado (requiere contraseña actual).

#### Request Body

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePass456!",
  "confirm_password": "NewSecurePass456!"
}
```

#### Response (200 OK)

```json
{
  "message": "Password changed successfully."
}
```

#### Errores

- **400 Bad Request** - Contraseña actual incorrecta

```json
{
  "current_password": ["Current password is incorrect."]
}
```

- **400 Bad Request** - Contraseñas no coinciden

```json
{
  "confirm_password": ["Passwords do not match."]
}
```

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/profile/change-password/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "current_password": "OldPassword123!",
    "new_password": "NewSecurePass456!",
    "confirm_password": "NewSecurePass456!"
  }'
```

---

## Gestión de Equipo

### 1. Listar Miembros del Equipo

**Endpoint:** `GET /api/users/team/`

**Autenticación:** Requerida (Bearer Token)

**Permisos:** Usuario debe pertenecer a un tenant

**Descripción:** Lista todos los usuarios del mismo tenant.

### Response (200 OK)

```json
[
  {
    "id": 4,
    "email": "jane@democompany.com",
    "username": "jane",
    "first_name": "Jane",
    "last_name": "Smith",
    "full_name": "Jane Smith",
    "phone": "+1234567890",
    "role": "admin",
    "job_title": "Loan Officer",
    "department": "Lending",
    "is_tenant_owner": true,
    "is_active": true,
    "email_verified": true,
    "last_login_at": "2025-10-28 22:04:27",
    "created_at": "2025-10-28 21:49:02"
  },
  {
    "id": 5,
    "email": "john@democompany.com",
    "username": "john",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "phone": "+1987654321",
    "role": "loan_officer",
    "job_title": "Loan Officer",
    "department": "Lending",
    "is_tenant_owner": false,
    "is_active": true,
    "email_verified": false,
    "last_login_at": null,
    "created_at": "2025-10-28 22:10:15"
  }
]
```

### Ejemplo cURL

```bash
curl -X GET http://localhost:8000/api/users/team/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 2. Crear Miembro del Equipo

**Endpoint:** `POST /api/users/team/create/`

**Autenticación:** Requerida (Bearer Token)

**Permisos:** Usuario debe ser tenant owner o tener permisos de gestión de usuarios

**Descripción:** Crea un nuevo usuario staff en el tenant.

#### Request Body

```json
{
  "email": "newuser@democompany.com",
  "username": "newuser",
  "first_name": "New",
  "last_name": "User",
  "phone": "+1555123456",
  "password": "SecurePass123!",
  "role": "loan_officer",
  "job_title": "Loan Officer",
  "department": "Lending"
}
```

#### Roles Disponibles

- `admin` - Administrador (solo tenant owner puede asignar)
- `manager` - Gerente
- `loan_officer` - Oficial de Préstamos
- `accountant` - Contador
- `cashier` - Cajero
- `viewer` - Visualizador

#### Response (201 Created)

```json
{
  "id": 5,
  "email": "newuser@democompany.com",
  "username": "newuser",
  "first_name": "New",
  "last_name": "User",
  "full_name": "New User",
  "phone": "+1555123456",
  "role": "loan_officer",
  "job_title": "Loan Officer",
  "department": "Lending",
  "is_tenant_owner": false,
  "is_active": true,
  "email_verified": false,
  "last_login_at": null,
  "created_at": "2025-10-28 22:10:15"
}
```

#### Errores

- **400 Bad Request** - Email ya existe

```json
{
  "email": ["A user with this email already exists."]
}
```

- **403 Forbidden** - Sin permisos

```json
{
  "error": "You do not have permission to create users."
}
```

#### Ejemplo cURL

```bash
curl -X POST http://localhost:8000/api/users/team/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "email": "newuser@democompany.com",
    "username": "newuser",
    "first_name": "New",
    "last_name": "User",
    "password": "SecurePass123!",
    "role": "loan_officer",
    "job_title": "Loan Officer",
    "department": "Lending"
  }'
```

---

### 3. Ver Detalles de Miembro del Equipo

**Endpoint:** `GET /api/users/team/{id}/`

**Autenticación:** Requerida (Bearer Token)

**Permisos:** Usuario debe estar en el mismo tenant

**Descripción:** Obtiene los detalles de un miembro específico del equipo.

### Response (200 OK)

```json
{
  "id": 5,
  "email": "john@democompany.com",
  "username": "john",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "phone": "+1987654321",
  "role": "loan_officer",
  "job_title": "Loan Officer",
  "department": "Lending",
  "is_tenant_owner": false,
  "is_active": true,
  "email_verified": false,
  "last_login_at": null,
  "created_at": "2025-10-28 22:10:15"
}
```

### Ejemplo cURL

```bash
curl -X GET http://localhost:8000/api/users/team/5/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Actualizar Miembro del Equipo

**Endpoint:** `PUT /api/users/team/{id}/` (actualización completa)
**Endpoint:** `PATCH /api/users/team/{id}/` (actualización parcial)

**Autenticación:** Requerida (Bearer Token)

**Permisos:** Usuario debe tener permisos de gestión de usuarios

**Descripción:** Actualiza la información de un miembro del equipo.

#### Request Body (Ejemplo Parcial)

```json
{
  "role": "manager",
  "job_title": "Senior Loan Officer",
  "department": "Lending"
}
```

#### Response (200 OK)

Retorna el usuario actualizado (mismo formato que GET /team/{id}/)

#### Restricciones

- No se puede cambiar el rol de un tenant owner
- Solo tenant owners pueden asignar rol `admin`
- No se puede desactivar al tenant owner

### Ejemplo cURL

```bash
curl -X PATCH http://localhost:8000/api/users/team/5/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "role": "manager",
    "job_title": "Senior Loan Officer"
  }'
```

---

### 5. Eliminar (Desactivar) Miembro del Equipo

**Endpoint:** `DELETE /api/users/team/{id}/`

**Autenticación:** Requerida (Bearer Token)

**Permisos:** Usuario debe tener permisos de gestión de usuarios

**Descripción:** Desactiva un usuario (no lo elimina de la base de datos).

#### Response (200 OK)

```json
{
  "message": "User has been deactivated."
}
```

#### Restricciones

- No se puede eliminar al tenant owner
- No se puede eliminar a uno mismo

#### Errores

- **403 Forbidden** - Intentando eliminar tenant owner

```json
{
  "error": "Cannot delete tenant owner. Transfer ownership first."
}
```

### Ejemplo cURL

```bash
curl -X DELETE http://localhost:8000/api/users/team/5/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Notas de Seguridad

### Tokens JWT

- **Access Token**: Expira en 60 minutos (configurable)
- **Refresh Token**: Expira en 24 horas (configurable)
- Los tokens se invalidan al hacer logout (blacklist)

### Mejores Prácticas

1. **HTTPS en Producción**: Nunca envíes tokens por HTTP
2. **Almacenamiento Seguro**:
   - Preferir `httpOnly` cookies en producción
   - O usar `sessionStorage` si no necesitas persistencia
3. **Rotación de Tokens**: Los refresh tokens rotan automáticamente
4. **Validación de Email**: Los nuevos usuarios deben verificar su email
5. **Cambio de Contraseña**: Siempre requiere la contraseña actual

### Frontend URL

La URL del frontend para links de verificación y recuperación se configura en `.env`:

```bash
FRONTEND_URL=http://localhost:3000
```

---

## Testing con Swagger UI

Toda la API está documentada y se puede probar en:

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/

---

## Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | Operación exitosa |
| 201 | Recurso creado exitosamente |
| 400 | Datos inválidos o error de validación |
| 401 | No autenticado (falta token o es inválido) |
| 403 | Sin permisos para realizar la operación |
| 404 | Recurso no encontrado |
| 500 | Error interno del servidor |

---

## Ejemplos de Flujos Completos

### Flujo de Registro y Verificación

```bash
# 1. Registrar nuevo tenant
curl -X POST http://localhost:8000/api/tenants/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "My Company",
    "tenant_name": "mycompany",
    "email": "contact@mycompany.com",
    "subdomain": "mycompany",
    "owner_email": "owner@mycompany.com",
    "owner_first_name": "John",
    "owner_last_name": "Doe",
    "owner_password": "SecurePass123!",
    "subscription_plan": "basic"
  }'

# 2. Enviar email de verificación
curl -X POST http://localhost:8000/api/users/auth/verify-email/send/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@mycompany.com"
  }'

# 3. Verificar email (usando uid y token del email)
curl -X POST http://localhost:8000/api/users/auth/verify-email/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "MQ",
    "token": "abc123"
  }'

# 4. Login
curl -X POST http://localhost:8000/api/tenants/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@mycompany.com",
    "password": "SecurePass123!"
  }'
```

### Flujo de Recuperación de Contraseña

```bash
# 1. Solicitar recuperación
curl -X POST http://localhost:8000/api/users/auth/password-reset/request/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@mycompany.com"
  }'

# 2. Confirmar nueva contraseña (usando uid y token del email)
curl -X POST http://localhost:8000/api/users/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "MQ",
    "token": "xyz789",
    "new_password": "NewPassword456!",
    "confirm_password": "NewPassword456!"
  }'

# 3. Login con nueva contraseña
curl -X POST http://localhost:8000/api/tenants/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@mycompany.com",
    "password": "NewPassword456!"
  }'
```

### Flujo de Gestión de Equipo

```bash
# 1. Login como owner
TOKEN=$(curl -s -X POST http://localhost:8000/api/tenants/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@mycompany.com",
    "password": "SecurePass123!"
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 2. Ver equipo actual
curl -X GET http://localhost:8000/api/users/team/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Crear nuevo staff user
curl -X POST http://localhost:8000/api/users/team/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "email": "staff@mycompany.com",
    "username": "staffuser",
    "first_name": "Staff",
    "last_name": "Member",
    "password": "StaffPass123!",
    "role": "loan_officer",
    "job_title": "Loan Officer",
    "department": "Lending"
  }'

# 4. Actualizar rol del staff user
curl -X PATCH http://localhost:8000/api/users/team/5/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "role": "manager"
  }'

# 5. Desactivar staff user
curl -X DELETE http://localhost:8000/api/users/team/5/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## Endpoints Completos

| Método | Endpoint | Autenticación | Descripción |
|--------|----------|---------------|-------------|
| POST | `/api/users/auth/verify-email/send/` | No | Enviar email de verificación |
| POST | `/api/users/auth/verify-email/confirm/` | No | Confirmar verificación de email |
| POST | `/api/users/auth/password-reset/request/` | No | Solicitar recuperación de contraseña |
| POST | `/api/users/auth/password-reset/confirm/` | No | Confirmar recuperación de contraseña |
| POST | `/api/users/auth/logout/` | Sí | Cerrar sesión |
| GET | `/api/users/profile/` | Sí | Ver perfil |
| PUT/PATCH | `/api/users/profile/update/` | Sí | Actualizar perfil |
| POST | `/api/users/profile/change-password/` | Sí | Cambiar contraseña |
| GET | `/api/users/team/` | Sí | Listar equipo |
| POST | `/api/users/team/create/` | Sí | Crear miembro |
| GET | `/api/users/team/{id}/` | Sí | Ver miembro |
| PUT/PATCH | `/api/users/team/{id}/` | Sí | Actualizar miembro |
| DELETE | `/api/users/team/{id}/` | Sí | Desactivar miembro |

---

**Documentación generada para CrediFlux v1.0**
**Última actualización:** 2025-10-28
