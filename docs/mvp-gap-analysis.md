# CrediFlux MVP — Gap Analysis para Demo a Clientes

> **Fecha:** 2026-03-30
> **Objetivo:** Identificar qué FALTA para presentar el módulo de financieras a clientes reales
> **Referencia:** DesiWeb DesiPos (competidor analizado)

---

## Lo que YA tenemos ✅

### Backend (Django)
- ✅ **Customer** — datos personales, contacto, dirección, empleo, documentos, crédito
- ✅ **CustomerDocument** — subida/verificación de documentos
- ✅ **Loan** — solicitud, aprobación, tipos, montos, tasas, frecuencia pagos, estados
- ✅ **LoanSchedule** — calendario de pagos con mora, días atraso
- ✅ **LoanPayment** — registro de pagos con desglose (capital, interés, mora)
- ✅ **Collateral** — garantías con metadata JSON por tipo
- ✅ **CollectionReminder** — recordatorios de cobro
- ✅ **CollectionContact** — registro de contactos/llamadas de cobro
- ✅ **ContractTemplate** — plantillas de contratos
- ✅ **Contract** — contratos generados con firma digital
- ✅ **ContractSignatureToken** — tokens para firma electrónica
- ✅ **Invoice / InvoiceItem** — facturación con items
- ✅ **DigitalCertificate** — certificados para e-CF
- ✅ **FiscalSequence** — secuencias NCF
- ✅ **ECFSubmission** — envío a DGII
- ✅ **AuditLog** — auditoría
- ✅ **Communications** — email, WhatsApp, tasks
- ✅ Multi-tenant con django_tenants
- ✅ API REST completa (ViewSets + Serializers para todo)

### Frontend (Next.js)
- ✅ Dashboard
- ✅ Customers — CRUD + detalle + editar + documentos
- ✅ Loans — lista + crear + detalle + préstamos vencidos
- ✅ Payments — lista + crear + detalle
- ✅ Schedules — vencidos
- ✅ Collections — lista + recordatorios + reportes
- ✅ Contracts — lista + generar + detalle + firma pública
- ✅ Contract Templates — CRUD + editor
- ✅ Billing — lista + crear + detalle + certificados + secuencias
- ✅ Users — CRUD
- ✅ Settings — general + préstamos
- ✅ Auth — login, register, forgot/reset password, tenant selection
- ✅ Audit log
- ✅ Communications
- ✅ Tasks

---

## Lo que FALTA para Demo 🔨

### P0 — CRÍTICO (sin esto no se puede presentar)

1. **🧮 Calculadora de Préstamos Avanzada**
   - DesiWeb tiene: Saldo Soluto (capitalizado), interés mensual directo
   - Necesitamos: Método Francés, Alemán, Saldo Soluto, Flat (interés sobre monto original)
   - Calcular en frontend antes de crear el préstamo
   - Mostrar tabla de amortización preview

2. **📊 Dashboard con métricas reales**
   - Total cartera activa (monto)
   - Cartera vencida vs al día (%)
   - Cobros del día/semana/mes
   - Préstamos por aprobar
   - Top clientes morosos
   - Gráficos: desembolsos por mes, cobros por mes, mora por antigüedad

3. **🏢 Datos de la Financiera (Tenant Config)**
   - RNC, razón social, dirección, logo
   - Configuración de mora (% diario, tope máximo)
   - Tasa de interés default
   - Moneda default (DOP)
   - Horarios de cobro

4. **💵 Moneda DOP (Peso Dominicano)**
   - Cambiar currency default de USD a DOP
   - Soporte multi-moneda (DOP + USD) si es necesario

### P1 — IMPORTANTE (para verse profesional)

5. **📋 Solicitud de Préstamo Multi-Step**
   - Wizard tipo DesiWeb: datos personales → laborales → garantes → garantía → documentos → préstamo
   - Guardar progreso parcial (draft)

6. **👥 Garantes/Co-deudores**
   - Modelo Guarantor (nombre, cédula, relación, dirección, teléfono, empleo)
   - Un préstamo puede tener 1-3 garantes

7. **📍 Geolocalización de Clientes**
   - Latitud/longitud en Customer
   - Mapa en la vista de cobros del día
   - Optimización de ruta para cobradores

8. **🖨️ Impresión de Documentos**
   - Recibo de pago (PDF)
   - Estado de cuenta del cliente (PDF)
   - Contrato firmado (PDF)
   - Tabla de amortización (PDF)

9. **📱 Vista móvil para Cobradores**
   - Lista de cobros del día (responsive)
   - Registrar pago rápido desde el teléfono
   - Registrar visita con GPS
   - Llamar al cliente desde la app

### P2 — NICE TO HAVE (para cerrar ventas)

10. **📊 Reportes DGII**
    - Formulario 606 (compras)
    - Formulario 607 (ventas)
    - Exportar en formato DGII

11. **💬 WhatsApp Integrado**
    - Enviar recordatorio de pago automático
    - Notificación de cuota próxima
    - Confirmación de pago recibido

12. **🏦 Gestión de Caja**
    - Apertura/cierre de caja
    - Conteo por denominación (como DesiWeb)
    - Resumen de transacciones del día

13. **📈 Data Crédito**
    - Consulta de historial crediticio
    - Score interno basado en comportamiento de pago

---

## Priorización para Sprint Inmediato

### Sprint 1 (1-2 semanas) — "Demo Ready"
| # | Feature | Esfuerzo | Impacto |
|---|---------|----------|---------|
| 1 | Calculadora avanzada (frontend) | 3 días | 🔴 Crítico |
| 2 | Dashboard con métricas reales | 3 días | 🔴 Crítico |
| 3 | Moneda DOP como default | 1 día | 🔴 Crítico |
| 4 | Tenant config (datos empresa) | 2 días | 🔴 Crítico |
| 5 | PDF: recibo de pago | 2 días | 🟡 Alto |

### Sprint 2 (2 semanas) — "Sale Ready"
| # | Feature | Esfuerzo | Impacto |
|---|---------|----------|---------|
| 6 | Solicitud multi-step wizard | 4 días | 🟡 Alto |
| 7 | Garantes/co-deudores | 2 días | 🟡 Alto |
| 8 | Estado de cuenta PDF | 2 días | 🟡 Alto |
| 9 | Vista móvil cobradores | 3 días | 🟡 Alto |
| 10 | Reportes DGII (606/607) | 3 días | 🟠 Medio |

### Sprint 3 (2 semanas) — "Enterprise Ready"
| # | Feature | Esfuerzo | Impacto |
|---|---------|----------|---------|
| 11 | WhatsApp notificaciones | 3 días | 🟠 Medio |
| 12 | Gestión de caja | 4 días | 🟠 Medio |
| 13 | Geolocalización + mapa | 3 días | 🟠 Medio |
| 14 | e-CF facturación electrónica | 5 días | 🟠 Medio |
| 15 | Data crédito interno | 2 días | 🟢 Bajo |

---

## Estimación Total: ~6 semanas para MVP presentable

**Semana 1-2:** Demo funcional (calculadora, dashboard, DOP, tenant config)
**Semana 3-4:** Profesional (wizard, garantes, PDFs, mobile)
**Semana 5-6:** Enterprise (WhatsApp, caja, geo, DGII)
