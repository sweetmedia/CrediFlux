# Distribución Automática de Pagos

## Resumen

Los pagos ahora se distribuyen automáticamente a través del cronograma de pagos del préstamo, manejando correctamente pagos exactos, pagos parciales y pagos en exceso.

## Cómo Funciona

### 1. Pago Exacto

**Escenario:** Cuota mensual = $2,333.33, Pago realizado = $2,333.33

**Resultado:**
- ✅ Cuota #1 marcada como `paid` (pagada)
- ✅ `paid_amount` = $2,333.33
- ✅ `paid_date` = fecha del pago

### 2. Pago en Exceso (Overpayment)

**Escenario:** Cuota mensual = $2,333.33, Pago realizado = $5,000.00

**Resultado:**
- ✅ Cuota #1 marcada como `paid` ($2,333.33 aplicado)
- ✅ Cuota #2 marcada como `paid` ($2,333.33 aplicado)
- ✅ Cuota #3 marcada como `partial` ($333.34 aplicado de $2,333.33 que debe)

**Explicación:**
El sistema distribuyó los $5,000 así:
- $2,333.33 → Cuota 1 (100% pagada)
- $2,333.33 → Cuota 2 (100% pagada)
- $333.34 → Cuota 3 (14.28% pagada, queda pendiente $2,000.00)

### 3. Pago Parcial

**Escenario:** Cuota mensual = $2,333.33, Pago realizado = $1,000.00

**Resultado:**
- ⚠️ Cuota #1 marcada como `partial` (parcial)
- ⚠️ `paid_amount` = $1,000.00
- ⚠️ Monto pendiente = $1,333.33

### 4. Múltiples Pagos Parciales

**Escenario:**
- Cuota #1 debe $2,333.33
- Primer pago: $1,000.00
- Segundo pago: $1,500.00

**Resultado después del primer pago:**
- Cuota #1 = `partial`, paid_amount = $1,000.00

**Resultado después del segundo pago:**
- Cuota #1 = `paid`, paid_amount = $2,500.00
- Exceso de $166.67 aplicado a Cuota #2 (marcada como `partial`)

## Estados de Cuotas

### `pending` (Pendiente)
- No se ha pagado nada
- `paid_amount` = $0.00
- `paid_date` = null

### `partial` (Parcial)
- Se ha pagado algo, pero no el total
- `paid_amount` > $0.00 y < `total_amount`
- `paid_date` = null

### `paid` (Pagada)
- Se ha pagado el monto completo (o más)
- `paid_amount` >= `total_amount`
- `paid_date` = fecha del último pago que completó la cuota

### `overdue` (Vencida)
- La fecha de vencimiento (`due_date`) ya pasó
- El monto no está completamente pagado
- Status cambia automáticamente cuando el sistema detecta cuotas vencidas

## Comportamiento Automático

### Al Crear un Pago

El sistema automáticamente:
1. ✅ Busca cuotas pendientes en orden cronológico
2. ✅ Aplica el pago a la primera cuota pendiente/parcial/vencida
3. ✅ Si hay exceso, lo aplica a las siguientes cuotas
4. ✅ Actualiza el estado de cada cuota afectada
5. ✅ Actualiza los totales del préstamo

### Al Eliminar un Pago

El sistema automáticamente:
1. ✅ Revierte los totales del préstamo
2. ✅ Reinicia todas las cuotas (`paid_amount` = $0, status = `pending`)
3. ✅ Re-aplica TODOS los pagos restantes del préstamo
4. ✅ Recalcula el estado de cada cuota

Esto garantiza que las cuotas siempre reflejen el estado correcto basándose en todos los pagos existentes.

## Vinculación de Pagos a Cuotas

### Pago CON Cuota Vinculada

Si al crear un pago especificas una cuota (`schedule`):
- El sistema comienza aplicando el pago desde esa cuota
- Si hay exceso, lo aplica a las siguientes cuotas

### Pago SIN Cuota Vinculada

Si no especificas una cuota:
- El sistema automáticamente vincula el pago a la primera cuota pendiente
- Aplica el pago desde esa cuota en adelante

## Ejemplos de API

### Crear un Pago Exacto

```bash
POST /api/loans/{loan_id}/payments/
{
  "amount": "2333.33",
  "payment_method": "cash",
  "payment_date": "2025-10-29"
}
```

**Resultado:** Primera cuota pendiente marcada como `paid`

### Crear un Pago en Exceso

```bash
POST /api/loans/{loan_id}/payments/
{
  "amount": "5000.00",
  "payment_method": "transfer",
  "payment_date": "2025-10-29"
}
```

**Resultado:** Múltiples cuotas marcadas como `paid`, última cuota afectada marcada como `partial`

### Crear un Pago Parcial

```bash
POST /api/loans/{loan_id}/payments/
{
  "amount": "1000.00",
  "payment_method": "cash",
  "payment_date": "2025-10-29"
}
```

**Resultado:** Primera cuota pendiente marcada como `partial`

### Crear un Pago para una Cuota Específica

```bash
POST /api/loans/{loan_id}/payments/
{
  "amount": "2333.33",
  "payment_method": "cash",
  "payment_date": "2025-10-29",
  "schedule": 3  // ID de la cuota #3
}
```

**Resultado:** Cuota #3 marcada como `paid` (incluso si las cuotas 1 y 2 están pendientes)

## Verificación

### Ver Estado de Cuotas

```bash
GET /api/loans/{loan_id}/schedules/
```

Respuesta:
```json
[
  {
    "id": 1,
    "installment_number": 1,
    "due_date": "2025-11-01",
    "total_amount": "2333.33",
    "paid_amount": "2333.33",
    "status": "paid",
    "paid_date": "2025-10-29"
  },
  {
    "id": 2,
    "installment_number": 2,
    "due_date": "2025-12-01",
    "total_amount": "2333.33",
    "paid_amount": "1000.00",
    "status": "partial",
    "paid_date": null
  },
  {
    "id": 3,
    "installment_number": 3,
    "due_date": "2026-01-01",
    "total_amount": "2333.33",
    "paid_amount": "0.00",
    "status": "pending",
    "paid_date": null
  }
]
```

### Ver Pagos del Préstamo

```bash
GET /api/loans/{loan_id}/payments/
```

Respuesta:
```json
[
  {
    "id": 1,
    "amount": "5000.00",
    "payment_date": "2025-10-29",
    "status": "completed",
    "schedule": 1,
    "principal_paid": "4500.00",
    "interest_paid": "500.00"
  }
]
```

## Consideraciones Importantes

### 1. Orden de Aplicación
Los pagos siempre se aplican en orden cronológico por `installment_number`.

### 2. Pagos Completados
Solo los pagos con `status = 'completed'` afectan las cuotas.

### 3. Eliminación de Pagos
Al eliminar un pago, se recalculan TODAS las cuotas del préstamo automáticamente.

### 4. Cuotas Vencidas
Las cuotas con `due_date` anterior a hoy se marcan automáticamente como `overdue` si no están pagadas.

### 5. Préstamo Totalmente Pagado
Cuando `outstanding_balance` llega a $0, el préstamo se marca como `paid` automáticamente.

## Implementación Técnica

La lógica está implementada en:
- **Archivo:** `backend/apps/loans/signals.py`
- **Función principal:** `distribute_payment_to_schedules(payment)`
- **Signal:** `update_loan_on_payment` (se ejecuta al crear un pago)
- **Signal:** `revert_loan_on_payment_delete` (se ejecuta al eliminar un pago)

---

**Última Actualización:** 2025-10-29
**Versión:** 1.0
