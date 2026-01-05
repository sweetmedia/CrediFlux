# Configuración de WhatsApp Webhooks

Esta guía explica cómo configurar la integración de WhatsApp Business Cloud API para recibir mensajes entrantes y notificaciones de estado en CrediFlux.

## Prerequisitos

1. Una cuenta de Meta Business (Facebook Business)
2. Una aplicación de Meta con WhatsApp Business API habilitada
3. Un número de teléfono verificado en WhatsApp Business
4. Acceso al panel de administración de CrediFlux

## Arquitectura

```
Meta Platform (WhatsApp Cloud API)
         │
         │ POST /api/webhooks/whatsapp/
         ▼
┌─────────────────────────────────────┐
│     WhatsAppWebhookView             │
│  - Valida firma SHA256              │
│  - Identifica tenant por phone_id   │
│  - Encola tarea Celery              │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│     Celery Worker                   │
│  - Procesa mensaje/status           │
│  - Guarda en WhatsAppMessage        │
│  - Asocia con Customer si existe    │
└─────────────────────────────────────┘
```

## Paso 1: Configurar la Aplicación en Meta

### 1.1 Crear una Aplicación de Meta

1. Ve a [Meta for Developers](https://developers.facebook.com/)
2. Haz clic en "My Apps" → "Create App"
3. Selecciona "Business" como tipo de aplicación
4. Completa los detalles de la aplicación

### 1.2 Agregar WhatsApp Business API

1. En el dashboard de tu app, haz clic en "Add Product"
2. Busca "WhatsApp" y haz clic en "Set up"
3. Sigue el asistente para conectar tu cuenta de WhatsApp Business

### 1.3 Obtener Credenciales

En la sección WhatsApp → API Setup, encontrarás:

- **Phone Number ID**: Identificador único de tu número de WhatsApp
- **Access Token**: Token de acceso permanente (generarlo en System Users)
- **App Secret**: En Settings → Basic → App Secret

## Paso 2: Configurar el Tenant en CrediFlux

### 2.1 Acceder al Panel de Administración

1. Inicia sesión en el admin de Django: `https://tu-dominio.com/admin/`
2. Navega a **Tenants** → **Tenants**
3. Selecciona el tenant que deseas configurar

### 2.2 Configurar Credenciales de WhatsApp

Completa los siguientes campos:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **WhatsApp Phone ID** | Phone Number ID de Meta | `123456789012345` |
| **WhatsApp Token** | Access Token permanente | `EAABc...xyz` |
| **WhatsApp Verify Token** | Token personalizado para verificar webhooks | `mi_token_secreto_123` |
| **WhatsApp App Secret** | App Secret de Meta (para validar firmas) | `abc123def456...` |

### 2.3 Generar un Verify Token Seguro

El Verify Token puede ser cualquier string secreto. Se recomienda generar uno aleatorio:

```bash
# Generar un token seguro
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Ejemplo de resultado: `xK9mN2pL5qR8sT1vW4yZ7aC0bD3eF6gH`

## Paso 3: Configurar Webhook en Meta

### 3.1 URL del Webhook

La URL del webhook de CrediFlux es:

```
https://tu-dominio.com/api/webhooks/whatsapp/
```

> **Importante**: La URL debe usar HTTPS y ser accesible públicamente.

### 3.2 Configurar en Meta Developer Console

1. Ve a tu aplicación en [Meta for Developers](https://developers.facebook.com/)
2. Navega a **WhatsApp** → **Configuration**
3. En la sección "Webhook", haz clic en **Edit**
4. Completa los campos:
   - **Callback URL**: `https://tu-dominio.com/api/webhooks/whatsapp/`
   - **Verify Token**: El mismo valor que configuraste en el tenant
5. Haz clic en **Verify and Save**

### 3.3 Suscribirse a Eventos

Después de verificar el webhook, suscríbete a los siguientes campos:

| Campo | Descripción |
|-------|-------------|
| `messages` | Mensajes entrantes (texto, imagen, audio, video, documentos) |
| `message_status` | Actualizaciones de estado (sent, delivered, read, failed) |

Para suscribirte:
1. En la misma sección de Webhook, busca "Webhook fields"
2. Marca las casillas de `messages` y `message_status`
3. Guarda los cambios

## Paso 4: Verificar la Configuración

### 4.1 Prueba de Verificación

Meta enviará una solicitud GET para verificar tu webhook:

```
GET /api/webhooks/whatsapp/?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=XXXXX
```

Si todo está configurado correctamente, recibirás un código 200 y Meta marcará el webhook como verificado.

### 4.2 Prueba de Mensaje

1. Envía un mensaje de WhatsApp al número configurado
2. Verifica en los logs de Celery que el mensaje fue procesado:

```bash
docker-compose logs -f celery
```

Deberías ver algo como:
```
[INFO] Processing WhatsApp webhook for tenant: mi_empresa
[INFO] Saved inbound message wamid.xxx from +18091234567
```

### 4.3 Verificar en la Base de Datos

```python
# En Django shell
from apps.communications.models import WhatsAppMessage
WhatsAppMessage.objects.order_by('-created_at')[:5]
```

## Paso 5: Ver Conversaciones en el Frontend

1. Inicia sesión en CrediFlux
2. Navega a **Comunicaciones** en el menú lateral
3. Selecciona la pestaña **WhatsApp**
4. Verás la lista de conversaciones con mensajes recibidos

## Estructura del Payload

### Mensaje Entrante

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "18091234567",
          "phone_number_id": "123456789012345"
        },
        "contacts": [{
          "profile": { "name": "Juan Pérez" },
          "wa_id": "18097654321"
        }],
        "messages": [{
          "id": "wamid.HBgLMTgwOTEyMzQ1Njc...",
          "from": "18097654321",
          "timestamp": "1704067200",
          "type": "text",
          "text": { "body": "Hola, necesito información" }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

### Actualización de Estado

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "metadata": { "phone_number_id": "123456789012345" },
        "statuses": [{
          "id": "wamid.HBgLMTgwOTEyMzQ1Njc...",
          "status": "delivered",
          "timestamp": "1704067300",
          "recipient_id": "18097654321"
        }]
      },
      "field": "messages"
    }]
  }]
}
```

## Seguridad

### Validación de Firma

Todos los webhooks de Meta incluyen una firma HMAC-SHA256 en el header `X-Hub-Signature-256`. CrediFlux valida esta firma usando el **App Secret** configurado en el tenant.

Si la firma no es válida, el webhook es rechazado con error 403.

### Idempotencia

Los mensajes se identifican por `wa_message_id`. Si Meta reenvía un webhook (por timeout o error), el sistema detecta el duplicado y no crea registros repetidos.

## Solución de Problemas

### El webhook no se verifica

1. Verifica que la URL sea accesible públicamente (usa `curl` para probar)
2. Confirma que el Verify Token coincida exactamente
3. Revisa los logs del backend: `docker-compose logs backend`

### Mensajes no llegan

1. Verifica que estés suscrito al campo `messages`
2. Revisa los logs de Celery: `docker-compose logs celery`
3. Confirma que el `whatsapp_phone_id` del tenant coincida con el de Meta

### Estados no se actualizan

1. Verifica que estés suscrito al campo `message_status`
2. Confirma que el `wa_message_id` del mensaje original existe en la base de datos

### Error 403 en webhooks

1. Verifica que el `whatsapp_app_secret` esté configurado correctamente
2. Confirma que el App Secret sea el correcto (de Settings → Basic en Meta)

## Referencia de Estados

| Estado | Descripción |
|--------|-------------|
| `pending` | Mensaje creado, pendiente de envío |
| `sent` | Enviado a servidores de WhatsApp |
| `delivered` | Entregado al dispositivo del destinatario |
| `read` | Leído por el destinatario |
| `failed` | Error en el envío |
| `received` | Mensaje entrante recibido |

## Recursos Adicionales

- [Documentación oficial de WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Guía de Webhooks de Meta](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Referencia de la API de Mensajes](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
