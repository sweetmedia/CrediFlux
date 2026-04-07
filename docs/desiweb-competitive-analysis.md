# DesiWeb DesiPos — Análisis Competitivo para CrediFlux

> **Fecha:** 2026-03-30
> **Fuente:** https://desiweb.com.do/DesiPos/
> **Tipo:** ERP PHP multi-módulo (POS + Préstamos + Contabilidad + más)
> **Screenshots:** `docs/desiweb-screenshots/` (32 capturas)

---

## 1. Resumen General

DesiWeb DesiPos es un **ERP monolítico en PHP** que cubre MUCHOS verticales: POS, odontología, veterinaria, laboratorio dental, bananera, renta car, academia, etc. El módulo de **Negocios/Préstamos** es solo una parte del sistema.

### Lo bueno (para inspirar CrediFlux):
- ✅ Flujo completo de préstamos: solicitud → aprobación → desembolso → cobro
- ✅ Gestión de cobros con filtros avanzados (por zona, cobrador, días atraso)
- ✅ Calculadora de préstamos con múltiples métodos de amortización
- ✅ Contratos personalizables con editor WYSIWYG
- ✅ Sistema de permisos granular por módulo
- ✅ Contabilidad integrada con DGII (NCF, Form 606, 607)
- ✅ Gestión de caja con cierre detallado
- ✅ Data Crédito integrado
- ✅ Geolocalización de clientes (latitud/longitud)

### Lo malo (donde CrediFlux puede DESTRUIR):
- ❌ UI anticuada (Bootstrap 3 era, colores planos, sin diseño moderno)
- ❌ No es SaaS — es una instalación on-premise por cliente
- ❌ No tiene multi-tenancy real
- ❌ Sin mobile app (solo responsive web)
- ❌ Sin API REST pública
- ❌ Sin dashboard analytics modernos (solo un gauge básico)
- ❌ Sin notificaciones push a clientes
- ❌ Sin portal de clientes (autoservicio)
- ❌ PHP monolítico — difícil de escalar
- ❌ Sin integraciones modernas (Stripe, WhatsApp, etc.)

---

## 2. Módulo de Préstamos — Desglose Completo

### 2.1 Solicitud de Préstamos (6 tabs)

**Tab 1: Datos del Cliente**
- Código cliente, fecha entrada, vía contacto, límite crédito
- Tipo identificación, cédula/pasaporte, nombre, apellido, apodo
- Teléfono celular, adicional, casa, email
- Fecha nacimiento, lugar nacimiento, nacionalidad, estado civil
- Años casados, género, dependientes, hijos
- Provincia, municipio, sector, dirección
- Profesión, ocupación, vivienda (propia/alquilada), renta mensual, otros gastos
- Preferencia envío info, comprobante, data crédito
- Latitud/longitud + mapa
- Observaciones/notas
- Botones especiales: Aut. Data Cred., Aut. Fotos, Link Img

**Tab 2: Datos Laborales**
- Información de empleo del solicitante

**Tab 3: Datos Terceros**
- Garantes/co-deudores/referencias

**Tab 4: Garantía**
- Bienes en garantía del préstamo

**Tab 5: Documentos Adjuntos**
- Subida de archivos (cédula, carta trabajo, etc.)

**Tab 6: Solicitud Préstamos**
- Detalles del préstamo solicitado

### 2.2 Calculadora de Préstamos
**Campos:**
- Tipo préstamo (dropdown)
- Método amortización: **SALDO SOLUTO (CAPITALIZADO)** — el estándar en RD
- Fecha inicio/fin
- Monto aprobado
- Interés mensual (%)
- Número de cuotas
- Forma de pago: Diario, Semanal, Quincenal, **Mensual**
- Calcular cuota (Si/No)
- Gastos legales + condición (Financiado/Deducido)
- Monto cuota (calculado o manual)

**Campos calculados:**
- Total préstamo
- Total desembolsado
- Total interés
- Plazo

**Métodos de amortización soportados:**
- Saldo Soluto (capitalizado) — el más común en financieras RD
- Probablemente: Francés, Alemán, Flat

### 2.3 Cartera de Préstamos
**Tabla con columnas (inferido de los datos):**
- Número préstamo, solicitud ID
- Nombre del cliente
- Monto, cuotas, días atraso
- Estado del préstamo
- Cobrador/gestor asignado

### 2.4 Listado de Cobros (Gestión de Cobranzas) ⭐
**Filtros SUPER granulares:**
- Tipo de listado: Todos, por cobrador, por zona
- Incluir: Cobrar Hoy, Atrasados, Todos
- Ordenar por: Fecha de pago, días atraso, monto
- Forma de pago: Efectivo, transferencia, cheque
- Comisionista
- Analista de crédito
- Gestor de cobros
- Oficial de cobros
- Tanda de cobro (turnos)
- Método de pago preferido del cliente
- Número de préstamo
- Nombre/cédula del cliente
- Mayor que X (filtrar por monto mínimo a cobrar)
- Cartera de préstamo
- Nombre empresa (del cliente)
- Días atraso desde/hasta
- Cuotas atraso desde/hasta
- Tipo de préstamo
- Cuotas para terminar
- **Geolocalización** (latitud/longitud + "Donde Estoy")

> **Insight:** Este es el módulo más usado día a día por los cobradores. CrediFlux NECESITA un equivalente mobile-first.

### 2.5 Depuración de Solicitudes
- Filtros por fecha, analista, gestor, estado
- Tabla: Fecha, Sol. No., Nombre, Monto Solicitado, Monto Aprobado, Estado, Analista, Usuario

### 2.6 Registro de Visitas
- Registro de visitas de cobro a clientes
- Fecha, cliente, comentario, resultado

### 2.7 Contratos
- Editor WYSIWYG (Summernote) para crear plantillas de contrato
- Variables dinámicas para autocompletar datos del préstamo
- Múltiples plantillas (8 contratos visibles)

### 2.8 Data Crédito
- Integración para consultar historial crediticio del cliente

### 2.9 Movimiento Fecha de Pago
- Permite cambiar la fecha de pago de cuotas

### 2.10 Reportes de Préstamos
- Rep. Visitas (por fecha, cobrador)
- Rep. Comisiones (por vendedor/comisionista)
- Rep. Préstamos (general)
- Rep. Balance Cartera (estado de la cartera)
- Rep. Cobros (pagos recibidos)

---

## 3. Otros Módulos Relevantes

### 3.1 Cuentas por Cobrar
- **Recibo de ingreso** — registro de pagos recibidos
  - Campos: factura #, cliente, monto, forma pago (efectivo/tarjeta/cheque/transferencia/bono), banco, descuento, retención, ITBIS
- **Nota de débito** — cargos adicionales
- **Nota de crédito** — ajustes/descuentos
- **Gestión de clientes** — seguimiento de cobros con llamadas
- Reportes: Listado CxC, Estado de cuenta, Antigüedad de saldos, Facturas vencidas

### 3.2 Contabilidad
- **Catálogo de cuentas** — plan contable completo
- **Configuración cuentas contables** — mapping de cuentas
- **Período contable** — apertura/cierre de períodos
- **Entrada de diario** — asientos contables
- **Registro de NCF** — secuencias de comprobantes fiscales
- **Gastos** — registro de gastos con categorías
- **Reportes DGII:**
  - Formulario 606 (compras)
  - Formulario 607 (ventas)
  - Mayor General
  - Balanza de Comprobación
  - Estado de Resultado
  - Estado de Situación

### 3.3 Facturación
- Nueva factura (con detalle de items)
- Factura rápida
- Cotizaciones
- Conduce (guía de despacho)
- Secuencias NCF

### 3.4 Finanzas/Banco
- Cuentas bancarias (nombre, banco, número, tipo, moneda, balance)
- Transferencias entre cuentas
- Movimientos bancarios
- Conciliación bancaria

### 3.5 Caja
- **Cierre de caja** — MUY detallado:
  - Conteo por denominación (monedas y billetes)
  - Depósitos a bancos (hasta 3 bancos)
  - Desglose: efectivo, tarjeta, cheque, bono, transferencia
  - Tablas de transacciones: ventas, cobros CxC, desembolsos, fondos, compras, gastos
  - Diferencia entre lo contado y lo del sistema

### 3.6 Configuración
- **Empresa** — datos de la empresa, logo, colores, tipo POS
- **Permisos de usuario** — sistema de roles con checkboxes por módulo:
  - Por cada módulo: Editar, Guardar, Ver, Modificar Documentos
  - Permisos especiales: Cambio Fecha, Descuento

### 3.7 Nómina
- Préstamos a empleados
- Generación de nómina
- Deducciones
- Importar asistencia

---

## 4. Datos del Dashboard

El dashboard muestra:
- Logo de la empresa
- Gauge circular con % de meta (73,600 / 200,000 = 36.80%)
- Gestión de cobros del día (lista de clientes con cuotas pendientes — 50 clientes visibles)
- Usuarios del sistema (JFERNANDEZ, JMTAVERAS, NPEREZ)
- Accesos directos a áreas frecuentes

---

## 5. Oportunidades para CrediFlux (Donde GANAR)

### 5.1 Features que DesiWeb tiene y CrediFlux NECESITA:
1. **Solicitud multi-tab** (datos personales, laborales, garantes, garantías, documentos)
2. **Calculadora de préstamos** con múltiples métodos de amortización
3. **Gestión de cobros** con filtros avanzados + geolocalización
4. **Contratos dinámicos** con plantillas
5. **Data Crédito** integrado
6. **Registro de visitas** de cobro
7. **Cierre de caja** con conteo por denominación
8. **Secuencias NCF** para comprobantes fiscales
9. **Formularios 606/607** para DGII
10. **Sistema de permisos** granular

### 5.2 Features donde CrediFlux será SUPERIOR:
1. 📱 **App móvil para cobradores** (DesiWeb solo tiene web)
2. 🔔 **Notificaciones push** a clientes (recordatorios de pago)
3. 📊 **Dashboard analytics** moderno (no un gauge de los 90s)
4. 💬 **WhatsApp/SMS** integrado para cobros
5. 🏢 **Multi-tenancy real** (SaaS, no instalación por cliente)
6. 🌐 **Portal de autoservicio** para clientes (ver saldo, pagar online)
7. 💳 **Pagos online** (Stripe, tarjetas, transferencias P2P)
8. 🤖 **Automatización** (recordatorios automáticos, escalamiento de cobros)
9. 📄 **Facturación electrónica** e-CF integrada
10. 📈 **ML/AI** para scoring crediticio
11. 🔗 **API REST** pública para integraciones
12. ☁️ **Cloud-native** — escala automáticamente
13. 🎨 **UI/UX moderna** — diseño del 2026, no del 2015

### 5.3 Feature Map — DesiWeb → CrediFlux

| DesiWeb Feature | CrediFlux Equivalente | Status |
|----------------|----------------------|--------|
| Solicitud Préstamo (tabs) | Loan Application Wizard | 🔨 Build |
| Calculadora Préstamo | Loan Calculator | ✅ Exists (basic) |
| Cartera Préstamo | Loan Portfolio | ✅ Exists |
| Listado Cobros | Collection Management | 🔨 Enhance |
| Depuración | Application Pipeline | 🔨 Build |
| Registro Visitas | Visit Tracking (GPS) | 🔨 Build |
| Contrato | Contract Templates | 🔨 Build |
| Data Crédito | Credit Score Integration | 🔨 Build |
| Cambio Fecha Pago | Payment Reschedule | 🔨 Build |
| Recibo Ingreso | Payment Receipt | ✅ Exists |
| Nota Débito/Crédito | Debit/Credit Notes | 🔨 Build |
| Gestión Cobros CxC | AR Management | 🔨 Build |
| NCF/Secuencias | e-CF Integration | 🔨 Build (ver doc facturación) |
| Form 606/607 | DGII Reports | 🔨 Build |
| Cierre Caja | Cash Reconciliation | 🔨 Build |
| Cuentas Banco | Bank Accounts | 🔨 Build |
| Permisos Usuario | Role-based Access | ✅ Exists (django_tenants) |

---

## 6. Priorización Recomendada

### Sprint 1 (Inmediato — Core Lending)
1. Loan Application Wizard (multi-step form)
2. Loan Calculator (múltiples métodos amortización)
3. Collection List (con filtros tipo DesiWeb pero UI moderna)

### Sprint 2 (Cobros)
4. Visit Tracking con GPS
5. WhatsApp/SMS notifications
6. Payment reschedule

### Sprint 3 (Compliance)
7. e-CF Integration (facturación electrónica)
8. NCF sequences
9. DGII Forms 606/607

### Sprint 4 (Financiero)
10. Cash reconciliation (cierre de caja)
11. Bank accounts management
12. Debit/Credit notes

### Sprint 5 (Diferenciadores)
13. Client self-service portal
14. Mobile app para cobradores
15. AI credit scoring

---

*Este análisis se basa en la exploración read-only del sistema DesiWeb. No se modificó ningún dato.*
