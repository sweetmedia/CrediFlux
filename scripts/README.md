# Scripts de CrediFlux

Este directorio contiene scripts útiles para configurar y gestionar tu aplicación CrediFlux.

## 🚀 Cloudflare Tunnel - Exponer tu App Online

### 🎯 DOS OPCIONES DISPONIBLES:

#### Opción 1: Quick Tunnel GRATIS ⚡ (RECOMENDADO para testing)

```bash
cd scripts
./quick-tunnel-free.sh
```

**✅ NO requiere cuenta, NO requiere dominio, 100% GRATIS**
- URL aleatoria tipo: `https://random-123.trycloudflare.com`
- Temporal (mientras corre el script)
- Ideal para testing rápido y demos

**Ver documentación:** [QUICK_TUNNEL_FREE.md](QUICK_TUNNEL_FREE.md)

#### Opción 2: Tunnel Permanente con Tu Dominio 🏢

```bash
cd scripts
./quick-tunnel.sh
```

Este script interactivo te guiará paso a paso:
1. ✅ Instala cloudflared
2. ✅ Te autentica con Cloudflare
3. ✅ Crea el túnel
4. ✅ Configura tus dominios
5. ✅ Inicia el túnel

**Requiere:** Cuenta de Cloudflare + Dominio propio
**Ideal para:** Producción, demos profesionales, URLs permanentes

**Ver documentación:** [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md)

### Scripts Disponibles

#### `quick-tunnel-free.sh` - Túnel Gratis Temporal ⚡ (NUEVO)
Túnel sin cuenta, sin dominio. URL aleatoria instantánea.
```bash
./quick-tunnel-free.sh
```

#### `quick-tunnel.sh` - Todo en uno con Dominio ⭐
Setup interactivo completo con menú de opciones (requiere cuenta).
```bash
./quick-tunnel.sh
```

#### `setup-cloudflare-tunnel.sh` - Setup Manual
Instala cloudflared y crea la configuración base.
```bash
./setup-cloudflare-tunnel.sh
```

#### `start-tunnel.sh` - Iniciar Túnel
Inicia el túnel de Cloudflare (generado automáticamente).
```bash
./start-tunnel.sh
```

#### `tunnel-info.sh` - Ver Información
Muestra información sobre túneles configurados.
```bash
./tunnel-info.sh
```

#### `cleanup-cloudflare-tunnel.sh` - Desinstalar
Elimina completamente el túnel y su configuración.
```bash
./cleanup-cloudflare-tunnel.sh
```

### ¿Qué necesitas?

- Una cuenta de Cloudflare (gratis): https://dash.cloudflare.com/sign-up
- Un dominio agregado a Cloudflare
- Docker Compose corriendo (tu app local)

### Flujo de Trabajo

```
1. Configura una vez:
   ./quick-tunnel.sh

2. Cada vez que quieras exponer tu app:
   ./start-tunnel.sh

3. Tu app estará en:
   https://tu-dominio.com

4. Para detener: Ctrl+C

5. Para limpiar todo:
   ./cleanup-cloudflare-tunnel.sh
```

### Solución de Problemas

**"cloudflared: command not found"**
```bash
# macOS
brew install cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

**"tunnel credentials file not found"**
```bash
# Copia manualmente las credenciales
cp ~/.cloudflared/<UUID>.json .cloudflare/credentials.json
```

**CORS errors**
Asegúrate de actualizar el backend .env:
```env
CORS_ALLOWED_ORIGINS=https://tu-dominio.com,http://localhost:3000
```

### Documentación Completa

Para más detalles, ver: [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md)

---

## 📁 Estructura de Archivos

Después de configurar el túnel:

```
scripts/
├── README.md                          # Este archivo
├── CLOUDFLARE_TUNNEL.md               # Documentación completa
├── quick-tunnel.sh                    # ⭐ Setup interactivo
├── setup-cloudflare-tunnel.sh         # Setup paso a paso
├── cleanup-cloudflare-tunnel.sh       # Desinstalar
├── start-tunnel.sh                    # Generado: inicia túnel
└── tunnel-info.sh                     # Generado: info del túnel

../.cloudflare/                        # Git ignored
├── config.yml                         # Configuración de rutas
└── credentials.json                   # Credenciales (NO COMMITEAR)
```

---

## 🔒 Seguridad

- ✅ Las credenciales están en `.gitignore`
- ✅ Todo el tráfico está encriptado
- ✅ No expones puertos localmente
- ✅ Puedes agregar autenticación Cloudflare Access

---

## 💡 Tips

1. **Desarrollo en equipo**: Cada miembro puede usar su propio túnel
2. **Testing de webhooks**: Ideal para APIs que necesitan URLs públicas
3. **Demos**: Comparte tu trabajo sin desplegar
4. **Mobile testing**: Prueba en tu teléfono sin estar en la misma red

---

## 🆘 Ayuda

¿Problemas? Revisa:
1. [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md) - Documentación completa
2. [Cloudflare Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
3. [cloudflared GitHub](https://github.com/cloudflare/cloudflared)

---

**¡Disfruta de tu túnel!** 🎉
