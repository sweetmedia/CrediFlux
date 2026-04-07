# Arquitectura Multi-Tenant

## Descripción General

CrediFlux utiliza **django-tenants** para implementar una arquitectura multi-tenant basada en **schemas de PostgreSQL**. Cada organización (tenant) tiene su propio schema aislado con sus propias tablas.

## Índice

- [Conceptos Clave](#conceptos-clave)
- [Modelo de Datos](#modelo-de-datos)
- [Schema Routing](#schema-routing)
- [Migraciones](#migraciones)
- [Gestión de Tenants](#gestión-de-tenants)
- [Mejores Prácticas](#mejores-prácticas)

---

## Conceptos Clave

### ¿Qué es Multi-Tenancy?

Multi-tenancy permite que una sola instancia de la aplicación sirva a múltiples organizaciones (tenants), manteniendo sus datos completamente aislados.

### Estrategias de Multi-Tenancy

| Estrategia | Descripción | Ventajas | Desventajas |
|------------|-------------|----------|-------------|
| **Schema-based** (usado) | Un schema por tenant | Aislamiento completo, fácil backup | Más complejo, límite de schemas |
| Database-based | Una DB por tenant | Máximo aislamiento | Muy complejo, costoso |
| Row-based | Columna `tenant_id` | Simple, escalable | Riesgo de fugas de datos |

### Por qué Schema-based

CrediFlux usa **schema-based** porque ofrece:

- ✅ **Aislamiento completo** de datos
- ✅ **Cumplimiento regulatorio** (datos financieros sensibles)
- ✅ **Backup/restore** por tenant individual
- ✅ **Personalización** de esquema por tenant (futuro)
- ✅ **Migración sencilla** a DB dedicada si es necesario

---

## Modelo de Datos

### Estructura de PostgreSQL

```
PostgreSQL Database: crediflux_db
│
├── public (schema compartido)
│   ├── tenants_tenant
│   ├── tenants_domain
│   └── django_migrations
│
├── caproinsa (tenant schema 1)
│   ├── users_user
│   ├── loans_customer
│   ├── loans_loan
│   ├── loans_loanpayment
│   └── ...
│
├── bancoprosa (tenant schema 2)
│   ├── users_user
│   ├── loans_customer
│   └── ...
│
└── cooperativa_abc (tenant schema 3)
    └── ...
```

### Schema Público (Compartido)

**Modelos en `public`**:

```python
# apps/tenants/models.py
from django_tenants.models import TenantMixin, DomainMixin

class Tenant(TenantMixin):
    name = CharField(max_length=100)
    schema_name = CharField(max_length=63, unique=True)
    business_name = CharField(max_length=200)
    email = EmailField()

    # Configuración de mora
    late_fee_type = CharField(max_length=20)
    late_fee_percentage = DecimalField(max_digits=5, decimal_places=2)
    late_fee_frequency = CharField(max_length=20)

    # Configuración de branding
    logo = ImageField(upload_to='tenant_logos/', blank=True)
    primary_color = CharField(max_length=7, default='#3B82F6')

    # Suscripción
    subscription_plan = CharField(max_length=50)
    is_active = BooleanField(default=True)

class Domain(DomainMixin):
    pass
```

**Características**:
- Único schema para TODOS los tenants
- Contiene información de tenants y dominios
- No contiene datos de negocio

### Schemas de Tenant

**Modelos en cada schema**:

- `users_user`
- `loans_customer`
- `loans_loan`
- `loans_loanpayment`
- `loans_loanschedule`
- Todos los modelos de negocio...

**Características**:
- Aislamiento completo
- Mismo esquema de tablas para todos
- Datos específicos del tenant

---

## Schema Routing

### Middleware de Tenant

**django-tenants** usa middleware para detectar el tenant actual:

```python
# config/settings/base.py
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # ... otros middlewares
]
```

### Detección por Dominio

**Configuración**:

```python
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"
```

**Flujo de detección**:

1. Usuario accede a `caproinsa.crediflux.com`
2. Middleware extrae `caproinsa` del dominio
3. Busca en `tenants_domain` el tenant asociado
4. Establece `connection.schema_name = 'caproinsa'`
5. Todas las queries van al schema `caproinsa`

**Ejemplo**:

```python
# Usuario accede a caproinsa.crediflux.com
# Middleware automáticamente establece:
connection.set_schema('caproinsa')

# Ahora todas las queries van a ese schema
loans = Loan.objects.all()
# SELECT * FROM caproinsa.loans_loan
```

### Uso Manual de Schema Context

Para operaciones admin o scripts:

```python
from django_tenants.utils import schema_context, tenant_context

# Opción 1: Schema context
with schema_context('caproinsa'):
    customers = Customer.objects.all()
    # Opera en schema 'caproinsa'

# Opción 2: Tenant context
tenant = Tenant.objects.get(schema_name='caproinsa')
with tenant_context(tenant):
    loans = Loan.objects.all()
    # Opera en schema del tenant
```

### Public Schema

Para acceder al schema público:

```python
from django_tenants.utils import get_public_schema_name, schema_context

with schema_context(get_public_schema_name()):
    tenants = Tenant.objects.all()
    # Opera en schema 'public'
```

---

## Migraciones

### Tipos de Migraciones

#### 1. Migraciones Compartidas (Shared)

**Apps en `SHARED_APPS`**:

```python
# config/settings/base.py
SHARED_APPS = [
    'django_tenants',
    'apps.tenants',
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
```

**Aplicar**:
```bash
python manage.py migrate_schemas --shared
```

**Resultado**: Migra solo el schema `public`

#### 2. Migraciones de Tenant

**Apps en `TENANT_APPS`**:

```python
TENANT_APPS = [
    'apps.loans',
    'apps.users',
    'apps.core',
    # ... apps específicas de tenant
]
```

**Aplicar a un tenant específico**:
```bash
python manage.py migrate_schemas --schema=caproinsa
```

**Aplicar a todos los tenants**:
```bash
python manage.py migrate_schemas
```

**Resultado**: Migra todos los schemas de tenant excepto `public`

### Crear Nueva Migración

```bash
# 1. Hacer cambios en models.py
# 2. Crear migración
python manage.py makemigrations

# 3. Aplicar a shared si es app compartida
python manage.py migrate_schemas --shared

# 4. O aplicar a tenants si es app de tenant
python manage.py migrate_schemas
```

### Rollback de Migración

```bash
# Rollback en tenant específico
python manage.py migrate_schemas --schema=caproinsa loans 0005

# Rollback en todos los tenants
python manage.py migrate_schemas loans 0005
```

---

## Gestión de Tenants

### Crear Tenant

**Método 1: Django Shell**

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant, Domain
from decimal import Decimal

# Crear tenant
tenant = Tenant.objects.create(
    schema_name='nuevacooperativa',  # Solo letras minúsculas, números, guiones
    name='Nueva Cooperativa',
    business_name='Cooperativa de Ahorro y Crédito Nueva Cooperativa',
    email='admin@nuevacooperativa.com',
    subscription_plan='professional',

    # Configuración de mora
    late_fee_type='percentage',
    late_fee_percentage=Decimal('5.0'),
    late_fee_frequency='monthly',
    grace_period_days=5,

    # Branding
    primary_color='#10B981'
)

# Crear dominio
domain = Domain.objects.create(
    domain='nuevacooperativa.localhost',  # Dev
    # domain='nuevacooperativa.crediflux.com',  # Prod
    tenant=tenant,
    is_primary=True
)

print(f"✅ Tenant creado: {tenant.name}")
print(f"✅ Schema: {tenant.schema_name}")
print(f"✅ Dominio: {domain.domain}")
```

**Método 2: Management Command (Recomendado)**

```bash
python manage.py create_tenant \
  --schema_name=nuevacooperativa \
  --name="Nueva Cooperativa" \
  --domain=nuevacooperativa.localhost
```

### Verificar Tenant

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant
from django_tenants.utils import schema_context

# Listar todos los tenants
tenants = Tenant.objects.all()
for t in tenants:
    print(f"- {t.name} ({t.schema_name})")

# Verificar schema existe
tenant = Tenant.objects.get(schema_name='caproinsa')
with schema_context(tenant.schema_name):
    from apps.loans.models import Customer
    count = Customer.objects.count()
    print(f"Clientes en {tenant.name}: {count}")
```

### Eliminar Tenant

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant
from django_tenants.utils import schema_context

tenant = Tenant.objects.get(schema_name='tenant_to_delete')

# CUIDADO: Esto elimina TODOS los datos
tenant.delete(force_drop=True)
```

**IMPORTANTE**: `delete(force_drop=True)` elimina el schema y TODOS los datos permanentemente.

### Listar Todos los Tenants

```bash
python manage.py list_tenants
```

---

## Mejores Prácticas

### 1. Siempre Usar Schema Context en Scripts

❌ **Incorrecto**:
```python
# En script standalone
from apps.loans.models import Loan
loans = Loan.objects.all()  # ¿Qué tenant?
```

✅ **Correcto**:
```python
from django_tenants.utils import schema_context

with schema_context('caproinsa'):
    from apps.loans.models import Loan
    loans = Loan.objects.all()
```

### 2. No Mezclar Datos de Tenants

❌ **Incorrecto**:
```python
# Intentar relacionar datos entre tenants
tenant1_customer = get_customer_from_tenant1()
tenant2_loan = Loan.objects.create(
    customer=tenant1_customer  # ERROR!
)
```

### 3. Validar Tenant en API

```python
from rest_framework.permissions import BasePermission

class IsTenantUser(BasePermission):
    def has_permission(self, request, view):
        # Verificar que usuario pertenece al tenant actual
        return request.user.tenant == request.tenant
```

### 4. Testing con Tenants

```python
from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

class LoanTestCase(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Auto-crea tenant de prueba
        cls.tenant = cls.get_test_tenant(
            schema_name='test',
            name='Test Tenant'
        )

    def test_create_loan(self):
        # Test corre en schema del tenant de prueba
        loan = Loan.objects.create(...)
        self.assertIsNotNone(loan.id)
```

### 5. Logs por Tenant

```python
import logging

logger = logging.getLogger(__name__)

def process_loan(loan):
    tenant_name = connection.tenant.name
    logger.info(f"[{tenant_name}] Processing loan {loan.loan_number}")
```

### 6. Celery Tasks con Tenant

```python
from celery import shared_task
from django_tenants.utils import schema_context

@shared_task
def calculate_late_fees_for_tenant(tenant_schema):
    with schema_context(tenant_schema):
        from apps.loans.models import LoanSchedule
        # Procesar en el schema correcto
        schedules = LoanSchedule.objects.filter(...)
```

---

## Seguridad

### Row Level Security (Adicional)

Aunque schemas proveen aislamiento, se puede agregar RLS:

```python
# apps/core/models.py
class TenantAwareModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Validar que estamos en el schema correcto
        if hasattr(connection, 'tenant'):
            assert connection.tenant.schema_name == self._state.db
        super().save(*args, **kwargs)
```

### Auditoría de Acceso

```python
# apps/core/middleware.py
class TenantAuditMiddleware:
    def __call__(self, request):
        if hasattr(request, 'tenant'):
            logger.info(
                f"User {request.user} accessing {request.tenant.name}"
            )
        return self.get_response(request)
```

---

## Performance

### Índices por Schema

Cada tenant tiene sus propios índices:

```python
class Loan(models.Model):
    loan_number = models.CharField(max_length=50)

    class Meta:
        indexes = [
            models.Index(fields=['loan_number']),
            models.Index(fields=['status', 'disbursement_date']),
        ]
```

Resultado: Índices creados en CADA schema de tenant.

### Connection Pooling

```python
# config/settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'OPTIONS': {
            'options': '-c search_path=public',
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}
```

### Query Optimization

```python
# Mal: N+1 queries
for loan in Loan.objects.all():
    print(loan.customer.name)  # Query por cada loan

# Bien: 1 query con join
for loan in Loan.objects.select_related('customer'):
    print(loan.customer.name)
```

---

## Limitaciones

### Límite de Schemas en PostgreSQL

PostgreSQL recomienda < 100 schemas por database para performance óptima.

**Solución para escalar**:
- Sharding horizontal (múltiples databases)
- Mover tenants grandes a database dedicada

### Shared Connections

Todas las conexiones van a la misma database, solo cambia el schema.

**Implicación**:
- No se puede tener configuraciones de DB diferentes por tenant
- No se puede tener versiones de PostgreSQL diferentes

### Migraciones Lentas

Migrar 50+ tenants puede tomar tiempo.

**Solución**:
```bash
# Migrar en paralelo (cuidado con recursos)
python manage.py migrate_schemas --executor=multiprocessing
```

---

## Troubleshooting

### "relation does not exist"

**Causa**: Ejecutando query sin schema context

**Solución**:
```python
with schema_context('caproinsa'):
    # queries aquí
```

### Tenant no se detecta

**Causa**: Dominio no configurado correctamente

**Verificar**:
```python
from apps.tenants.models import Domain
Domain.objects.filter(domain='caproinsa.localhost')
# Debe existir
```

### Datos aparecen en tenant incorrecto

**Causa**: No usar schema context en script

**Prevenir**: Siempre validar schema actual:
```python
from django.db import connection
print(f"Current schema: {connection.schema_name}")
```

---

## Migración Futura

### De Schema-based a Database-based

Si un tenant crece mucho, se puede migrar a su propia database:

```bash
# 1. Dump del schema
pg_dump -n caproinsa crediflux_db > caproinsa.sql

# 2. Crear nueva database
createdb caproinsa_db

# 3. Restore
psql caproinsa_db < caproinsa.sql

# 4. Actualizar configuración de tenant
tenant.database_name = 'caproinsa_db'
tenant.save()
```

---

**Última actualización**: 2025-10-30
