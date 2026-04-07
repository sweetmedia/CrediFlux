# CrediFlux - Documento de Contexto

## Fecha: 3 de Noviembre, 2025

---

## Resumen del Proyecto

CrediFlux es un sistema multi-tenant de gestión de préstamos construido con Django (backend) y Next.js (frontend). El sistema permite a múltiples empresas de préstamos gestionar sus operaciones de forma independiente en la misma plataforma.

### Stack Tecnológico

**Backend:**
- Django 5.0.9
- Django REST Framework
- Django-tenants (multi-tenancy)
- PostgreSQL
- Docker / Docker Compose
- PyWa 3.4.0 (WhatsApp Cloud API)

**Frontend:**
- Next.js 16.0.0 con Turbopack
- TypeScript
- Tailwind CSS
- Shadcn/ui components
- React Hook Form + Zod

---

## Funcionalidades Completadas

### ✅ Core del Sistema
- [x] Sistema multi-tenant con aislamiento de datos por esquemas
- [x] Autenticación y autorización basada en JWT
- [x] Dashboard con métricas y gráficos
- [x] Gestión de préstamos (CRUD completo)
- [x] Gestión de clientes (CRUD completo)
- [x] Gestión de pagos con múltiples métodos
- [x] Sistema de cobranza con filtros avanzados
- [x] Gestión de usuarios y equipos
- [x] Sistema de permisos y roles

### ✅ Contratos Digitales
- [x] Generación de contratos desde plantillas HTML
- [x] Editor visual de plantillas con variables dinámicas
- [x] Firma digital de contratos
- [x] Página pública para firma de contratos
- [x] Almacenamiento de contratos firmados

### ✅ WhatsApp Integration
- [x] Configuración de WhatsApp Cloud API
- [x] Modelos para mensajes de WhatsApp
- [x] Integración con PyWa library
- [x] UI para conversaciones de WhatsApp

### ✅ Sistema de Comunicaciones
- [x] Página de Comunicaciones con tabs Email/WhatsApp
- [x] UI estilo Gmail con diseño de 3 columnas
- [x] 11 carpetas de email (Inbox, Drafts, Sent, Junk, Trash, Archive, Social, Updates, Forums, Shopping, Promotions)
- [x] Sistema de labels/tags con colores
- [x] Avatares con iniciales para remitentes
- [x] Indicadores de emails no leídos e importantes
- [x] Vista detallada de emails con opciones de Reply/Forward/Archive/Delete
- [x] Filtros All mail / Unread
- [x] Buscador de emails
- [x] Modelos de Email y WhatsAppMessage en backend
- [x] Configuración SMTP/IMAP en Settings

### ✅ Sistema de Tareas
- [x] Página de Tareas con Kanban board
- [x] 4 columnas: Por Hacer, En Progreso, En Revisión, Completado
- [x] Creación de tareas con título, descripción, prioridad, fecha límite, asignación y tags
- [x] Mover tareas entre columnas
- [x] Indicadores visuales de prioridad (Baja/Media/Alta)
- [x] Sistema de tags para categorización

### ✅ Configuración del Sistema
- [x] Settings con 6 tabs: General, Préstamos, Pagos, Notificaciones, Email
- [x] Configuración de WhatsApp (Phone ID, Token, Business Account ID)
- [x] Configuración SMTP/IMAP con presets (Gmail, Outlook, Yahoo)
- [x] Logo personalizable por tenant
- [x] Información de negocio

---

## Tareas Pendientes

### 🔴 Prioridad Alta

#### Backend - Sistema de Emails

1. **Crear servicio SMTP/IMAP**
   - Implementar servicio para envío de emails usando SMTP
   - Implementar servicio para recepción de emails usando IMAP
   - Conectar con configuración del tenant (smtp_host, smtp_port, etc.)
   - Manejo de errores y reintentos
   - File: `backend/apps/communications/services/email_service.py`

2. **Crear endpoints API para gestión de emails**
   - `GET /api/communications/emails/` - Listar emails
   - `POST /api/communications/emails/send/` - Enviar email
   - `GET /api/communications/emails/{id}/` - Obtener email
   - `DELETE /api/communications/emails/{id}/` - Eliminar email
   - `POST /api/communications/emails/{id}/reply/` - Responder email
   - `POST /api/communications/emails/{id}/forward/` - Reenviar email
   - `POST /api/communications/emails/sync/` - Sincronizar con servidor IMAP
   - `GET /api/communications/folders/` - Obtener carpetas del servidor
   - Files:
     - `backend/apps/communications/views.py`
     - `backend/apps/communications/serializers.py`
     - `backend/apps/communications/urls.py`

3. **Crear endpoints API para WhatsApp**
   - `GET /api/communications/whatsapp/conversations/` - Listar conversaciones
   - `GET /api/communications/whatsapp/messages/` - Listar mensajes
   - `POST /api/communications/whatsapp/send/` - Enviar mensaje
   - `POST /api/communications/whatsapp/webhook/` - Webhook de WhatsApp
   - Files:
     - `backend/apps/communications/views.py`
     - `backend/apps/communications/serializers.py`

#### Frontend - Integración

4. **Conectar frontend de emails con APIs**
   - Crear cliente API en `lib/api/communications.ts`
   - Implementar fetchEmails(), sendEmail(), replyEmail(), forwardEmail()
   - Implementar syncEmails() para sincronizar con servidor
   - Implementar fetchFolders() para obtener carpetas reales del servidor
   - Conectar con UI existente en `/app/communications/page.tsx`

5. **Conectar frontend de WhatsApp con APIs**
   - Implementar fetchConversations(), fetchMessages(), sendMessage()
   - Conectar con UI existente en `/app/communications/page.tsx`
   - Implementar actualización en tiempo real (WebSockets o polling)

### 🟡 Prioridad Media

#### Backend - Sistema de Tareas

6. **Crear modelo Task en backend**
   - Campos: title, description, status, priority, assignee, due_date, tags, tenant
   - File: `backend/apps/tasks/models.py` (crear nueva app)

7. **Crear endpoints API para tareas**
   - `GET /api/tasks/` - Listar tareas
   - `POST /api/tasks/` - Crear tarea
   - `PUT /api/tasks/{id}/` - Actualizar tarea
   - `PATCH /api/tasks/{id}/status/` - Cambiar estado
   - `DELETE /api/tasks/{id}/` - Eliminar tarea

8. **Conectar frontend de tareas con APIs**
   - Crear cliente API en `lib/api/tasks.ts`
   - Implementar fetchTasks(), createTask(), updateTask(), deleteTask()
   - Conectar con Kanban board en `/app/tasks/page.tsx`

#### Mejoras del Sistema

9. **Sistema de notificaciones**
   - Notificaciones in-app
   - Notificaciones por email
   - Notificaciones por WhatsApp
   - Centro de notificaciones en UI

10. **Reportes y Analytics**
    - Reportes de préstamos
    - Reportes de pagos
    - Reportes de cobranza
    - Exportación a PDF/Excel

11. **Mejoras de Seguridad**
    - Encriptar contraseñas SMTP/IMAP en base de datos
    - Implementar rate limiting en APIs
    - Audit log de acciones importantes
    - Two-factor authentication (2FA)

### 🟢 Prioridad Baja

12. **Drag & Drop en Kanban**
    - Implementar drag & drop para mover tareas entre columnas
    - Usar library como `react-beautiful-dnd` o `@dnd-kit/core`

13. **Rich Text Editor para Emails**
    - Integrar editor WYSIWYG para composición de emails
    - Opciones de formato (negrita, cursiva, listas, etc.)
    - Inserción de imágenes

14. **Archivos adjuntos en Emails**
    - Upload de archivos adjuntos
    - Descarga de adjuntos recibidos
    - Vista previa de archivos comunes (imágenes, PDFs)

15. **Templates de Email**
    - Crear templates reutilizables para emails
    - Variables dinámicas en templates
    - Gestión de templates en UI

16. **Calendario Integrado**
    - Vista de calendario para fechas de vencimiento de préstamos
    - Vista de calendario para tareas
    - Integración con Google Calendar (opcional)

---

## Estructura del Proyecto

```
CrediFlux/
├── backend/
│   ├── apps/
│   │   ├── loans/          # ✅ Gestión de préstamos
│   │   ├── tenants/        # ✅ Multi-tenancy
│   │   ├── users/          # ✅ Gestión de usuarios
│   │   ├── communications/ # ✅ Email y WhatsApp (modelos)
│   │   └── tasks/          # ⏳ Pendiente crear
│   ├── config/
│   ├── media/
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── dashboard/      # ✅ Dashboard
    │   ├── loans/          # ✅ Préstamos
    │   ├── customers/      # ✅ Clientes
    │   ├── contracts/      # ✅ Contratos
    │   ├── payments/       # ✅ Pagos
    │   ├── collections/    # ✅ Cobranza
    │   ├── communications/ # ✅ Email y WhatsApp (UI)
    │   ├── tasks/          # ✅ Tareas Kanban (UI)
    │   ├── users/          # ✅ Usuarios
    │   └── settings/       # ✅ Configuración
    ├── components/
    ├── lib/
    └── package.json
```

---

## Notas de Desarrollo

### Configuración de Email

Para que el sistema de emails funcione correctamente, cada tenant debe configurar:

1. **SMTP (Envío)**
   - Host: ej. `smtp.gmail.com`
   - Puerto: 587 (TLS) o 465 (SSL)
   - Usuario y contraseña
   - TLS/SSL activado

2. **IMAP (Recepción)**
   - Host: ej. `imap.gmail.com`
   - Puerto: 993 (SSL) o 143
   - Usuario y contraseña
   - SSL activado

### Configuración de WhatsApp

Para usar WhatsApp Cloud API:

1. Crear cuenta en Meta for Developers
2. Crear app y obtener Phone Number ID
3. Generar Access Token permanente
4. Obtener Business Account ID
5. Configurar webhook URL (para recibir mensajes)
6. Configurar Verify Token personalizado

---

## Testing Pendiente

### Backend Tests
- [ ] Tests de servicio SMTP
- [ ] Tests de servicio IMAP
- [ ] Tests de endpoints de emails
- [ ] Tests de endpoints de WhatsApp
- [ ] Tests de endpoints de tareas

### Frontend Tests
- [ ] Tests de integración con APIs
- [ ] Tests de componentes de emails
- [ ] Tests de Kanban board
- [ ] Tests E2E de flujos completos

---

## Deployment

### Variables de Entorno Requeridas

**Backend:**
```env
DATABASE_URL=postgresql://user:pass@localhost/crediflux
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

**Frontend:**
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Próximos Pasos de Deployment

1. [ ] Configurar servidor de producción
2. [ ] Configurar CI/CD pipeline
3. [ ] Configurar backups automáticos de base de datos
4. [ ] Configurar monitoreo y logging
5. [ ] Configurar CDN para archivos estáticos
6. [ ] Configurar SSL/TLS

---

## Contacto

Para cualquier pregunta o ayuda con el desarrollo, contactar al equipo.

---

**Última actualización:** 3 de Noviembre, 2025
**Versión:** 1.0.0
**Estado:** En Desarrollo Activo
