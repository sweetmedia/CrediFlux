# CrediFlux 💰

<div align="center">

**Plataforma SaaS Multi-Tenant para Gestión Financiera**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

[Características](#características) •
[Instalación](#instalación) •
[Documentación](#documentación) •
[API](#api) •
[Arquitectura](#arquitectura)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Tech Stack](#tech-stack)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Uso](#uso)
- [Módulos](#módulos)
- [API](#api)
- [Desarrollo](#desarrollo)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contribución](#contribución)

---

## 📖 Descripción

CrediFlux es una plataforma SaaS multi-tenant diseñada específicamente para instituciones financieras, cooperativas de ahorro y crédito, y empresas de microfinanzas. Proporciona una solución integral para la gestión de préstamos, cobranza, y operaciones financieras.

### 🎯 Problema que Resuelve

Las instituciones financieras pequeñas y medianas enfrentan desafíos al gestionar:
- **Múltiples préstamos** con diferentes términos y condiciones
- **Seguimiento de pagos** y cálculo automático de mora
- **Cobranza efectiva** con recordatorios automatizados
- **Reportes financieros** en tiempo real
- **Cumplimiento regulatorio** con auditoría completa

CrediFlux automatiza estos procesos, reduce errores manuales y mejora la eficiencia operativa.

---

## ✨ Características

### 🏦 Gestión de Préstamos
- ✅ Múltiples tipos de préstamos (Personal, Auto, Hipoteca, Negocio, Estudiantil)
- ✅ Cálculo automático de amortización
- ✅ Generación de cronogramas de pago
- ✅ Aprobación y desembolso workflow
- ✅ Garantías y colaterales

### 💳 Sistema de Pagos
- ✅ Múltiples métodos de pago (Efectivo, Cheque, Transferencia, Tarjeta, Móvil)
- ✅ Aplicación automática a cuotas vencidas
- ✅ Distribución inteligente: Mora → Interés → Capital
- ✅ Reversión de pagos con auditoría
- ✅ Generación de recibos

### 📞 Sistema de Cobranza
- ✅ Dashboard de cobranza en tiempo real
- ✅ Identificación automática de pagos vencidos
- ✅ Cálculo automático de mora (configurable por tenant)
- ✅ Recordatorios automatizados (Email, SMS, WhatsApp)
- ✅ Gestión de promesas de pago
- ✅ Escalamiento de casos críticos
- ✅ Historial completo de contactos

### 👥 Gestión de Clientes
- ✅ Perfiles completos con KYC
- ✅ Historial crediticio
- ✅ Documentación digital
- ✅ Credit scoring
- ✅ Múltiples préstamos por cliente

### 📊 Reportes y Analytics
- ✅ Dashboard ejecutivo
- ✅ Métricas de cartera
- ✅ Indicadores de mora
- ✅ Reportes de cobranza
- ✅ Proyecciones de flujo de caja

### 🏢 Multi-Tenancy
- ✅ Aislamiento completo de datos por tenant
- ✅ Configuración personalizada por organización
- ✅ Subdominios dedicados
- ✅ Branding personalizado
- ✅ Múltiples usuarios y roles por tenant

---

## 🛠️ Tech Stack

### Backend
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.11+ | Lenguaje principal |
| **Django** | 5.0.9 | Framework web |
| **Django REST Framework** | 3.14+ | API REST |
| **PostgreSQL** | 15+ | Base de datos |
| **Redis** | 7+ | Cache y message broker |
| **Celery** | 5.3+ | Tareas asíncronas |
| **django-tenants** | 3.5+ | Multi-tenancy |
| **django-money** | 3.4+ | Manejo de monedas |
| **Django Unfold** | Latest | Admin UI moderna |

### Frontend
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Next.js** | 14+ | Framework React |
| **React** | 18+ | UI Library |
| **TypeScript** | 5+ | Tipado estático |
| **Tailwind CSS** | 3+ | Styling |
| **shadcn/ui** | Latest | Componentes UI |
| **Axios** | 1.6+ | HTTP Client |
| **React Hook Form** | 7+ | Form handling |
| **Zod** | 3+ | Validación |

### DevOps
| Tecnología | Propósito |
|------------|-----------|
| **Docker** | Containerización |
| **docker-compose** | Orquestación local |
| **Nginx** | Reverse proxy |
| **GitHub Actions** | CI/CD |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Loans   │  │ Payments │  │Collections│  │ Reports  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API (JWT)
┌───────────────────────────┴─────────────────────────────────┐
│                     Backend (Django DRF)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   API Layer                           │   │
│  │  Serializers │ ViewSets │ Permissions │ Validators   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                Business Logic Layer                   │   │
│  │  Loan Processing │ Payment Distribution │ Collections│   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Data Layer                          │   │
│  │  Models │ Managers │ QuerySets │ Validators          │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                    PostgreSQL (Multi-Schema)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  public  │  │ tenant_1 │  │ tenant_2 │  │ tenant_N │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Estructura del Proyecto

```
CrediFlux/
├── backend/                        # Django Backend
│   ├── apps/
│   │   ├── core/                   # Modelos base y utilidades
│   │   │   ├── models.py          # BaseModel con timestamps
│   │   │   ├── permissions.py     # Permission classes
│   │   │   └── utils.py           # Utilidades compartidas
│   │   ├── tenants/               # Multi-tenant management
│   │   │   ├── models.py          # Tenant, Domain
│   │   │   ├── middleware.py      # Tenant routing
│   │   │   └── admin.py           # Admin customization
│   │   ├── users/                 # Gestión de usuarios
│   │   │   ├── models.py          # User model
│   │   │   ├── serializers.py    # User serializers
│   │   │   └── views.py           # Auth endpoints
│   │   └── loans/                 # Módulo de préstamos
│   │       ├── models.py          # Loan, Payment, Schedule, etc.
│   │       ├── serializers.py     # DRF Serializers
│   │       ├── views.py           # ViewSets
│   │       ├── permissions.py     # Custom permissions
│   │       ├── filters.py         # DjangoFilterBackend
│   │       └── management/
│   │           └── commands/      # Management commands
│   │               └── calculate_late_fees.py
│   ├── config/                    # Configuración Django
│   │   ├── settings/
│   │   │   ├── base.py           # Settings base
│   │   │   ├── development.py    # Dev settings
│   │   │   └── production.py     # Prod settings
│   │   ├── urls.py               # URL routing
│   │   ├── wsgi.py               # WSGI application
│   │   └── celery.py             # Celery config
│   ├── requirements/              # Dependencias Python
│   │   ├── base.txt              # Dependencias base
│   │   ├── development.txt       # Dev dependencies
│   │   └── production.txt        # Prod dependencies
│   ├── Dockerfile                 # Docker image
│   └── manage.py
│
├── frontend/                      # Next.js Frontend
│   ├── app/                       # App Router (Next.js 14)
│   │   ├── (auth)/               # Auth routes
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/            # Dashboard
│   │   ├── loans/                # Gestión de préstamos
│   │   │   ├── page.tsx         # Lista de préstamos
│   │   │   ├── [id]/            # Detalle de préstamo
│   │   │   ├── new/             # Crear préstamo
│   │   │   └── overdue/         # Préstamos morosos
│   │   ├── payments/             # Pagos
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   └── new/
│   │   ├── collections/          # Cobranza
│   │   │   ├── page.tsx         # Dashboard de cobranza
│   │   │   ├── contacts/
│   │   │   ├── reminders/
│   │   │   └── reports/
│   │   ├── customers/            # Clientes
│   │   └── schedules/            # Cronogramas
│   ├── components/               # React components
│   │   ├── ui/                  # shadcn/ui components
│   │   └── shared/              # Shared components
│   ├── lib/                     # Utilities
│   │   ├── api/                 # API client
│   │   │   ├── client.ts       # Axios instance
│   │   │   ├── loans.ts        # Loans API
│   │   │   └── auth.ts         # Auth API
│   │   ├── contexts/           # React contexts
│   │   └── utils/              # Helper functions
│   ├── types/                  # TypeScript types
│   ├── public/                 # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── docker/                      # Docker configurations
│   ├── backend/
│   │   └── Dockerfile
│   ├── frontend/
│   │   └── Dockerfile
│   └── nginx/
│       └── nginx.conf
│
├── docs/                        # Documentación
│   ├── api/                    # API docs
│   ├── architecture/           # Diagramas
│   ├── deployment/             # Guías de deploy
│   └── development/            # Guías de desarrollo
│
├── docker-compose.yml          # Orquestación Docker
├── .env.example               # Variables de entorno ejemplo
├── .gitignore
└── README.md
```

---

## 🚀 Instalación

### Requisitos Previos

- **Docker** 24+ y **Docker Compose** 2+
- **Git**
- **Node.js** 20+ (para desarrollo frontend)
- **Python** 3.11+ (para desarrollo backend sin Docker)

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/sweetmedia/CrediFlux.git
cd CrediFlux
```

### 2️⃣ Configurar Variables de Entorno

```bash
cp .env.example .env
```

Edita `.env` con tus configuraciones:

```env
# Database
POSTGRES_DB=crediflux_db
POSTGRES_USER=crediflux_user
POSTGRES_PASSWORD=secure_password_here

# Django
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret-here

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3️⃣ Iniciar con Docker

```bash
# Construir y levantar los contenedores
docker-compose up --build -d

# Esperar a que PostgreSQL esté listo
docker-compose logs -f db  # Ctrl+C cuando esté listo

# Ejecutar migraciones
docker-compose exec backend python manage.py migrate_schemas --shared

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser
```

### 4️⃣ Crear Tenant de Prueba

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant
from django_tenants.utils import schema_context

# Crear tenant
tenant = Tenant.objects.create(
    schema_name='caproinsa',
    name='Caproinsa SRL.',
    business_name='Cooperativa de Ahorro Caproinsa',
    email='admin@caproinsa.com',
    subscription_plan='professional',
    # Configuración de mora
    late_fee_type='percentage',
    late_fee_percentage=5.0,  # 5% mensual
    late_fee_frequency='monthly',
    grace_period_days=5
)

# Crear dominio
from apps.tenants.models import Domain
domain = Domain.objects.create(
    domain='caproinsa.localhost',
    tenant=tenant,
    is_primary=True
)

print(f"✅ Tenant creado: {tenant.name}")
exit()
```

### 5️⃣ Generar Datos de Prueba (Opcional)

```bash
# Crear clientes y préstamos de ejemplo
docker-compose exec backend python manage.py shell -c "
from apps.loans.models import Customer, Loan
from django_tenants.utils import schema_context
from decimal import Decimal
from moneyed import Money

with schema_context('caproinsa'):
    # Crear cliente
    customer = Customer.objects.create(
        first_name='Juan',
        last_name='Pérez',
        email='juan.perez@example.com',
        phone='809-555-1234',
        id_type='cedula',
        id_number='001-1234567-8',
        monthly_income=Money(50000, 'DOP')
    )

    # Crear préstamo
    loan = Loan.objects.create(
        customer=customer,
        loan_type='personal',
        principal_amount=Money(100000, 'DOP'),
        interest_rate=Decimal('18.0'),
        term_months=12,
        payment_frequency='biweekly',
        status='pending'
    )

    print(f'✅ Cliente creado: {customer.get_full_name()}')
    print(f'✅ Préstamo creado: {loan.loan_number}')
"
```

### 6️⃣ Acceder a la Aplicación

- **Frontend**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Docs (Swagger)**: http://localhost:8000/swagger/
- **Tenant específico**: http://caproinsa.localhost:3000

---

## 💻 Uso

### Flujo de Trabajo Típico

#### 1. Crear un Cliente

```bash
POST /api/loans/customers/
{
  "first_name": "María",
  "last_name": "González",
  "email": "maria@example.com",
  "phone": "809-555-5678",
  "id_type": "cedula",
  "id_number": "001-9876543-2",
  "date_of_birth": "1985-05-15",
  "monthly_income": "75000.00",
  "employment_status": "employed",
  "employer_name": "ABC Company"
}
```

#### 2. Crear Solicitud de Préstamo

```bash
POST /api/loans/
{
  "customer": "customer-uuid",
  "loan_type": "personal",
  "principal_amount": "200000.00",
  "interest_rate": "15.00",
  "term_months": 24,
  "payment_frequency": "monthly",
  "purpose": "Consolidación de deudas"
}
```

#### 3. Aprobar Préstamo

```bash
POST /api/loans/{loan_id}/approve/
{
  "notes": "Cliente cumple con todos los requisitos"
}
```

#### 4. Desembolsar Préstamo

```bash
POST /api/loans/{loan_id}/disburse/
```

Esto automáticamente:
- ✅ Cambia el status a `active`
- ✅ Genera el cronograma de pagos
- ✅ Calcula la primera fecha de pago

#### 5. Registrar Pago

```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "10000.00",
  "payment_method": "cash",
  "payment_date": "2025-10-30"
}
```

El sistema automáticamente:
- ✅ Busca la cuota más vencida
- ✅ Aplica el pago: Mora → Interés → Capital
- ✅ Actualiza el balance del préstamo
- ✅ Genera recibo

---

## 📦 Módulos

### 🏦 Loans (Préstamos)

**Estado actual:** ✅ Completamente funcional

**Características:**
- Gestión completa de préstamos
- Múltiples tipos y frecuencias de pago
- Workflow de aprobación
- Cronogramas automáticos
- Cálculo de amortización

**Documentación:** [Ver docs/modules/loans.md](docs/modules/loans.md)

### 💳 Payments (Pagos)

**Estado actual:** ✅ Completamente funcional

**Características:**
- Registro de pagos
- Distribución inteligente
- Aplicación automática a cuotas vencidas
- Reversión con auditoría
- Múltiples métodos de pago

**Documentación:** [Ver docs/modules/payments.md](docs/modules/payments.md)

### 📞 Collections (Cobranza)

**Estado actual:** ✅ Completamente funcional

**Características:**
- Dashboard de cobranza
- Cálculo automático de mora
- Sistema de recordatorios
- Gestión de contactos
- Promesas de pago
- Reportes de cobranza

**Documentación:** [Ver docs/modules/collections.md](docs/modules/collections.md)

### 👥 Customers (Clientes)

**Estado actual:** ✅ Completamente funcional

**Características:**
- Perfiles completos
- KYC y documentación
- Historial crediticio
- Múltiples préstamos

**Documentación:** [Ver docs/modules/customers.md](docs/modules/customers.md)

### 📊 Reports (Reportes)

**Estado actual:** 🚧 En desarrollo

**Planificado:**
- Reportes de cartera
- Análisis de mora
- Proyecciones
- Export a Excel/PDF

### 💼 Próximos Módulos

- ⏳ **Facturación** - En planificación
- ⏳ **Cuentas por Cobrar** - En planificación
- ⏳ **Inventario** - En planificación
- ⏳ **Contabilidad** - En planificación
- ⏳ **Nómina** - En planificación

---

## 🔌 API

### Autenticación

CrediFlux usa **JWT (JSON Web Tokens)** para autenticación.

#### Obtener Token

```bash
POST /api/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Respuesta:**

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "loan_officer"
  }
}
```

#### Usar Token

```bash
GET /api/loans/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

#### Refrescar Token

```bash
POST /api/auth/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Endpoints Principales

#### Customers

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/customers/` | Listar clientes |
| POST | `/api/loans/customers/` | Crear cliente |
| GET | `/api/loans/customers/{id}/` | Detalle de cliente |
| PUT | `/api/loans/customers/{id}/` | Actualizar cliente |
| DELETE | `/api/loans/customers/{id}/` | Eliminar cliente |
| GET | `/api/loans/customers/{id}/loans/` | Préstamos del cliente |

#### Loans

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/` | Listar préstamos |
| POST | `/api/loans/` | Crear préstamo |
| GET | `/api/loans/{id}/` | Detalle de préstamo |
| PUT | `/api/loans/{id}/` | Actualizar préstamo |
| POST | `/api/loans/{id}/approve/` | Aprobar préstamo |
| POST | `/api/loans/{id}/disburse/` | Desembolsar |
| POST | `/api/loans/{id}/reject/` | Rechazar |
| GET | `/api/loans/statistics/` | Estadísticas |

#### Payments

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/payments/` | Listar pagos |
| POST | `/api/loans/payments/` | Registrar pago |
| GET | `/api/loans/payments/{id}/` | Detalle de pago |
| POST | `/api/loans/payments/{id}/reverse/` | Reversar pago |

#### Schedules

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/schedules/` | Listar cronogramas |
| GET | `/api/loans/schedules/overdue/` | Pagos vencidos |

**Documentación completa:** [Ver docs/api/README.md](docs/api/README.md)

---

## 👨‍💻 Desarrollo

### Desarrollo Local (sin Docker)

#### Backend

```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
cd backend
pip install -r requirements/development.txt

# Configurar variables de entorno
export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=postgres://user:pass@localhost:5432/crediflux_db

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

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Comandos de Desarrollo

```bash
# Backend

# Crear migraciones
docker-compose exec backend python manage.py makemigrations

# Aplicar migraciones a todos los tenants
docker-compose exec backend python manage.py migrate_schemas

# Calcular moras
docker-compose exec backend python manage.py calculate_late_fees --tenant caproinsa

# Shell de Django
docker-compose exec backend python manage.py shell

# Shell con tenant específico
docker-compose exec backend python manage.py tenant_command shell --schema=caproinsa

# Colectar archivos estáticos
docker-compose exec backend python manage.py collectstatic --noinput

# Frontend

# Lint
npm run lint

# Type check
npm run type-check

# Build
npm run build
```

### Convenciones de Código

#### Python/Django
- Seguir **PEP 8**
- Usar **type hints** cuando sea posible
- Docstrings en formato **Google Style**
- Max line length: **120 caracteres**

#### TypeScript/React
- Seguir **Airbnb Style Guide**
- Usar **functional components** con hooks
- **Named exports** para componentes
- **Arrow functions** para componentes

#### Git Commits
- Usar **Conventional Commits**
- Formato: `tipo(scope): mensaje`
- Tipos: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Ejemplos:
```bash
feat(loans): Add automatic late fee calculation
fix(payments): Correct payment distribution to overdue schedules
docs(api): Update authentication documentation
```

---

## 🧪 Testing

### Backend Tests

```bash
# Ejecutar todos los tests
docker-compose exec backend pytest

# Con coverage
docker-compose exec backend pytest --cov=apps --cov-report=html

# Test específico
docker-compose exec backend pytest apps/loans/tests/test_payments.py

# Con verbose output
docker-compose exec backend pytest -v
```

### Frontend Tests

```bash
cd frontend

# Unit tests
npm test

# E2E tests (Playwright)
npm run test:e2e

# Coverage
npm run test:coverage
```

---

## 🚀 Deployment

### Producción con Docker

```bash
# Build para producción
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Aplicar migraciones
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate_schemas

# Colectar estáticos
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### Variables de Entorno (Producción)

```env
# Database
POSTGRES_DB=crediflux_prod
POSTGRES_USER=crediflux_prod_user
POSTGRES_PASSWORD=super_secure_password

# Django
DJANGO_SECRET_KEY=production-secret-key-very-long-and-random
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=crediflux.com,www.crediflux.com

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@crediflux.com
EMAIL_HOST_PASSWORD=app_specific_password
```

**Guía completa de deployment:** [Ver docs/deployment/README.md](docs/deployment/README.md)

---

## 🤝 Contribución

### Workflow de Desarrollo

1. **Fork** el repositorio
2. **Crear** una branch para tu feature (`git checkout -b feature/amazing-feature`)
3. **Commit** tus cambios (`git commit -m 'feat: Add amazing feature'`)
4. **Push** a la branch (`git push origin feature/amazing-feature`)
5. **Crear** un Pull Request

### Pull Request Guidelines

- ✅ Descripción clara de los cambios
- ✅ Tests que cubran nuevas funcionalidades
- ✅ Documentación actualizada
- ✅ Screenshots para cambios de UI
- ✅ Sin conflictos con `master`

---

## 📝 Documentación Adicional

- **[Guía de Arquitectura](docs/architecture/README.md)** - Diagramas y decisiones técnicas
- **[API Reference](docs/api/README.md)** - Documentación completa de la API
- **[Módulo de Préstamos](docs/modules/loans.md)** - Guía del módulo de loans
- **[Módulo de Cobranza](docs/modules/collections.md)** - Sistema de cobranza
- **[Multi-Tenancy](docs/architecture/multi-tenancy.md)** - Arquitectura multi-tenant
- **[Deployment](docs/deployment/README.md)** - Guías de deployment
- **[Troubleshooting](docs/troubleshooting.md)** - Solución de problemas comunes

---

## 📄 Licencia

**Proprietary** - Todos los derechos reservados © 2025 CrediFlux

---

## 📞 Soporte

- **Email**: support@crediflux.com
- **Documentation**: https://docs.crediflux.com
- **GitHub Issues**: https://github.com/sweetmedia/CrediFlux/issues

---

<div align="center">

**Hecho con ❤️ por el equipo de CrediFlux**

[⬆ Volver arriba](#crediflux-)

</div>
