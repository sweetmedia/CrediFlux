# Quick Tunnel GRATIS - Cloudflare (Sin Cuenta)

## 🎯 ¿Qué es esto?

Un túnel **TEMPORAL y GRATIS** que NO requiere:
- ❌ Cuenta de Cloudflare
- ❌ Dominio propio
- ❌ Configuración DNS
- ❌ Pago

Solo genera URLs aleatorias tipo: `https://random-words-123.trycloudflare.com`

## 🚀 Uso Super Rápido

```bash
cd scripts
./quick-tunnel-free.sh
```

Selecciona qué exponer:
1. Solo Frontend
2. Solo Backend
3. Ambos (en 2 túneles)

¡Y listo! Te dará una URL pública instantánea.

## 📋 Ejemplo de Uso

```bash
$ ./quick-tunnel-free.sh

╔═══════════════════════════════════════════════════════════╗
║      CloudFlare Quick Tunnel - GRATIS y TEMPORAL         ║
╚═══════════════════════════════════════════════════════════╝

¿Qué servicio quieres exponer?
  1) Frontend (Next.js)
  2) Backend (Django API)
  3) Ambos
  4) Cancelar

Selecciona: 1

Iniciando túnel para FRONTEND...
Espera unos segundos...

2025-10-29T02:30:15Z INF +--------------------------------------------------------------------------------------------+
2025-10-29T02:30:15Z INF |  Your quick Tunnel has been created! Visit it at:                                          |
2025-10-29T02:30:15Z INF |  https://amazing-voice-123.trycloudflare.com                                               |
2025-10-29T02:30:15Z INF +--------------------------------------------------------------------------------------------+

✓ Listo! Tu app está online en: https://amazing-voice-123.trycloudflare.com
```

## 🔄 Diferencias: Quick Tunnel vs Tunnel Normal

| Característica | Quick Tunnel (GRATIS) | Tunnel Normal |
|----------------|----------------------|---------------|
| Requiere cuenta | ❌ NO | ✅ Sí |
| Requiere dominio | ❌ NO | ✅ Sí |
| Configuración DNS | ❌ NO | ✅ Sí |
| URL | Aleatoria temporal | Tu dominio permanente |
| Duración | Mientras corra el script | Permanente |
| Costo | 🆓 GRATIS | 🆓 GRATIS (con cuenta) |
| Ideal para | Testing rápido, demos | Producción, proyectos serios |

## ⚡ Scripts Disponibles

### `quick-tunnel-free.sh` - Túnel Temporal
```bash
./quick-tunnel-free.sh
```

Menú interactivo para:
- Exponer solo frontend
- Exponer solo backend
- Exponer ambos en 2 túneles separados

## 📝 Pasos Detallados

### 1. Instalar cloudflared (solo una vez)

El script lo hace automáticamente, pero si quieres hacerlo manual:

```bash
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### 2. Iniciar tus servicios

```bash
docker-compose up
```

Verifica que estén corriendo:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### 3. Ejecutar el túnel

```bash
cd scripts
./quick-tunnel-free.sh
```

### 4. Copiar la URL

Busca en la salida del comando una línea como:
```
Your quick Tunnel has been created! Visit it at:
https://random-words-123.trycloudflare.com
```

¡Esa es tu URL pública! Compártela con quien quieras.

### 5. Detener el túnel

Presiona `Ctrl+C` en la terminal donde corre el túnel.

La URL dejará de funcionar inmediatamente.

## 🔧 Configuración para Exponer Ambos Servicios

Si expones frontend y backend por separado, necesitas actualizar las URLs:

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=https://backend-url-random.trycloudflare.com
```

### Backend (.env)
```env
CORS_ALLOWED_ORIGINS=https://frontend-url-random.trycloudflare.com,http://localhost:3000
```

Reinicia los servicios después de cambiar las variables:
```bash
docker-compose restart
```

## 💡 Casos de Uso

### ✅ Ideal Para:
- 🎯 Testing rápido con amigos/clientes
- 📱 Probar en tu móvil sin estar en la misma red
- 🔗 Testing de webhooks (necesitas URL pública)
- 👨‍💻 Demos rápidas sin desplegar
- 🐛 Debug de problemas específicos de producción

### ❌ NO Ideal Para:
- 🏢 Producción (la URL cambia cada vez)
- 📈 Proyectos a largo plazo
- 🔒 Aplicaciones que requieren URL fija
- 💼 Clientes que necesitan URL profesional

## ⚠️ Limitaciones

1. **URL aleatoria**: Cada vez que ejecutas el túnel, obtienes una URL diferente
2. **Temporal**: Si detienes el script, la URL deja de funcionar
3. **Sin personalización**: No puedes elegir la URL
4. **CORS**: Necesitas actualizar CORS cada vez si usas URLs diferentes

## 🎨 Ejemplo Completo

```bash
# Terminal 1: Iniciar servicios
docker-compose up

# Terminal 2: Túnel de frontend
cd scripts
./quick-tunnel-free.sh
# Selecciona opción 1
# Copia la URL: https://abc-123.trycloudflare.com

# Terminal 3: Túnel de backend (si lo necesitas)
cd scripts
./quick-tunnel-free.sh
# Selecciona opción 2
# Copia la URL: https://xyz-456.trycloudflare.com

# Actualiza variables de entorno con las URLs nuevas
# Reinicia servicios si es necesario

# Comparte la URL del frontend con quien quieras!
```

## 🔍 Troubleshooting

### "Connection refused"
Tu servicio local no está corriendo. Inicia Docker:
```bash
docker-compose up
```

### "cloudflared: command not found"
Instala cloudflared:
```bash
brew install cloudflared  # macOS
```

### CORS errors en el navegador
Actualiza `CORS_ALLOWED_ORIGINS` en el backend con la URL del túnel:
```env
CORS_ALLOWED_ORIGINS=https://tu-url-aleatoria.trycloudflare.com
```

### La URL no funciona después de un rato
El túnel solo funciona mientras el script está corriendo. Si lo detienes (Ctrl+C), la URL deja de funcionar.

### "ERR_NAME_NOT_RESOLVED"
Espera unos segundos, Cloudflare tarda 10-15 segundos en activar la URL completamente.

## 🆚 ¿Cuándo Usar Cada Tipo de Túnel?

### Quick Tunnel (este script)
```bash
./quick-tunnel-free.sh
```
- ✅ Testing rápido
- ✅ Sin configuración
- ✅ URL cambia cada vez
- ✅ 100% gratis

### Tunnel Normal (con cuenta)
```bash
./quick-tunnel.sh  # El otro script que creé
```
- ✅ URL personalizada permanente
- ✅ Tu propio dominio
- ✅ Configuración avanzada
- ✅ Ideal para producción/demos profesionales

## 📚 Recursos

- [Cloudflared Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/do-more-with-tunnels/trycloudflare/)
- [GitHub cloudflared](https://github.com/cloudflare/cloudflared)

## 🎉 ¡Disfruta tu túnel gratis!

Ahora puedes compartir tu aplicación con cualquiera, en cualquier lugar, sin configuración compleja.

---

**Tip:** Si necesitas una URL permanente con tu dominio, usa los otros scripts:
- `./quick-tunnel.sh` - Setup completo con dominio propio
- `./setup-cloudflare-tunnel.sh` - Setup paso a paso
