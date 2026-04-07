# CrediFlux - Estructura de Proyecto ClickUp

## Espacio: CrediFlux

---

## Folder: Backend Development

### Lista: Autenticacion 2FA

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Agregar campos 2FA al modelo User | Completado | Alta | totp_secret, is_2fa_enabled, backup_codes |
| Crear serializers 2FA | Completado | Alta | Setup, Verify, Disable, BackupCodes |
| Crear views 2FA | Completado | Alta | TwoFactorSetupView, VerifyView, DisableView |
| Configurar URLs 2FA | Completado | Alta | /auth/2fa/setup, verify, disable, backup-codes |
| Modificar flujo de login para 2FA | Completado | Alta | Retornar requires_2fa y temp_token |
| Generar migraciones 2FA | Completado | Media | python manage.py makemigrations users |

### Lista: Sistema de Auditoria

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear app audit | Completado | Alta | python manage.py startapp audit |
| Crear modelo AuditLog | Completado | Alta | UUID, user, action, model_name, changes, IP |
| Crear middleware AuditMiddleware | Completado | Alta | Capturar IP y user-agent del request |
| Crear signals para auto-logging | Completado | Alta | pre_save, post_save, post_delete |
| Crear ViewSet de auditoria | Completado | Media | Filtros por user, action, model, fecha |
| Crear serializers de auditoria | Completado | Media | AuditLogSerializer, AuditLogStatsSerializer |

### Lista: Busqueda Global

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear GlobalSearchView | Completado | Alta | Buscar en customers, loans, payments, contracts |
| Configurar URL /api/search/ | Completado | Alta | GET con parametro q |
| Implementar busqueda icontains | Completado | Media | first_name, last_name, id_number, email, phone |
| Corregir filtro de tenant | Completado | Alta | Remover tenant filter (django-tenants usa schemas) |
| Corregir campo reference_number | Completado | Alta | Cambiar receipt_number por reference_number |

### Lista: Dashboard Avanzado

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear endpoint dashboard_statistics | Completado | Alta | Distribucion por status, desembolsos, cobranza |
| Agregar filtro por periodo | Pendiente | Media | daily, weekly, monthly, yearly |
| Crear endpoint export_report | Pendiente | Media | Exportar a PDF y CSV |

### Lista: Notificaciones Automatizadas

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear modelo NotificationTemplate | Pendiente | Alta | name, type, channel, subject, content |
| Crear modelo NotificationPreference | Pendiente | Media | Preferencias por cliente (email, sms, whatsapp) |
| Crear modelo NotificationLog | Pendiente | Media | Log de notificaciones enviadas |
| Integrar Twilio para SMS | Pendiente | Alta | SMSService con Twilio API |
| Agregar campos Twilio a Tenant | Pendiente | Alta | account_sid, auth_token, phone_number |
| Mejorar Celery tasks de recordatorios | Pendiente | Media | Multi-canal (email + SMS + WhatsApp) |

### Lista: Integracion WhatsApp

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Investigar proveedores WhatsApp API | Pendiente | Alta | Twilio WhatsApp, WhatsApp Business API, 360dialog |
| Instalar dependencia pywa o twilio | Pendiente | Alta | pip install pywa o twilio |
| Crear WhatsAppService | Pendiente | Alta | Servicio para enviar mensajes WhatsApp |
| Agregar campos WhatsApp a Tenant | Pendiente | Alta | whatsapp_api_key, whatsapp_phone_id, whatsapp_business_id |
| Crear endpoint webhook WhatsApp | Pendiente | Alta | Recibir mensajes entrantes y status updates |
| Crear modelo WhatsAppMessage | Pendiente | Media | Log de mensajes enviados/recibidos |
| Crear plantillas de mensajes WhatsApp | Pendiente | Media | Templates aprobados por Meta |
| Implementar envio recordatorio de pago | Pendiente | Alta | Celery task para enviar recordatorios via WhatsApp |
| Implementar envio confirmacion de pago | Pendiente | Media | Notificar cuando se registra un pago |
| Implementar envio aviso de mora | Pendiente | Alta | Notificar pagos vencidos |
| Crear comando para sincronizar plantillas | Pendiente | Baja | python manage.py sync_whatsapp_templates |
| Implementar respuestas automaticas | Pendiente | Media | Bot para consultas de saldo, proximos pagos |
| Crear tests WhatsApp service | Pendiente | Media | Unit tests con mocks |

---

## Folder: Frontend Development

### Lista: Componentes 2FA

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear TwoFactorSetup.tsx | Completado | Alta | QR code + input de verificacion |
| Crear TwoFactorVerify.tsx | Completado | Alta | Input 6 digitos para login |
| Crear BackupCodesDisplay.tsx | Completado | Media | Mostrar codigos de respaldo |
| Actualizar AuthContext | Completado | Alta | Agregar complete2FALogin method |
| Modificar login page | Completado | Alta | Integrar flujo 2FA |
| Agregar seccion 2FA en Settings | Completado | Media | Configuracion en /settings/general |

### Lista: Pagina de Auditoria

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear /app/audit/page.tsx | Completado | Alta | Tabla con filtros y paginacion |
| Crear lib/api/audit.ts | Completado | Alta | getLogs, getStats |
| Agregar link en Sidebar | Completado | Media | Solo visible para admin/manager |
| Corregir Select.Item values | Completado | Media | Cambiar empty string a "all" |

### Lista: Busqueda Global UI

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear GlobalSearch.tsx | Completado | Alta | Modal con Cmd+K |
| Crear lib/api/search.ts | Completado | Alta | globalSearch(query) |
| Integrar en Sidebar | Completado | Media | Boton de busqueda + shortcut |
| Agregar DialogTitle | Completado | Baja | Fix accesibilidad |

### Lista: Dashboard con Graficos

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear LoanStatusPieChart.tsx | Pendiente | Media | PieChart con Recharts |
| Crear MonthlyDisbursementsBarChart.tsx | Pendiente | Media | BarChart de desembolsos |
| Crear CollectionTrendsLineChart.tsx | Pendiente | Media | LineChart de cobranza |
| Reemplazar datos mock en Dashboard | Pendiente | Alta | Conectar con API real |
| Agregar selector de periodo | Pendiente | Media | Dropdown para filtrar |
| Agregar boton exportar PDF/CSV | Pendiente | Baja | Descargar reportes |

### Lista: Configuracion Notificaciones

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear /settings/notifications/page.tsx | Pendiente | Alta | Configurar plantillas |
| Crear formulario config Twilio | Pendiente | Alta | Account SID, Auth Token, Phone |
| Crear vista log de notificaciones | Pendiente | Media | Historial de envios |

### Lista: Integracion WhatsApp UI

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Crear /settings/whatsapp/page.tsx | Pendiente | Alta | Configuracion de WhatsApp Business |
| Crear formulario config WhatsApp API | Pendiente | Alta | API Key, Phone ID, Business ID |
| Crear componente WhatsAppTemplates | Pendiente | Media | Gestionar plantillas de mensajes |
| Crear vista conversaciones WhatsApp | Pendiente | Media | Inbox de mensajes recibidos |
| Crear componente WhatsAppChat | Pendiente | Media | Vista de conversacion individual |
| Agregar WhatsApp a pagina de cliente | Pendiente | Media | Boton para enviar mensaje directo |
| Crear indicador de status WhatsApp | Pendiente | Baja | Mostrar si mensaje fue entregado/leido |
| Crear lib/api/whatsapp.ts | Pendiente | Alta | sendMessage, getConversations, getTemplates |

---

## Folder: DevOps & QA

### Lista: Testing

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Tests unitarios 2FA | Pendiente | Media | Verificar setup, verify, disable |
| Tests de auditoria | Pendiente | Media | Verificar logging automatico |
| Tests de busqueda | Pendiente | Media | Verificar resultados por tipo |
| Tests E2E flujo 2FA | Pendiente | Baja | Cypress/Playwright |
| Tests WhatsApp service | Pendiente | Media | Mocks para API externa |

### Lista: Documentacion

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Documentar API 2FA | Pendiente | Baja | Swagger/OpenAPI |
| Documentar API Auditoria | Pendiente | Baja | Endpoints y filtros |
| Documentar API WhatsApp | Pendiente | Media | Webhooks y endpoints |
| Manual de usuario 2FA | Pendiente | Baja | Guia para activar 2FA |
| Manual configuracion WhatsApp | Pendiente | Media | Guia paso a paso |

### Lista: Infraestructura

| Tarea | Estado | Prioridad | Descripcion |
|-------|--------|-----------|-------------|
| Configurar webhook URL produccion | Pendiente | Alta | URL publica para WhatsApp callbacks |
| Configurar variables de entorno WhatsApp | Pendiente | Alta | Secrets en produccion |
| Configurar Celery beat para recordatorios | Pendiente | Media | Scheduled tasks |

---

## Resumen de Progreso

| Modulo | Completado | Pendiente | Porcentaje |
|--------|------------|-----------|------------|
| 2FA Backend | 6 | 0 | 100% |
| 2FA Frontend | 6 | 0 | 100% |
| Auditoria Backend | 6 | 0 | 100% |
| Auditoria Frontend | 4 | 0 | 100% |
| Busqueda Backend | 5 | 0 | 100% |
| Busqueda Frontend | 4 | 0 | 100% |
| Dashboard Backend | 1 | 2 | 33% |
| Dashboard Frontend | 0 | 6 | 0% |
| Notificaciones Backend | 0 | 6 | 0% |
| Notificaciones Frontend | 0 | 3 | 0% |
| WhatsApp Backend | 0 | 13 | 0% |
| WhatsApp Frontend | 0 | 8 | 0% |
| Testing | 0 | 5 | 0% |
| Documentacion | 0 | 5 | 0% |
| Infraestructura | 0 | 3 | 0% |
| **TOTAL** | **32** | **51** | **39%** |

---

## Dependencias de Implementacion

### WhatsApp - Orden Recomendado

1. **Fase 1 - Configuracion Base**
   - Investigar proveedores WhatsApp API
   - Instalar dependencias
   - Agregar campos a Tenant
   - Crear WhatsAppService basico

2. **Fase 2 - Backend Core**
   - Crear modelo WhatsAppMessage
   - Crear endpoint webhook
   - Implementar envio de mensajes

3. **Fase 3 - Plantillas y Automatizacion**
   - Crear plantillas de mensajes
   - Implementar recordatorios de pago
   - Implementar avisos de mora

4. **Fase 4 - Frontend**
   - Pagina de configuracion
   - Vista de conversaciones
   - Integracion en pagina de cliente

5. **Fase 5 - Avanzado**
   - Respuestas automaticas (bot)
   - Sincronizacion de plantillas
   - Tests y documentacion

---

## Notas Tecnicas

### Proveedores WhatsApp Recomendados

| Proveedor | Pros | Contras | Costo |
|-----------|------|---------|-------|
| **Twilio WhatsApp** | Facil integracion, mismo SDK que SMS | Costo por mensaje | ~$0.005/msg |
| **WhatsApp Business API (Meta)** | Oficial, mas features | Setup complejo | Gratis + hosting |
| **360dialog** | Facil setup, buen precio | Menos documentacion | ~$0.004/msg |

### Plantillas WhatsApp Requeridas

1. **payment_reminder** - Recordatorio de pago proximo
2. **payment_confirmation** - Confirmacion de pago recibido
3. **overdue_notice** - Aviso de pago vencido
4. **loan_approval** - Notificacion de prestamo aprobado
5. **balance_inquiry** - Respuesta a consulta de saldo

### Variables de Entorno WhatsApp

```env
# WhatsApp Business API
WHATSAPP_API_URL=https://graph.facebook.com/v17.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_verify_token
```
