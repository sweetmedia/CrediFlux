# Módulo de Clientes (Customers)

## Descripción General

El módulo de clientes gestiona toda la información de los clientes del sistema, incluyendo datos personales, información crediticia, documentación KYC (Know Your Customer) y el historial de préstamos.

## Índice

- [Modelo Customer](#modelo-customer)
- [KYC y Documentación](#kyc-y-documentación)
- [Credit Scoring](#credit-scoring)
- [Historial Crediticio](#historial-crediticio)
- [API Endpoints](#api-endpoints)
- [Casos de Uso](#casos-de-uso)

---

## Modelo Customer

**Ubicación**: `backend/apps/loans/models.py`

```python
class Customer(BaseModel):
    # Información Personal
    first_name = CharField(max_length=100)
    last_name = CharField(max_length=100)
    middle_name = CharField(max_length=100, blank=True)
    email = EmailField(unique=True)
    phone = CharField(max_length=20)
    alternate_phone = CharField(max_length=20, blank=True)

    # Identificación
    id_type = CharField(choices=ID_TYPE_CHOICES)
    id_number = CharField(max_length=50, unique=True)
    date_of_birth = DateField()
    place_of_birth = CharField(max_length=200, blank=True)
    nationality = CharField(max_length=50)

    # Dirección
    address = TextField()
    city = CharField(max_length=100)
    state_province = CharField(max_length=100)
    postal_code = CharField(max_length=20)
    country = CharField(max_length=50, default='DO')

    # Información Financiera
    employment_status = CharField(choices=EMPLOYMENT_STATUS_CHOICES)
    employer_name = CharField(max_length=200, blank=True)
    employer_phone = CharField(max_length=20, blank=True)
    monthly_income = MoneyField()
    other_income = MoneyField(default=Money(0, 'DOP'))

    # Información Crediticia
    credit_score = IntegerField(null=True, blank=True)
    risk_category = CharField(choices=RISK_CATEGORY_CHOICES)

    # Estado
    status = CharField(choices=CUSTOMER_STATUS_CHOICES)
    is_blacklisted = BooleanField(default=False)
    blacklist_reason = TextField(blank=True)

    # Referencias
    reference1_name = CharField(max_length=200, blank=True)
    reference1_phone = CharField(max_length=20, blank=True)
    reference1_relationship = CharField(max_length=100, blank=True)
    reference2_name = CharField(max_length=200, blank=True)
    reference2_phone = CharField(max_length=20, blank=True)
    reference2_relationship = CharField(max_length=100, blank=True)
```

### Campos Importantes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_type` | Choice | Tipo de identificación (cédula, pasaporte, RNC) |
| `id_number` | String | Número único de identificación |
| `employment_status` | Choice | Estado laboral |
| `monthly_income` | Money | Ingreso mensual |
| `credit_score` | Integer | Puntaje crediticio (300-850) |
| `risk_category` | Choice | Categoría de riesgo (low, medium, high) |
| `status` | Choice | Estado del cliente (active, inactive, blacklisted) |

### Tipos de Identificación

```python
ID_TYPE_CHOICES = [
    ('cedula', 'Cédula de Identidad'),
    ('passport', 'Pasaporte'),
    ('rnc', 'RNC (Registro Nacional de Contribuyentes)'),
    ('other', 'Otro'),
]
```

### Estados de Empleo

```python
EMPLOYMENT_STATUS_CHOICES = [
    ('employed', 'Empleado'),
    ('self_employed', 'Trabajador Independiente'),
    ('business_owner', 'Dueño de Negocio'),
    ('unemployed', 'Desempleado'),
    ('retired', 'Jubilado'),
    ('student', 'Estudiante'),
]
```

### Categorías de Riesgo

```python
RISK_CATEGORY_CHOICES = [
    ('low', 'Riesgo Bajo'),
    ('medium', 'Riesgo Medio'),
    ('high', 'Riesgo Alto'),
]
```

---

## KYC y Documentación

### CustomerDocument

**Modelo para documentos adjuntos**:

```python
class CustomerDocument(BaseModel):
    customer = ForeignKey(Customer, related_name='documents')
    document_type = CharField(choices=DOCUMENT_TYPE_CHOICES)
    file = FileField(upload_to='customer_documents/')
    uploaded_date = DateTimeField(auto_now_add=True)
    verified = BooleanField(default=False)
    verified_by = ForeignKey(User, null=True, blank=True)
    verified_date = DateTimeField(null=True, blank=True)
    notes = TextField(blank=True)
```

### Tipos de Documentos

```python
DOCUMENT_TYPE_CHOICES = [
    ('id_front', 'Cédula/ID (Frente)'),
    ('id_back', 'Cédula/ID (Reverso)'),
    ('proof_of_income', 'Comprobante de Ingresos'),
    ('bank_statement', 'Estado de Cuenta Bancario'),
    ('utility_bill', 'Factura de Servicios (Prueba de Domicilio)'),
    ('employment_letter', 'Carta de Trabajo'),
    ('tax_return', 'Declaración de Impuestos'),
    ('business_license', 'Licencia de Negocio'),
    ('other', 'Otro'),
]
```

### Proceso KYC

**Nivel 1 - Básico** (requerido para todos):
- ✅ Cédula o pasaporte (frente y reverso)
- ✅ Comprobante de domicilio
- ✅ Referencias personales (2 mínimo)

**Nivel 2 - Estándar** (préstamos > $100,000):
- ✅ Nivel 1 completo
- ✅ Comprobante de ingresos
- ✅ Estado de cuenta bancario (últimos 3 meses)
- ✅ Verificación de empleo

**Nivel 3 - Avanzado** (préstamos > $500,000):
- ✅ Nivel 2 completo
- ✅ Declaración de impuestos
- ✅ Estados financieros (si es negocio)
- ✅ Licencias profesionales/comerciales
- ✅ Verificación de referencias

### API para Documentos

**Subir Documento**:

```bash
POST /api/loans/customers/{customer_id}/documents/
Content-Type: multipart/form-data

document_type: id_front
file: [binary data]
```

**Listar Documentos**:

```bash
GET /api/loans/customers/{customer_id}/documents/
```

**Verificar Documento**:

```bash
POST /api/loans/customers/{customer_id}/documents/{doc_id}/verify/
{
  "verified": true,
  "notes": "Documento verificado correctamente"
}
```

---

## Credit Scoring

### Cálculo de Score

El sistema calcula automáticamente un credit score basado en múltiples factores:

```python
def calculate_credit_score(customer):
    """
    Calcula credit score de 300 a 850
    Similar al FICO score
    """
    score = 300  # Base score

    # Factor 1: Historial de Pagos (35%)
    payment_history_score = calculate_payment_history(customer)
    score += int(payment_history_score * 0.35 * 550)

    # Factor 2: Deuda Actual (30%)
    debt_ratio_score = calculate_debt_ratio(customer)
    score += int(debt_ratio_score * 0.30 * 550)

    # Factor 3: Historial Crediticio (15%)
    credit_history_score = calculate_credit_history_length(customer)
    score += int(credit_history_score * 0.15 * 550)

    # Factor 4: Nuevos Créditos (10%)
    new_credit_score = calculate_new_credit_inquiries(customer)
    score += int(new_credit_score * 0.10 * 550)

    # Factor 5: Mix de Crédito (10%)
    credit_mix_score = calculate_credit_mix(customer)
    score += int(credit_mix_score * 0.10 * 550)

    return min(850, max(300, score))
```

### Factores del Score

#### 1. Historial de Pagos (35%)

```python
def calculate_payment_history(customer):
    loans = customer.loans.filter(status__in=['active', 'paid'])
    if not loans.exists():
        return 0.5  # Neutral si no hay historial

    total_payments = 0
    on_time_payments = 0

    for loan in loans:
        for payment in loan.payments.all():
            total_payments += 1
            if payment.payment_date <= payment.schedule.due_date:
                on_time_payments += 1

    if total_payments == 0:
        return 0.5

    return on_time_payments / total_payments
```

#### 2. Ratio de Deuda (30%)

```python
def calculate_debt_ratio(customer):
    total_debt = customer.loans.filter(
        status='active'
    ).aggregate(
        total=Sum('outstanding_balance')
    )['total'] or 0

    monthly_payment = customer.calculate_monthly_obligations()
    debt_to_income = monthly_payment / customer.monthly_income

    # Mejor score si DTI < 20%
    if debt_to_income < 0.20:
        return 1.0
    elif debt_to_income < 0.30:
        return 0.8
    elif debt_to_income < 0.40:
        return 0.6
    elif debt_to_income < 0.50:
        return 0.4
    else:
        return 0.2
```

#### 3. Longitud de Historial (15%)

```python
def calculate_credit_history_length(customer):
    first_loan = customer.loans.order_by('created_at').first()
    if not first_loan:
        return 0

    months = (timezone.now().date() - first_loan.created_at.date()).days / 30

    # Mejor score con más historial
    if months >= 60:  # 5+ años
        return 1.0
    elif months >= 36:  # 3-5 años
        return 0.8
    elif months >= 24:  # 2-3 años
        return 0.6
    elif months >= 12:  # 1-2 años
        return 0.4
    else:
        return 0.2
```

### Interpretación del Score

| Rango | Categoría | Descripción |
|-------|-----------|-------------|
| 800-850 | Excelente | Cliente ideal, tasa preferencial |
| 740-799 | Muy Bueno | Bajo riesgo, tasas favorables |
| 670-739 | Bueno | Riesgo aceptable, tasas estándar |
| 580-669 | Regular | Riesgo medio, tasas más altas |
| 300-579 | Pobre | Alto riesgo, requiere garantías |

### Actualizar Score

```python
# Manual
customer = Customer.objects.get(id='uuid')
customer.credit_score = customer.calculate_credit_score()
customer.save()

# Automático con signal
@receiver(post_save, sender=LoanPayment)
def update_customer_score(sender, instance, **kwargs):
    customer = instance.loan.customer
    customer.credit_score = customer.calculate_credit_score()
    customer.save()
```

---

## Historial Crediticio

### Ver Historial

```bash
GET /api/loans/customers/{id}/credit_history/
```

**Response**:

```json
{
  "customer": {
    "id": "uuid",
    "name": "Juan Pérez",
    "credit_score": 720
  },
  "summary": {
    "total_loans": 5,
    "active_loans": 2,
    "paid_loans": 3,
    "total_borrowed": "500000.00",
    "total_repaid": "350000.00",
    "outstanding_balance": "150000.00",
    "on_time_payment_rate": "95.5"
  },
  "loans": [
    {
      "id": "uuid",
      "loan_number": "LN-2025-ABC",
      "loan_type": "personal",
      "principal_amount": "100000.00",
      "disbursement_date": "2025-01-15",
      "status": "active",
      "outstanding_balance": "75000.00",
      "days_overdue": 0,
      "payment_performance": "excellent"
    }
  ],
  "payment_behavior": {
    "average_days_to_pay": 2,
    "late_payments_count": 3,
    "on_time_payments_count": 45,
    "missed_payments_count": 0
  }
}
```

---

## API Endpoints

### Listar Clientes

```bash
GET /api/loans/customers/
```

**Query Parameters**:
- `search`: Buscar por nombre, email, ID
- `employment_status`: Filtrar por empleo
- `risk_category`: Filtrar por categoría de riesgo
- `status`: active, inactive, blacklisted
- `ordering`: -created_at, first_name, credit_score

### Crear Cliente

```bash
POST /api/loans/customers/
{
  "first_name": "María",
  "last_name": "González",
  "email": "maria@example.com",
  "phone": "809-555-5678",
  "id_type": "cedula",
  "id_number": "001-9876543-2",
  "date_of_birth": "1990-03-20",
  "address": "Calle Principal #123",
  "city": "Santo Domingo",
  "state_province": "Distrito Nacional",
  "postal_code": "10100",
  "country": "DO",
  "monthly_income": "75000.00",
  "employment_status": "employed",
  "employer_name": "ABC Company",
  "reference1_name": "Pedro Martínez",
  "reference1_phone": "809-555-1111",
  "reference1_relationship": "Amigo"
}
```

### Actualizar Cliente

```bash
PATCH /api/loans/customers/{id}/
{
  "phone": "809-555-NEW",
  "monthly_income": "80000.00"
}
```

### Detalle de Cliente

```bash
GET /api/loans/customers/{id}/
```

### Préstamos del Cliente

```bash
GET /api/loans/customers/{id}/loans/
```

### Estadísticas del Cliente

```bash
GET /api/loans/customers/{id}/statistics/
```

**Response**:

```json
{
  "total_loans": 5,
  "active_loans": 2,
  "total_borrowed": "500000.00",
  "total_repaid": "350000.00",
  "current_debt": "150000.00",
  "monthly_obligation": "12000.00",
  "debt_to_income_ratio": "16.0",
  "payment_performance": {
    "on_time_rate": "95.5",
    "average_days_late": "1.2"
  }
}
```

---

## Casos de Uso

### Caso 1: Registro de Nuevo Cliente

```bash
# 1. Crear perfil básico
POST /api/loans/customers/
{
  "first_name": "Ana",
  "last_name": "Rodríguez",
  "email": "ana@example.com",
  "phone": "809-555-7890",
  "id_type": "cedula",
  "id_number": "001-1112223-3",
  "date_of_birth": "1988-07-10",
  "address": "Av. Venezuela #456",
  "city": "Santiago",
  "monthly_income": "60000.00",
  "employment_status": "employed",
  "employer_name": "XYZ Corp"
}

# 2. Subir documentos KYC
POST /api/loans/customers/{id}/documents/
[Upload cédula frontal]

POST /api/loans/customers/{id}/documents/
[Upload cédula reverso]

POST /api/loans/customers/{id}/documents/
[Upload comprobante de ingresos]

# 3. Verificar documentos
POST /api/loans/customers/{id}/documents/{doc_id}/verify/

# 4. Cliente listo para solicitar préstamo
```

### Caso 2: Actualización de Información

```bash
# Cliente cambia de trabajo
PATCH /api/loans/customers/{id}/
{
  "employer_name": "Nueva Empresa SA",
  "employer_phone": "809-555-NEW",
  "monthly_income": "85000.00"
}

# Subir nuevo comprobante
POST /api/loans/customers/{id}/documents/
{
  "document_type": "employment_letter",
  "file": [nuevo documento]
}
```

### Caso 3: Evaluación Crediticia

```python
# Backend - al revisar solicitud de préstamo
customer = Customer.objects.get(id='uuid')

# Verificar KYC
if not customer.is_kyc_complete():
    return "Documentación KYC incompleta"

# Verificar score
credit_score = customer.credit_score or customer.calculate_credit_score()
if credit_score < 580:
    return "Score crediticio muy bajo, requiere garantías adicionales"

# Verificar DTI
dti = customer.calculate_debt_to_income_ratio()
if dti > 0.40:
    return "Ratio deuda-ingreso muy alto (DTI: {dti}%)"

# Verificar blacklist
if customer.is_blacklisted:
    return f"Cliente en lista negra: {customer.blacklist_reason}"

# Cliente aprobado para evaluación
```

### Caso 4: Cliente en Lista Negra

```bash
# Agregar a blacklist
PATCH /api/loans/customers/{id}/
{
  "is_blacklisted": true,
  "blacklist_reason": "Fraude detectado en documentación",
  "status": "blacklisted"
}

# Intentar crear préstamo fallará
POST /api/loans/
{
  "customer": "blacklisted-customer-id",
  ...
}

# Response: 400 Bad Request
{
  "error": "Cliente en lista negra: Fraude detectado en documentación"
}
```

---

## Validaciones

### Email Único

```python
# Al crear/actualizar
customer = Customer.objects.filter(email='duplicate@example.com').exists()
if customer:
    raise ValidationError("Email ya existe")
```

### ID Number Único

```python
customer = Customer.objects.filter(
    id_number='001-1234567-8'
).exclude(id=current_customer_id).exists()

if customer:
    raise ValidationError("Número de identificación ya registrado")
```

### Formato de Cédula (Dominicana)

```python
import re

def validate_cedula(cedula):
    # Formato: XXX-XXXXXXX-X
    pattern = r'^\d{3}-\d{7}-\d{1}$'
    if not re.match(pattern, cedula):
        raise ValidationError("Formato de cédula inválido")
```

### Edad Mínima

```python
from django.utils import timezone
from datetime import timedelta

def validate_age(date_of_birth):
    today = timezone.now().date()
    age = (today - date_of_birth).days / 365.25

    if age < 18:
        raise ValidationError("Cliente debe ser mayor de 18 años")
    if age > 100:
        raise ValidationError("Fecha de nacimiento inválida")
```

---

## Mejores Prácticas

### 1. Actualizar Información Regularmente

Solicitar actualización de datos cada:
- 6 meses para clientes activos
- 12 meses para clientes sin préstamos

### 2. Re-verificar KYC

Re-verificar documentación si:
- Han pasado más de 2 años
- Cliente solicita monto significativamente mayor
- Cambios importantes en información

### 3. Monitorear Score

```python
# Recalcular score después de cada pago
@receiver(post_save, sender=LoanPayment)
def update_score_on_payment(sender, instance, **kwargs):
    customer = instance.loan.customer
    old_score = customer.credit_score
    new_score = customer.calculate_credit_score()

    if abs(new_score - old_score) >= 10:
        # Notificar cambio significativo
        notify_score_change(customer, old_score, new_score)

    customer.credit_score = new_score
    customer.save()
```

---

## Próximas Funcionalidades

- [ ] Integración con burós de crédito (DataCrédito, TransUnion)
- [ ] Verificación biométrica (facial, huella)
- [ ] OCR automático de documentos
- [ ] Verificación automática de empleo
- [ ] Score de comportamiento (behavioral scoring)
- [ ] Alertas de cambio de riesgo
- [ ] Portal de cliente para auto-actualización

---

**Última actualización**: 2025-10-30
