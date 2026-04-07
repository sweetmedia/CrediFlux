# Módulo de Cobranza (Collections)

## Descripción General

El módulo de cobranza automatiza la gestión de pagos vencidos, cálculo de mora, recordatorios, gestión de contactos y seguimiento de promesas de pago.

## Índice

- [Modelos](#modelos)
- [Cálculo de Mora](#cálculo-de-mora)
- [Sistema de Recordatorios](#sistema-de-recordatorios)
- [Gestión de Contactos](#gestión-de-contactos)
- [Promesas de Pago](#promesas-de-pago)
- [Dashboard de Cobranza](#dashboard-de-cobranza)
- [API Endpoints](#api-endpoints)

---

## Modelos

### CollectionContact (Registro de Contacto)

**Ubicación**: `backend/apps/loans/models.py`

```python
class CollectionContact(BaseModel):
    loan = ForeignKey(Loan, related_name='collection_contacts')
    contact_date = DateTimeField(default=timezone.now)
    contact_type = CharField(choices=CONTACT_TYPE_CHOICES)

    outcome = CharField(choices=CONTACT_OUTCOME_CHOICES)
    promise_date = DateField(null=True, blank=True)
    promise_amount = MoneyField(null=True, blank=True)

    notes = TextField()
    contacted_by = ForeignKey(User, related_name='collection_contacts')
```

**Tipos de contacto**:
- `phone_call`: Llamada telefónica
- `email`: Correo electrónico
- `whatsapp`: Mensaje WhatsApp
- `sms`: Mensaje SMS
- `in_person`: Visita personal
- `letter`: Carta física

**Resultados de contacto**:
- `promise_to_pay`: Promesa de pago
- `partial_payment_promised`: Promesa de pago parcial
- `refused_to_pay`: Se niega a pagar
- `dispute`: Disputa el monto
- `no_answer`: No contestó
- `wrong_number`: Número incorrecto
- `will_contact_us`: Contactará a la institución
- `payment_made`: Realizó el pago

### CollectionReminder (Recordatorio)

```python
class CollectionReminder(BaseModel):
    schedule = ForeignKey(LoanSchedule, related_name='reminders')
    reminder_type = CharField(choices=REMINDER_TYPE_CHOICES)
    scheduled_date = DateTimeField()

    status = CharField(choices=REMINDER_STATUS_CHOICES)
    sent_date = DateTimeField(null=True, blank=True)
    delivery_status = CharField(max_length=50, blank=True)

    message = TextField()
```

**Tipos de recordatorio**:
- `pre_due`: Antes del vencimiento
- `on_due`: Día de vencimiento
- `overdue_1`: 1 día vencido
- `overdue_7`: 7 días vencido
- `overdue_15`: 15 días vencido
- `overdue_30`: 30 días vencido

**Estados**:
- `pending`: Pendiente de envío
- `sent`: Enviado
- `delivered`: Entregado
- `failed`: Falló
- `cancelled`: Cancelado

---

## Cálculo de Mora

### Configuración por Tenant

Cada tenant puede configurar su política de mora:

```python
class Tenant(TenantMixin):
    # Configuración de mora
    late_fee_type = CharField(choices=[
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto Fijo')
    ])
    late_fee_percentage = DecimalField(max_digits=5, decimal_places=2)
    late_fee_fixed_amount = MoneyField()
    late_fee_frequency = CharField(choices=[
        ('daily', 'Diario'),
        ('monthly', 'Mensual'),
        ('one_time', 'Una sola vez')
    ])
    grace_period_days = PositiveIntegerField(default=0)
```

### Ejemplo de Configuración

**Caproinsa SRL**:
```python
tenant = Tenant.objects.get(schema_name='caproinsa')
tenant.late_fee_type = 'percentage'
tenant.late_fee_percentage = Decimal('5.0')  # 5% mensual
tenant.late_fee_frequency = 'monthly'
tenant.grace_period_days = 5  # 5 días de gracia
```

### Comando de Cálculo

**Ubicación**: `backend/apps/loans/management/commands/calculate_late_fees.py`

**Ejecución manual**:
```bash
# Para un tenant específico
docker-compose exec backend python manage.py calculate_late_fees --tenant caproinsa

# Para todos los tenants
docker-compose exec backend python manage.py calculate_late_fees --all
```

**Ejecución automática con Celery Beat**:
```python
# config/celery.py
app.conf.beat_schedule = {
    'calculate-late-fees-daily': {
        'task': 'apps.loans.tasks.calculate_all_late_fees',
        'schedule': crontab(hour=1, minute=0),  # Todos los días a la 1 AM
    },
}
```

### Algoritmo de Cálculo

```python
def calculate_late_fee(schedule, tenant):
    # Verificar período de gracia
    days_overdue = (timezone.now().date() - schedule.due_date).days
    if days_overdue <= tenant.grace_period_days:
        return Money(0, schedule.loan.currency)

    effective_days = days_overdue - tenant.grace_period_days

    if tenant.late_fee_type == 'percentage':
        # Calcular mora como porcentaje del saldo pendiente
        balance = schedule.total_amount - schedule.paid_amount

        if tenant.late_fee_frequency == 'monthly':
            # Mora mensual compuesta
            months_overdue = effective_days / 30
            late_fee = balance * (tenant.late_fee_percentage / 100) * months_overdue

        elif tenant.late_fee_frequency == 'daily':
            # Mora diaria
            daily_rate = tenant.late_fee_percentage / 100 / 30
            late_fee = balance * daily_rate * effective_days

        elif tenant.late_fee_frequency == 'one_time':
            # Mora única
            late_fee = balance * (tenant.late_fee_percentage / 100)

    else:  # fixed amount
        if tenant.late_fee_frequency == 'one_time':
            late_fee = tenant.late_fee_fixed_amount.amount
        else:
            # Monto fijo por mes/día
            periods = effective_days if tenant.late_fee_frequency == 'daily' else (effective_days / 30)
            late_fee = tenant.late_fee_fixed_amount.amount * periods

    return Money(late_fee, schedule.loan.currency)
```

### Ejemplo de Cálculo

**Configuración**:
- Tipo: Porcentaje
- Tasa: 5% mensual
- Frecuencia: Mensual
- Gracia: 5 días

**Cuota vencida**:
- Fecha vencimiento: 2025-10-01
- Fecha actual: 2025-10-30
- Días vencidos: 29 días
- Días efectivos: 24 días (29 - 5 gracia)
- Balance: $10,000

**Cálculo**:
```
Meses vencidos = 24 / 30 = 0.8 meses
Mora = $10,000 × 5% × 0.8 = $400
```

---

## Sistema de Recordatorios

### Configuración de Recordatorios

Los recordatorios se generan automáticamente según el cronograma:

```python
REMINDER_SCHEDULE = {
    'pre_due': -3,      # 3 días antes
    'on_due': 0,        # Día de vencimiento
    'overdue_1': 1,     # 1 día después
    'overdue_7': 7,     # 7 días después
    'overdue_15': 15,   # 15 días después
    'overdue_30': 30,   # 30 días después
}
```

### Generación Automática

**Trigger**: Cuando se crea un cronograma de pago

```python
def create_reminders_for_schedule(schedule):
    for reminder_type, days_offset in REMINDER_SCHEDULE.items():
        reminder_date = schedule.due_date + timedelta(days=days_offset)

        CollectionReminder.objects.create(
            schedule=schedule,
            reminder_type=reminder_type,
            scheduled_date=datetime.combine(reminder_date, time(9, 0)),
            status='pending',
            message=generate_reminder_message(schedule, reminder_type)
        )
```

### Plantillas de Mensajes

```python
REMINDER_TEMPLATES = {
    'pre_due': """
Estimado/a {customer_name},

Le recordamos que tiene una cuota próxima a vencer:

Préstamo: {loan_number}
Cuota #{installment_number}
Monto: {amount}
Fecha de vencimiento: {due_date}

Para pagar, visite nuestra oficina o use nuestra app móvil.

Atentamente,
{company_name}
""",
    'overdue_7': """
Estimado/a {customer_name},

Su cuota del préstamo {loan_number} está vencida hace {days_overdue} días.

Monto original: {original_amount}
Mora acumulada: {late_fee}
Total a pagar: {total_due}

Por favor, regularice su situación lo antes posible.

Para asistencia, contáctenos al {phone}.

{company_name}
"""
}
```

### Envío de Recordatorios

**Task de Celery**:

```python
@shared_task
def send_pending_reminders():
    now = timezone.now()

    pending = CollectionReminder.objects.filter(
        status='pending',
        scheduled_date__lte=now
    )

    for reminder in pending:
        try:
            # Determinar canal
            if reminder.schedule.loan.customer.prefers_email:
                send_email_reminder(reminder)
            elif reminder.schedule.loan.customer.prefers_sms:
                send_sms_reminder(reminder)
            elif reminder.schedule.loan.customer.prefers_whatsapp:
                send_whatsapp_reminder(reminder)

            reminder.status = 'sent'
            reminder.sent_date = now
            reminder.save()

        except Exception as e:
            reminder.status = 'failed'
            reminder.delivery_status = str(e)
            reminder.save()
```

---

## Gestión de Contactos

### Registrar Contacto

**Frontend**: `/collections/contacts/new`

**API**:
```bash
POST /api/loans/collection-contacts/
{
  "loan": "loan-uuid",
  "contact_type": "phone_call",
  "outcome": "promise_to_pay",
  "promise_date": "2025-11-05",
  "promise_amount": "10000.00",
  "notes": "Cliente promete pagar cuota completa el viernes"
}
```

### Historial de Contactos

**API**:
```bash
GET /api/loans/collection-contacts/?loan={loan-uuid}
```

**Response**:
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid",
      "loan": "loan-uuid",
      "loan_number": "LN-2025-ABC",
      "customer_name": "Juan Pérez",
      "contact_date": "2025-10-30T10:30:00Z",
      "contact_type": "phone_call",
      "contact_type_display": "Llamada telefónica",
      "outcome": "promise_to_pay",
      "outcome_display": "Promesa de pago",
      "promise_date": "2025-11-05",
      "promise_amount": "10000.00",
      "notes": "Cliente promete pagar cuota completa el viernes",
      "contacted_by": {
        "id": "user-uuid",
        "name": "María González"
      }
    }
  ]
}
```

### Filtros de Contactos

```bash
# Por cobrador
GET /api/loans/collection-contacts/?contacted_by={user-uuid}

# Por resultado
GET /api/loans/collection-contacts/?outcome=promise_to_pay

# Por rango de fechas
GET /api/loans/collection-contacts/?date_from=2025-10-01&date_to=2025-10-31

# Por tipo
GET /api/loans/collection-contacts/?contact_type=phone_call
```

---

## Promesas de Pago

### Crear Promesa

Al registrar un contacto con outcome `promise_to_pay`, se genera una promesa:

```python
if contact.outcome == 'promise_to_pay' and contact.promise_date:
    # Crear recordatorio para la fecha prometida
    CollectionReminder.objects.create(
        schedule=contact.loan.get_next_overdue_schedule(),
        reminder_type='promise_follow_up',
        scheduled_date=contact.promise_date,
        message=f"Seguimiento de promesa de pago de {contact.customer_name}"
    )
```

### Seguimiento de Promesas

**Promesas para hoy**:
```bash
GET /api/loans/collections/promises_due_today/
```

**Response**:
```json
{
  "count": 12,
  "total_promised": "120000.00",
  "results": [
    {
      "contact": {
        "id": "uuid",
        "contact_date": "2025-10-25T14:20:00Z",
        "contacted_by": "María González"
      },
      "loan": {
        "id": "uuid",
        "loan_number": "LN-2025-ABC",
        "customer_name": "Juan Pérez",
        "customer_phone": "809-555-1234"
      },
      "promise_date": "2025-10-30",
      "promise_amount": "10000.00",
      "days_since_promise": 5,
      "fulfilled": false
    }
  ]
}
```

### Promesas Incumplidas

**API**:
```bash
GET /api/loans/collections/broken_promises/
```

Retorna contactos donde:
- `promise_date` < hoy
- No hay pago registrado en esa fecha
- `fulfilled` = false

### Marcar Promesa como Cumplida

Automático al registrar pago:

```python
def mark_promises_as_fulfilled(loan, payment):
    # Buscar promesas pendientes
    recent_contacts = loan.collection_contacts.filter(
        outcome='promise_to_pay',
        promise_date__lte=payment.payment_date,
        fulfilled=False
    )

    for contact in recent_contacts:
        contact.fulfilled = True
        contact.fulfillment_date = payment.payment_date
        contact.fulfillment_payment = payment
        contact.save()
```

---

## Dashboard de Cobranza

**Ubicación**: `/collections/`

### Métricas Principales

#### Pagos Vencidos
```python
overdue_schedules = LoanSchedule.objects.filter(
    due_date__lt=timezone.now().date(),
    status__in=['pending', 'overdue', 'partial']
)

stats = {
    'overdue_count': overdue_schedules.count(),
    'total_overdue': overdue_schedules.aggregate(
        total=Sum('balance')
    )['total']
}
```

#### Mora Acumulada
```python
total_late_fees = overdue_schedules.aggregate(
    total=Sum(F('late_fee_amount') - F('late_fee_paid'))
)['total']
```

#### Recordatorios Pendientes
```python
pending_reminders = CollectionReminder.objects.filter(
    status='pending'
).count()
```

#### Promesas de Hoy
```python
today = timezone.now().date()
promises_today = CollectionContact.objects.filter(
    outcome='promise_to_pay',
    promise_date=today,
    fulfilled=False
).count()
```

#### Promesas Incumplidas
```python
broken_promises = CollectionContact.objects.filter(
    outcome='promise_to_pay',
    promise_date__lt=today,
    fulfilled=False
).count()
```

### Acciones Urgentes

**Escalamiento requerido**:
```python
# Préstamos con mora > 90 días
escalation_required = Loan.objects.filter(
    status__in=['active', 'defaulted'],
    payment_schedules__due_date__lt=timezone.now().date() - timedelta(days=90),
    payment_schedules__status__in=['pending', 'overdue', 'partial']
).distinct()
```

---

## API Endpoints

### Dashboard Stats

```bash
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

### Pagos Vencidos

```bash
GET /api/loans/schedules/overdue/
```

### Recordatorios Pendientes

```bash
GET /api/loans/collections/pending_reminders/
```

### Préstamos Requiriendo Escalamiento

```bash
GET /api/loans/collections/requiring_escalation/
```

---

## Reportes de Cobranza

### Reporte de Gestión Diaria

```bash
GET /api/loans/collections/daily_report/?date=2025-10-30
```

**Response**:
```json
{
  "date": "2025-10-30",
  "contacts_made": 45,
  "by_outcome": {
    "promise_to_pay": 15,
    "payment_made": 10,
    "no_answer": 12,
    "refused_to_pay": 3,
    "will_contact_us": 5
  },
  "promises_made": 15,
  "total_promised": "150000.00",
  "payments_collected": 10,
  "total_collected": "100000.00"
}
```

### Reporte de Cartera Vencida

```bash
GET /api/loans/collections/aging_report/
```

**Response**:
```json
{
  "as_of_date": "2025-10-30",
  "total_portfolio": "50000000.00",
  "current": {
    "count": 400,
    "amount": "40000000.00",
    "percentage": "80.0"
  },
  "1-30_days": {
    "count": 50,
    "amount": "5000000.00",
    "percentage": "10.0"
  },
  "31-60_days": {
    "count": 30,
    "amount": "3000000.00",
    "percentage": "6.0"
  },
  "61-90_days": {
    "count": 15,
    "amount": "1500000.00",
    "percentage": "3.0"
  },
  "90+_days": {
    "count": 5,
    "amount": "500000.00",
    "percentage": "1.0"
  }
}
```

---

## Mejores Prácticas

### 1. Contacto Temprano
- Contactar ANTES del vencimiento (recordatorio -3 días)
- Establecer relación proactiva

### 2. Múltiples Canales
- Intentar por diferentes medios (teléfono, email, WhatsApp)
- Respetar preferencias del cliente

### 3. Documentación Completa
- Registrar TODOS los contactos
- Incluir detalles de conversación
- Registrar promesas con fecha y monto específico

### 4. Seguimiento de Promesas
- Revisar promesas diarias
- Contactar el día de la promesa
- Marcar como cumplida/incumplida

### 5. Escalamiento Oportuno
- 30 días: Gerente de cobranza
- 60 días: Gerente de crédito
- 90 días: Legal/Externa

---

## Próximas Funcionalidades

- [ ] Integración con SMS gateway (Twilio)
- [ ] Integración con WhatsApp Business API
- [ ] Bot de cobranza automatizado
- [ ] Scoring de comportamiento de pago
- [ ] Machine learning para predecir incumplimiento
- [ ] App móvil para cobradores de campo
- [ ] Grabación de llamadas
- [ ] Geolocalización de visitas

---

**Última actualización**: 2025-10-30
