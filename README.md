# CrediFlux - Multi-Module SaaS Platform

CrediFlux es una plataforma SaaS multi-tenant diseñada para instituciones financieras. El sistema incluye módulos para:

- Gestión de Préstamos
- Facturación
- Cuentas por Cobrar
- Inventario
- Contabilidad
- Nómina
- Cuentas por Pagar

## Tech Stack

### Backend
- **Django 5.0.9** - Framework web
- **Django REST Framework** - API REST
- **PostgreSQL** - Base de datos
- **Redis** - Cache y message broker
- **Celery** - Tareas asíncronas
- **django-tenants** - Multi-tenancy
- **Django Unfold** - Admin interface moderna
- **JWT** - Autenticación

### Frontend
- **Next.js** - Framework React
- **TypeScript** - Tipado estático
- **React** - UI Library

### Infraestructura
- **Docker** - Containerización
- **docker-compose** - Orquestación local

## Estructura del Proyecto

```
CrediFlux/
├── backend/                    # Django backend
│   ├── apps/
│   │   ├── core/              # Modelos y utilidades compartidas
│   │   ├── tenants/           # Multi-tenant management
│   │   ├── users/             # Gestión de usuarios
│   │   └── loans/             # Módulo de préstamos
│   ├── config/                # Configuración Django
│   │   ├── settings/          # Settings modulares
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── celery.py
│   ├── requirements/          # Dependencias Python
│   └── manage.py
├── frontend/                   # Next.js frontend
├── docker/                     # Dockerfiles
└── docker-compose.yml
```

## Requisitos Previos

- Docker & Docker Compose
- Python 3.11+ (para desarrollo local sin Docker)
- Node.js 20+ (para desarrollo frontend)

## Instalación y Setup

### 1. Clonar el repositorio

```bash
cd "Django Projects/CrediFlux"
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones.

### 3. Iniciar con Docker

```bash
# Construir y levantar los contenedores
docker-compose up --build

# En otra terminal, ejecutar migraciones
docker-compose exec backend python manage.py migrate_schemas --shared

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser

# Crear tenant público
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant, Domain
from django.db import connection

# Crear tenant público
tenant = Tenant.objects.create(
    schema_name='public',
    name='Public',
    business_name='CrediFlux Platform',
    email='admin@crediflux.com'
)

# Crear dominio
domain = Domain.objects.create(
    domain='localhost',
    tenant=tenant,
    is_primary=True
)

print(f"Tenant público creado: {tenant.name}")
```

### 4. Crear un tenant de prueba

```python
# Crear tenant de prueba
tenant = Tenant.objects.create(
    schema_name='company1',
    name='Company One',
    business_name='Company One LLC',
    email='admin@company1.com',
    subscription_plan='professional'
)

# Crear dominio
domain = Domain.objects.create(
    domain='company1.localhost',
    tenant=tenant,
    is_primary=True
)

print(f"Tenant creado: {tenant.name}")
```

### 5. Acceder a la aplicación

- **API Backend**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Documentation (Swagger)**: http://localhost:8000/swagger/
- **Frontend**: http://localhost:3000

## Desarrollo Local (sin Docker)

### Backend

```bash
# Activar entorno virtual
cd backend
source ../venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements/development.txt

# Configurar variables de entorno
export DJANGO_SETTINGS_MODULE=config.settings.development

# Ejecutar migraciones
python manage.py migrate_schemas --shared

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver

# En otra terminal, ejecutar Celery
celery -A config worker -l info

# En otra terminal, ejecutar Celery Beat
celery -A config beat -l info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Módulo de Préstamos

El módulo de préstamos incluye:

### Modelos

1. **Customer**: Clientes que solicitan préstamos
   - Información personal y contacto
   - Identificación y documentos
   - Información de empleo e ingresos
   - Score crediticio

2. **Loan**: Préstamos
   - Tipos: Personal, Auto, Hipoteca, Negocio, Estudiantil
   - Montos y tasas de interés
   - Calendario de pagos
   - Estados: Draft, Pending, Approved, Active, Paid, Defaulted

3. **LoanSchedule**: Calendario de pagos
   - Cuotas programadas
   - Desglose de principal e interés
   - Estado de pago

4. **LoanPayment**: Pagos realizados
   - Métodos de pago: Efectivo, Cheque, Transferencia, Tarjeta
   - Asignación a principal, interés y mora
   - Recibos y referencias

5. **Collateral**: Garantías
   - Tipos: Vehículo, Propiedad, Equipos, etc.
   - Valuación y documentos

### API Endpoints

#### Customers
- `GET /api/loans/customers/` - Listar clientes
- `POST /api/loans/customers/` - Crear cliente
- `GET /api/loans/customers/{id}/` - Detalle de cliente
- `PUT /api/loans/customers/{id}/` - Actualizar cliente
- `DELETE /api/loans/customers/{id}/` - Eliminar cliente
- `GET /api/loans/customers/{id}/loans/` - Préstamos del cliente
- `GET /api/loans/customers/{id}/statistics/` - Estadísticas del cliente

#### Loans
- `GET /api/loans/` - Listar préstamos
- `POST /api/loans/` - Crear préstamo
- `GET /api/loans/{id}/` - Detalle de préstamo
- `PUT /api/loans/{id}/` - Actualizar préstamo
- `POST /api/loans/{id}/approve/` - Aprobar préstamo
- `POST /api/loans/{id}/disburse/` - Desembolsar préstamo
- `POST /api/loans/{id}/reject/` - Rechazar préstamo
- `GET /api/loans/{id}/schedule/` - Calendario de pagos
- `GET /api/loans/{id}/payments/` - Pagos del préstamo
- `GET /api/loans/statistics/` - Estadísticas generales

#### Payments
- `GET /api/loans/payments/` - Listar pagos
- `POST /api/loans/payments/` - Registrar pago
- `GET /api/loans/payments/{id}/` - Detalle de pago
- `POST /api/loans/payments/{id}/reverse/` - Reversar pago

#### Schedules
- `GET /api/loans/schedules/` - Listar calendario
- `GET /api/loans/schedules/overdue/` - Pagos vencidos

#### Collaterals
- `GET /api/loans/collaterals/` - Listar garantías
- `POST /api/loans/collaterals/` - Crear garantía
- `GET /api/loans/collaterals/{id}/` - Detalle de garantía
- `POST /api/loans/collaterals/{id}/release/` - Liberar garantía
- `POST /api/loans/collaterals/{id}/liquidate/` - Liquidar garantía

## Autenticación JWT

### Obtener Token

```bash
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "password"
}

# Respuesta
{
  "access": "eyJ0eXAiOiJKV1QiLCJ...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJ...",
  "user": {...}
}
```

### Usar Token en Requests

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/loans/
```

### Refrescar Token

```bash
POST /api/auth/token/refresh/
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJ..."
}
```

## Multi-Tenancy

Cada empresa/organización tiene su propio:
- Schema de base de datos aislado
- Usuarios y datos independientes
- Subdominio único (ej: company1.crediflux.com)

### Acceder a un Tenant Específico

En desarrollo local, usar el formato:
- `http://company1.localhost:8000` - Tenant específico
- `http://localhost:8000` - Schema público

## Testing

```bash
# Ejecutar tests
docker-compose exec backend pytest

# Con coverage
docker-compose exec backend pytest --cov=apps
```

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f backend

# Acceder a shell de Django
docker-compose exec backend python manage.py shell

# Acceder a base de datos
docker-compose exec db psql -U crediflux_user -d crediflux_db

# Crear migraciones
docker-compose exec backend python manage.py makemigrations

# Aplicar migraciones
docker-compose exec backend python manage.py migrate_schemas

# Colectar archivos estáticos
docker-compose exec backend python manage.py collectstatic --noinput

# Crear datos de prueba
docker-compose exec backend python manage.py loaddata fixtures/sample_data.json
```

## Próximos Módulos

- Facturación
- Cuentas por Cobrar
- Inventario
- Contabilidad
- Nómina
- Cuentas por Pagar

## Licencia

Proprietary - Todos los derechos reservados

## Contacto

Para soporte o consultas, contactar a: contact@crediflux.com
