# API Reference - CrediFlux

## Información General

**Base URL**: `http://localhost:8000/api` (desarrollo)
**Base URL**: `https://api.crediflux.com` (producción)

**Versión**: v1
**Formato**: JSON
**Autenticación**: JWT (JSON Web Tokens)

---

## Índice

- [Autenticación](#autenticación)
- [Errores](#errores)
- [Paginación](#paginación)
- [Filtros y Ordenamiento](#filtros-y-ordenamiento)
- [Endpoints](#endpoints)
  - [Auth](#auth)
  - [Customers](#customers)
  - [Loans](#loans)
  - [Payments](#payments)
  - [Schedules](#schedules)
  - [Collections](#collections)

---

## Autenticación

CrediFlux usa **JWT (JSON Web Tokens)** para autenticación.

### Obtener Token

**Endpoint**: `POST /api/auth/login/`

**Request**:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "loan_officer",
    "tenant": {
      "id": "tenant-uuid",
      "name": "Caproinsa SRL",
      "schema_name": "caproinsa"
    }
  }
}
```

### Usar Token

Incluir el token en el header `Authorization`:

```bash
curl -X GET http://localhost:8000/api/loans/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Refrescar Token

**Endpoint**: `POST /api/auth/token/refresh/`

**Request**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc... (nuevo token)"
}
```

### Expiración

- **Access Token**: 60 minutos
- **Refresh Token**: 7 días

---

## Errores

### Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 201 | Created - Recurso creado |
| 204 | No Content - Eliminación exitosa |
| 400 | Bad Request - Error de validación |
| 401 | Unauthorized - No autenticado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 409 | Conflict - Conflicto de estado |
| 500 | Internal Server Error |

### Formato de Errores

**Ejemplo - Error de Validación** (400):
```json
{
  "principal_amount": [
    "Este campo es requerido."
  ],
  "interest_rate": [
    "Asegúrese de que este valor sea menor o igual a 100."
  ]
}
```

**Ejemplo - Error de Autenticación** (401):
```json
{
  "detail": "Las credenciales de autenticación no se proveyeron."
}
```

**Ejemplo - Error de Permisos** (403):
```json
{
  "detail": "No tiene permiso para realizar esta acción."
}
```

**Ejemplo - No Encontrado** (404):
```json
{
  "detail": "No encontrado."
}
```

---

## Paginación

Todas las listas usan paginación por defecto.

**Tamaño de página por defecto**: 50 items

**Query Parameters**:
- `page`: Número de página (default: 1)
- `page_size`: Tamaño de página (max: 100)

**Ejemplo**:
```bash
GET /api/loans/?page=2&page_size=20
```

**Response**:
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/loans/?page=3&page_size=20",
  "previous": "http://localhost:8000/api/loans/?page=1&page_size=20",
  "results": [
    { ... },
    { ... }
  ]
}
```

---

## Filtros y Ordenamiento

### Filtrado

Usar query parameters para filtrar:

```bash
# Filtrar por status
GET /api/loans/?status=active

# Múltiples valores (OR)
GET /api/loans/?status=active&status=defaulted

# Filtrar por rango de fechas
GET /api/loans/?disbursement_date_after=2025-01-01&disbursement_date_before=2025-12-31

# Búsqueda por texto
GET /api/loans/?search=juan
```

### Ordenamiento

Usar el parámetro `ordering`:

```bash
# Ordenar ascendente
GET /api/loans/?ordering=disbursement_date

# Ordenar descendente (prefijo -)
GET /api/loans/?ordering=-disbursement_date

# Múltiples campos
GET /api/loans/?ordering=-status,disbursement_date
```

---

## Endpoints

## Auth

### Login

```
POST /api/auth/login/
```

**Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### Refresh Token

```
POST /api/auth/token/refresh/
```

**Body**:
```json
{
  "refresh": "refresh-token-here"
}
```

### Logout

```
POST /api/auth/logout/
```

**Headers**: `Authorization: Bearer {access-token}`

---

## Customers

### Listar Clientes

```
GET /api/loans/customers/
```

**Query Parameters**:
- `search`: Buscar por nombre, email, ID
- `employment_status`: Filtrar por empleo
- `ordering`: Ordenar (-created_at, first_name)

**Response**:
```json
{
  "count": 100,
  "results": [
    {
      "id": "uuid",
      "first_name": "Juan",
      "last_name": "Pérez",
      "email": "juan@example.com",
      "phone": "809-555-1234",
      "id_type": "cedula",
      "id_number": "001-1234567-8",
      "date_of_birth": "1985-05-15",
      "monthly_income": "50000.00",
      "employment_status": "employed",
      "employer_name": "ABC Company",
      "credit_score": 720,
      "total_loans": 2,
      "active_loans": 1,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Crear Cliente

```
POST /api/loans/customers/
```

**Body**:
```json
{
  "first_name": "María",
  "last_name": "González",
  "email": "maria@example.com",
  "phone": "809-555-5678",
  "id_type": "cedula",
  "id_number": "001-9876543-2",
  "date_of_birth": "1990-03-20",
  "address": "Calle Principal #123, Santo Domingo",
  "monthly_income": "75000.00",
  "employment_status": "employed",
  "employer_name": "XYZ Corp",
  "employer_phone": "809-555-9999"
}
```

**Response** (201 Created):
```json
{
  "id": "new-customer-uuid",
  "first_name": "María",
  ...
}
```

### Detalle de Cliente

```
GET /api/loans/customers/{id}/
```

**Response**:
```json
{
  "id": "uuid",
  "first_name": "Juan",
  "last_name": "Pérez",
  "email": "juan@example.com",
  ...
  "loans": [
    {
      "id": "loan-uuid",
      "loan_number": "LN-2025-ABC123",
      "status": "active",
      "principal_amount": "200000.00",
      "outstanding_balance": "150000.00"
    }
  ]
}
```

### Actualizar Cliente

```
PUT /api/loans/customers/{id}/
PATCH /api/loans/customers/{id}/  (actualización parcial)
```

**Body** (PATCH):
```json
{
  "phone": "809-555-NEW",
  "monthly_income": "80000.00"
}
```

### Eliminar Cliente

```
DELETE /api/loans/customers/{id}/
```

**Response**: 204 No Content

**Nota**: Solo si no tiene préstamos activos.

### Préstamos del Cliente

```
GET /api/loans/customers/{id}/loans/
```

---

## Loans

### Listar Préstamos

```
GET /api/loans/
```

**Query Parameters**:
- `status`: active, pending, paid, defaulted, etc.
- `loan_type`: personal, auto, business, etc.
- `customer`: customer-uuid
- `search`: Buscar por loan_number o customer name
- `disbursement_date_after`: YYYY-MM-DD
- `disbursement_date_before`: YYYY-MM-DD
- `ordering`: -disbursement_date, outstanding_balance

**Response**:
```json
{
  "count": 500,
  "results": [
    {
      "id": "uuid",
      "loan_number": "LN-2025-ABC123",
      "customer": {
        "id": "customer-uuid",
        "name": "Juan Pérez",
        "email": "juan@example.com"
      },
      "loan_type": "personal",
      "loan_type_display": "Personal",
      "status": "active",
      "status_display": "Activo",
      "principal_amount": "200000.00",
      "outstanding_balance": "150000.00",
      "interest_rate": "18.00",
      "term_months": 24,
      "payment_frequency": "monthly",
      "disbursement_date": "2025-01-15",
      "maturity_date": "2027-01-15",
      "next_payment_date": "2025-11-15",
      "next_payment_amount": "9168.46",
      "days_overdue": 5,
      "is_overdue": true,
      "created_at": "2025-01-10T09:00:00Z"
    }
  ]
}
```

### Crear Préstamo

```
POST /api/loans/
```

**Body**:
```json
{
  "customer": "customer-uuid",
  "loan_type": "personal",
  "principal_amount": "200000.00",
  "interest_rate": "18.00",
  "term_months": 24,
  "payment_frequency": "monthly",
  "purpose": "Consolidación de deudas",
  "requested_amount": "200000.00"
}
```

**Response** (201 Created):
```json
{
  "id": "new-loan-uuid",
  "loan_number": "LN-2025-XYZ789",
  "status": "pending",
  ...
}
```

### Detalle de Préstamo

```
GET /api/loans/{id}/
```

**Response**:
```json
{
  "id": "uuid",
  "loan_number": "LN-2025-ABC123",
  "customer": {
    "id": "uuid",
    "first_name": "Juan",
    "last_name": "Pérez",
    "email": "juan@example.com",
    "phone": "809-555-1234"
  },
  "loan_type": "personal",
  "status": "active",
  "principal_amount": "200000.00",
  "outstanding_balance": "150000.00",
  "interest_rate": "18.00",
  "term_months": 24,
  "payment_frequency": "monthly",
  "monthly_payment": "9168.46",
  "disbursement_date": "2025-01-15",
  "first_payment_date": "2025-02-15",
  "maturity_date": "2027-01-15",
  "payment_schedules": [
    {
      "id": "schedule-uuid",
      "installment_number": 1,
      "due_date": "2025-02-15",
      "total_amount": "9168.46",
      "principal_amount": "7668.46",
      "interest_amount": "1500.00",
      "paid_amount": "9168.46",
      "status": "paid",
      "paid_date": "2025-02-15"
    },
    {
      "installment_number": 2,
      "due_date": "2025-03-15",
      "total_amount": "9168.46",
      "paid_amount": "0.00",
      "balance": "9168.46",
      "status": "pending",
      "days_overdue": 0
    }
  ],
  "recent_payments": [
    {
      "id": "payment-uuid",
      "payment_number": "PAY-2025-ABC",
      "payment_date": "2025-02-15",
      "amount": "9168.46",
      "payment_method": "cash",
      "status": "completed"
    }
  ],
  "collaterals": [],
  "approved_by": null,
  "approved_at": null,
  "created_at": "2025-01-10T09:00:00Z"
}
```

### Aprobar Préstamo

```
POST /api/loans/{id}/approve/
```

**Body**:
```json
{
  "notes": "Cliente cumple con todos los requisitos. DTI: 32%"
}
```

**Response** (200 OK):
```json
{
  "message": "Préstamo aprobado exitosamente",
  "loan": {
    "id": "uuid",
    "status": "approved",
    "approved_by": "approver-user-uuid",
    "approved_at": "2025-10-30T14:30:00Z"
  }
}
```

### Desembolsar Préstamo

```
POST /api/loans/{id}/disburse/
```

**Response** (200 OK):
```json
{
  "message": "Préstamo desembolsado exitosamente",
  "loan": {
    "id": "uuid",
    "status": "active",
    "disbursement_date": "2025-10-30",
    "first_payment_date": "2025-11-30",
    "maturity_date": "2027-10-30"
  },
  "schedules_created": 24
}
```

### Rechazar Préstamo

```
POST /api/loans/{id}/reject/
```

**Body**:
```json
{
  "reason": "DTI superior al 40%"
}
```

### Estadísticas de Préstamos

```
GET /api/loans/statistics/
```

**Response**:
```json
{
  "total_loans": 500,
  "active_loans": 320,
  "pending_approval": 45,
  "total_disbursed": "50000000.00",
  "total_outstanding": "35000000.00",
  "total_collected": "15000000.00",
  "default_rate": "5.2",
  "average_loan_size": "156250.00",
  "by_status": {
    "active": 320,
    "pending": 45,
    "paid": 120,
    "defaulted": 15
  },
  "by_type": {
    "personal": 250,
    "auto": 100,
    "business": 80,
    "mortgage": 50,
    "student": 20
  }
}
```

---

## Payments

### Listar Pagos

```
GET /api/loans/payments/
```

**Query Parameters**:
- `loan`: loan-uuid
- `customer`: customer-uuid
- `payment_method`: cash, check, bank_transfer, etc.
- `status`: completed, pending, failed, reversed
- `date_from`: YYYY-MM-DD
- `date_to`: YYYY-MM-DD
- `ordering`: -payment_date, amount

**Response**:
```json
{
  "count": 1000,
  "results": [
    {
      "id": "uuid",
      "payment_number": "PAY-2025-ABC123",
      "loan": "loan-uuid",
      "loan_number": "LN-2025-XYZ",
      "customer_name": "Juan Pérez",
      "schedule": "schedule-uuid",
      "payment_date": "2025-10-30",
      "amount": "10000.00",
      "principal_paid": "8000.00",
      "interest_paid": "1500.00",
      "late_fee_paid": "500.00",
      "payment_method": "cash",
      "payment_method_display": "Efectivo",
      "reference_number": "",
      "status": "completed",
      "notes": "",
      "created_at": "2025-10-30T10:15:00Z"
    }
  ]
}
```

### Registrar Pago

```
POST /api/loans/payments/
```

**Body** (Básico):
```json
{
  "loan": "loan-uuid",
  "amount": "10000.00",
  "payment_method": "cash",
  "payment_date": "2025-10-30",
  "notes": "Pago de cuota #5"
}
```

**Body** (Con Schedule Específico):
```json
{
  "loan": "loan-uuid",
  "schedule": "schedule-uuid",
  "amount": "9168.46",
  "payment_method": "bank_transfer",
  "reference_number": "TXN-20251030-12345",
  "payment_date": "2025-10-30"
}
```

**Response** (201 Created):
```json
{
  "id": "payment-uuid",
  "payment_number": "PAY-2025-ABC123",
  "loan": "loan-uuid",
  "schedule": "schedule-uuid",
  "amount": "10000.00",
  "principal_paid": "8000.00",
  "interest_paid": "1500.00",
  "late_fee_paid": "500.00",
  "payment_method": "cash",
  "status": "completed",
  "message": "Pago aplicado exitosamente a cuota #5"
}
```

### Detalle de Pago

```
GET /api/loans/payments/{id}/
```

### Reversar Pago

```
POST /api/loans/payments/{id}/reverse/
```

**Body**:
```json
{
  "reason": "Cheque devuelto por falta de fondos"
}
```

**Response** (200 OK):
```json
{
  "message": "Pago revertido exitosamente",
  "payment": {
    "id": "uuid",
    "status": "reversed",
    "reversed_at": "2025-10-30T16:00:00Z",
    "reversed_by": "user-uuid",
    "reversal_reason": "Cheque devuelto por falta de fondos"
  }
}
```

---

## Schedules

### Listar Cronogramas

```
GET /api/loans/schedules/
```

**Query Parameters**:
- `loan`: loan-uuid
- `status`: pending, paid, partial, overdue
- `due_date_before`: YYYY-MM-DD
- `due_date_after`: YYYY-MM-DD

### Cronogramas Vencidos

```
GET /api/loans/schedules/overdue/
```

**Response**:
```json
{
  "count": 45,
  "total_overdue": "450000.00",
  "total_late_fees": "22500.00",
  "results": [
    {
      "id": "uuid",
      "loan": "loan-uuid",
      "loan_number": "LN-2025-ABC",
      "customer_name": "Juan Pérez",
      "installment_number": 5,
      "due_date": "2025-09-15",
      "total_amount": "9168.46",
      "balance": "9168.46",
      "late_fee_amount": "500.00",
      "late_fee_paid": "0.00",
      "days_overdue": 45,
      "status": "overdue"
    }
  ]
}
```

---

## Collections

### Dashboard Stats

```
GET /api/loans/collections/dashboard_stats/
```

**Response**:
```json
{
  "overdueSchedules": 45,
  "totalOverdue": "450000.00",
  "totalLateFees": "22500.00",
  "pendingReminders": 120,
  "promisesToday": 8,
  "brokenPromises": 15,
  "escalationRequired": 3
}
```

### Recordatorios Pendientes

```
GET /api/loans/collections/pending_reminders/
```

### Promesas de Pago para Hoy

```
GET /api/loans/collections/promises_due_today/
```

### Promesas Incumplidas

```
GET /api/loans/collections/broken_promises/
```

### Casos Requiriendo Escalamiento

```
GET /api/loans/collections/requiring_escalation/
```

**Response**:
```json
{
  "count": 3,
  "results": [
    {
      "id": "loan-uuid",
      "loan_number": "LN-2025-XYZ",
      "customer": {
        "id": "uuid",
        "name": "Cliente Problema",
        "phone": "809-555-XXXX"
      },
      "days_overdue": 95,
      "total_overdue": "50000.00",
      "late_fees": "7500.00",
      "last_contact": "2025-09-15",
      "last_payment": "2025-07-01"
    }
  ]
}
```

### Registrar Contacto de Cobranza

```
POST /api/loans/collection-contacts/
```

**Body**:
```json
{
  "loan": "loan-uuid",
  "contact_type": "phone_call",
  "outcome": "promise_to_pay",
  "promise_date": "2025-11-05",
  "promise_amount": "10000.00",
  "notes": "Cliente promete pagar cuota completa el viernes. Tiene dificultades temporales pero compromiso firme."
}
```

### Historial de Contactos

```
GET /api/loans/collection-contacts/?loan={loan-uuid}
```

---

## Webhooks (Futuro)

### Configurar Webhook

```
POST /api/webhooks/
```

**Body**:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["payment.completed", "loan.approved", "payment.overdue"],
  "secret": "your-webhook-secret"
}
```

### Eventos Disponibles

- `loan.created`
- `loan.approved`
- `loan.disbursed`
- `loan.rejected`
- `payment.completed`
- `payment.reversed`
- `payment.overdue`
- `schedule.overdue`

---

## Rate Limiting

- **Límite por defecto**: 100 requests/minuto por usuario
- **Límite para login**: 5 intentos/minuto por IP

**Header de respuesta**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1635789600
```

---

## Ambientes

### Desarrollo
- **URL**: http://localhost:8000
- **Docs**: http://localhost:8000/swagger/

### Staging
- **URL**: https://staging-api.crediflux.com
- **Docs**: https://staging-api.crediflux.com/swagger/

### Producción
- **URL**: https://api.crediflux.com
- **Docs**: https://api.crediflux.com/swagger/

---

**Última actualización**: 2025-10-30
