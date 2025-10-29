# Cloudflare Tunnel para CrediFlux

Este documento explica cómo usar los scripts de Cloudflare Tunnel para exponer tu aplicación CrediFlux en internet de forma segura.

## ¿Qué es Cloudflare Tunnel?

Cloudflare Tunnel (anteriormente Argo Tunnel) te permite exponer tu aplicación local a internet sin abrir puertos en tu firewall ni necesitar una IP pública. Todo el tráfico pasa por la red de Cloudflare de forma segura.

## Requisitos

- Una cuenta de Cloudflare (gratis)
- Un dominio configurado en Cloudflare
- Docker Compose corriendo (frontend y backend)

## Instalación Rápida

### 1. Ejecutar el script de setup

```bash
cd scripts
chmod +x setup-cloudflare-tunnel.sh
./setup-cloudflare-tunnel.sh
```

Este script:
- ✅ Instala `cloudflared` si no está instalado (vía Homebrew en macOS)
- ✅ Crea el directorio de configuración `.cloudflare/`
- ✅ Genera archivos de configuración base
- ✅ Crea scripts helper (start-tunnel.sh, tunnel-info.sh)

### 2. Autenticar con Cloudflare

```bash
cloudflared tunnel login
```

Esto abrirá tu navegador para autorizar el acceso. Selecciona tu dominio.

### 3. Crear el túnel

```bash
cloudflared tunnel create crediflux-dev
```

Este comando:
- Crea un túnel llamado `crediflux-dev`
- Genera un archivo de credenciales (UUID.json)
- Te muestra dónde está guardado

### 4. Copiar credenciales

Copia el archivo de credenciales generado al directorio del proyecto:

```bash
# El archivo estará en ~/.cloudflared/<UUID>.json
cp ~/.cloudflared/<UUID>.json .cloudflare/credentials.json
```

### 5. Configurar DNS

Ejecuta el siguiente comando para ver las rutas que necesitas crear:

```bash
cloudflared tunnel route dns crediflux-dev tu-dominio.com
cloudflared tunnel route dns crediflux-dev api-tu-dominio.com
```

O configura manualmente en el dashboard de Cloudflare:

**Frontend:**
- Tipo: CNAME
- Nombre: `crediflux` (o `@` para root domain)
- Contenido: `<UUID>.cfargotunnel.com`

**Backend API:**
- Tipo: CNAME
- Nombre: `api-crediflux`
- Contenido: `<UUID>.cfargotunnel.com`

### 6. Editar configuración

Edita `.cloudflare/config.yml` y reemplaza los dominios de ejemplo:

```yaml
ingress:
  # Frontend (Next.js)
  - hostname: crediflux.tu-dominio.com
    service: http://localhost:3000

  # Backend API (Django)
  - hostname: api-crediflux.tu-dominio.com
    service: http://localhost:8000

  - service: http_status:404
```

### 7. Iniciar el túnel

```bash
./scripts/start-tunnel.sh
```

¡Listo! Tu aplicación ahora es accesible desde:
- Frontend: https://crediflux.tu-dominio.com
- Backend API: https://api-crediflux.tu-dominio.com

## Comandos Útiles

### Ver información del túnel

```bash
./scripts/tunnel-info.sh
```

### Ver túneles existentes

```bash
cloudflared tunnel list
```

### Ver conexiones activas

```bash
cloudflared tunnel info crediflux-dev
```

### Detener el túnel

Presiona `Ctrl+C` en la terminal donde está corriendo.

## Configuración de CORS

Asegúrate de actualizar la configuración de CORS en el backend para permitir tu dominio:

En `.env` o `backend/config/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    'https://crediflux.tu-dominio.com',
    'http://localhost:3000',
]
```

## Desinstalación

Para eliminar completamente el túnel y su configuración:

```bash
cd scripts
chmod +x cleanup-cloudflare-tunnel.sh
./cleanup-cloudflare-tunnel.sh
```

Este script te preguntará:
1. ¿Eliminar configuración local? (archivos en `.cloudflare/`)
2. ¿Eliminar túnel de Cloudflare?
3. ¿Desinstalar cloudflared del sistema?

Puedes elegir qué eliminar en cada paso.

## Estructura de Archivos

Después de la instalación:

```
CrediFlux/
├── .cloudflare/              # Configuración del túnel (git ignored)
│   ├── config.yml            # Configuración de rutas
│   └── credentials.json      # Credenciales del túnel
├── scripts/
│   ├── setup-cloudflare-tunnel.sh      # Script de instalación
│   ├── cleanup-cloudflare-tunnel.sh    # Script de limpieza
│   ├── start-tunnel.sh                 # Iniciar túnel
│   ├── tunnel-info.sh                  # Ver información
│   └── CLOUDFLARE_TUNNEL.md            # Esta documentación
```

## Troubleshooting

### Error: "tunnel credentials file not found"

Asegúrate de haber copiado el archivo de credenciales a `.cloudflare/credentials.json`

### Error: "no such host"

Verifica que los DNS records estén configurados correctamente en Cloudflare y que hayan propagado (puede tomar unos minutos).

### El frontend no carga assets

Asegúrate de configurar `NEXT_PUBLIC_API_URL` en el frontend para que apunte a tu dominio de API:

```env
NEXT_PUBLIC_API_URL=https://api-crediflux.tu-dominio.com
```

### Problemas de CORS

Actualiza `CORS_ALLOWED_ORIGINS` en el backend para incluir tu dominio público.

## Modo de Desarrollo vs Producción

Este túnel es ideal para:
- ✅ Testing remoto
- ✅ Demos a clientes
- ✅ Desarrollo colaborativo
- ✅ Testing de webhooks

Para producción, considera:
- Despliegue en servidor real
- Certificados SSL propios
- Configuración de caché
- Load balancing

## Seguridad

El túnel de Cloudflare es seguro porque:
- Todo el tráfico está encriptado
- No necesitas exponer puertos
- Puedes agregar autenticación de Cloudflare Access
- Logs de acceso en el dashboard de Cloudflare

## Soporte

Para más información sobre Cloudflare Tunnel:
- [Documentación oficial](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [GitHub de cloudflared](https://github.com/cloudflare/cloudflared)

---

**Nota:** Recuerda agregar `.cloudflare/` a tu `.gitignore` para no commitear credenciales.
