# API de Login para Tenants - CrediFlux

## Descripción

Este endpoint permite a los usuarios de tenants autenticarse en la plataforma CrediFlux y obtener tokens JWT para acceder a recursos protegidos.

El sistema valida:
- Credenciales del usuario (email y contraseña)
- Estado activo del usuario
- Estado activo del tenant
- Pertenencia del usuario a un tenant

## Endpoint

### POST `/api/tenants/login/`

**Autenticación**: No requerida (endpoint público)

**Content-Type**: `application/json`

## Request Body

```json
{
  "email": "jane@democompany.com",
  "password": "DemoPass123!"
}
```

### Campos Requeridos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `email` | email | Email del usuario (username para login) |
| `password` | string | Contraseña del usuario |

## Response

### Éxito (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 4,
    "email": "jane@democompany.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "full_name": "Jane Smith",
    "role": "admin",
    "is_tenant_owner": true,
    "is_staff": true,
    "is_superuser": false
  },
  "tenant": {
    "id": 7,
    "name": "democompany",
    "business_name": "Demo Company Inc",
    "subscription_plan": "basic",
    "is_active": true,
    "domain": "democompany"
  },
  "message": "Login successful"
}
```

### Campos de Respuesta

#### Tokens
| Campo | Descripción |
|-------|-------------|
| `access_token` | Token JWT de acceso (válido por 60 minutos por defecto) |
| `refresh_token` | Token JWT de refresco (válido por 24 horas por defecto) |

#### User
| Campo | Descripción |
|-------|-------------|
| `id` | ID del usuario |
| `email` | Email del usuario |
| `first_name` | Nombre del usuario |
| `last_name` | Apellido del usuario |
| `full_name` | Nombre completo |
| `role` | Rol del usuario (admin, manager, loan_officer, accountant, cashier, viewer) |
| `is_tenant_owner` | Indica si es el dueño del tenant |
| `is_staff` | Indica si puede acceder al admin panel |
| `is_superuser` | Indica si es superusuario del sistema |

#### Tenant
| Campo | Descripción |
|-------|-------------|
| `id` | ID del tenant |
| `name` | Nombre único del tenant |
| `business_name` | Nombre comercial de la empresa |
| `subscription_plan` | Plan de suscripción (basic, professional, enterprise) |
| `is_active` | Indica si el tenant está activo |
| `domain` | Subdominio del tenant |

### Errores

#### 400 Bad Request - Credenciales Inválidas

```json
{
  "non_field_errors": [
    "Invalid email or password."
  ]
}
```

#### 400 Bad Request - Campos Faltantes

```json
{
  "email": [
    "This field is required."
  ],
  "password": [
    "This field is required."
  ]
}
```

#### 400 Bad Request - Usuario Inactivo

```json
{
  "non_field_errors": [
    "This account has been deactivated. Please contact support."
  ]
}
```

#### 400 Bad Request - Tenant Inactivo

```json
{
  "non_field_errors": [
    "Your tenant account has been deactivated. Please contact support."
  ]
}
```

#### 400 Bad Request - Usuario sin Tenant

```json
{
  "non_field_errors": [
    "Your account is not associated with any tenant. Please contact support."
  ]
}
```

## Ejemplos de Uso

### cURL

```bash
curl -X POST http://localhost:8000/api/tenants/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@democompany.com",
    "password": "DemoPass123!"
  }'
```

### JavaScript (Fetch API)

```javascript
const login = async (email, password) => {
  try {
    const response = await fetch('http://localhost:8000/api/tenants/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      // Store tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      // Store user and tenant info
      localStorage.setItem('user', JSON.stringify(data.user));
      localStorage.setItem('tenant', JSON.stringify(data.tenant));

      console.log('Login successful:', data);
      return data;
    } else {
      console.error('Login failed:', data);
      throw new Error(data.non_field_errors || 'Login failed');
    }
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
};

// Usage
login('jane@democompany.com', 'DemoPass123!')
  .then(data => {
    console.log('Logged in as:', data.user.full_name);
    console.log('Tenant:', data.tenant.business_name);
  })
  .catch(error => {
    console.error('Login error:', error.message);
  });
```

### Python (requests)

```python
import requests

def login(email, password):
    url = 'http://localhost:8000/api/tenants/login/'
    data = {
        'email': email,
        'password': password,
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        print(f"Login successful! Welcome {result['user']['full_name']}")

        # Store tokens
        access_token = result['access_token']
        refresh_token = result['refresh_token']

        return result
    else:
        print('Login failed:', response.json())
        return None

# Usage
result = login('jane@democompany.com', 'DemoPass123!')
if result:
    print(f"Tenant: {result['tenant']['business_name']}")
    print(f"Role: {result['user']['role']}")
```

### React Hook

```javascript
import { useState } from 'react';

export const useLogin = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/tenants/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.non_field_errors?.[0] || 'Login failed');
      }

      // Store tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      localStorage.setItem('tenant', JSON.stringify(data.tenant));

      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { login, loading, error };
};

// Usage in component
function LoginForm() {
  const { login, loading, error } = useLogin();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const email = e.target.email.value;
    const password = e.target.password.value;

    try {
      const data = await login(email, password);
      console.log('Logged in:', data.user.full_name);
      // Redirect to dashboard
    } catch (err) {
      console.error('Login error:', err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" type="email" required />
      <input name="password" type="password" required />
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

## Uso de Tokens JWT

### Hacer Requests Autenticados

Una vez que obtienes el `access_token`, debes incluirlo en el header `Authorization` de todas las requests a endpoints protegidos:

```bash
curl -X GET http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

```javascript
// JavaScript
fetch('http://localhost:8000/api/loans/', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json',
  },
});
```

### Refresh Token

Cuando el `access_token` expire (por defecto en 60 minutos), puedes usar el `refresh_token` para obtener un nuevo par de tokens:

```bash
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

Respuesta:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Flujo de Autenticación Completo

```
1. Usuario envía credenciales → POST /api/tenants/login/

2. Backend valida:
   ✓ Email y contraseña correctos
   ✓ Usuario está activo
   ✓ Tenant está activo

3. Backend genera:
   - access_token (60 min)
   - refresh_token (24 hrs)

4. Cliente guarda tokens en localStorage/sessionStorage

5. Cliente hace requests con access_token
   - Header: Authorization: Bearer <access_token>

6. Cuando access_token expira:
   - Cliente usa refresh_token para obtener nuevo access_token
   - POST /api/auth/token/refresh/

7. Cuando refresh_token expira:
   - Cliente debe hacer login nuevamente
```

## Seguridad

### Mejores Prácticas

1. **Almacenamiento de Tokens**
   - Usa `httpOnly` cookies en producción (más seguro que localStorage)
   - O usa `sessionStorage` si no necesitas persistencia entre sesiones

2. **HTTPS**
   - Siempre usa HTTPS en producción
   - Los tokens nunca deben enviarse por HTTP

3. **Expiración**
   - access_token: corto (60 min)
   - refresh_token: medio (24 hrs)
   - Implementa logout para invalidar tokens

4. **Validación**
   - El backend valida cada request con el token
   - Los tokens no pueden ser modificados (firma JWT)

## Configuración

Los tiempos de expiración de tokens se configuran en `config/settings/base.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=24),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## Documentación API Completa

La documentación completa de la API está disponible en:
- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/

## Notas Importantes

- ⚠️ El endpoint es público (no requiere autenticación)
- ⚠️ Los tokens JWT son stateless y no se pueden invalidar hasta que expiren
- ⚠️ El backend actualiza automáticamente el campo `last_login_at` del usuario
- ⚠️ Las contraseñas nunca se retornan en ninguna respuesta
- ⚠️ Solo usuarios activos con tenants activos pueden hacer login
- ⚠️ Los superusers del sistema (sin tenant) también pueden usar este endpoint
