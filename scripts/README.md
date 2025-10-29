# Scripts de CrediFlux

Este directorio contiene scripts útiles para configurar y gestionar tu aplicación CrediFlux.

## 🚀 Cloudflare Quick Tunnel - Túnel GRATIS

Expón tu aplicación online instantáneamente **sin cuenta, sin dominio, sin configuración**.

### ⚡ Inicio Super Rápido

```bash
cd scripts
./quick-tunnel-free.sh
```

### 🎯 Características

- ✅ **100% GRATIS** - Sin costo alguno
- ✅ **Sin cuenta** - No necesitas registrarte en Cloudflare
- ✅ **Sin dominio** - No necesitas comprar dominio
- ✅ **Sin configuración** - Zero setup, funciona inmediatamente
- ✅ **URL aleatoria** - Tipo: `https://random-words-123.trycloudflare.com`
- ✅ **Temporal** - Funciona mientras el script esté corriendo

### 📋 Ejemplo de Uso

```bash
$ cd scripts
$ ./quick-tunnel-free.sh

╔═══════════════════════════════════════════════════════════╗
║      CloudFlare Quick Tunnel - GRATIS y TEMPORAL         ║
╚═══════════════════════════════════════════════════════════╝

✓ Frontend corriendo en http://localhost:3000
✓ Backend corriendo en http://localhost:8000

¿Qué servicio quieres exponer?
  1) Frontend (Next.js)
  2) Backend (Django API)
  3) Ambos
  4) Cancelar

Selecciona: 1

Iniciando túnel para FRONTEND...
Your quick Tunnel has been created! Visit it at:
https://amazing-voice-123.trycloudflare.com

✓ Listo! Comparte esta URL con quien quieras!
```

### 🎨 Opciones Disponibles

**Opción 1: Solo Frontend**
- Expone tu interfaz Next.js en una URL pública
- Ideal para mostrar la UI a clientes o testers

**Opción 2: Solo Backend**
- Expone tu API Django en una URL pública
- Perfecto para testing de webhooks o integraciones

**Opción 3: Ambos Servicios**
- Crea 2 túneles separados (frontend + backend)
- Obtienes 2 URLs diferentes
- Se abren en terminales separadas

### 📝 Requisitos Previos

1. **Tener Docker corriendo:**
   ```bash
   docker-compose up
   ```

2. **cloudflared instalado** (el script lo instala automáticamente si no lo tienes)

### 🔧 Configuración para Ambos Servicios

Si expones frontend y backend por separado, actualiza las variables de entorno:

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=https://tu-backend-url.trycloudflare.com
```

**Backend (.env):**
```env
CORS_ALLOWED_ORIGINS=https://tu-frontend-url.trycloudflare.com
```

Luego reinicia los servicios:
```bash
docker-compose restart
```

### 💡 Casos de Uso Ideales

- 🎯 **Testing rápido** - Prueba con amigos o clientes sin desplegar
- 📱 **Testing móvil** - Prueba en tu teléfono sin estar en la misma red
- 🔗 **Webhooks** - Testing de APIs que necesitan URLs públicas
- 👨‍💻 **Demos** - Comparte tu trabajo en progreso
- 🐛 **Debug** - Reproduce problemas específicos con URLs públicas

### ⚠️ Importante

- La URL es **temporal** - Solo funciona mientras el script corre
- La URL es **aleatoria** - Cambia cada vez que ejecutas el script
- Para detener: Presiona `Ctrl+C`

### 🔍 Troubleshooting

**"Connection refused"**
```bash
# Tu servicio no está corriendo, inicia Docker:
docker-compose up
```

**"cloudflared: command not found"**
```bash
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**CORS errors**
```bash
# Actualiza CORS_ALLOWED_ORIGINS en backend con la URL del túnel
```

**"ERR_NAME_NOT_RESOLVED"**
```bash
# Espera 10-15 segundos, Cloudflare tarda en activar la URL
```

### 📚 Documentación Completa

Ver [QUICK_TUNNEL_FREE.md](QUICK_TUNNEL_FREE.md) para documentación detallada.

### 🎉 ¡Listo!

Ahora puedes compartir tu aplicación con cualquiera, en cualquier lugar, sin configuración compleja.

```bash
# Ejecuta y obtén tu URL en segundos:
./quick-tunnel-free.sh
```

---

**Hecho con ❤️ para desarrollo rápido y testing sin complicaciones**
