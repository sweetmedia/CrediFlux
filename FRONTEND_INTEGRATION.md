# Integración Frontend-Backend CrediFlux

Este documento describe la integración completa entre el frontend (Next.js + TypeScript) y el backend (Django REST Framework) de CrediFlux.

## Stack Tecnológico

### Frontend
- **Next.js 16** - Framework React con App Router
- **React 19** - Librería UI
- **TypeScript** - Tipado estático
- **TanStack Query** - Gestión de estado del servidor
- **Axios** - Cliente HTTP
- **React Hook Form + Zod** - Gestión de formularios y validación
- **Tailwind CSS** - Estilos
- **shadcn/ui** - Componentes UI

### Backend
- **Django 5.0.9** - Framework web
- **Django REST Framework** - API REST
- **SimpleJWT** - Autenticación JWT
- **django-tenants** - Multi-tenancy
- **PostgreSQL** - Base de datos

## Arquitectura de la Integración

```
Frontend (Next.js)
├── API Client (Axios)
│   ├── Interceptores de request (agregar token)
│   └── Interceptores de response (refresh token)
├── Services (lib/api/)
│   ├── auth.ts - Servicios de autenticación
│   ├── customers.ts - Servicios de clientes
│   └── loans.ts - Servicios de préstamos
├── Context (lib/contexts/)
│   └── AuthContext.tsx - Estado global de autenticación
├── Hooks personalizados (hooks/)
│   ├── useProfile.ts
│   ├── useTeam.ts
│   ├── useEmailVerification.ts
│   └── usePasswordReset.ts
└── Páginas (app/)
    ├── login/
    ├── register/
    └── dashboard/
```

## Archivos Creados/Modificados

### 1. Tipos TypeScript (`types/index.ts`)

Interfaces completas para:
- `Tenant` - Información del tenant
- `TenantLoginResponse` - Respuesta del login
- `TenantRegistrationData` - Datos de registro
- `EmailVerificationRequest/Confirm` - Verificación de email
- `PasswordResetRequest/Confirm` - Reseteo de contraseña
- `ProfileUpdateData` - Actualización de perfil
- `PasswordChangeData` - Cambio de contraseña
- `TeamMember/Create/Update` - Gestión de equipo

### 2. Cliente API (`lib/api/client.ts`)

**Existente - Sin cambios necesarios**

- Interceptor de request: agrega token JWT automáticamente
- Interceptor de response: maneja refresh token en 401
- Métodos: get, post, put, patch, delete

### 3. Servicio de Autenticación (`lib/api/auth.ts`)

**Completamente reescrito** con todos los endpoints:

#### Tenant Registration & Login
- `registerTenant(data)` - Registrar nuevo tenant
- `login(credentials)` - Login de usuarios
- `logout()` - Logout con blacklist

#### Email Verification
- `sendEmailVerification(data)` - Enviar email de verificación
- `confirmEmailVerification(data)` - Confirmar verificación

#### Password Reset
- `requestPasswordReset(data)` - Solicitar reset
- `confirmPasswordReset(data)` - Confirmar reset

#### Profile Management
- `getProfile()` - Obtener perfil
- `updateProfile(data)` - Actualizar perfil
- `changePassword(data)` - Cambiar contraseña

#### Team Management
- `getTeamMembers()` - Listar equipo
- `getTeamMember(id)` - Obtener miembro
- `createTeamMember(data)` - Crear miembro
- `updateTeamMember(id, data)` - Actualizar miembro
- `deleteTeamMember(id)` - Desactivar miembro

#### Utilidades
- `getStoredUser()` - Usuario del localStorage
- `getStoredTenant()` - Tenant del localStorage
- `isAuthenticated()` - Verificar autenticación

### 4. Contexto de Autenticación (`lib/contexts/AuthContext.tsx`)

**Nuevo archivo** - Context global de autenticación:

```typescript
interface AuthContextType {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials) => Promise<TenantLoginResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}
```

**Características:**
- Carga inicial desde localStorage (UI instantáneo)
- Fetch de datos frescos del API
- Sincronización automática
- Manejo de logout

### 5. Hooks Personalizados

#### `useAuth()` (desde AuthContext)
```typescript
const { user, tenant, isAuthenticated, isLoading, login, logout, refreshUser } = useAuth();
```

#### `useProfile()` (hooks/useProfile.ts)
```typescript
const {
  profile,
  isLoading,
  error,
  updateProfile,
  isUpdatingProfile,
  updateProfileError,
  changePassword,
  isChangingPassword,
  changePasswordError,
} = useProfile();
```

#### `useTeam()` (hooks/useTeam.ts)
```typescript
const {
  teamMembers,
  isLoading,
  error,
  getTeamMember,
  createTeamMember,
  isCreating,
  createError,
  updateTeamMember,
  isUpdating,
  updateError,
  deleteTeamMember,
  isDeleting,
  deleteError,
} = useTeam();
```

#### `useEmailVerification()` (hooks/useEmailVerification.ts)
```typescript
const {
  sendVerification,
  isSending,
  sendError,
  sendSuccess,
  confirmVerification,
  isConfirming,
  confirmError,
  confirmSuccess,
} = useEmailVerification();
```

#### `usePasswordReset()` (hooks/usePasswordReset.ts)
```typescript
const {
  requestReset,
  isRequesting,
  requestError,
  requestSuccess,
  confirmReset,
  isConfirming,
  confirmError,
  confirmSuccess,
} = usePasswordReset();
```

### 6. Providers (`app/providers.tsx`)

**Nuevo archivo** - Wraps toda la aplicación:

```typescript
<QueryClientProvider>
  <AuthProvider>
    {children}
  </AuthProvider>
</QueryClientProvider>
```

### 7. Layout Principal (`app/layout.tsx`)

**Actualizado** para incluir Providers:

```typescript
<html lang="en">
  <body>
    <Providers>{children}</Providers>
  </body>
</html>
```

### 8. Página de Login (`app/login/page.tsx`)

**Nueva página** con:
- Formulario con React Hook Form + Zod
- Validación en tiempo real
- Manejo de errores del API
- Redirección automática a dashboard
- Links a registro y recuperación de contraseña

### 9. Componentes UI (`components/ui/alert.tsx`)

**Nuevo componente** - Alert con variantes para mostrar errores/éxitos

## Flujo de Autenticación Completo

### 1. Login

```typescript
// En el componente
const { login } = useAuth();

const onSubmit = async (data) => {
  await login(data); // Guarda tokens y usuario en context
  router.push('/dashboard');
};
```

**Backend:** `POST /api/tenants/login/`
**Response:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": { ... },
  "tenant": { ... },
  "message": "Login successful"
}
```

### 2. Requests Autenticados

Todos los requests automáticamente incluyen el token:

```typescript
// El interceptor agrega automáticamente:
// Authorization: Bearer <access_token>

const profile = await authAPI.getProfile();
```

### 3. Refresh Token Automático

Cuando un request retorna 401:
1. Interceptor captura el error
2. Intenta refresh con refresh_token
3. Si tiene éxito, reintenta el request original
4. Si falla, hace logout automático

### 4. Logout

```typescript
const { logout } = useAuth();

await logout(); // Blacklist token + limpia localStorage + redirect
```

**Backend:** `POST /api/users/auth/logout/`

### 5. Gestión de Perfil

```typescript
const { profile, updateProfile } = useProfile();

// Actualizar perfil
updateProfile({
  first_name: 'Juan',
  job_title: 'Loan Officer',
});
```

**Backend:** `PATCH /api/users/profile/update/`

### 6. Gestión de Equipo

```typescript
const { teamMembers, createTeamMember } = useTeam();

// Crear nuevo miembro
createTeamMember({
  email: 'staff@company.com',
  username: 'staff',
  first_name: 'Staff',
  last_name: 'Member',
  password: 'SecurePass123!',
  role: 'loan_officer',
});
```

**Backend:** `POST /api/users/team/create/`

## Configuración de Entorno

### Frontend (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=CrediFlux
```

### Backend (`.env`)

```bash
# API Configuration
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=crediflux_db
DB_USER=crediflux_user
DB_PASSWORD=crediflux_pass
DB_HOST=db
DB_PORT=5432

# JWT Configuration
JWT_ACCESS_TOKEN_LIFETIME=60  # minutes
JWT_REFRESH_TOKEN_LIFETIME=1440  # 24 hours

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000

# Tenant
TENANT_BASE_DOMAIN=localhost
```

## Iniciar Aplicación

### Backend

```bash
cd backend
python manage.py runserver
```

Servidor en: http://localhost:8000
API Docs: http://localhost:8000/swagger/

### Frontend

```bash
cd frontend
npm run dev
```

Aplicación en: http://localhost:3000

## Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| **Autenticación** |
| POST | `/api/tenants/register/` | Registrar tenant |
| POST | `/api/tenants/login/` | Login |
| POST | `/api/users/auth/logout/` | Logout |
| **Email Verification** |
| POST | `/api/users/auth/verify-email/send/` | Enviar verificación |
| POST | `/api/users/auth/verify-email/confirm/` | Confirmar verificación |
| **Password Reset** |
| POST | `/api/users/auth/password-reset/request/` | Solicitar reset |
| POST | `/api/users/auth/password-reset/confirm/` | Confirmar reset |
| **Profile** |
| GET | `/api/users/profile/` | Ver perfil |
| PUT/PATCH | `/api/users/profile/update/` | Actualizar perfil |
| POST | `/api/users/profile/change-password/` | Cambiar contraseña |
| **Team** |
| GET | `/api/users/team/` | Listar equipo |
| POST | `/api/users/team/create/` | Crear miembro |
| GET | `/api/users/team/{id}/` | Ver miembro |
| PUT/PATCH | `/api/users/team/{id}/` | Actualizar miembro |
| DELETE | `/api/users/team/{id}/` | Desactivar miembro |

## Ejemplo de Uso Completo

### Componente con Autenticación

```typescript
'use client';

import { useAuth } from '@/lib/contexts/AuthContext';
import { useProfile } from '@/hooks/useProfile';
import { useTeam } from '@/hooks/useTeam';

export default function DashboardPage() {
  const { user, tenant, logout } = useAuth();
  const { profile } = useProfile();
  const { teamMembers } = useTeam();

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1>Welcome, {user.first_name}!</h1>
      <p>Tenant: {tenant?.business_name}</p>
      <p>Role: {user.role}</p>

      <h2>Team Members</h2>
      <ul>
        {teamMembers?.map(member => (
          <li key={member.id}>
            {member.full_name} - {member.role}
          </li>
        ))}
      </ul>

      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

### Protected Route (Middleware)

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value;

  if (!token && !request.nextUrl.pathname.startsWith('/login')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/profile/:path*', '/team/:path*'],
};
```

## Manejo de Errores

### Errores del API

```typescript
try {
  await login(credentials);
} catch (err: any) {
  if (err.response?.data) {
    // Errores de validación del backend
    const errorData = err.response.data;
    if (errorData.non_field_errors) {
      setError(errorData.non_field_errors[0]);
    } else if (errorData.email) {
      setError(errorData.email[0]);
    }
  } else {
    // Error de red
    setError('Error al conectar con el servidor');
  }
}
```

### Estados de Carga

```typescript
const { isLoading, error } = useProfile();

if (isLoading) {
  return <LoadingSpinner />;
}

if (error) {
  return <ErrorMessage error={error} />;
}
```

## Testing

### Login Test

```bash
curl -X POST http://localhost:8000/api/tenants/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@democompany.com",
    "password": "DemoPass123!"
  }'
```

### Profile Test (con token)

```bash
TOKEN="your_access_token_here"

curl -X GET http://localhost:8000/api/users/profile/ \
  -H "Authorization: Bearer $TOKEN"
```

## Seguridad

### Almacenamiento de Tokens

Actualmente los tokens se guardan en `localStorage`:
- ✅ Fácil de implementar
- ⚠️ Vulnerable a XSS

**Recomendación para producción:**
- Usar `httpOnly` cookies
- Implementar CSRF protection

### HTTPS en Producción

- Todos los requests deben ir por HTTPS
- Configurar CORS correctamente
- Usar variables de entorno para URLs

## Próximos Pasos

1. **Páginas adicionales:**
   - Registro de tenant
   - Recuperación de contraseña
   - Verificación de email
   - Gestión de equipo (CRUD completo)
   - Dashboard con estadísticas

2. **Middleware de protección:**
   - Protected routes
   - Role-based access control

3. **Mejoras de UX:**
   - Loading states mejorados
   - Toast notifications
   - Validaciones en tiempo real

4. **Testing:**
   - Unit tests
   - Integration tests
   - E2E tests

## Documentación Adicional

- **Backend API:** Ver `backend/API_AUTHENTICATION.md`
- **API Swagger:** http://localhost:8000/swagger/
- **API ReDoc:** http://localhost:8000/redoc/

---

**Integración completada:** 2025-10-28
**Stack:** Next.js 16 + Django 5.0.9 + JWT
**Estado:** Listo para desarrollo adicional
