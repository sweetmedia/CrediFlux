# Facturación Electrónica DGII — Investigación para CrediFlux

> Fecha: 2026-03-28
> Investigado por: Leo 🦁

---

## 1. ¿Qué es el e-CF?

El **Comprobante Fiscal Electrónico (e-CF)** es la versión digital de los comprobantes fiscales en RD. Tiene la misma validez legal que su versión impresa.

- **Formato:** XML firmado digitalmente
- **Validación:** Se envía a la DGII en tiempo real para aprobación
- **Conservación:** Obligatorio guardar por **10 años**
- **Marco legal:** Ley 32-23 + Decreto 587-24 + Norma General 06-2018

## 2. Tipos de e-CF (Relevantes para CrediFlux)

| Tipo | Código | Uso en CrediFlux |
|------|--------|-----------------|
| **Factura de Crédito Fiscal** | E31 | ✅ Principal — cobro de intereses, comisiones, servicios a empresas |
| **Factura de Consumo** | E32 | ✅ Para clientes persona física sin RNC |
| **Nota de Débito** | E33/E34 | ✅ Ajustes a facturas (cargos adicionales, mora) |
| **Nota de Crédito** | E41 | ✅ Reversos, descuentos, ajustes a favor del cliente |
| Compras | E43 | ⚠️ Cuando CrediFlux compra servicios |
| Gastos Menores | E44 | ⚠️ Gastos operativos menores |
| Reg. Especiales | E45 | ❌ No aplica generalmente |
| Gubernamental | E46 | ⚠️ Si hay préstamos a entidades gubernamentales |

### Para una financiera de préstamos, los más usados son:
1. **E31 (Crédito Fiscal)** — Para facturar intereses, comisiones de desembolso, seguros, y servicios a clientes con RNC
2. **E32 (Consumo)** — Para clientes persona física (la mayoría de los prestatarios)
3. **E34 (Nota de Débito)** — Para cargos por mora, penalidades
4. **E41 (Nota de Crédito)** — Para ajustes, descuentos, o reversos

## 3. Requisitos para ser Emisor Electrónico

1. Estar inscrito en el **RNC** (Registro Nacional de Contribuyentes)
2. Tener **obligaciones tributarias** registradas
3. Obtener **certificado digital** (de una entidad certificadora autorizada por INDOTEL)
4. **Solicitar autorización** a la DGII via OFV (Oficina Virtual)
5. Completar **pruebas de certificación** con la DGII
6. Tener **software homologado** (desarrollo propio o via proveedor PSFE)
7. Cumplir con la **Norma General 06-2018**

## 4. Calendario de Obligatoriedad

- ✅ **Grandes contribuyentes nacionales** — Ya completaron (2024)
- ✅ **Grandes contribuyentes locales y medianos** — Plazo: 15 nov 2025
- ⏰ **Pequeñas/micro empresas y no clasificados** — Plazo: **15 mayo 2026**

> **Para CrediFlux:** Dependiendo del tamaño de cada tenant (cliente), caen en diferentes categorías. El sistema debe soportar e-CF para TODOS los clientes.

## 5. Flujo Técnico del e-CF

```
┌─────────────┐    ┌──────────────┐    ┌────────────┐    ┌──────┐
│ CrediFlux   │───▶│ Proveedor    │───▶│ DGII       │───▶│ Estado│
│ (Backend)   │    │ API (PSFE)   │    │ Validación │    │ Final │
│             │◀───│              │◀───│            │◀───│       │
└─────────────┘    └──────────────┘    └────────────┘    └──────┘
     JSON              XML/Firma         Validación       Aceptado/
                       Digital                            Rechazado
```

### Pasos:
1. CrediFlux genera datos de la factura (JSON)
2. Se envía al proveedor PSFE via API REST
3. El proveedor genera XML, firma digitalmente, envía a DGII
4. DGII valida y retorna estado (aceptado/rechazado/condicional)
5. Se recibe e-NCF (número de comprobante), PDF, XML firmado, QR
6. CrediFlux almacena todo y vincula al préstamo/pago

## 6. Opciones de Integración (Desarrollo vs Proveedor)

### Opción A: Desarrollo Propio (NO recomendado)
- Generar XML según XSD de DGII
- Implementar firma digital con certificado P12
- Envío SOAP al servicio DGII
- Manejar estados asincrónicos
- Certificarse directamente ante DGII
- **Pros:** Control total, sin costos recurrentes
- **Contras:** Complejidad ENORME, meses de desarrollo, certificación propia

### Opción B: Proveedor PSFE via API (RECOMENDADO ✅)
Usar un proveedor certificado que exponga una API REST. Nosotros enviamos JSON, ellos hacen todo lo demás.

#### Proveedores evaluados:

**1. EF2.do** ⭐ Favorito
- API REST simple (JSON in → e-NCF + PDF + XML out)
- Una sola llamada para emitir cualquier tipo de comprobante
- Firma digital automática
- Generación automática de e-NCF
- **Soporte Python** con ejemplos
- Autenticación JWT/Bearer Token
- URL: `https://master.ef2.do/api2`
- Sandbox con credenciales de prueba disponibles
- Precio: Por investigar

**2. DGMax.do** ⭐ Muy bueno
- API RESTful completa
- **SDK Python nativo** (`dgmaxclient`)
- Multi-empresa (perfecto para CrediFlux multi-tenant!)
- Límites soft (nunca bloquea facturación)
- Todos los tipos de e-CF soportados
- Maneja recepción + acuses automáticos (ARECF/ACECF)
- Free trial 14 días
- URL: `https://dgmax.do`
- Precio: Por investigar

**3. Alanube**
- API REST con webhooks
- Sandbox y producción
- Documentación extensa
- Más enfocado en empresas grandes
- URL: `https://alanube.co/rd`

**4. MSeller eCF**
- API REST para e-CF
- Manejo de certificados y contingencia
- URL: `https://ecf.mseller.app`

## 7. Plan de Implementación para CrediFlux

### Fase 1: Modelo de Datos (Django)
```python
# Nueva app: invoicing/

class FiscalInvoice(TenantModel):
    """Comprobante fiscal electrónico"""
    loan = models.ForeignKey('loans.Loan', null=True, blank=True)
    payment = models.ForeignKey('loans.Payment', null=True, blank=True)
    
    # Tipo de e-CF
    ecf_type = models.CharField(choices=[
        ('E31', 'Factura Crédito Fiscal'),
        ('E32', 'Factura de Consumo'),
        ('E34', 'Nota de Débito'),
        ('E41', 'Nota de Crédito'),
    ])
    
    # DGII
    encf = models.CharField(max_length=20, unique=True, null=True)  # e-NCF asignado
    security_code = models.CharField(max_length=10, null=True)
    dgii_status = models.CharField(choices=[
        ('PENDING', 'Pendiente'),
        ('PROCESSING', 'En proceso'),
        ('ACCEPTED', 'Aceptado'),
        ('REJECTED', 'Rechazado'),
        ('CONDITIONAL', 'Aceptado condicional'),
    ])
    
    # Datos factura
    buyer_rnc = models.CharField(max_length=11, null=True, blank=True)
    buyer_name = models.CharField(max_length=200)
    buyer_email = models.EmailField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    itbis = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Archivos
    xml_url = models.URLField(null=True)
    pdf_url = models.URLField(null=True)
    qr_url = models.URLField(null=True)
    stamp_url = models.URLField(null=True)
    
    # Metadata
    provider_response = models.JSONField(default=dict)
    issued_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-issued_at']


class FiscalConfig(TenantModel):
    """Configuración fiscal por tenant"""
    rnc = models.CharField(max_length=11)
    business_name = models.CharField(max_length=200)
    commercial_name = models.CharField(max_length=200, blank=True)
    address = models.TextField()
    municipality_code = models.CharField(max_length=6)
    province_code = models.CharField(max_length=6)
    email = models.EmailField()
    
    # Proveedor PSFE
    psfe_provider = models.CharField(choices=[
        ('ef2', 'EF2.do'),
        ('dgmax', 'DGMax.do'),
        ('alanube', 'Alanube'),
    ], default='ef2')
    psfe_api_key = models.CharField(max_length=200)  # Encriptar!
    psfe_api_secret = models.CharField(max_length=200, blank=True)
    
    # Certificado digital
    certificate_expiry = models.DateField(null=True)
    
    is_active = models.BooleanField(default=False)
```

### Fase 2: Servicio de Facturación
```python
# invoicing/services.py

class InvoicingService:
    """Servicio que abstrae el proveedor PSFE"""
    
    def emit_invoice(self, loan, payment, ecf_type='E32'):
        """Emite un e-CF para un pago de préstamo"""
        config = FiscalConfig.objects.get(tenant=loan.tenant)
        provider = self.get_provider(config)
        
        invoice_data = self.build_invoice_data(loan, payment, ecf_type, config)
        result = provider.emit(invoice_data)
        
        return FiscalInvoice.objects.create(
            loan=loan,
            payment=payment,
            ecf_type=ecf_type,
            encf=result['encf'],
            dgii_status=result['status'],
            # ... etc
        )
    
    def get_provider(self, config):
        providers = {
            'ef2': EF2Provider,
            'dgmax': DGMaxProvider,
        }
        return providers[config.psfe_provider](config)
```

### Fase 3: Triggers Automáticos
- **Al registrar un pago de cuota** → Emitir e-CF automáticamente
- **Al desembolsar un préstamo** → Facturar comisión de desembolso
- **Al aplicar mora** → Nota de débito
- **Al reversar un pago** → Nota de crédito
- **Mensual** → Facturar intereses del período

### Fase 4: UI/Frontend
- Dashboard de comprobantes emitidos por tenant
- Estado de cada e-CF (aceptado/rechazado)
- Descarga de PDF/XML
- Configuración fiscal del tenant
- Reportes para declaración DGII

## 8. Consideraciones Especiales para Financieras

### ITBIS (Impuesto, equivalente al IVA)
- Los **intereses de préstamos** están **exentos de ITBIS** en RD
- Las **comisiones y servicios** SÍ pagan ITBIS (18%)
- Los **seguros** tienen tratamiento especial
- Los **cargos por mora** son debatibles — consultar contador

### Facturación por Concepto:
| Concepto | ITBIS | Tipo e-CF |
|----------|-------|-----------|
| Intereses del préstamo | Exento | E31/E32 |
| Comisión de desembolso | 18% | E31/E32 |
| Comisión de administración | 18% | E31/E32 |
| Seguro de deuda | Exento* | E31/E32 |
| Cargo por mora | Exento | E34 (Nota Débito) |
| Penalidad por prepago | 18% | E31/E32 |

*Verificar con contador — puede variar según tipo de seguro

### Multi-Tenancy
- Cada tenant en CrediFlux = una empresa diferente con su propio RNC
- Cada una necesita su propio certificado digital
- Cada una se certifica independientemente ante DGII
- **DGMax es ideal para esto** — soporta multi-empresa nativamente

## 9. Próximos Pasos

1. [ ] **Elegir proveedor PSFE** — Solicitar pricing de EF2 y DGMax
2. [ ] **Crear app `invoicing`** en el proyecto Django
3. [ ] **Modelos + migraciones** — FiscalInvoice, FiscalConfig, FiscalItem
4. [ ] **Service layer** — Abstracción del proveedor con patrón Strategy
5. [ ] **Integración sandbox** — Probar con credenciales de prueba
6. [ ] **Triggers automáticos** — Señales Django al registrar pagos
7. [ ] **API endpoints** — Para frontend (lista, detalle, descarga PDF)
8. [ ] **Frontend** — Dashboard de comprobantes en Next.js
9. [ ] **Testing** — Con sandbox del proveedor
10. [ ] **Producción** — Certificación ante DGII por cada tenant

## 10. Links de Referencia

- DGII Facturación Electrónica: <https://dgii.gov.do/cicloContribuyente/facturacion/comprobantesFiscalesElectronicosE-CF/>
- Documentación técnica DGII: <https://dgii.gov.do/.../documentacionSobreE-CF.aspx>
- XSD schemas: Disponibles en la página de documentación DGII
- EF2 API Docs: <https://doc.ef2.do/>
- DGMax API: <https://dgmax.do/blog/api-facturacion-electronica-desarrolladores>
- Alanube API Guide: <https://blog.alanube.co/rd/api-de-facturacion-electronica-rd/>
- Ley 32-23: Ley de Facturación Electrónica
- Decreto 587-24: Reglamento de aplicación
