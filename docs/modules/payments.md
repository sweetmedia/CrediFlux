# Módulo de Pagos (Payments)

## Descripción General

El módulo de pagos gestiona todos los registros de pagos realizados por clientes, aplicando automáticamente los montos a las cuotas vencidas con prioridad inteligente: Mora → Interés → Capital.

## Índice

- [Modelo LoanPayment](#modelo-loanpayment)
- [Distribución Automática](#distribución-automática-de-pagos)
- [Métodos de Pago](#métodos-de-pago)
- [Reversión de Pagos](#reversión-de-pagos)
- [API Endpoints](#api-endpoints)
- [Casos de Uso](#casos-de-uso)

---

## Modelo LoanPayment

**Ubicación**: `backend/apps/loans/models.py`

```python
class LoanPayment(BaseModel):
    payment_number = CharField(max_length=50, unique=True)
    loan = ForeignKey(Loan, related_name='payments')
    schedule = ForeignKey(LoanSchedule, null=True, blank=True)

    payment_date = DateField()
    amount = MoneyField()

    # Distribución del pago
    principal_paid = MoneyField(default=Money(0, 'DOP'))
    interest_paid = MoneyField(default=Money(0, 'DOP'))
    late_fee_paid = MoneyField(default=Money(0, 'DOP'))

    payment_method = CharField(choices=PAYMENT_METHOD_CHOICES)
    reference_number = CharField(max_length=100, blank=True)

    status = CharField(choices=PAYMENT_STATUS_CHOICES)
    notes = TextField(blank=True)
    receipt = FileField(upload_to='receipts/', blank=True)
```

### Campos Importantes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `payment_number` | String | Número único autogenerado (PAY-2025-XXXXXX) |
| `loan` | FK | Préstamo al que se aplica el pago |
| `schedule` | FK | Cuota específica (opcional, se selecciona automáticamente) |
| `amount` | Money | Monto total del pago |
| `principal_paid` | Money | Parte aplicada a capital |
| `interest_paid` | Money | Parte aplicada a intereses |
| `late_fee_paid` | Money | Parte aplicada a mora |
| `payment_method` | Choice | Método utilizado |
| `status` | Choice | Estado del pago |

### Estados del Pago

| Estado | Descripción |
|--------|-------------|
| `pending` | En proceso de verificación |
| `completed` | Completado y aplicado |
| `failed` | Falló (ej: cheque rechazado) |
| `reversed` | Revertido por error |

---

## Distribución Automática de Pagos

### Algoritmo de Aplicación

El sistema aplica pagos con la siguiente prioridad:

```
1. MORA (Late Fees) de la cuota más vencida
2. INTERÉS de la cuota más vencida
3. CAPITAL de la cuota más vencida
4. Si sobra dinero, se aplica a próximas cuotas
```

### Implementación

**Ubicación**: `backend/apps/loans/serializers.py` - `LoanPaymentCreateSerializer.create()`

```python
def create(self, validated_data):
    loan = validated_data['loan']
    payment_amount = validated_data['amount'].amount
    remaining_payment = payment_amount

    # Variables para distribución
    principal_payment = Decimal('0')
    interest_payment = Decimal('0')
    late_fee_payment = Decimal('0')

    # Si no se especifica cuota, buscar la más vencida
    if not validated_data.get('schedule'):
        oldest_overdue = loan.payment_schedules.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'overdue', 'partial']
        ).order_by('due_date').first()

        if oldest_overdue:
            # PASO 1: Aplicar a MORA
            late_fee_balance = (
                oldest_overdue.late_fee_amount.amount -
                oldest_overdue.late_fee_paid.amount
            )
            if late_fee_balance > 0 and remaining_payment > 0:
                late_fee_payment = min(remaining_payment, late_fee_balance)
                remaining_payment -= late_fee_payment

            # PASO 2: Aplicar a INTERÉS
            interest_balance = calculate_interest_balance(oldest_overdue)
            if interest_balance > 0 and remaining_payment > 0:
                interest_payment = min(remaining_payment, interest_balance)
                remaining_payment -= interest_payment

            # PASO 3: Aplicar a CAPITAL
            principal_balance = calculate_principal_balance(oldest_overdue)
            if principal_balance > 0 and remaining_payment > 0:
                principal_payment = min(remaining_payment, principal_balance)
                remaining_payment -= principal_payment

            # Vincular pago a esta cuota
            validated_data['schedule'] = oldest_overdue

            # Si aún sobra dinero (sobrepago), agregar a capital
            if remaining_payment > 0:
                principal_payment += remaining_payment

    # Crear el pago con distribución calculada
    payment = LoanPayment.objects.create(
        **validated_data,
        principal_paid=Money(principal_payment, loan.currency),
        interest_paid=Money(interest_payment, loan.currency),
        late_fee_paid=Money(late_fee_payment, loan.currency)
    )

    # Actualizar cuota si está vinculada
    if payment.schedule:
        update_schedule_balance(payment.schedule, payment)

    # Actualizar balance del préstamo
    loan.update_outstanding_balance()

    return payment
```

### Ejemplo de Distribución

**Escenario**:
- Cuota #5 vencida hace 30 días
- Balance cuota: $10,000
  - Mora acumulada: $500
  - Interés pendiente: $1,500
  - Capital pendiente: $8,000
- Cliente paga: $6,000

**Distribución**:
```
1. Mora:     $500  (paga toda la mora)
2. Interés:  $1,500 (paga todo el interés)
3. Capital:  $4,000 (paga parte del capital)

Total: $6,000

Balance restante de la cuota: $4,000 (solo capital)
Estado de la cuota: PARTIAL
```

---

## Métodos de Pago

### Métodos Soportados

| Método | Código | Requiere Referencia | Verificación |
|--------|--------|---------------------|--------------|
| Efectivo | `cash` | No | Inmediata |
| Cheque | `check` | Sí (# cheque) | Diferida |
| Transferencia Bancaria | `bank_transfer` | Sí (# transacción) | Inmediata |
| Tarjeta | `card` | Sí (últimos 4 dígitos) | Inmediata |
| Pago Móvil | `mobile_payment` | Sí (# referencia) | Inmediata |

### Configuración de Métodos

```python
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Efectivo'),
    ('check', 'Cheque'),
    ('bank_transfer', 'Transferencia Bancaria'),
    ('card', 'Tarjeta de Crédito/Débito'),
    ('mobile_payment', 'Pago Móvil (WhatsApp, etc.)'),
]
```

### Validaciones por Método

#### Efectivo
- No requiere número de referencia
- Status inmediato: `completed`
- Generar recibo obligatorio

#### Cheque
- Requiere número de cheque
- Requiere banco emisor
- Status inicial: `pending` (hasta que se confirme)
- Adjuntar foto del cheque (opcional)

#### Transferencia Bancaria
- Requiere número de transacción
- Requiere banco origen
- Validar contra extracto bancario

#### Tarjeta
- Requiere últimos 4 dígitos
- Integración con gateway de pago (futuro)
- Comisión aplicable

#### Pago Móvil
- Requiere número de referencia
- Validar formato según proveedor
- Confirmación instantánea

---

## Reversión de Pagos

### Cuándo Reversar

- Cheque devuelto por falta de fondos
- Error en el monto registrado
- Pago duplicado
- Solicitud del cliente con justificación válida

### Proceso de Reversión

**Endpoint**:
```bash
POST /api/loans/payments/{payment_id}/reverse/
{
  "reason": "Cheque devuelto por falta de fondos"
}
```

**Acciones automáticas**:

1. Cambiar status del pago a `reversed`
2. Revertir distribución:
   - Sumar `principal_paid` de vuelta al balance de capital
   - Sumar `interest_paid` de vuelta al balance de interés
   - Sumar `late_fee_paid` de vuelta a la mora
3. Actualizar estado de la cuota vinculada
4. Recalcular `outstanding_balance` del préstamo
5. Registrar auditoría con usuario y razón

**Ejemplo**:

```python
def reverse_payment(payment, reason, user):
    if payment.status == 'reversed':
        raise ValidationError("Pago ya fue revertido")

    with transaction.atomic():
        # Revertir en la cuota
        if payment.schedule:
            schedule = payment.schedule
            schedule.paid_amount -= payment.amount
            schedule.late_fee_paid -= payment.late_fee_paid

            # Recalcular estado
            if schedule.paid_amount == Money(0, 'DOP'):
                schedule.status = 'pending'
            elif schedule.paid_amount < schedule.total_amount:
                schedule.status = 'partial'

            schedule.save()

        # Actualizar préstamo
        payment.loan.outstanding_balance += payment.principal_paid
        payment.loan.save()

        # Marcar pago como revertido
        payment.status = 'reversed'
        payment.reversal_reason = reason
        payment.reversed_by = user
        payment.reversed_at = timezone.now()
        payment.save()

        # Log de auditoría
        PaymentAuditLog.objects.create(
            payment=payment,
            action='reversed',
            user=user,
            reason=reason
        )
```

### Restricciones

- Solo usuarios con permiso `can_reverse_payment`
- No se puede reversar un pago ya revertido
- Reversiones quedan registradas en auditoría
- No se eliminan registros, solo se marcan como `reversed`

---

## API Endpoints

### Registrar Pago

```bash
POST /api/loans/payments/
Content-Type: application/json
Authorization: Bearer {token}

{
  "loan": "loan-uuid",
  "amount": "10000.00",
  "payment_method": "cash",
  "payment_date": "2025-10-30",
  "notes": "Pago de cuota #5"
}
```

**Respuesta exitosa** (201 Created):
```json
{
  "id": "payment-uuid",
  "payment_number": "PAY-2025-A1B2C3",
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
  "status": "completed",
  "created_at": "2025-10-30T10:30:00Z"
}
```

### Listar Pagos

```bash
GET /api/loans/payments/
```

**Query Parameters**:
- `loan`: UUID del préstamo
- `customer`: UUID del cliente
- `payment_method`: Filtrar por método
- `status`: Filtrar por estado
- `date_from`: Fecha desde (YYYY-MM-DD)
- `date_to`: Fecha hasta (YYYY-MM-DD)
- `ordering`: Ordenar (-payment_date, amount)

### Detalle de Pago

```bash
GET /api/loans/payments/{id}/
```

**Response incluye**:
- Información completa del pago
- Detalles del préstamo vinculado
- Cuota vinculada (si aplica)
- Distribución detallada
- Cliente asociado
- Historial de auditoría (si fue revertido)

### Reversar Pago

```bash
POST /api/loans/payments/{id}/reverse/
{
  "reason": "Cheque devuelto - NSF (fondos insuficientes)"
}
```

**Permisos requeridos**: `can_reverse_payment`

**Respuesta** (200 OK):
```json
{
  "message": "Pago revertido exitosamente",
  "payment": {
    "id": "uuid",
    "status": "reversed",
    "reversed_at": "2025-10-30T15:45:00Z",
    "reversed_by": "admin-uuid",
    "reversal_reason": "Cheque devuelto - NSF"
  }
}
```

---

## Casos de Uso

### Caso 1: Pago Puntual

**Escenario**: Cliente paga exactamente la cuota del mes

```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "9168.46",
  "payment_method": "bank_transfer",
  "reference_number": "TXN-20251030-12345",
  "payment_date": "2025-10-30"
}
```

**Resultado**:
- Sistema encuentra cuota vencida más antigua
- Aplica $0 a mora (no hay)
- Aplica $1,500 a interés
- Aplica $7,668.46 a capital
- Marca cuota como `paid`

### Caso 2: Pago con Mora

**Escenario**: Cliente paga cuota vencida hace 15 días

**Estado de cuota antes del pago**:
- Total cuota: $9,168.46
- Mora acumulada (15 días): $300
- Total a pagar: $9,468.46

**Cliente paga**:
```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "9468.46",
  "payment_method": "cash"
}
```

**Distribución**:
```
Mora:     $300.00
Interés:  $1,500.00
Capital:  $7,668.46
Total:    $9,468.46
```

### Caso 3: Pago Parcial

**Escenario**: Cliente solo puede pagar $5,000 de una cuota de $9,168.46

```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "5000.00",
  "payment_method": "cash"
}
```

**Distribución** (asumiendo $500 de mora):
```
Mora:     $500.00  (paga toda la mora)
Interés:  $1,500.00 (paga todo el interés)
Capital:  $3,000.00 (paga parte del capital)

Balance restante: $4,668.46
Estado cuota: PARTIAL
```

### Caso 4: Pago Adelantado

**Escenario**: Cliente paga 3 cuotas por adelantado

```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "27505.38",  # 3 × $9,168.46
  "payment_method": "bank_transfer",
  "reference_number": "TXN-XXXXX"
}
```

**Sistema**:
1. Busca cuota más vencida (ej: cuota #5)
2. Aplica $9,168.46 a cuota #5 → marca como `paid`
3. Busca siguiente cuota (cuota #6)
4. Aplica $9,168.46 a cuota #6 → marca como `paid`
5. Busca siguiente cuota (cuota #7)
6. Aplica $9,168.46 a cuota #7 → marca como `paid`

### Caso 5: Pago Total del Préstamo

**Escenario**: Cliente desea liquidar el préstamo completo

**Cálculo de liquidación**:
```bash
GET /api/loans/{loan-uuid}/payoff_quote/
```

**Response**:
```json
{
  "outstanding_balance": "150000.00",
  "accrued_interest": "2500.00",
  "late_fees": "1500.00",
  "payoff_amount": "154000.00",
  "good_through_date": "2025-11-05"
}
```

**Registrar pago total**:
```bash
POST /api/loans/payments/
{
  "loan": "loan-uuid",
  "amount": "154000.00",
  "payment_method": "bank_transfer",
  "notes": "Liquidación total del préstamo"
}
```

**Resultado**:
- Todas las cuotas pendientes marcadas como `paid`
- Status del préstamo cambia a `paid`
- `outstanding_balance` = $0
- Se genera certificado de pago total

---

## Integraciones Futuras

### Gateway de Pagos

- [ ] Stripe para pagos con tarjeta
- [ ] PayPal para pagos internacionales
- [ ] Pasarelas locales (Cardnet, Azul, etc.)

### Notificaciones

- [ ] Email de confirmación de pago
- [ ] SMS con recibo digital
- [ ] WhatsApp con comprobante
- [ ] Recordatorios pre-vencimiento

### Automatización

- [ ] Débito automático de cuenta
- [ ] Domiciliación bancaria
- [ ] Pagos recurrentes programados

---

## Reportes de Pagos

### Reporte de Pagos Diarios

```bash
GET /api/loans/payments/daily_report/?date=2025-10-30
```

**Response**:
```json
{
  "date": "2025-10-30",
  "total_payments": 45,
  "total_amount": "450000.00",
  "by_method": {
    "cash": {"count": 20, "amount": "180000.00"},
    "bank_transfer": {"count": 15, "amount": "200000.00"},
    "check": {"count": 10, "amount": "70000.00"}
  },
  "by_status": {
    "completed": 40,
    "pending": 5
  }
}
```

### Reporte de Morosidad

```bash
GET /api/loans/payments/arrears_report/
```

**Response**:
```json
{
  "total_overdue_amount": "2500000.00",
  "total_late_fees": "125000.00",
  "loans_overdue": 50,
  "by_age_bucket": {
    "1-30_days": {"count": 30, "amount": "1000000.00"},
    "31-60_days": {"count": 15, "amount": "800000.00"},
    "61-90_days": {"count": 3, "amount": "500000.00"},
    "90+_days": {"count": 2, "amount": "200000.00"}
  }
}
```

---

## Troubleshooting

### El pago no se aplica correctamente

**Síntoma**: Distribución de pago no coincide con lo esperado

**Diagnóstico**:
```python
payment = LoanPayment.objects.get(id='uuid')
print(f"Total: {payment.amount}")
print(f"Principal: {payment.principal_paid}")
print(f"Interest: {payment.interest_paid}")
print(f"Late Fee: {payment.late_fee_paid}")
print(f"Sum: {payment.principal_paid + payment.interest_paid + payment.late_fee_paid}")
```

**Solución**: Verificar que la suma de componentes = amount total

### Balance del préstamo no actualiza

**Causa**: `update_outstanding_balance()` no se ejecutó

**Solución**:
```bash
docker-compose exec backend python manage.py shell

from apps.loans.models import Loan
loan = Loan.objects.get(id='uuid')
loan.update_outstanding_balance()
```

### Reversión de pago falla

**Causa común**: Pago ya fue revertido anteriormente

**Verificar**:
```python
payment.status == 'reversed'
```

---

**Última actualización**: 2025-10-30
