# Producción en el VPS (beta)

Runbook para subir CrediFlux V2 al VPS actual (`23.95.73.125`) con `docker-compose.prod.yml`. El VPS
es compartido: allí también corren kinpop y la web/landing de CrediFlux. La migración a Sevalla
está al final.

**Topología**

```
Cliente → Cloudflare (proxy, TLS)
        → nginx del host (cert de origen *.crediflux.com.do; docs/deployment/nginx/crediflux-prod.conf)
        → 127.0.0.1:3700  frontend (SPA, nginx del contenedor)
        → 127.0.0.1:8700  backend (gunicorn)    + celery + celery-beat
          (db y redis sin puertos publicados)
```

- **Repo:** `/opt/crediflux-prod`, rama `v2` de github. `/opt/crediflux` (V1) queda intacto como
  rollback.
- **Datos:**
  - Postgres en el volumen `crediflux-prod_pg_data`;
  - archivos subidos en `/opt/crediflux-prod/data/media`;
  - estáticos de Django en `/opt/crediflux-prod/data/static`, que sirve nginx.
- El stack V1 anterior (`crediflux_*`, puertos 3600/8600 y volumen `crediflux_postgres_data`) está
  parado. No se borra hasta que el beta esté estable.

## 0. Antes (una vez, fuera del servidor)

- **Cloudflare:**
  - SSL/TLS en **Full (strict)**: el origen ya tiene el certificado de origen de Cloudflare en
    `/etc/nginx/ssl/crediflux-origin.*`.
  - DNS proxied (nube naranja) para `app` y `*` en `crediflux.com.do`.
- **Resend:**
  - Verificar el dominio `crediflux.com.do` (registros SPF/DKIM en Cloudflare).
  - Crear una API key de envío.
  - El remitente es `DEFAULT_FROM_EMAIL`.
- **Disco:** el `/` del VPS está al 82 % (13 GB libres). Limpiar imágenes viejas antes de construir:
  `docker image prune -a` revisando qué borra. No borrar los volúmenes de kinpop ni los de la web.

## 1. Código y variables

```bash
git clone -b v2 https://github.com/sweetmedia/CrediFlux.git /opt/crediflux-prod
cd /opt/crediflux-prod
cp .env.production.example .env.production && chmod 600 .env.production
mkdir -p data/media data/static
```

Rellenar `.env.production`:
- los cuatro `CAMBIAR` (los comandos para generarlos están en el archivo);
- revisar dominios y correo.

`FIELD_ENCRYPTION_KEY` y `POSTGRES_PASSWORD` se guardan también en el gestor de contraseñas. Sin
`FIELD_ENCRYPTION_KEY` no se descifran los secretos guardados en la BD.

`VITE_APP_URL` tiene que tener el mismo host que `FRONTEND_URL`, porque se incrusta en el build.

## 2. Construir e inicializar

```bash
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
$C build
$C up -d db redis
$C run --rm backend python manage.py migrate_schemas --shared
$C run --rm backend python manage.py init_public_tenant --domain app.crediflux.com.do
$C run --rm backend python manage.py createsuperuser   # superusuario de plataforma (sin tenant)
$C run --rm backend python manage.py setup_periodic_tasks
$C up -d
$C ps    # backend healthy
```

Las migraciones nunca corren solas. En cada actualización:
`$C run --rm backend python manage.py migrate_schemas` (todos los schemas).

## 3. nginx del host

```bash
cp docs/deployment/nginx/crediflux-prod.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/crediflux-prod.conf /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/crediflux-ssl.conf     # vhost V1 (3000/8000)
```

En `/etc/nginx/sites-enabled/crediflux.com.do`:
- quitar los bloques de puerto 80 de `app.`, `demo.` y el comodín `~^(?<tenant>…)`, que apuntan a
  3600/8600;
- dejar el de `crediflux.com.do` / `www`, la landing.

Después:

```bash
nginx -t && systemctl reload nginx
```

Antes de recargar, revisar que los rangos `set_real_ip_from` del conf coinciden con
https://www.cloudflare.com/ips/.

## 4. Firewall

Docker publica en `127.0.0.1`, así que nada del stack queda expuesto. Aun así, cerrar las reglas
V1 que ya no se usan:

```bash
ufw delete allow 8600/tcp
ufw delete allow 3600/tcp
ufw delete allow 8625/tcp
```

## 5. Alta del cliente beta

- Desde `https://app.crediflux.com.do/register`, o desde el admin con el superusuario de plataforma
  en `https://app.crediflux.com.do/admin/`.
- El tenant queda en `https://<subdominio>.crediflux.com.do`.
- Revisar su política de préstamos en Configuración. Los defaults de tenants nuevos son estrictos:
  cédula y aprobación de desembolso obligatorias, tasa máxima del 36 % anual.

## 5b. Padrón de la JCE (D5)

El padrón vive en `public.padron_jce` y se carga con un comando, todo o nada: si el archivo trae
una línea con otro número de columnas, una cédula que no sea de 11 dígitos o un sexo distinto de
M/F, no se carga nada y la tabla anterior queda intacta. Archivo `|`-delimitado, UTF-8, sin cabecera.

```bash
cd /opt/crediflux-prod
C="docker compose -f docker-compose.prod.yml --env-file .env.production"
$C cp /opt/crediflux/data/padron_extract.csv backend:/tmp/padron_extract.csv
# 1) validar sin tocar la tabla
$C exec backend python manage.py load_padron_jce /tmp/padron_extract.csv --dry-run
# 2) cargar (reemplaza el contenido anterior; ~7,9 M de filas)
$C exec backend python manage.py load_padron_jce /tmp/padron_extract.csv
$C exec backend rm /tmp/padron_extract.csv
```

La carga bloquea la tabla del padrón mientras dura (las consultas por cédula esperan), así que hay
que correrla en una ventana tranquila. `--dry-run` hace la carga completa y la revierte, por lo que
tarda casi lo mismo. Si el archivo trae menos del 90 % de las filas actuales el comando se niega
(parece truncado); `--force` sólo para un archivo intencionalmente más pequeño.

Es un dato de referencia pesado (550 MB): no va en el repo ni en los backups de media.

## 6. Comprobaciones después de subir

Sin carga y sin datos reales:

- [ ] `curl -sI https://app.crediflux.com.do/api/health/` → 200 por Cloudflare.
- [ ] `https://app.crediflux.com.do/swagger/` → 404 (la documentación no se publica).
- [ ] Login en el subdominio del beta y en `/admin/`.
- [ ] Correo de reset recibido, con remitente correcto y enlace al subdominio del tenant.
- [ ] IP real:
  - hacer una acción y ver en la auditoría (`/api/audit/` o el admin) que `ip_address` es la IP
    pública propia;
  - repetir con un `X-Forwarded-For: 192.0.2.1` inventado: debe seguir saliendo la real. Cierra la
    pista `DRF_NUM_PROXIES` de run-7.
- [ ] `docker compose … exec backend python -c "from django.conf import settings as s; print(s.DEBUG, getattr(s,'CORS_ALLOW_ALL_ORIGINS',False))"`
      → `False False`. Cierra la pista del overlay de run-7.
- [ ] Subir un documento de prueba y abrirlo: la URL es `/media/s/<firma>/`, y `/media/<ruta>` da 404.

## 7. Backups y tareas

En el `crontab` de root:

```cron
# BD + media cada noche, 7 días de retención (copiar fuera del VPS: el disco es pequeño)
30 3 * * * cd /opt/crediflux-prod && docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db pg_dump -U crediflux -Fc crediflux > /opt/backups/crediflux-$(date +\%F).dump && tar czf /opt/backups/crediflux-media-$(date +\%F).tgz -C data media && find /opt/backups -name 'crediflux-*' -mtime +7 -delete
# Registros pendientes sin aprovisionar: se borran a los 7 días
15 4 * * * cd /opt/crediflux-prod && docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend python manage.py expire_pending_registrations --days 7
```

Probar una restauración en local antes de dar el beta por estable:
`pg_restore -d <bd vacía> crediflux-AAAA-MM-DD.dump`.

## 8. Actualizar

```bash
cd /opt/crediflux-prod && git pull --ff-only
$C build && $C run --rm backend python manage.py migrate_schemas && $C up -d
```

**Rollback:**
1. `git checkout <commit anterior>` y luego `$C build && $C up -d`.
2. Si hubo migraciones, restaurar el dump de esa noche.

## 9. Migrar a Sevalla (después del beta)

Las imágenes y las variables son las mismas; cambia la infraestructura:

1. **Postgres gestionado** en Sevalla:
   - `DATABASE_URL` sustituye a `POSTGRES_*`;
   - restaurar el último `pg_dump -Fc` con `pg_restore`;
   - django-tenants necesita que el usuario pueda crear schemas.
2. **Redis gestionado**: `REDIS_URL`, `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`.
3. **Procesos:**
   - `backend` (web, puerto 8000);
   - `celery` y `celery-beat` (workers con el mismo Dockerfile y otro comando);
   - `frontend` como sitio estático (build de `frontend/`, fallback a `index.html`, y la cabecera
     `Referrer-Policy: no-referrer` de `frontend/nginx.conf`).
4. **Media:**
   - Sevalla no tiene disco persistente compartido: pasar a object storage.
   - Antes hay que separar media de static: storage propio para media con `location='media'`,
     privado y con URLs firmadas. Es la pista S3 de run-7.
   - Hasta entonces no activar `USE_S3`.
5. **Proxy:**
   - Cloudflare delante de Sevalla cambia la cadena de proxies. Recalcular `DRF_NUM_PROXIES` o
     confiar sólo en `CF-Connecting-IP`, y repetir la comprobación de IP real del §6.
6. **Dominios:** wildcard `*.crediflux.com.do` hacia Sevalla; comprobar que la plataforma admite
   dominios comodín con TLS.
