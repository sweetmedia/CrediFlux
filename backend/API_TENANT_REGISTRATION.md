# API de Registro de Tenants - CrediFlux

## Descripción

Este endpoint permite a nuevas empresas registrarse en la plataforma SaaS CrediFlux. Al registrarse, se crea automáticamente:

1. **Tenant (Empresa)**: Un nuevo tenant con esquema de base de datos aislado
2. **Dominio**: Un subdominio para acceder al admin del tenant
3. **Usuario Owner**: Un usuario administrador que es dueño del tenant

## Endpoint

### POST `/api/tenants/register/`

**Autenticación**: No requerida (endpoint público)

**Content-Type**: `application/json`

## Request Body

```json
{
  "business_name": "ACME Corporation",
  "tenant_name": "acme-corp",
  "tax_id": "12-3456789",
  "email": "contact@acme.com",
  "phone": "+1234567890",
  "address": "123 Main Street",
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "postal_code": "10001",
  "subdomain": "acme",
  "owner_first_name": "John",
  "owner_last_name": "Doe",
  "owner_email": "john@acme.com",
  "owner_password": "SecurePass123!",
  "owner_phone": "+1234567890",
  "subscription_plan": "basic"
}
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `business_name` | string | Nombre de la empresa |
| `tenant_name` | string | Identificador único del tenant (solo minúsculas, números y guiones) |
| `email` | email | Email de contacto de la empresa |
| `subdomain` | string | Subdominio para el tenant (ej: "acme" → acme.localhost) |
| `owner_first_name` | string | Nombre del dueño/administrador |
| `owner_last_name` | string | Apellido del dueño/administrador |
| `owner_email` | email | Email del dueño (será su username para login) |
| `owner_password` | string | Contraseña del dueño (mínimo 8 caracteres) |

### Campos Opcionales

| Campo | Tipo | Descripción | Default |
|-------|------|-------------|---------|
| `tax_id` | string | Número de identificación fiscal | - |
| `phone` | string | Teléfono de la empresa | - |
| `address` | string | Dirección de la empresa | - |
| `city` | string | Ciudad | - |
| `state` | string | Estado/Provincia | - |
| `country` | string | País | - |
| `postal_code` | string | Código postal | - |
| `owner_phone` | string | Teléfono del dueño | - |
| `subscription_plan` | string | Plan de suscripción: basic, professional, enterprise | basic |

## Response

### Éxito (201 Created)

```json
{
  "tenant": {
    "id": 6,
    "name": "testcompany",
    "business_name": "Test Company LLC",
    "email": "contact@testcompany.com",
    "subscription_plan": "basic",
    "is_active": true
  },
  "domain": {
    "domain": "testcompany",
    "is_primary": true
  },
  "owner": {
    "id": 3,
    "email": "john@testcompany.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_tenant_owner": true
  },
  "message": "Tenant registered successfully! Please check your email to verify your account.",
  "next_steps": [
    "Verify your email address",
    "Login to your tenant admin panel",
    "Start creating loans and managing customers"
  ]
}
```

### Error de Validación (400 Bad Request)

```json
{
  "tenant_name": [
    "A tenant with this name already exists."
  ],
  "owner_email": [
    "A user with this email already exists."
  ]
}
```

### Error del Servidor (500 Internal Server Error)

```json
{
  "error": "Failed to create tenant: Internal server error"
}
```

## Ejemplos de Uso

### cURL

```bash
curl -X POST http://localhost:8000/api/tenants/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Test Company LLC",
    "tenant_name": "testcompany",
    "tax_id": "12-3456789",
    "email": "contact@testcompany.com",
    "phone": "+1234567890",
    "address": "123 Test Street",
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "postal_code": "10001",
    "subdomain": "testcompany",
    "owner_first_name": "John",
    "owner_last_name": "Doe",
    "owner_email": "john@testcompany.com",
    "owner_password": "SecurePass123!",
    "owner_phone": "+1234567890",
    "subscription_plan": "basic"
  }'
```

### JavaScript (Fetch API)

```javascript
const registerTenant = async () => {
  const response = await fetch('http://localhost:8000/api/tenants/register/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      business_name: 'ACME Corporation',
      tenant_name: 'acme-corp',
      email: 'contact@acme.com',
      subdomain: 'acme',
      owner_first_name: 'John',
      owner_last_name: 'Doe',
      owner_email: 'john@acme.com',
      owner_password: 'SecurePass123!',
      subscription_plan: 'basic',
    }),
  });

  const data = await response.json();

  if (response.ok) {
    console.log('Tenant registered:', data);
    // Redirect to login or verification page
  } else {
    console.error('Registration failed:', data);
  }
};
```

### Python (requests)

```python
import requests

url = 'http://localhost:8000/api/tenants/register/'
data = {
    'business_name': 'ACME Corporation',
    'tenant_name': 'acme-corp',
    'email': 'contact@acme.com',
    'subdomain': 'acme',
    'owner_first_name': 'John',
    'owner_last_name': 'Doe',
    'owner_email': 'john@acme.com',
    'owner_password': 'SecurePass123!',
    'subscription_plan': 'basic',
}

response = requests.post(url, json=data)

if response.status_code == 201:
    print('Tenant registered successfully!')
    print(response.json())
else:
    print('Registration failed:', response.json())
```

## Reglas de Validación

### tenant_name
- Solo minúsculas, números y guiones
- Debe ser único en el sistema
- Ejemplo válido: `acme-corp`, `company123`
- Ejemplo inválido: `ACME Corp`, `acme_corp`, `acme.corp`

### subdomain
- Solo minúsculas, números y guiones
- Debe ser único en el sistema
- No puede usar subdominios reservados: `www`, `admin`, `api`, `app`, `mail`, `ftp`, `localhost`, `public`
- Ejemplo válido: `acme`, `company-xyz`
- Ejemplo inválido: `ACME`, `admin`, `acme_corp`

### owner_email
- Debe ser un email válido
- Debe ser único en el sistema
- Se usará como username para login

### owner_password
- Mínimo 8 caracteres
- Se recomienda usar combinación de mayúsculas, minúsculas, números y símbolos

## Health Check

Para verificar que la API está funcionando:

```bash
curl http://localhost:8000/api/tenants/health/
```

Respuesta:
```json
{
  "status": "healthy",
  "service": "tenant-registration",
  "message": "Tenant registration API is operational",
  "endpoints": {
    "register": "/api/tenants/register/",
    "health": "/api/tenants/health/"
  }
}
```

## Flujo Post-Registro

1. **Tenant creado**: El tenant se crea con su propio esquema de base de datos
2. **Usuario Owner creado**: El usuario tiene:
   - `is_tenant_owner = True`
   - `role = admin`
   - `is_staff = True` (puede acceder al admin panel)
   - `tenant = [el tenant creado]`
3. **Login**: El usuario puede iniciar sesión usando su email y contraseña
4. **Acceso al Admin**: Puede acceder al admin panel en `http://[subdomain].localhost:8000/admin/`
5. **Gestión de usuarios**: El owner puede crear usuarios adicionales para su empresa

## Documentación API Completa

La documentación completa de la API está disponible en:
- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/

## Notas Importantes

- ⚠️ El endpoint es público (no requiere autenticación)
- ⚠️ El `schema_name` se genera automáticamente reemplazando guiones por guiones bajos en `tenant_name`
- ⚠️ Cada tenant tiene su propio esquema de base de datos aislado
- ⚠️ Los usuarios están vinculados a un tenant específico
- ⚠️ El usuario owner tiene privilegios completos sobre su tenant
