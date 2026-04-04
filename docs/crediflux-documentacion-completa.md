# CrediFlux — Documentación Completa

**Sistema de Gestión de Préstamos Multi-Tenant para Financieras en República Dominicana**

Versión: 1.0 | Fecha: Abril 2026 | Autor: Sweet Media Digital Agency

---

## Tabla de Contenido

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Módulos del Sistema](#3-módulos-del-sistema)
4. [Flujo de Uso Completo](#4-flujo-de-uso-completo)
5. [Gestión de Clientes](#5-gestión-de-clientes)
6. [Gestión de Préstamos](#6-gestión-de-préstamos)
7. [Cobros y Pagos](#7-cobros-y-pagos)
8. [Facturación Electrónica (e-CF)](#8-facturación-electrónica-e-cf)
9. [Caja (Cash Management)](#9-caja-cash-management)
10. [Cobranza y Geolocalización](#10-cobranza-y-geolocalización)
11. [Comunicaciones (WhatsApp)](#11-comunicaciones-whatsapp)
12. [Contratos Digitales](#12-contratos-digitales)
13. [Asistente AI](#13-asistente-ai)
14. [Reportes DGII (606/607)](#14-reportes-dgii-606607)
15. [Auditoría](#15-auditoría)
16. [Configuración del Tenant](#16-configuración-del-tenant)
17. [Gestión de Usuarios y Roles](#17-gestión-de-usuarios-y-roles)
18. [Calculadora de Préstamos](#18-calculadora-de-préstamos)
19. [API Reference](#19-api-reference)
20. [Despliegue e Infraestructura](#20-despliegue-e-infraestructura)

---

## 1. Descripción General

### ¿Qué es CrediFlux?

CrediFlux es un sistema SaaS (Software as a Service) de gestión de préstamos diseñado específicamente para financieras, cooperativas de ahorro y crédito, y prestamistas en la República Dominicana. El sistema maneja todo el ciclo de vida de un préstamo: desde la solicitud y evaluación del cliente, hasta el desembolso, cobro, y cierre.

### Características Principales

- **Multi-tenant**: Cada financiera opera en su propio espacio aislado con datos separados
- **Moneda nativa DOP (RD$)**: Diseñado para el mercado dominicano
- **Facturación electrónica (e-CF)**: Integración con la DGII
- **WhatsApp**: Notificaciones automáticas de pagos, recordatorios de mora
- **Geolocalización de cobradores**: Rastreo de rutas y visitas de cobro
- **Gestión de caja**: Apertura/cierre de caja con conteo de denominaciones
- **Asistente AI**: Consultas inteligentes con djangosdk
- **Contratos digitales**: Generación y firma electrónica
- **Reportes DGII**: Generación automática de formatos 606/607

### Usuarios Objetivo

| Rol | Descripción |
|-----|-------------|
| **Administrador** | Configura el tenant, gestiona usuarios y parámetros del sistema |
| **Oficial de Crédito** | Evalúa solicitudes, aprueba/rechaza préstamos, gestiona desembolsos |
| **Cajero** | Recibe pagos, maneja apertura/cierre de caja |
| **Cobrador** | Realiza cobros en campo, registra visitas con geolocalización |
| **Analista** | Consulta reportes, analiza cartera, genera reportes DGII |

---

## 2. Arquitectura del Sistema

### Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| **Backend** | Django 5.0 + Django REST Framework |
| **Frontend** | Next.js 14 + Tailwind CSS + shadcn/ui |
| **Base de Datos** | PostgreSQL 16 (multi-tenant via django-tenants) |
| **Cache/Broker** | Redis 7 |
| **Tareas asíncronas** | Celery + Celery Beat |
| **AI** | djangosdk + LiteLLM (Groq/Gemini/Anthropic/OpenAI) |
| **Contenedores** | Docker + Docker Compose |
| **Moneda** | django-money (soporte multi-moneda, default DOP) |

### Arquitectura Multi-Tenant

CrediFlux usa **esquemas separados de PostgreSQL** para cada tenant (financiera). Esto significa:

```
PostgreSQL
├── public (schema compartido)
│   ├── tenants (tabla de tenants)
│   ├── tenant_domains (dominios por tenant)
│   └── users (usuarios compartidos)
├── demo (schema del tenant "Financiera Demo")
│   ├── customers
│   ├── loans
│   ├── loan_schedules
│   ├── payments
│   └── ... (todas las tablas de negocio)
└── otra_financiera (schema de otro tenant)
    ├── customers
    └── ... (datos completamente aislados)
```

Cada tenant se identifica por su dominio: `financiera.crediflux.com` → mapea al schema correspondiente.

### Contenedores Docker

| Contenedor | Puerto | Función |
|-----------|--------|---------|
| `crediflux_backend` | 8000/8600 | API Django + Gunicorn |
| `crediflux_frontend` | 3000/3600 | Next.js UI |
| `crediflux_db` | 5432/5434 | PostgreSQL |
| `crediflux_redis` | 6379/6381 | Cache + Message Broker |
| `crediflux_celery` | — | Worker de tareas asíncronas |
| `crediflux_celery_beat` | — | Scheduler de tareas periódicas |
| `crediflux_mailhog` | 8025/8625 | Email testing (dev) |
| `crediflux_docs` | 3001/3601 | Documentación |

---

## 3. Módulos del Sistema

### 3.1 Core (`apps.core`)
- Health checks del sistema
- Búsqueda global (clientes, préstamos, pagos)
- Servicio de consulta RNC/Cédula en la DGII
- Temas de UI por tenant

### 3.2 Tenants (`apps.tenants`)
- Gestión de tenants (financieras)
- Configuración por tenant (moneda, tasas, colores, etc.)
- Dominios y subdominios
- Login por tenant

### 3.3 Users (`apps.users`)
- Autenticación JWT (access + refresh tokens)
- Perfiles de usuario con foto
- Autenticación de dos factores (2FA con TOTP)
- Gestión de equipo (crear, editar, desactivar usuarios)
- Roles: admin, loan_officer, collector, cashier, analyst
- Reseteo y cambio de contraseña

### 3.4 Loans (`apps.loans`) — Módulo Principal
- **Clientes**: CRUD completo con cédula-first, multi-contacto, documentos
- **Préstamos**: Solicitud → Aprobación → Desembolso → Cobro → Cierre
- **Amortización**: 4 métodos (Francés, Flat, Saldo Insoluto, Alemán)
- **Pagos**: Registro con múltiples métodos, recibos PDF
- **Garantes**: Hasta 3 por préstamo
- **Colaterales**: Vehículos, propiedades, equipos, etc.
- **Tareas**: Asignación de tareas a oficiales de crédito

### 3.5 Billing (`apps.billing`)
- Facturación electrónica (e-CF) con la DGII
- Secuencias fiscales (e-NCF)
- Certificados digitales para firma XML
- Proveedores PSFE (DGMax, EF2, DGII Directo)
- Envío y consulta de comprobantes

### 3.6 Cashbox (`apps.cashbox`)
- Registros de caja (cajas físicas o lógicas)
- Sesiones de caja (apertura con balance, cierre con conteo)
- Movimientos (ingresos, egresos, ajustes)
- Conteo de denominaciones (billetes y monedas RD$)

### 3.7 Communications (`apps.communications`)
- Integración WhatsApp Business API (via pywa)
- Envío automático de confirmaciones de pago
- Avisos de mora (15, 30, 60, 90 días)
- Historial de conversaciones

### 3.8 AI (`apps.ai`)
- Asistente inteligente con djangosdk
- 3 modos: Rápido, Completo, Analista
- 7 herramientas: búsqueda de clientes, análisis de riesgo, dashboard, proyecciones

### 3.9 Audit (`apps.audit`)
- Registro automático de todas las operaciones
- Quién hizo qué, cuándo, desde dónde
- Filtros por fecha, usuario, acción, modelo

---

## 4. Flujo de Uso Completo

### Flujo Principal: De Solicitud a Pago Completado

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DE UN PRÉSTAMO                      │
│                                                              │
│  1. REGISTRO DE CLIENTE                                      │
│     └── Ingresar cédula → Auto-poblar datos DGII            │
│     └── Completar: contactos, dirección, empleo              │
│     └── Subir documentos (cédula, ingresos, etc.)            │
│                                                              │
│  2. SOLICITUD DE PRÉSTAMO                                    │
│     └── Seleccionar cliente existente                        │
│     └── Definir: monto, plazo, tasa, frecuencia, tipo       │
│     └── Seleccionar método de amortización                   │
│     └── Agregar garantes (si aplica)                         │
│     └── Agregar colaterales (si aplica)                      │
│     └── Estado: PENDIENTE                                    │
│                                                              │
│  3. EVALUACIÓN Y APROBACIÓN                                  │
│     └── Oficial de crédito revisa solicitud                  │
│     └── Verificar documentos del cliente                     │
│     └── Consultar historial crediticio                       │
│     └── AI: Análisis de riesgo automático                    │
│     └── Aprobar / Rechazar / Solicitar más info              │
│     └── Estado: APROBADO o RECHAZADO                         │
│                                                              │
│  4. DESEMBOLSO                                               │
│     └── Generar tabla de amortización (schedule)             │
│     └── Crear contrato digital                               │
│     └── Firmar contrato (firma electrónica)                  │
│     └── Registrar desembolso                                 │
│     └── Enviar confirmación por WhatsApp                     │
│     └── Estado: ACTIVO                                       │
│                                                              │
│  5. COBRO PERIÓDICO                                          │
│     └── Cuotas generadas automáticamente                     │
│     └── Cobrador visita cliente (geolocalización)            │
│     └── Registrar pago (efectivo/transferencia/tarjeta)      │
│     └── Generar recibo PDF automático                        │
│     └── Enviar confirmación WhatsApp                         │
│     └── Actualizar saldo del préstamo                        │
│                                                              │
│  6. SEGUIMIENTO DE MORA                                      │
│     └── Cuotas vencidas marcadas automáticamente             │
│     └── Avisos WhatsApp: 15, 30, 60, 90 días                │
│     └── Vista móvil del cobrador con urgencia                │
│     └── Cargos por mora (si configurado)                     │
│                                                              │
│  7. CIERRE                                                   │
│     └── Última cuota pagada                                  │
│     └── Liberar colaterales                                  │
│     └── Estado: PAGADO                                       │
│     └── Generar estado de cuenta final (PDF)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Gestión de Clientes

### 5.1 Registro de Cliente (Cédula-First)

El formulario de nuevo cliente está optimizado para el flujo dominicano:

**Paso 1 — Identificación** (lo más importante primero)
- Tipo de ID: Cédula, Pasaporte, RNC
- **Número de cédula**: Al ingresar y salir del campo, el sistema consulta la DGII automáticamente y llena:
  - Nombre completo
  - Fecha de nacimiento
  - Dirección registrada

**Paso 2 — Datos Personales**
- Nombre, segundo nombre, apellido
- Fecha de nacimiento, género
- Foto del cliente (opcional)

**Paso 3 — Contacto** (Multi-contacto)
- **Teléfonos**: Hasta 5 números con tipo (Celular, Casa, Oficina, Fijo, WhatsApp)
  - Marcar teléfono principal con estrella ⭐
  - Marcar cuáles tienen WhatsApp
- **Emails**: Hasta 3 con tipo (Personal, Trabajo, Empresa)
  - Marcar email principal

**Paso 4 — Dirección**
- Dirección línea 1 y 2
- Ciudad, Provincia, Código postal, País

**Paso 5 — Empleo**
- Estado laboral: Empleado, Independiente, Desempleado, Jubilado
- Nombre del empleador
- Ocupación
- **Fecha de ingreso al empleo** (para evaluar estabilidad laboral)
- Ingreso mensual (RD$)

**Paso 6 — Notas**
- Observaciones adicionales sobre el cliente

### 5.2 Documentos del Cliente

Tipos de documentos soportados:
- Cédula / Pasaporte
- Comprobante de ingresos
- Estado de cuenta bancario
- Comprobante de domicilio
- Carta de empleo
- Declaración de impuestos
- Licencia de negocio
- Factura de servicios
- Contrato / Acuerdo
- Otros

Cada documento tiene un estado de verificación: Pendiente → Verificado / Rechazado / Expirado

### 5.3 Estados del Cliente

| Estado | Descripción |
|--------|-------------|
| **Activo** | Cliente habilitado para solicitar préstamos |
| **Inactivo** | Cliente temporalmente deshabilitado |
| **Blacklisted** | Cliente bloqueado (historial negativo) |

---

## 6. Gestión de Préstamos

### 6.1 Tipos de Préstamo

| Tipo | Descripción |
|------|-------------|
| Personal | Préstamo personal sin garantía específica |
| Auto | Préstamo para vehículo (colateral: vehículo) |
| Hipotecario | Préstamo con garantía inmobiliaria |
| Negocio | Préstamo empresarial |
| Estudiantil | Préstamo educativo |
| Payday | Préstamo a corto plazo (nómina) |

### 6.2 Métodos de Amortización

CrediFlux soporta 4 métodos de cálculo de cuotas:

#### Método Francés (Cuota Fija)
- La cuota mensual es **constante** durante todo el plazo
- Al inicio se paga más interés y menos capital
- Al final se paga más capital y menos interés
- Fórmula: `Cuota = P × [r(1+r)^n] / [(1+r)^n - 1]`
- **El más usado en RD**

#### Método Flat (Interés Plano)
- Interés calculado sobre el **monto original** durante todo el plazo
- Cuota constante pero más cara que el francés
- Fórmula: `Cuota = (P + P × r × n) / n`
- **Común en financieras pequeñas**

#### Saldo Insoluto (Interés sobre Saldo)
- Interés calculado sobre el **saldo pendiente** de cada período
- Capital fijo, interés decreciente → cuota decreciente
- Primera cuota es la más alta, última la más baja

#### Método Alemán
- Similar al saldo insoluto: capital fijo + interés sobre saldo
- Cuotas decrecientes
- Favorece al cliente: paga menos intereses en total

### 6.3 Frecuencias de Pago

| Frecuencia | Descripción |
|-----------|-------------|
| Diario | Cobro diario (microfinanzas) |
| Semanal | Cobro cada 7 días |
| Quincenal | Cobro cada 15 días |
| Mensual | Cobro mensual (el más común) |
| Trimestral | Cobro cada 3 meses |

### 6.4 Ciclo de Vida del Préstamo

```
PENDIENTE → APROBADO → ACTIVO → PAGADO
    │           │                    
    │           └→ RECHAZADO         
    │                                
    └→ RECHAZADO   ACTIVO → INCUMPLIDO → CASTIGADO
```

| Estado | Descripción |
|--------|-------------|
| **Pendiente** | Solicitud en revisión |
| **Aprobado** | Solicitud aprobada, pendiente de desembolso |
| **Activo** | Préstamo desembolsado, en cobro |
| **Pagado** | Todas las cuotas pagadas |
| **Incumplido** | Mora grave, en gestión de cobro |
| **Castigado** | Préstamo dado de baja (pérdida) |
| **Rechazado** | Solicitud no aprobada |

### 6.5 Tabla de Amortización (Schedule)

Al aprobar un préstamo, el sistema genera automáticamente la tabla de amortización con:
- Número de cuota
- Fecha de vencimiento
- Monto de capital
- Monto de interés
- Cargo por mora (si aplica)
- Monto total de la cuota
- Saldo pendiente
- Estado: Pendiente / Pagado / Vencido / Parcial / Castigado

### 6.6 Garantes

- Hasta 3 garantes por préstamo
- Cada garante incluye:
  - Datos personales (nombre, cédula, fecha de nacimiento)
  - Contacto (teléfono, email)
  - Dirección
  - Relación con el cliente (Cónyuge, Familiar, Amigo, Colega, Socio)
  - Documentos (cédula, comprobante de ingresos)
  - Empleador, ocupación, ingreso mensual

### 6.7 Colaterales

Tipos soportados:
- **Vehículo**: Marca, modelo, año, VIN, valor estimado
- **Propiedad/Inmueble**: Dirección, escritura, valor catastral
- **Equipo**: Descripción, serial, valor
- **Inventario**: Lista de bienes, valor estimado
- **Valores/Acciones**: Tipo, cantidad, valor de mercado
- **Depósito en Efectivo**: Monto, banco, número de cuenta
- **Otros**: Descripción libre

Estados del colateral: Activo → Liberado / Liquidado

---

## 7. Cobros y Pagos

### 7.1 Registro de Pago

Para registrar un pago:
1. Seleccionar el préstamo
2. Seleccionar la(s) cuota(s) a pagar
3. Ingresar monto recibido
4. Seleccionar método de pago:
   - Efectivo
   - Cheque
   - Transferencia bancaria
   - Tarjeta de crédito/débito
   - Pago móvil
5. Agregar notas (opcional)
6. Confirmar pago

### 7.2 Acciones Automáticas al Registrar Pago

Cuando se registra un pago, el sistema automáticamente:
- Actualiza el estado de la(s) cuota(s) afectada(s)
- Recalcula el saldo pendiente del préstamo
- Genera un **recibo en PDF** descargable
- Envía **confirmación por WhatsApp** al cliente (si está habilitado)
- Registra la transacción en la **auditoría**
- Actualiza el **estado de cuenta** del cliente

### 7.3 Recibo de Pago (PDF)

El recibo incluye:
- Logo y datos de la financiera
- Número de recibo
- Datos del cliente (nombre, cédula)
- Número del préstamo
- Detalle del pago (fecha, monto, método)
- Saldo anterior y nuevo saldo
- Firma del cajero
- Código QR de verificación (opcional)

### 7.4 Estado de Cuenta del Cliente (PDF)

Reporte completo con:
- Datos del cliente
- Todos los préstamos (activos e históricos)
- Historial de pagos de cada préstamo
- Saldos pendientes
- Resumen financiero global

---

## 8. Facturación Electrónica (e-CF)

### 8.1 Integración con la DGII

CrediFlux soporta la emisión de Comprobantes Fiscales Electrónicos (e-CF) según la normativa de la DGII:

**Tipos de e-CF soportados:**
| Código | Tipo |
|--------|------|
| 31 | Factura de Crédito Fiscal Electrónica |
| 32 | Factura de Consumo Electrónica |
| 33 | Nota de Débito Electrónica |
| 34 | Nota de Crédito Electrónica |
| 41 | Compras Electrónico |
| 43 | Gastos Menores Electrónico |
| 44 | Regímenes Especiales Electrónico |
| 45 | Gubernamental Electrónico |
| 46 | Comprobante de Exportaciones |
| 47 | Pagos al Exterior |

### 8.2 Ambientes DGII

| Ambiente | URL Base | Uso |
|----------|---------|-----|
| **testecf** (Pre-Certificación) | `ecf.dgii.gov.do/testecf` | Pruebas y desarrollo |
| **certecf** (Certificación) | `ecf.dgii.gov.do/certecf` | Proceso de certificación |
| **ecf** (Producción) | `ecf.dgii.gov.do/ecf` | Operación real |

### 8.3 Proveedores e-CF

CrediFlux soporta 3 proveedores con patrón Strategy:

| Proveedor | Tipo | Descripción |
|-----------|------|-------------|
| **DGII Directo** | Certificado propio | La financiera tiene su certificado digital y envía directamente |
| **DGMax.do** | PSFE | Proveedor de servicios de facturación electrónica |
| **EF2.do** | PSFE | Proveedor alternativo de facturación electrónica |

### 8.4 Flujo de Facturación

```
1. Generar XML del e-CF (ecf_generator.py)
2. Firmar XML con certificado digital (ecf_signer.py)
3. Obtener semilla de la DGII (dgii_auth.py)
4. Firmar semilla y obtener token JWT
5. Enviar e-CF firmado a la DGII (dgii_client.py)
6. Recibir respuesta: Aceptado / Rechazado / Condicional
7. Almacenar resultado y trackingId
```

### 8.5 Certificados Digitales

- Formato: `.p12` / `.pfx`
- Gestión desde `/billing/certificates`
- Soporte para múltiples certificados (rotación)
- Cada certificado tiene: nombre, emisor, fecha de validez, estado activo/inactivo

### 8.6 Secuencias Fiscales (e-NCF)

- Gestión de rangos autorizados por la DGII
- Secuencia automática por tipo de comprobante
- Alertas cuando quedan pocos números disponibles

### 8.7 Nota sobre ITBIS

- **Intereses de préstamos**: EXENTOS de ITBIS en RD
- **Comisiones de servicio**: Pagan 18% de ITBIS
- La tasa usuraria la define la Junta Monetaria

---

## 9. Caja (Cash Management)

### 9.1 Cajas Registradoras

Cada financiera puede tener múltiples cajas:
- **Caja Principal** — oficina central
- **Caja Cobros** — ventanilla de cobros
- **Caja Móvil** — cobrador en ruta

### 9.2 Sesión de Caja

**Apertura:**
1. Seleccionar caja
2. Ingresar balance de apertura (RD$)
3. Notas opcionales

**Durante la sesión:**
- Registrar ingresos (pagos recibidos)
- Registrar egresos (desembolsos, gastos)
- Registrar ajustes

**Cierre:**
1. Realizar conteo físico de denominaciones
2. El sistema compara el conteo con el saldo esperado
3. Registrar diferencia (sobrante/faltante)
4. Cerrar sesión

### 9.3 Conteo de Denominaciones

Billetes RD$: 2000, 1000, 500, 200, 100, 50
Monedas RD$: 25, 10, 5, 1

El cajero ingresa la cantidad de cada denominación y el sistema calcula el total automáticamente.

---

## 10. Cobranza y Geolocalización

### 10.1 Vista del Cobrador Móvil (`/collector`)

Interfaz optimizada para móvil con:
- **Header fijo**: Fecha, filtros rápidos, búsqueda
- **Chips de filtro**: Todos, Esta Semana, Este Mes, Críticos
- **Tarjetas expandibles** por cliente morado con:
  - Nombre del cliente
  - Días de atraso
  - Monto pendiente
  - Número de préstamo
  - **Código de color por urgencia**:
    - 🟡 Amarillo: 1-7 días (Reciente)
    - 🟠 Naranja: 8-30 días (Urgente)
    - 🔴 Rojo: 31-60 días (Crítico)
    - 🔴 Rojo oscuro: 60+ días (Severo)

### 10.2 Acciones Rápidas del Cobrador

- 📞 **Llamar**: Marca el teléfono del cliente directamente
- 💬 **WhatsApp**: Abre chat de WhatsApp con el cliente
- 💰 **Registrar Pago**: Formulario rápido de pago en campo

### 10.3 Geolocalización

**Visitas del Cobrador (`CollectorVisit`):**
- Check-in GPS al llegar al cliente
- Check-out GPS al salir
- Duración de la visita
- Resultado: Pagó, No pagó, No encontrado, Reprogramado
- Notas de la visita

**Ubicación en Tiempo Real (`CollectorLocation`):**
- Pings periódicos del dispositivo del cobrador
- Reconstrucción de ruta del día
- Estadísticas: distancia recorrida, clientes visitados

---

## 11. Comunicaciones (WhatsApp)

### 11.1 Configuración

Cada tenant configura su integración WhatsApp:
- Phone Number ID (Meta Business API)
- Token de acceso
- Business Account ID
- Verify Token (para webhook)
- App Secret

### 11.2 Notificaciones Automáticas

| Evento | Mensaje |
|--------|---------|
| **Pago recibido** | Confirmación con monto, préstamo, saldo restante |
| **15 días de mora** | Recordatorio amable de cuota vencida |
| **30 días de mora** | Aviso más urgente con monto acumulado |
| **60 días de mora** | Alerta de mora grave |
| **90 días de mora** | Notificación de posible acción legal |

### 11.3 Tareas Celery

- `send_payment_confirmation`: Envía al pagar
- `send_overdue_notice`: Envía al vencerse
- `send_payment_reminders`: Batch diario de recordatorios
- `send_tenant_payment_reminders`: Por tenant con configuración propia

---

## 12. Contratos Digitales

### 12.1 Plantillas de Contrato

- Editor de plantillas con variables dinámicas
- Variables disponibles: `{nombre_cliente}`, `{cedula}`, `{monto}`, `{tasa}`, `{plazo}`, `{cuota}`, etc.
- Múltiples plantillas por tipo de préstamo

### 12.2 Generación de Contrato

1. Seleccionar préstamo aprobado
2. Seleccionar plantilla
3. El sistema reemplaza las variables automáticamente
4. Generar contrato PDF

### 12.3 Firma Electrónica

- Se genera un **token único** por contrato
- Se envía **enlace de firma** al cliente (email/WhatsApp)
- El cliente accede a `/sign/{token}` (vista pública, sin login)
- Revisa el contrato y firma digitalmente
- El sistema registra: IP, timestamp, user agent
- El contrato queda marcado como firmado

---

## 13. Asistente AI

### 13.1 Descripción

CrediFlux integra un asistente AI powered by **djangosdk** que ayuda a los usuarios a consultar datos del sistema, analizar riesgo crediticio y realizar cálculos de préstamos usando lenguaje natural.

### 13.2 Modos de Agente

| Modo | Descripción | Tokens | Acceso a Datos |
|------|-------------|--------|----------------|
| ⚡ **Rápido** (Lite) | Preguntas generales, cálculos, conceptos | ~200 | No |
| 🤖 **Completo** (Assistant) | Consultas con herramientas del sistema | ~5000 | Sí |
| 🧠 **Analista** (Analyst) | Análisis profundo de riesgo crediticio | ~5000 | Sí |

### 13.3 Herramientas AI Disponibles (Modo Completo/Analista)

| Herramienta | Función |
|-------------|----------|
| `buscar_cliente` | Busca clientes por nombre, cédula o teléfono |
| `resumen_cliente` | Obtiene resumen completo de un cliente (datos + préstamos) |
| `analizar_riesgo_cliente` | Evalúa riesgo crediticio basado en historial |
| `dashboard_resumen` | Estadísticas generales (cartera, mora, cobros) |
| `clientes_en_mora` | Lista de clientes con pagos vencidos |
| `calcular_prestamo` | Calcula cuotas con cualquier método de amortización |
| `proyeccion_cobros` | Proyección de cobros esperados por período |

### 13.4 Ejemplos de Uso

```
Usuario: "¿Cuánto sería la cuota de un préstamo de RD$200,000 a 3% mensual por 18 meses?"
Agente: Calcula y muestra tabla resumida con cuota, interés total, y monto total

Usuario: "¿Quiénes son los clientes más morosos?"
Agente: Consulta clientes_en_mora y presenta lista con montos y días de atraso

Usuario: "Analiza el riesgo de Juan Pérez 001-1234567-8"
Agente: Busca cliente, revisa historial, evalúa capacidad de pago, emite recomendación
```

### 13.5 Proveedores AI Soportados

djangsdk usa LiteLLM, soportando 12+ proveedores:
- Groq (LLaMA 3.3 70B) — free tier disponible
- Google Gemini (2.0 Flash) — free tier disponible
- Anthropic Claude
- OpenAI GPT-4
- Mistral, Cohere, Fireworks, Together, y más

Cambiar de proveedor es una sola línea en el `.env`:
```env
AI_DEFAULT_MODEL=groq/llama-3.3-70b-versatile
# o
AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
# o
AI_DEFAULT_MODEL=anthropic/claude-3-5-sonnet
```

---

## 14. Reportes DGII (606/607)

### 14.1 Formato 606 — Compras y Gastos

Reporte mensual que la financiera presenta a la DGII con:
- RNC/Cédula del proveedor
- Tipo de comprobante
- Número de NCF
- Fecha del comprobante
- Monto facturado
- ITBIS facturado
- ITBIS retenido
- Forma de pago

### 14.2 Formato 607 — Ventas

Reporte mensual de ventas/ingresos:
- RNC/Cédula del cliente
- Tipo de comprobante
- Número de NCF
- Fecha del comprobante
- Monto facturado
- ITBIS facturado
- Tipo de ingreso

### 14.3 Generación

Desde `/billing/dgii-reports`:
1. Seleccionar período (Año + Mes)
2. El sistema genera el reporte automáticamente
3. Vista previa en tabla con todos los registros
4. Descargar como CSV en formato DGII oficial

---

## 15. Auditoría

### 15.1 Registro Automático

El sistema registra automáticamente:
- **Quién**: Usuario que realizó la acción
- **Qué**: Modelo y campo afectado + valores anteriores/nuevos
- **Cuándo**: Timestamp exacto
- **Desde dónde**: IP y User Agent
- **Tipo**: Crear, Actualizar, Eliminar, Login, Logout, Otro

### 15.2 Vista de Auditoría (`/audit`)

- Lista cronológica de todos los eventos
- Filtros por:
  - Rango de fechas
  - Usuario
  - Tipo de acción (CRUD)
  - Modelo afectado
- Detalle expandible con JSON de cambios
- Estadísticas: total de eventos, usuarios más activos, modelos más modificados

---

## 16. Configuración del Tenant

### 16.1 Configuración General (`/settings/general`)

| Campo | Descripción | Ejemplo |
|-------|-------------|----------|
| Nombre | Nombre de la financiera | "Financiera XYZ" |
| Tax ID (RNC) | Número de RNC | 131-12345-6 |
| Moneda | Moneda principal | DOP |
| Símbolo | Símbolo de moneda | RD$ |
| Teléfono | Teléfono principal | 809-555-1234 |
| Email | Email de la empresa | info@financieraxyz.com |
| Dirección | Dirección fiscal | Av. Winston Churchill #1234, Santo Domingo |
| Logo | Logo de la financiera | Archivo imagen |
| Color primario | Color de marca | #163300 |

### 16.2 Configuración de Préstamos (`/settings/loans`)

| Campo | Descripción | Default |
|-------|-------------|----------|
| Tasa de interés por defecto | Tasa mensual | 3.0% |
| Método de amortización | Método por defecto | Francés |
| Plazo máximo | Meses máximo | 60 |
| Monto mínimo | Préstamo mínimo | RD$ 5,000 |
| Monto máximo | Préstamo máximo | RD$ 5,000,000 |
| Mora automática | Días gracia antes de mora | 5 |
| Tasa de mora | Penalización por mora | 2% |
| Requiere garante | A partir de qué monto | RD$ 50,000 |

### 16.3 Configuración e-CF

| Campo | Descripción |
|-------|-------------|
| Proveedor e-CF | direct / dgmax / ef2 |
| Ambiente DGII | testecf / certecf / ecf |
| API Key | Clave del proveedor |
| API Secret | Secreto del proveedor |
| Certificado digital | .p12 con contraseña |
| Recordatorios WhatsApp | Activar/desactivar |

---

## 17. Gestión de Usuarios y Roles

### 17.1 Roles del Sistema

| Rol | Permisos |
|-----|----------|
| **admin** | Acceso total: configuración, usuarios, reportes, todos los módulos |
| **loan_officer** | Gestión de clientes, préstamos, aprobaciones, contratos |
| **collector** | Vista de cobros, registrar pagos, geolocalización |
| **cashier** | Gestión de caja, recibir pagos, generar recibos |
| **analyst** | Reportes, dashboard, DGII, auditoría (solo lectura) |

### 17.2 Autenticación

- **JWT**: Access token (15 min) + Refresh token (7 días)
- **2FA**: TOTP compatible con Google Authenticator, Authy, etc.
- **Códigos de respaldo**: 10 códigos de uso único para emergencias
- **Reset de contraseña**: Via email con token temporal

### 17.3 Gestión de Equipo (`/users`)

- Crear nuevos usuarios con rol asignado
- Activar/desactivar cuentas
- Editar perfiles y permisos
- Ver actividad reciente de cada usuario

---

## 18. Calculadora de Préstamos

### 18.1 Calculadora Pública (`/calculator`)

Herramienta de cálculo disponible sin necesidad de crear un préstamo:

**Entradas:**
- Monto del préstamo (RD$)
- Tasa de interés mensual (%)
- Plazo (meses)
- Frecuencia de pago
- Método de amortización

**Salidas:**
- Cuota periódica
- Total de intereses
- Monto total a pagar
- Tabla de amortización completa
- Gráficos: distribución capital vs interés, evolución del saldo

### 18.2 API de Calculadora

4 endpoints para integrar en otros sistemas:

```
POST /api/loans/calculate/

Body:
{
  "principal": 100000,
  "monthly_rate": 3.0,
  "term_months": 24,
  "method": "french"  // flat, saldo_insoluto, german
}

Response:
{
  "monthly_payment": 5871.53,
  "total_interest": 40916.72,
  "total_amount": 140916.72,
  "schedule": [
    {
      "period": 1,
      "payment": 5871.53,
      "principal": 2871.53,
      "interest": 3000.00,
      "balance": 97128.47
    },
    ...
  ]
}
```

---

## 19. API Reference

### 19.1 Autenticación

Todas las API requieren JWT token (excepto las públicas):

```
POST /api/auth/login/
Body: {"email": "user@financiera.com", "password": "..."}
Response: {"access": "eyJ...", "refresh": "eyJ..."}

Headers para requests autenticados:
Authorization: Bearer eyJ...
```

### 19.2 Endpoints Principales

#### Core
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/core/health/` | Health check |
| GET | `/api/core/search/?q=term` | Búsqueda global |
| GET | `/api/core/validate-rnc/?rnc=123456789` | Validar RNC en DGII |
| GET | `/api/core/ui-theme/` | Tema visual del tenant |

#### Clientes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/customers/` | Listar clientes |
| POST | `/api/loans/customers/` | Crear cliente |
| GET | `/api/loans/customers/{id}/` | Detalle de cliente |
| PUT | `/api/loans/customers/{id}/` | Actualizar cliente |
| DELETE | `/api/loans/customers/{id}/` | Eliminar cliente |
| GET | `/api/loans/customers/{id}/statement-pdf/` | Estado de cuenta PDF |
| POST | `/api/loans/customer-phones/` | Agregar teléfono |
| POST | `/api/loans/customer-emails/` | Agregar email |
| POST | `/api/loans/customer-documents/` | Subir documento |

#### Préstamos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/` | Listar préstamos |
| POST | `/api/loans/` | Crear préstamo |
| GET | `/api/loans/{id}/` | Detalle de préstamo |
| PUT | `/api/loans/{id}/` | Actualizar préstamo |
| POST | `/api/loans/{id}/approve/` | Aprobar préstamo |
| POST | `/api/loans/{id}/reject/` | Rechazar préstamo |
| POST | `/api/loans/{id}/disburse/` | Desembolsar |
| GET | `/api/loans/stats/` | Estadísticas generales |

#### Pagos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/payments/` | Listar pagos |
| POST | `/api/loans/payments/` | Registrar pago |
| GET | `/api/loans/payments/{id}/` | Detalle de pago |
| GET | `/api/loans/payments/{id}/receipt-pdf/` | Recibo PDF |
| GET | `/api/loans/payments/{id}/receipt-preview/` | Vista previa recibo |

#### Amortización
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/loans/schedules/` | Listar cuotas |
| GET | `/api/loans/schedules/overdue/` | Cuotas vencidas |
| POST | `/api/loans/calculate/` | Calculadora |

#### Garantes y Colaterales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/loans/guarantors/` | CRUD garantes |
| GET/POST | `/api/loans/collaterals/` | CRUD colaterales |

#### Facturación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/billing/invoices/` | CRUD facturas |
| GET/POST | `/api/billing/sequences/` | Secuencias NCF |
| GET/POST | `/api/billing/certificates/` | Certificados digitales |
| GET | `/api/billing/dgii-reports/` | Reportes DGII |
| POST | `/api/billing/submissions/` | Enviar e-CF |
| GET | `/api/billing/ecf-provider/config/` | Config del proveedor |

#### Caja
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/cashbox/registers/` | Cajas registradoras |
| GET/POST | `/api/cashbox/sessions/` | Sesiones de caja |
| POST | `/api/cashbox/sessions/{id}/close/` | Cerrar sesión |
| GET/POST | `/api/cashbox/movements/` | Movimientos |
| POST | `/api/cashbox/denominations/` | Conteo denominaciones |

#### Comunicaciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/communications/whatsapp/conversations/` | Conversaciones |

#### AI
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/ai/chat/` | Chat con agente AI |
| GET | `/api/ai/agents/` | Lista de agentes disponibles |

#### Contratos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/loans/contract-templates/` | Plantillas |
| GET/POST | `/api/loans/contracts/` | Contratos |
| GET | `/api/loans/public/contracts/{token}/` | Vista pública (sin auth) |
| POST | `/api/loans/public/contracts/{token}/sign/` | Firmar (sin auth) |

#### Cobranza
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET/POST | `/api/loans/collection-contacts/` | Contactos de cobro |
| GET/POST | `/api/loans/collection-reminders/` | Recordatorios |
| GET/POST | `/api/loans/collector-visits/` | Visitas del cobrador |
| GET/POST | `/api/loans/collector-locations/` | Ubicaciones GPS |

#### Usuarios
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Login (JWT) |
| POST | `/api/auth/logout/` | Logout |
| GET | `/api/users/profile/` | Perfil actual |
| PUT | `/api/users/profile/update/` | Actualizar perfil |
| POST | `/api/users/profile/change-password/` | Cambiar contraseña |
| GET | `/api/users/team/` | Listar equipo |
| POST | `/api/users/team/create/` | Crear usuario |
| POST | `/api/auth/2fa/setup/` | Configurar 2FA |
| POST | `/api/auth/2fa/verify/` | Verificar código 2FA |

#### Tenant
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/tenants/settings/` | Configuración del tenant |
| PUT | `/api/tenants/settings/` | Actualizar configuración |
| GET | `/api/tenants/health/` | Health check del tenant |

---

## 20. Despliegue e Infraestructura

### 20.1 Requisitos del Servidor

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disco | 20 GB SSD | 50 GB SSD |
| OS | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Docker | 24.0+ | 29.0+ |

### 20.2 Variables de Entorno (`.env`)

```env
# Base de datos
DB_NAME=crediflux_db
DB_USER=crediflux_user
DB_PASSWORD=<seguro>
DB_HOST=db
DB_PORT=5432

# Django
SECRET_KEY=<django-secret-key>
DEBUG=False
ALLOWED_HOSTS=*

# Redis
REDIS_URL=redis://redis:6379/0

# AI
AI_DEFAULT_PROVIDER=groq
AI_DEFAULT_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=<groq-key>

# Email (producción)
EMAIL_HOST=smtp.ejemplo.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@financiera.com
EMAIL_HOST_PASSWORD=<password>

# WhatsApp
WHATSAPP_PHONE_ID=<phone-number-id>
WHATSAPP_TOKEN=<meta-token>
```

### 20.3 Despliegue con Docker Compose

```bash
# Clonar el repositorio
git clone https://github.com/sweetmedia/CrediFlux.git
cd CrediFlux

# Configurar variables
cp .env.example .env
nano .env

# Levantar todo
cd docker
docker compose up -d --build

# Correr migraciones
docker compose exec backend python manage.py migrate_schemas

# Crear superusuario
docker compose exec backend python manage.py createsuperuser

# Crear tenant inicial
docker compose exec backend python manage.py create_tenant
```

### 20.4 Modelo de Precios (SaaS)

| Plan | Precio/mes | Módulos Incluidos |
|------|------------|-------------------|
| **Starter** | $29 USD | Préstamos + Facturación básica |
| **Professional** | $59 USD | + Caja + WhatsApp + Contratos + AI |
| **Enterprise** | $99 USD | + Geolocalización + Reportes DGII + Auditoría + API |
| **Custom** | $39+ USD | Módulos a la carta |

---

## Apéndice A: Glosario

| Término | Definición |
|---------|------------|
| **Amortización** | Proceso de pago gradual de un préstamo |
| **Colateral** | Bien que garantiza un préstamo |
| **Cuota** | Pago periódico que incluye capital + intereses |
| **DGII** | Dirección General de Impuestos Internos (RD) |
| **DOP** | Peso Dominicano (moneda oficial) |
| **e-CF** | Comprobante Fiscal Electrónico |
| **e-NCF** | Número de Comprobante Fiscal Electrónico |
| **Garante** | Persona que respalda un préstamo |
| **ITBIS** | Impuesto sobre Transferencias de Bienes y Servicios (18%) |
| **Mora** | Atraso en el pago de una cuota |
| **NCF** | Número de Comprobante Fiscal |
| **PSFE** | Proveedor de Servicios de Facturación Electrónica |
| **RNC** | Registro Nacional de Contribuyentes |
| **Saldo Insoluto** | Capital pendiente de pago |
| **Tenant** | Financiera/organización con espacio aislado en el sistema |

## Apéndice B: Contacto y Soporte

- **Desarrollado por**: Sweet Media Digital Agency
- **Email**: soporte@crediflux.app
- **Discord**: Canal #crediflux-general
- **Documentación**: http://servidor:3601

---

*CrediFlux v1.0 — Diseñado para financieras dominicanas, construido con tecnología moderna.*