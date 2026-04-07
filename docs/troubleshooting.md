# Troubleshooting Guide - CrediFlux

## Índice

- [Problemas de Instalación](#problemas-de-instalación)
- [Problemas de Base de Datos](#problemas-de-base-de-datos)
- [Problemas de Multi-Tenancy](#problemas-de-multi-tenancy)
- [Problemas de Autenticación](#problemas-de-autenticación)
- [Problemas de Préstamos](#problemas-de-préstamos)
- [Problemas de Pagos](#problemas-de-pagos)
- [Problemas de Cálculo de Mora](#problemas-de-cálculo-de-mora)
- [Problemas de Frontend](#problemas-de-frontend)
- [Problemas de Performance](#problemas-de-performance)

---

## Problemas de Instalación

### Docker no inicia

**Síntoma**:
```bash
docker-compose up
ERROR: Couldn't connect to Docker daemon
```

**Soluciones**:

1. Verificar que Docker Desktop está corriendo
2. Reiniciar Docker Desktop
3. Verificar permisos:
```bash
sudo chmod 666 /var/run/docker.sock
```

### "Port already in use"

**Síntoma**:
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solución**:

```bash
# Encontrar proceso usando el puerto
lsof -i :8000

# Matar el proceso
kill -9 <PID>

# O cambiar puerto en docker-compose.yml
ports:
  - "8001:8000"  # Usar 8001 en lugar de 8000
```

### Dependencias de Python fallan

**Síntoma**:
```
ERROR: Could not find a version that satisfies the requirement django-tenants
```

**Solución**:

```bash
# Limpiar cache de pip
docker-compose exec backend pip cache purge

# Reinstalar
docker-compose exec backend pip install -r requirements/base.txt --no-cache-dir
```

---

## Problemas de Base de Datos

### "relation does not exist"

**Síntoma**:
```
django.db.utils.ProgrammingError: relation "loans_loan" does not exist
```

**Causa**: Migraciones no ejecutadas

**Solución**:

```bash
# Aplicar migraciones compartidas
docker-compose exec backend python manage.py migrate_schemas --shared

# Aplicar migraciones de tenant
docker-compose exec backend python manage.py migrate_schemas
```

### "too many connections"

**Síntoma**:
```
FATAL: sorry, too many clients already
```

**Solución**:

```bash
# Editar postgresql.conf
max_connections = 200  # Aumentar de 100

# O configurar connection pooling
# config/settings/production.py
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,
    }
}
```

### Migraciones bloqueadas

**Síntoma**:
```
django.db.utils.OperationalError: could not obtain lock on row
```

**Solución**:

```sql
-- Conectar a PostgreSQL
docker-compose exec db psql -U crediflux_user crediflux_db

-- Ver transacciones bloqueadas
SELECT * FROM pg_locks WHERE NOT granted;

-- Matar transacción bloqueante
SELECT pg_terminate_backend(<pid>);
```

### Backup y Restore

**Backup**:
```bash
# Backup completo
docker-compose exec db pg_dump -U crediflux_user crediflux_db > backup.sql

# Backup de un schema específico
docker-compose exec db pg_dump -U crediflux_user -n caproinsa crediflux_db > caproinsa_backup.sql
```

**Restore**:
```bash
# Restore completo
docker-compose exec -T db psql -U crediflux_user crediflux_db < backup.sql

# Restore de schema
docker-compose exec -T db psql -U crediflux_user crediflux_db < caproinsa_backup.sql
```

---

## Problemas de Multi-Tenancy

### Tenant no se detecta

**Síntoma**: 404 o "Tenant matching query does not exist"

**Diagnóstico**:

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant, Domain

# Listar todos los dominios
for d in Domain.objects.all():
    print(f"{d.domain} -> {d.tenant.name}")

# Verificar dominio específico
domain = Domain.objects.filter(domain='caproinsa.localhost').first()
if domain:
    print(f"✅ Tenant: {domain.tenant.name}")
else:
    print("❌ Dominio no encontrado")
```

**Solución**:

```python
# Crear dominio faltante
from apps.tenants.models import Tenant, Domain

tenant = Tenant.objects.get(schema_name='caproinsa')
Domain.objects.create(
    domain='caproinsa.localhost',
    tenant=tenant,
    is_primary=True
)
```

### "search_path" error

**Síntoma**:
```
relation "public.tenants_tenant" does not exist
```

**Causa**: Schema público no accesible

**Solución**:

```python
# config/settings/base.py
DATABASES = {
    'default': {
        'OPTIONS': {
            'options': '-c search_path=public,pg_catalog'
        }
    }
}
```

### Datos aparecen en tenant incorrecto

**Diagnóstico**:

```python
from django.db import connection

# Verificar schema actual
print(f"Current schema: {connection.schema_name}")

# Verificar tenant actual
if hasattr(connection, 'tenant'):
    print(f"Current tenant: {connection.tenant.name}")
```

**Solución**: Siempre usar `schema_context`:

```python
from django_tenants.utils import schema_context

with schema_context('caproinsa'):
    # Operaciones aquí garantizan schema correcto
    loans = Loan.objects.all()
```

---

## Problemas de Autenticación

### JWT Token expirado

**Síntoma**:
```json
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid"
}
```

**Solución**:

1. **Frontend**: Implementar refresh automático:

```typescript
// lib/api/client.ts
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Intentar refresh
      const refresh = localStorage.getItem('refresh_token');
      const response = await api.post('/auth/token/refresh/', { refresh });
      localStorage.setItem('access_token', response.data.access);

      // Reintentar request original
      error.config.headers.Authorization = `Bearer ${response.data.access}`;
      return api.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

2. **Backend**: Aumentar tiempo de expiración:

```python
# config/settings/base.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),  # Aumentar de 1 a 2 horas
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
}
```

### CORS errors

**Síntoma**:
```
Access to fetch at 'http://localhost:8000/api/loans/' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Solución**:

```python
# config/settings/development.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

### Usuario no tiene permisos

**Síntoma**:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Diagnóstico**:

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.users.models import User

user = User.objects.get(email='user@example.com')

# Verificar permisos
print(f"Is superuser: {user.is_superuser}")
print(f"Is staff: {user.is_staff}")
print(f"Role: {user.role}")

# Ver permisos específicos
for perm in user.get_all_permissions():
    print(f"  - {perm}")
```

**Solución**: Asignar permisos correctos:

```python
# Hacer superuser
user.is_superuser = True
user.is_staff = True
user.save()

# O asignar rol específico
user.role = 'manager'
user.save()
```

---

## Problemas de Préstamos

### Cronograma no se genera

**Síntoma**: `loan.payment_schedules.count() == 0` después de desembolsar

**Diagnóstico**:

```python
loan = Loan.objects.get(id='uuid')
print(f"Status: {loan.status}")
print(f"Disbursement date: {loan.disbursement_date}")
print(f"Schedules: {loan.payment_schedules.count()}")
```

**Solución**:

```python
# Regenerar cronograma manualmente
from apps.loans.utils import generate_payment_schedule

generate_payment_schedule(loan)
```

### Balance incorrecto

**Síntoma**: `outstanding_balance` no coincide con suma de cuotas pendientes

**Solución**: Recalcular balance:

```bash
docker-compose exec backend python manage.py shell
```

```python
from apps.loans.models import Loan

loan = Loan.objects.get(id='uuid')

# Recalcular
loan.update_outstanding_balance()

print(f"Nuevo balance: {loan.outstanding_balance}")
```

### `days_overdue` siempre 0

**Causa**: Status de schedules no incluye 'overdue' o 'partial'

**Solución**: Verificar filtro en `get_days_overdue()`:

```python
# apps/loans/serializers.py
def get_days_overdue(self, obj):
    from django.utils import timezone

    most_overdue = obj.payment_schedules.filter(
        status__in=['pending', 'overdue', 'partial'],  # Importante!
        due_date__lt=timezone.now().date()
    ).order_by('due_date').first()

    if most_overdue:
        return (timezone.now().date() - most_overdue.due_date).days
    return 0
```

---

## Problemas de Pagos

### Pago no se aplica correctamente

**Síntoma**: Distribución de pago (principal/interest/late_fee) incorrecta

**Diagnóstico**:

```python
payment = LoanPayment.objects.get(id='uuid')

print(f"Total: {payment.amount}")
print(f"Principal: {payment.principal_paid}")
print(f"Interest: {payment.interest_paid}")
print(f"Late Fee: {payment.late_fee_paid}")

total_dist = payment.principal_paid + payment.interest_paid + payment.late_fee_paid
print(f"Sum: {total_dist}")
print(f"Match: {total_dist == payment.amount}")
```

**Solución**: Verificar lógica en `LoanPaymentCreateSerializer.create()`

### Mora no se cobra

**Síntoma**: `late_fee_paid` siempre $0 aunque haya mora acumulada

**Causa**: Pago sin `schedule` especificado y lógica antigua

**Verificar**:

```python
# apps/loans/serializers.py - línea ~277
else:
    # Debe buscar oldest_overdue y aplicar a mora primero
    oldest_overdue = loan.payment_schedules.filter(...)
```

**Solución**: Asegurar código actualizado del fix de mora.

### Balance de cuota no actualiza

**Causa**: `update_schedule_balance()` no se ejecuta

**Solución Manual**:

```python
payment = LoanPayment.objects.get(id='uuid')
schedule = payment.schedule

if schedule:
    schedule.paid_amount += payment.amount
    if payment.late_fee_paid:
        schedule.late_fee_paid += payment.late_fee_paid

    # Recalcular status
    if schedule.paid_amount >= schedule.total_amount + schedule.late_fee_amount:
        schedule.status = 'paid'
    elif schedule.paid_amount > 0:
        schedule.status = 'partial'

    schedule.save()
```

---

## Problemas de Cálculo de Mora

### Mora no se calcula automáticamente

**Causa**: Comando `calculate_late_fees` no se ejecuta

**Solución**:

```bash
# Ejecutar manualmente
docker-compose exec backend python manage.py calculate_late_fees --tenant caproinsa

# Verificar Celery Beat
docker-compose logs -f celery-beat

# Verificar configuración
# config/celery.py
app.conf.beat_schedule = {
    'calculate-late-fees-daily': {
        'task': 'apps.loans.tasks.calculate_all_late_fees',
        'schedule': crontab(hour=1, minute=0),
    },
}
```

### Mora calculada incorrecta

**Diagnóstico**:

```python
from apps.tenants.models import Tenant

tenant = Tenant.objects.get(schema_name='caproinsa')

print(f"Late fee type: {tenant.late_fee_type}")
print(f"Percentage: {tenant.late_fee_percentage}%")
print(f"Frequency: {tenant.late_fee_frequency}")
print(f"Grace period: {tenant.grace_period_days} days")
```

**Verificar cálculo**:

```python
from django_tenants.utils import schema_context
from apps.loans.models import LoanSchedule

with schema_context('caproinsa'):
    schedule = LoanSchedule.objects.filter(status='overdue').first()

    days_overdue = (timezone.now().date() - schedule.due_date).days
    effective_days = days_overdue - tenant.grace_period_days

    print(f"Days overdue: {days_overdue}")
    print(f"Effective days: {effective_days}")
    print(f"Balance: {schedule.balance}")
    print(f"Late fee: {schedule.late_fee_amount}")
```

### Período de gracia no aplica

**Verificar configuración de tenant**:

```python
tenant.grace_period_days = 5  # Asegurar que está configurado
tenant.save()
```

---

## Problemas de Frontend

### "Cannot read properties of undefined"

**Síntoma**:
```
TypeError: Cannot read properties of undefined (reading 'loan_number')
```

**Causa**: Datos no cargados o null

**Solución**:

```typescript
// Usar optional chaining y valores por defecto
{payment?.loan_number ?? 'N/A'}

// Verificar carga
if (!payment) {
  return <Loader />;
}
```

### "$NaN" en currency displays

**Causa**: Arithmetic en valores null/undefined

**Solución**:

```typescript
const totalOverdue = response.reduce(
  (sum, s) => sum + (Number(s.balance) || 0),  // Usar || 0
  0
);
```

### Hard refresh no soluciona cambios

**Solución**:

```bash
# Limpiar cache de Next.js
cd frontend
rm -rf .next
npm run dev
```

### API calls failing with 401

**Verificar token**:

```typescript
const token = localStorage.getItem('access_token');
console.log('Token:', token);

// Verificar expiración
const payload = JSON.parse(atob(token.split('.')[1]));
const exp = new Date(payload.exp * 1000);
console.log('Expires:', exp);
```

---

## Problemas de Performance

### Queries lentas

**Diagnóstico**:

```python
# Habilitar query logging
# config/settings/development.py
LOGGING = {
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

**Solución**: Usar `select_related` y `prefetch_related`:

```python
# Mal (N+1)
loans = Loan.objects.all()
for loan in loans:
    print(loan.customer.name)  # Query cada vez

# Bien
loans = Loan.objects.select_related('customer').all()
for loan in loans:
    print(loan.customer.name)  # No extra queries
```

### Alto uso de memoria

**Diagnóstico**:

```bash
# Ver uso de memoria de contenedor
docker stats

# Ver procesos Python
docker-compose exec backend ps aux
```

**Solución**:

```python
# Usar iterator() para datasets grandes
for loan in Loan.objects.iterator(chunk_size=100):
    process(loan)

# Limitar querysets
recent_loans = Loan.objects.all()[:100]
```

### Celery tasks se acumulan

**Diagnóstico**:

```bash
# Ver cola de Celery
docker-compose exec backend celery -A config inspect active

# Ver workers
docker-compose exec backend celery -A config inspect stats
```

**Solución**:

```bash
# Purgar cola
docker-compose exec backend celery -A config purge

# Aumentar workers
docker-compose up --scale celery-worker=4
```

---

## Comandos Útiles de Diagnóstico

### Verificar estado general

```bash
# Ver logs de todos los servicios
docker-compose logs --tail=100

# Ver logs de servicio específico
docker-compose logs -f backend

# Verificar conectividad de DB
docker-compose exec db pg_isready

# Verificar Redis
docker-compose exec redis redis-cli ping
```

### Verificar configuración

```bash
# Ver configuración de Django
docker-compose exec backend python manage.py diffsettings

# Ver apps instaladas
docker-compose exec backend python manage.py showmigrations

# Verificar URLs
docker-compose exec backend python manage.py show_urls
```

### Limpiar sistema

```bash
# Limpiar contenedores
docker-compose down -v

# Reconstruir desde cero
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Limpiar migraciones
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
```

---

## Contacto de Soporte

Si el problema persiste:

- **Email**: support@crediflux.com
- **GitHub Issues**: https://github.com/sweetmedia/CrediFlux/issues
- **Documentación**: https://docs.crediflux.com

---

**Última actualización**: 2025-10-30
