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

### 🔧 Configuración para Acceso desde Móvil

**El problema:** Por defecto, el frontend intenta conectarse a tu IP local y el backend no permite CORS desde URLs externas.

**La solución:** Usa el configurador automático!

#### Pasos para Acceso desde Móvil:

1. **Inicia los túneles** (necesitas 2: frontend + backend)
   ```bash
   # Opción A: Automático (abre 2 terminales)
   ./quick-tunnel-free.sh
   # Selecciona opción 3 (Ambos)

   # Opción B: Manual (en 2 terminales diferentes)
   # Terminal 1:
   ./quick-tunnel-free.sh  # Selecciona 1 (Frontend)

   # Terminal 2:
   ./quick-tunnel-free.sh  # Selecciona 2 (Backend)
   ```

2. **Copia las URLs** que aparecen en las terminales:
   ```
   Frontend: https://abc-123.trycloudflare.com
   Backend:  https://xyz-456.trycloudflare.com
   ```

3. **Ejecuta el configurador:**
   ```bash
   ./configure-tunnel-urls.sh
   ```

   - Ingresa la URL del frontend
   - Ingresa la URL del backend
   - Confirma que reinicie los contenedores

4. **¡Listo!** Ahora accede desde tu móvil:
   ```
   https://abc-123.trycloudflare.com
   ```

#### Volver a Configuración Local:

Cuando termines de usar el túnel:
```bash
./restore-local-config.sh
```

Esto restaura las URLs locales (`localhost:3000` y `localhost:8000`).

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
