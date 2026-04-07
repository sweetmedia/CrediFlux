# Módulo de Préstamos (Loans)

## Descripción General

El módulo de préstamos es el núcleo de CrediFlux, encargado de gestionar todo el ciclo de vida de un préstamo desde la solicitud inicial hasta el pago completo.

## Índice

- [Modelos](#modelos)
- [Tipos de Préstamos](#tipos-de-préstamos)
- [Workflow de Aprobación](#workflow-de-aprobación)
- [Cálculo de Amortización](#cálculo-de-amortización)
- [API Endpoints](#api-endpoints)
- [Casos de Uso](#casos-de-uso)

---

## Modelos

### Loan (Préstamo)

**Ubicación**: `backend/apps/loans/models.py`

**Campos principales**:

```python
class Loan(BaseModel):
    loan_number = CharField(max_length=50, unique=True)
    customer = ForeignKey(Customer)
    loan_type = CharField(choices=LOAN_TYPE_CHOICES)
    status = CharField(choices=LOAN_STATUS_CHOICES)
    principal_amount = MoneyField()
    interest_rate = DecimalField(max_digits=5, decimal_places=2)
    term_months = PositiveIntegerField()
    payment_frequency = CharField(choices=PAYMENT_FREQUENCY_CHOICES)
    disbursement_date = DateField()
    first_payment_date = DateField()
    maturity_date = DateField()
    outstanding_balance = MoneyField()
```

**Estados del préstamo**:

| Estado | Descripción | Transiciones Permitidas |
|--------|-------------|------------------------|
| `draft` | Borrador, sin completar | → `pending` |
| `pending` | Esperando aprobación | → `active`, `rejected` |
| `active` | Aprobado y desembolsado | → `paid`, `defaulted`, `written_off` |
| `defaulted` | En mora grave (90+ días) | → `paid`, `written_off` |
| `paid` | Completamente pagado | (Estado final) |
| `rejected` | Rechazado | (Estado final) |
| `written_off` | Castigado | (Estado final) |

### LoanSchedule (Cronograma de Pagos)

**Campos principales**:

```python
class LoanSchedule(BaseModel):
    loan = ForeignKey(Loan, related_name='payment_schedules')
    installment_number = PositiveIntegerField()
    due_date = DateField()
    total_amount = MoneyField()
    principal_amount = MoneyField()
    interest_amount = MoneyField()
    paid_amount = MoneyField(default=Money(0, 'DOP'))
    status = CharField(choices=SCHEDULE_STATUS_CHOICES)
    late_fee_amount = MoneyField(default=Money(0, 'DOP'))
    late_fee_paid = MoneyField(default=Money(0, 'DOP'))
```

**Estados del cronograma**:

- `pending`: Pendiente de pago
- `partial`: Parcialmente pagado
- `paid`: Completamente pagado
- `overdue`: Vencido con mora calculada

### LoanCollateral (Garantía)

```python
class LoanCollateral(BaseModel):
    loan = ForeignKey(Loan, related_name='collaterals')
    collateral_type = CharField(choices=COLLATERAL_TYPE_CHOICES)
    description = TextField()
    estimated_value = MoneyField()
    ownership_document = FileField()
```

**Tipos de garantía**:

- `property`: Propiedad inmueble
- `vehicle`: Vehículo
- `equipment`: Equipo/Maquinaria
- `jewelry`: Joyas
- `other`: Otro

---

## Tipos de Préstamos

### 1. Personal

**Características**:
- Monto: Hasta $500,000 DOP
- Plazo: 6-60 meses
- Tasa: 15-25% anual
- Garantía: No requerida para montos < $100,000

**Uso común**: Gastos personales, consolidación de deudas, emergencias

### 2. Auto

**Características**:
- Monto: Hasta $2,000,000 DOP
- Plazo: 12-84 meses
- Tasa: 12-18% anual
- Garantía: El propio vehículo

**Requisitos especiales**:
- Tasación del vehículo
- Seguro obligatorio
- Transferencia de propiedad

### 3. Hipotecario

**Características**:
- Monto: Hasta $10,000,000 DOP
- Plazo: 60-360 meses
- Tasa: 8-12% anual
- Garantía: Hipoteca sobre la propiedad

**Requisitos especiales**:
- Avalúo profesional
- Estudio de títulos
- Seguro de vida e incendio

### 4. Negocio

**Características**:
- Monto: Variable según plan de negocio
- Plazo: 12-120 meses
- Tasa: 14-22% anual
- Garantía: Activos del negocio

**Requisitos especiales**:
- Plan de negocio
- Estados financieros
- Proyecciones de flujo de caja

### 5. Estudiantil

**Características**:
- Monto: Hasta $1,000,000 DOP
- Plazo: 12-120 meses
- Tasa: 6-10% anual (subsidiada)
- Garantía: Aval solidario

**Requisitos especiales**:
- Carta de admisión
- Constancia de matrícula
- Fiador solidario

---

## Workflow de Aprobación

### Diagrama de Flujo

```
┌─────────────┐
│   Borrador  │ (Cliente inicia solicitud)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Pendiente  │ (Oficial de crédito revisa)
└──────┬──────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
  ┌─────────┐  ┌──────────┐  ┌──────────┐
  │ Activo  │  │Rechazado │  │Necesita  │
  │         │  │          │  │más info  │
  └────┬────┘  └──────────┘  └────┬─────┘
       │                           │
       │                           └───┐
       │                               │
       ▼                               ▼
  ┌─────────┐                    ┌─────────┐
  │  Pagado │                    │Pendiente│
  └─────────┘                    └─────────┘
       │
       ▼
  (Castigado si mora > 180 días)
```

### Proceso Detallado

#### 1. Creación de Solicitud (`draft` → `pending`)

**Responsable**: Cliente o Oficial de Crédito

**Acciones**:
1. Seleccionar cliente
2. Elegir tipo de préstamo
3. Definir monto y plazo
4. Calcular cuota estimada
5. Adjuntar documentación

**Validaciones**:
- Cliente debe existir y estar activo
- Monto dentro de límites del tipo de préstamo
- Plazo válido para el tipo de préstamo
- Documentación KYC completa

**API Endpoint**:
```bash
POST /api/loans/
{
  "customer": "uuid",
  "loan_type": "personal",
  "principal_amount": "200000.00",
  "interest_rate": "18.00",
  "term_months": 24,
  "payment_frequency": "monthly",
  "purpose": "Consolidación de deudas"
}
```

#### 2. Revisión y Aprobación (`pending` → `active`)

**Responsable**: Oficial de Crédito / Gerente de Crédito

**Acciones**:
1. Verificar información del cliente
2. Revisar historial crediticio
3. Validar capacidad de pago
4. Evaluar garantías
5. Calcular relación deuda-ingreso
6. Aprobar o rechazar

**Cálculo de capacidad de pago**:
```python
monthly_income = customer.monthly_income
monthly_obligations = customer.calculate_monthly_obligations()
available_income = monthly_income - monthly_obligations
debt_to_income_ratio = monthly_obligations / monthly_income

# Regla general: DTI < 40%
if debt_to_income_ratio > 0.40:
    # Rechazar o solicitar más garantías
```

**API Endpoint**:
```bash
POST /api/loans/{loan_id}/approve/
{
  "notes": "Cliente cumple con todos los requisitos. DTI: 32%"
}
```

#### 3. Desembolso (`active` - inicio de pagos)

**Responsable**: Gerente de Operaciones / Tesorero

**Acciones automáticas**:
1. Cambiar status a `active`
2. Registrar fecha de desembolso
3. Generar cronograma de pagos
4. Calcular primera fecha de pago
5. Crear registro contable (si aplica)

**Generación de Cronograma**:

El sistema calcula automáticamente el cronograma usando el método de amortización francesa (cuota fija):

```python
def generate_payment_schedule(loan):
    monthly_rate = loan.interest_rate / 100 / 12
    num_payments = loan.term_months

    # Calcular cuota fija
    pmt = loan.principal_amount * (
        monthly_rate * (1 + monthly_rate) ** num_payments
    ) / (
        (1 + monthly_rate) ** num_payments - 1
    )

    balance = loan.principal_amount

    for i in range(1, num_payments + 1):
        interest = balance * monthly_rate
        principal = pmt - interest
        balance -= principal

        LoanSchedule.objects.create(
            loan=loan,
            installment_number=i,
            due_date=calculate_due_date(i),
            total_amount=pmt,
            principal_amount=principal,
            interest_amount=interest
        )
```

**API Endpoint**:
```bash
POST /api/loans/{loan_id}/disburse/
```

---

## Cálculo de Amortización

### Método Francés (Cuota Fija)

**Fórmula**:

```
Cuota = P × [r(1 + r)^n] / [(1 + r)^n - 1]

Donde:
P = Principal (monto del préstamo)
r = Tasa de interés mensual (tasa_anual / 12 / 100)
n = Número de pagos
```

**Ejemplo**:

```
Principal: $100,000 DOP
Tasa: 18% anual = 1.5% mensual
Plazo: 12 meses

Cuota = 100000 × [0.015(1.015)^12] / [(1.015)^12 - 1]
Cuota = 100000 × 0.01946 / 0.19562
Cuota = $9,168.46 DOP
```

**Cronograma de ejemplo**:

| Cuota | Saldo Inicial | Interés | Capital | Cuota | Saldo Final |
|-------|---------------|---------|---------|-------|-------------|
| 1 | $100,000.00 | $1,500.00 | $7,668.46 | $9,168.46 | $92,331.54 |
| 2 | $92,331.54 | $1,384.97 | $7,783.49 | $9,168.46 | $84,548.05 |
| 3 | $84,548.05 | $1,268.22 | $7,900.24 | $9,168.46 | $76,647.81 |
| ... | ... | ... | ... | ... | ... |
| 12 | $9,033.96 | $135.51 | $9,032.95 | $9,168.46 | $1.01 |

### Frecuencias de Pago

#### Mensual (monthly)
- Cuota cada 30 días
- Total de cuotas = term_months

#### Quincenal (biweekly)
- Cuota cada 15 días
- Total de cuotas = term_months × 2
- Tasa ajustada = interest_rate / 24

#### Semanal (weekly)
- Cuota cada 7 días
- Total de cuotas = term_months × 4.33
- Tasa ajustada = interest_rate / 52

---

## API Endpoints

### Listar Préstamos

```bash
GET /api/loans/
```

**Query Parameters**:
- `status`: Filtrar por estado (active, pending, etc.)
- `customer`: UUID del cliente
- `loan_type`: Tipo de préstamo
- `search`: Buscar por loan_number o customer name
- `ordering`: Ordenar por campo (-created_at, disbursement_date)

**Response**:
```json
{
  "count": 150,
  "next": "http://api/loans/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "loan_number": "LN-2025-ABC123",
      "customer": {
        "id": "uuid",
        "name": "Juan Pérez",
        "email": "juan@example.com"
      },
      "loan_type": "personal",
      "status": "active",
      "principal_amount": "200000.00",
      "outstanding_balance": "150000.00",
      "interest_rate": "18.00",
      "term_months": 24,
      "payment_frequency": "monthly",
      "disbursement_date": "2025-01-15",
      "maturity_date": "2027-01-15",
      "days_overdue": 5,
      "is_overdue": true
    }
  ]
}
```

### Crear Préstamo

```bash
POST /api/loans/
Content-Type: application/json
Authorization: Bearer {token}

{
  "customer": "customer-uuid",
  "loan_type": "personal",
  "principal_amount": "200000.00",
  "interest_rate": "18.00",
  "term_months": 24,
  "payment_frequency": "monthly",
  "purpose": "Consolidación de deudas"
}
```

**Validaciones**:
- `customer` debe existir
- `principal_amount` > 0
- `interest_rate` entre 0.1 y 100
- `term_months` > 0
- `payment_frequency` en choices válidos

### Detalle de Préstamo

```bash
GET /api/loans/{id}/
```

**Response incluye**:
- Información completa del préstamo
- Cliente con datos completos
- Cronograma de pagos (`payment_schedules`)
- Historial de pagos recientes (`recent_payments`)
- Garantías (`collaterals`)
- Métricas calculadas (days_overdue, next_payment_date)

### Aprobar Préstamo

```bash
POST /api/loans/{id}/approve/
{
  "notes": "Aprobado por DTI favorable"
}
```

**Permisos**: `can_approve_loan`

**Acciones**:
1. Cambia status de `pending` → `approved`
2. Registra `approved_by` y `approved_at`
3. Guarda notas de aprobación

### Desembolsar Préstamo

```bash
POST /api/loans/{id}/disburse/
```

**Permisos**: `can_disburse_loan`

**Acciones**:
1. Cambia status a `active`
2. Registra `disbursement_date`
3. Calcula `first_payment_date` y `maturity_date`
4. Genera cronograma completo de pagos
5. Inicializa `outstanding_balance`

### Rechazar Préstamo

```bash
POST /api/loans/{id}/reject/
{
  "reason": "DTI superior al 40%"
}
```

**Permisos**: `can_reject_loan`

### Estadísticas de Préstamos

```bash
GET /api/loans/statistics/
```

**Response**:
```json
{
  "total_loans": 500,
  "active_loans": 320,
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

## Casos de Uso

### Caso 1: Préstamo Personal Simple

**Escenario**: Juan Pérez necesita $100,000 para consolidar deudas

**Pasos**:

1. **Crear cliente** (si no existe):
```bash
POST /api/loans/customers/
{
  "first_name": "Juan",
  "last_name": "Pérez",
  "email": "juan@example.com",
  "phone": "809-555-1234",
  "id_type": "cedula",
  "id_number": "001-1234567-8",
  "monthly_income": "50000.00"
}
```

2. **Crear solicitud de préstamo**:
```bash
POST /api/loans/
{
  "customer": "customer-uuid",
  "loan_type": "personal",
  "principal_amount": "100000.00",
  "interest_rate": "18.00",
  "term_months": 12,
  "payment_frequency": "monthly",
  "purpose": "Consolidación de deudas"
}
```

3. **Aprobar**:
```bash
POST /api/loans/{loan-uuid}/approve/
{
  "notes": "Cliente tiene historial crediticio positivo"
}
```

4. **Desembolsar**:
```bash
POST /api/loans/{loan-uuid}/disburse/
```

5. **Resultado**: Cronograma de 12 cuotas de ~$9,168.46 c/u

### Caso 2: Préstamo de Auto con Garantía

**Escenario**: María quiere comprar un vehículo de $800,000

**Pasos adicionales**:

1. Crear préstamo tipo `auto`
2. **Agregar garantía**:
```bash
POST /api/loans/{loan-uuid}/collaterals/
{
  "collateral_type": "vehicle",
  "description": "Toyota Corolla 2020, VIN: 123456789",
  "estimated_value": "900000.00",
  "ownership_document": [file upload]
}
```

3. Aprobar con validación de tasación
4. Desembolsar con transferencia de título

### Caso 3: Préstamo con Pago Anticipado

**Escenario**: Cliente desea pagar por adelantado

**Implementación**:
```python
# Al registrar pago
payment = LoanPayment.objects.create(
    loan=loan,
    amount=Money(50000, 'DOP'),
    payment_method='bank_transfer'
)

# El sistema automáticamente:
# 1. Aplica a mora si existe
# 2. Aplica a intereses de cuotas vencidas
# 3. Aplica a capital de cuotas vencidas
# 4. Si sobra dinero, aplica a próximas cuotas
```

---

## Próximas Funcionalidades

- [ ] Refinanciamiento de préstamos
- [ ] Reestructuración de deuda
- [ ] Préstamos con período de gracia
- [ ] Comisiones por apertura
- [ ] Seguros opcionales
- [ ] Simulador de préstamos en frontend
- [ ] Firma electrónica de contratos
- [ ] Integración con burós de crédito

---

## Troubleshooting

### El cronograma no se genera

**Causa**: Préstamo no ha sido desembolsado

**Solución**: Ejecutar `POST /api/loans/{id}/disburse/`

### Saldos no cuadran

**Causa**: Pagos aplicados manualmente sin actualizar balances

**Solución**:
```bash
docker-compose exec backend python manage.py shell

from apps.loans.models import Loan
loan = Loan.objects.get(id='uuid')
loan.recalculate_balance()
```

### Cuota calculada incorrecta

**Causa**: Frecuencia de pago no considerada en cálculo de tasa

**Solución**: Verificar que la tasa se ajusta según frecuencia:
- Monthly: rate/12
- Biweekly: rate/24
- Weekly: rate/52

---

**Última actualización**: 2025-10-30
