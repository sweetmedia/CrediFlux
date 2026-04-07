# Deployment Guide - CrediFlux

## Índice

- [Pre-requisitos](#pre-requisitos)
- [Deployment con Docker](#deployment-con-docker)
- [Configuración de Producción](#configuración-de-producción)
- [Nginx y SSL](#nginx-y-ssl)
- [Variables de Entorno](#variables-de-entorno)
- [Monitoreo](#monitoreo)
- [Backups](#backups)
- [Actualización de Código](#actualización-de-código)
- [Rollback](#rollback)
- [Troubleshooting en Producción](#troubleshooting-en-producción)

---

## Pre-requisitos

### Servidor

**Recomendado**:
- **CPU**: 4+ cores
- **RAM**: 8GB+ (mínimo 4GB)
- **Disco**: 50GB+ SSD
- **OS**: Ubuntu 22.04 LTS o superior

### Software

- Docker 24+
- Docker Compose 2+
- Nginx 1.18+
- PostgreSQL 15+ (puede estar en Docker)
- Redis 7+ (puede estar en Docker)
- Git

### Dominios

- Dominio principal: `crediflux.com`
- Wildcard subdomain: `*.crediflux.com` (para tenants)
- Certificados SSL (Let's Encrypt recomendado)

---

## Deployment con Docker

### 1. Configurar Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

### 2. Clonar Repositorio

```bash
# Crear directorio para la app
sudo mkdir -p /opt/crediflux
sudo chown $USER:$USER /opt/crediflux
cd /opt/crediflux

# Clonar
git clone https://github.com/sweetmedia/CrediFlux.git .

# Checkout a tag de producción (recomendado)
git checkout tags/v1.0.0
```

### 3. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env.production

# Editar con valores de producción
nano .env.production
```

**Contenido de `.env.production`**:

```env
# Django
DJANGO_SECRET_KEY=your-super-secret-key-here-min-50-chars
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=crediflux.com,*.crediflux.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Database
POSTGRES_DB=crediflux_prod
POSTGRES_USER=crediflux_prod_user
POSTGRES_PASSWORD=super-secure-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CORS (si frontend está en otro dominio)
CORS_ALLOWED_ORIGINS=https://app.crediflux.com

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@crediflux.com
EMAIL_HOST_PASSWORD=app-specific-password-here

# JWT
JWT_SECRET_KEY=another-super-secret-key-for-jwt

# AWS S3 (opcional para media files)
USE_S3=True
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=crediflux-media
AWS_S3_REGION_NAME=us-east-1

# Monitoring
SENTRY_DSN=https://your-sentry-dsn-here
```

### 4. Crear docker-compose.prod.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env.production
    restart: always
    networks:
      - crediflux-network

  redis:
    image: redis:7-alpine
    restart: always
    networks:
      - crediflux-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - crediflux-network

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A config worker -l info --concurrency=4
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - crediflux-network

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A config beat -l info
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: always
    networks:
      - crediflux-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    env_file:
      - .env.production
    restart: always
    networks:
      - crediflux-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/conf.d:/etc/nginx/conf.d:ro
      - static_volume:/var/www/static
      - media_volume:/var/www/media
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - backend
      - frontend
    restart: always
    networks:
      - crediflux-network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  crediflux-network:
    driver: bridge
```

### 5. Crear Dockerfile.prod

**backend/Dockerfile.prod**:

```dockerfile
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements/production.txt /app/requirements.txt

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código
COPY . /app/

# Crear usuario no-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Colectar archivos estáticos
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

**frontend/Dockerfile.prod**:

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
```

### 6. Build y Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Verificar servicios corriendo
docker-compose -f docker-compose.prod.yml ps
```

### 7. Inicializar Base de Datos

```bash
# Aplicar migraciones compartidas
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate_schemas --shared

# Crear superusuario
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Crear tenant inicial
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
```

```python
from apps.tenants.models import Tenant, Domain

tenant = Tenant.objects.create(
    schema_name='demo',
    name='Demo Company',
    email='admin@demo.crediflux.com',
    subscription_plan='professional'
)

Domain.objects.create(
    domain='demo.crediflux.com',
    tenant=tenant,
    is_primary=True
)
```

---

## Configuración de Producción

### Settings de Django

**config/settings/production.py**:

```python
from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS')

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Static files
STATIC_ROOT = '/app/staticfiles'
STATIC_URL = '/static/'

# Media files (usar S3 en producción)
if env.bool('USE_S3', default=False):
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
else:
    MEDIA_ROOT = '/app/media'
    MEDIA_URL = '/media/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/crediflux/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Sentry (error tracking)
if env('SENTRY_DSN', default=None):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
        environment='production',
    )
```

---

## Nginx y SSL

### 1. Instalar Certbot

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado para dominio principal
sudo certbot --nginx -d crediflux.com -d www.crediflux.com

# Certificado wildcard (requiere DNS challenge)
sudo certbot certonly --manual --preferred-challenges=dns \
  -d crediflux.com -d *.crediflux.com
```

### 2. Configurar Nginx

**docker/nginx/conf.d/crediflux.conf**:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name crediflux.com *.crediflux.com;
    return 301 https://$host$request_uri;
}

# Main app
server {
    listen 443 ssl http2;
    server_name crediflux.com www.crediflux.com;

    ssl_certificate /etc/letsencrypt/live/crediflux.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crediflux.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin
    location /admin {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/media/;
        expires 7d;
    }

    # Max upload size
    client_max_body_size 20M;
}

# Tenant subdomains
server {
    listen 443 ssl http2;
    server_name ~^(?<tenant>.+)\.crediflux\.com$;

    ssl_certificate /etc/letsencrypt/live/crediflux.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crediflux.com/privkey.pem;

    # Same SSL config as above...

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Renovar SSL Automáticamente

```bash
# Agregar a crontab
sudo crontab -e

# Agregar línea:
0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f /opt/crediflux/docker-compose.prod.yml restart nginx
```

---

## Monitoreo

### 1. Health Checks

```bash
# Crear script de health check
cat > /opt/crediflux/healthcheck.sh << 'EOF'
#!/bin/bash

# Check backend
curl -f http://localhost/api/health/ || exit 1

# Check DB
docker-compose -f docker-compose.prod.yml exec -T db pg_isready || exit 1

# Check Redis
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping || exit 1

echo "All services healthy"
EOF

chmod +x /opt/crediflux/healthcheck.sh
```

### 2. Monitoring con Prometheus (opcional)

**docker-compose.prod.yml** (agregar):

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: always

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    restart: always
```

### 3. Alertas por Email

```python
# config/settings/production.py
ADMINS = [
    ('Admin Name', 'admin@crediflux.com'),
]

SERVER_EMAIL = 'server@crediflux.com'
```

---

## Backups

### 1. Backup Automático de PostgreSQL

```bash
# Crear script de backup
cat > /opt/crediflux/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/crediflux/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup completo
docker-compose -f /opt/crediflux/docker-compose.prod.yml exec -T db \
  pg_dump -U crediflux_prod_user crediflux_prod | \
  gzip > $BACKUP_DIR/crediflux_$DATE.sql.gz

# Mantener solo últimos 30 días
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Subir a S3 (opcional)
aws s3 cp $BACKUP_DIR/crediflux_$DATE.sql.gz \
  s3://crediflux-backups/database/

echo "Backup completed: crediflux_$DATE.sql.gz"
EOF

chmod +x /opt/crediflux/backup.sh
```

### 2. Cron para Backups Diarios

```bash
# Agregar a crontab
sudo crontab -e

# Backup diario a las 2 AM
0 2 * * * /opt/crediflux/backup.sh >> /var/log/crediflux/backup.log 2>&1
```

### 3. Restore desde Backup

```bash
# Descargar backup
aws s3 cp s3://crediflux-backups/database/crediflux_20251030_020000.sql.gz .

# Descomprimir
gunzip crediflux_20251030_020000.sql.gz

# Restore
docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U crediflux_prod_user crediflux_prod < crediflux_20251030_020000.sql
```

---

## Actualización de Código

### Deploy de Nueva Versión

```bash
cd /opt/crediflux

# 1. Backup
./backup.sh

# 2. Pull código
git pull origin master
# O checkout a tag específico
git checkout tags/v1.1.0

# 3. Rebuild images
docker-compose -f docker-compose.prod.yml build

# 4. Aplicar migraciones
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate_schemas

# 5. Colectar estáticos
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# 6. Restart servicios
docker-compose -f docker-compose.prod.yml restart

# 7. Verificar
curl -f https://crediflux.com/api/health/
```

### Zero-Downtime Deploy

```bash
# 1. Build nuevas images con tag
docker-compose -f docker-compose.prod.yml build --parallel

# 2. Scale up con nuevas images
docker-compose -f docker-compose.prod.yml up -d --scale backend=2

# 3. Wait for health checks
sleep 10

# 4. Remove old containers
docker-compose -f docker-compose.prod.yml up -d --remove-orphans
```

---

## Rollback

```bash
# 1. Checkout a versión anterior
git checkout tags/v1.0.0

# 2. Restore DB si es necesario
# (ver sección de Backups)

# 3. Rebuild y restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting en Producción

### Ver Logs

```bash
# Todos los servicios
docker-compose -f docker-compose.prod.yml logs --tail=100 -f

# Servicio específico
docker-compose -f docker-compose.prod.yml logs -f backend

# Logs de Django
tail -f /var/log/crediflux/django.log

# Logs de Nginx
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### Verificar Recursos

```bash
# Uso de Docker
docker stats

# Espacio en disco
df -h

# Memoria
free -h

# Conexiones de DB
docker-compose -f docker-compose.prod.yml exec db \
  psql -U crediflux_prod_user -c "SELECT count(*) FROM pg_stat_activity;"
```

---

**Última actualización**: 2025-10-30
