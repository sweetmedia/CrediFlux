# Resumen Técnico — Facturación Electrónica DGII (e-CF)

> Fuente: DGII República Dominicana | Versión 1.6 (Junio 2023)
> Formato e-CF v1.0 (Octubre 2025) | 89 páginas de especificación

---

## 1. Tipos de Comprobantes Fiscales Electrónicos (e-CF)

| Código | Tipo | Uso |
|--------|------|-----|
| **31** | Factura de Crédito Fiscal Electrónica | Ventas B2B con crédito fiscal |
| **32** | Factura de Consumo Electrónica | Ventas al consumidor final |
| **33** | Nota de Débito Electrónica | Correcciones a favor del emisor |
| **34** | Nota de Crédito Electrónica | Correcciones a favor del comprador |
| **41** | Compras Electrónico | Registro de compras |
| **43** | Gastos Menores Electrónico | Gastos menores |
| **44** | Regímenes Especiales Electrónico | Regímenes especiales |
| **45** | Gubernamental Electrónico | Ventas al gobierno |
| **46** | Comprobante de Exportaciones Electrónico | Exportaciones |
| **47** | Comprobante para Pagos al Exterior Electrónico | Pagos internacionales |

**Para CrediFlux:** Principalmente usaremos **31** (crédito fiscal B2B) y **32** (consumo).

---

## 2. Ambientes de la DGII

| Ambiente | Dominio Base | Propósito |
|----------|-------------|-----------|
| **Pre-Certificación** | `https://ecf.dgii.gov.do/testecf/` | Pruebas (secuencias 1-10M, datos se borran en 60 días) |
| **Certificación** | `https://ecf.dgii.gov.do/certecf/` | Validación de capacidades antes de producción |
| **Producción** | `https://ecf.dgii.gov.do/ecf/` | Envíos con validez fiscal |

Cada ambiente tiene documentación Swagger (OpenAPI) en:
`https://ecf.dgii.gov.do/{ambiente}/{servicio}/help/index.html`

---

## 3. Servicios Web (API REST)

### 3.1. Autenticación (OAuth-like con Semilla + Firma Digital)

**Flujo:**
1. `GET /api/autenticacion/semilla` → Recibe XML con valor semilla
2. Firmar la semilla con certificado digital del contribuyente
3. `POST /api/autenticacion/validarsemilla` → Enviar semilla firmada → Recibe token JWT (1 hora)
4. Usar token en header: `Authorization: Bearer {token}`

**URLs:**
- Pre-cert: `https://ecf.dgii.gov.do/testecf/autenticacion`
- Cert: `https://ecf.dgii.gov.do/certecf/autenticacion`
- Prod: `https://ecf.dgii.gov.do/ecf/autenticacion`

### 3.2. Recepción de e-CF

**Endpoint:** `POST /api/facturaselectronicas`
- Enviar XML del e-CF firmado digitalmente
- Respuesta: `TrackId` para consultar estado
- **Facturas de Consumo (32) < RD$250,000**: NO van aquí, van al servicio de Resumen FC

**URLs:**
- Pre-cert: `https://ecf.dgii.gov.do/testecf/recepcion`
- Cert: `https://ecf.dgii.gov.do/certecf/recepcion`
- Prod: `https://ecf.dgii.gov.do/ecf/recepcion`

### 3.3. Recepción de Resumen Factura de Consumo

Para Facturas de Consumo (32) con monto < RD$250,000.
- **URLs:** `https://fc.dgii.gov.do/{ambiente}/...`

### 3.4. Consulta Resultado

Consultar estado de un e-CF enviado usando el `TrackId`.

### 3.5. Consulta Estado

Verificar estado de los servicios de la DGII.

### 3.6. Consulta Directorio

Consultar si un RNC es emisor electrónico certificado.

### 3.7. Anulación de Rangos

Anular secuencias de e-NCF no utilizadas.

### 3.8. Servicio Emisor-Receptor (Entre contribuyentes)

- `EmisionComprobantes` — Enviar e-CF al receptor
- `RecepcioneCF` — Recibir e-CF como receptor
- `Consulta de acuse de recibo`

---

## 4. Estructura del XML (e-CF)

### Composición obligatoria:
1. **Encabezado** — Identificación del e-CF, emisor, comprador, datos tributarios
2. **Detalle de Bienes o Servicios** — Línea por cada ítem
3. **Subtotales Informativos** — Solo informativos, no afectan totales
4. **Descuentos o Recargos** — Globales que afectan el total
5. **Paginación** — Para representación impresa
6. **Información de Referencia** — e-CF modificados (notas de crédito/débito)
7. **Fecha y Hora de firma digital**
8. **Firma Digital** — Sobre toda la información anterior

### Tags XML principales:
```xml
<ECF>
  <Encabezado>
    <IdDoc>
      <TipoeCF>31</TipoeCF>        <!-- Tipo comprobante -->
      <eNCF>E310000000001</eNCF>    <!-- Secuencia autorizada -->
      <FechaVencimientoSecuencia>...</FechaVencimientoSecuencia>
    </IdDoc>
    <Emisor>...</Emisor>
    <Comprador>...</Comprador>
    <Totales>...</Totales>
  </Encabezado>
  <DetallesItems>...</DetallesItems>
  <SubtotalesInformativos>...</SubtotalesInformativos>
  <DescuentosORecargos>...</DescuentosORecargos>
  <Paginacion>...</Paginacion>
  <InformacionReferencia>...</InformacionReferencia>
  <FechaHoraFirma>...</FechaHoraFirma>
  <Signature>...</Signature>    <!-- Firma XMLDSig -->
</ECF>
```

### Formatos adicionales:
| Formato | Tag Madre | Uso |
|---------|-----------|-----|
| e-CF | `<ECF>` | Comprobante fiscal electrónico |
| Aprobación Comercial | `<ACECF>` | Respuesta del receptor |
| Acuse de Recibo | `<ARECF>` | Constancia de recepción |
| Anulación | `<ANECF>` | Anulación de secuencias |
| Resumen FC | `<RFCE>` | Resumen facturas consumo < 250K |

---

## 5. Firma Digital

- Certificado digital emitido por entidad certificadora autorizada en RD
- Firma XMLDSig sobre todo el contenido del e-CF
- La semilla de autenticación también debe firmarse con el mismo certificado
- Documentos: `firmado-ecf.pdf` y `Instructivo App Firma Digital`

---

## 6. Proceso de Certificación

**Pasos para ser Emisor Electrónico:**
1. Solicitar usuario administrador de e-CF en la DGII
2. Obtener certificado digital
3. Desarrollar/integrar software de facturación
4. Realizar pruebas en ambiente de Pre-Certificación
5. Completar pruebas requeridas en ambiente de Certificación
6. Aprobación por la DGII → Pasa a Producción

**Opción alternativa:** Usar un Proveedor de Servicios de FE Certificado (más rápido).

---

## 7. Restricciones Técnicas

- **Codificación:** UTF-8
- **NO incluir tags vacíos** en los XML
- **Formato de nombre de archivo:** Especificado en el estándar
- **Formato de fechas:** `dd-MM-AAAA` en campos del e-CF, ISO 8601 para tokens
- **Servicios no sensitivos** a mayúsculas/minúsculas
- **Puertos de red:** Usar puertos tradicionales (80/443)

---

## 8. XSD Schemas Descargados

- `ecf-31-v1.0.xsd` — Factura de Crédito Fiscal
- `ecf-32-v1.0.xsd` — Factura de Consumo
- (Pendientes: 33, 34, 41, 43, 44, 45, 46, 47, RFCE, ARECF, ANECF, ACECF, Semilla)

---

## 9. Implicaciones para CrediFlux

### Lo que necesitamos implementar:
1. **Módulo `billing` o `invoicing`** — Generación de e-CF XML
2. **Firma digital** — Integración con certificados digitales (por tenant)
3. **API Client DGII** — Autenticación, envío, consulta de estado
4. **Almacenamiento** — Guardar XML firmados y respuestas de la DGII
5. **Representación impresa** — PDF del e-CF para clientes
6. **Secuencias e-NCF** — Gestión de rangos autorizados por tenant
7. **Servicio Emisor-Receptor** — Para recibir e-CF de otros contribuyentes

### Configuración por tenant:
- RNC del emisor
- Certificado digital (.p12/.pfx)
- Secuencias autorizadas por tipo de e-CF
- Ambiente activo (pre-cert/cert/producción)
- Datos del emisor (razón social, dirección, etc.)

### Prioridad de implementación:
1. 🔴 Tipo 31 (Factura Crédito Fiscal) — Para cobros de préstamos B2B
2. 🔴 Tipo 32 (Factura de Consumo) — Para cobros individuales
3. 🟡 Tipo 34 (Nota de Crédito) — Para ajustes/devoluciones
4. 🟡 Tipo 33 (Nota de Débito) — Para correcciones
5. 🟢 Resto — Según necesidad

---

## 10. PDFs de Referencia (Descargados)

| Archivo | Contenido | Páginas |
|---------|-----------|---------|
| `descripcion-tecnica-fe.pdf` | Servicios web, APIs, ambientes | 66 |
| `formato-ecf-v1.0.pdf` | Campos del XML, validaciones, tablas | 89 |
| `firmado-ecf.pdf` | Proceso de firma digital | 20 |
| `informe-tecnico-ecf-v1.0.pdf` | Informe general del sistema | ~100 |
| `proceso-certificacion-emisor.pdf` | Pasos para certificarse | 26 |
| `formato-acuse-recibo-v1.0.pdf` | Formato XML acuse de recibo | ~10 |
