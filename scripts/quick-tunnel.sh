#!/bin/bash

# Quick Setup Script para Cloudflare Tunnel
# Este script guía paso a paso la configuración completa

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CF_DIR="${PROJECT_DIR}/.cloudflare"

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║         CloudFlare Tunnel - Quick Setup                  ║
║                 CrediFlux                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${BLUE}Este script te guiará paso a paso para configurar el túnel.${NC}"
echo ""

# Step 1: Check if already configured
if [ -f "${CF_DIR}/credentials.json" ] && [ -f "${SCRIPT_DIR}/start-tunnel.sh" ]; then
    echo -e "${GREEN}✓ El túnel ya está configurado!${NC}"
    echo ""
    echo "Opciones:"
    echo "  1) Iniciar túnel"
    echo "  2) Ver información del túnel"
    echo "  3) Reconfigurar túnel"
    echo "  4) Eliminar túnel"
    echo "  5) Salir"
    echo ""
    read -p "Selecciona una opción (1-5): " choice

    case $choice in
        1)
            exec "${SCRIPT_DIR}/start-tunnel.sh"
            ;;
        2)
            exec "${SCRIPT_DIR}/tunnel-info.sh"
            ;;
        3)
            echo -e "${YELLOW}Reconfigurando...${NC}"
            ;;
        4)
            exec "${SCRIPT_DIR}/cleanup-cloudflare-tunnel.sh"
            ;;
        5)
            exit 0
            ;;
        *)
            echo -e "${RED}Opción inválida${NC}"
            exit 1
            ;;
    esac
fi

# Step 2: Run setup
echo -e "${YELLOW}Paso 1/5: Instalando cloudflared...${NC}"
echo ""
"${SCRIPT_DIR}/setup-cloudflare-tunnel.sh"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 3: Login
echo -e "${YELLOW}Paso 2/5: Autenticación con Cloudflare${NC}"
echo ""
echo -e "${BLUE}Abriendo tu navegador para autenticar...${NC}"
echo -e "${BLUE}Selecciona el dominio donde quieres crear el túnel.${NC}"
echo ""
read -p "Presiona Enter para continuar..."

cloudflared tunnel login

echo ""
echo -e "${GREEN}✓ Autenticación completada${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 4: Create tunnel
echo -e "${YELLOW}Paso 3/5: Creando túnel${NC}"
echo ""

read -p "¿Nombre del túnel? (default: crediflux-dev): " tunnel_name
tunnel_name=${tunnel_name:-crediflux-dev}

cloudflared tunnel create "$tunnel_name"

echo ""
echo -e "${GREEN}✓ Túnel creado${NC}"
echo ""

# Find credentials file
CRED_FILE=$(ls ~/.cloudflared/*.json 2>/dev/null | head -1)

if [ -n "$CRED_FILE" ]; then
    echo -e "${BLUE}Copiando credenciales...${NC}"
    mkdir -p "${CF_DIR}"
    cp "$CRED_FILE" "${CF_DIR}/credentials.json"
    echo -e "${GREEN}✓ Credenciales copiadas${NC}"
else
    echo -e "${RED}⚠ No se encontró el archivo de credenciales automáticamente${NC}"
    echo "Por favor copia manualmente:"
    echo "  cp ~/.cloudflared/<UUID>.json ${CF_DIR}/credentials.json"
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 5: Configure domains
echo -e "${YELLOW}Paso 4/5: Configuración de dominios${NC}"
echo ""
echo -e "${BLUE}Ingresa tu dominio de Cloudflare${NC}"
read -p "Dominio (ej: midominio.com): " domain

if [ -z "$domain" ]; then
    echo -e "${RED}⚠ Dominio requerido${NC}"
    exit 1
fi

read -p "Subdominio para frontend (default: crediflux): " subdomain_frontend
subdomain_frontend=${subdomain_frontend:-crediflux}

read -p "Subdominio para API (default: api-crediflux): " subdomain_api
subdomain_api=${subdomain_api:-api-crediflux}

frontend_hostname="${subdomain_frontend}.${domain}"
api_hostname="${subdomain_api}.${domain}"

# Update config file
cat > "${CF_DIR}/config.yml" << EOF
# Cloudflare Tunnel Configuration for CrediFlux
tunnel: ${tunnel_name}
credentials-file: ${CF_DIR}/credentials.json

ingress:
  # Frontend (Next.js)
  - hostname: ${frontend_hostname}
    service: http://localhost:3000

  # Backend API (Django)
  - hostname: ${api_hostname}
    service: http://localhost:8000

  # Catch-all rule (required)
  - service: http_status:404
EOF

echo ""
echo -e "${GREEN}✓ Configuración actualizada${NC}"
echo ""
echo -e "${BLUE}Configurando DNS...${NC}"

cloudflared tunnel route dns "$tunnel_name" "$frontend_hostname" || echo -e "${YELLOW}⚠ Configura manualmente si falló${NC}"
cloudflared tunnel route dns "$tunnel_name" "$api_hostname" || echo -e "${YELLOW}⚠ Configura manualmente si falló${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 6: CORS configuration reminder
echo -e "${YELLOW}Paso 5/5: Configuración final${NC}"
echo ""
echo -e "${CYAN}IMPORTANTE: Actualiza la configuración de CORS en tu backend${NC}"
echo ""
echo "Agrega estas líneas a tu archivo .env del backend:"
echo ""
echo -e "${GREEN}CORS_ALLOWED_ORIGINS=https://${frontend_hostname},http://localhost:3000${NC}"
echo ""
read -p "Presiona Enter cuando hayas actualizado la configuración..."

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Summary
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ✓ Configuración Completada                  ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${GREEN}Tu aplicación estará disponible en:${NC}"
echo ""
echo -e "  Frontend:  ${CYAN}https://${frontend_hostname}${NC}"
echo -e "  Backend:   ${CYAN}https://${api_hostname}${NC}"
echo ""
echo -e "${YELLOW}Para iniciar el túnel:${NC}"
echo -e "  ${GREEN}./scripts/start-tunnel.sh${NC}"
echo ""
echo -e "${YELLOW}Para ver información:${NC}"
echo -e "  ${GREEN}./scripts/tunnel-info.sh${NC}"
echo ""
echo -e "${YELLOW}Para limpiar/desinstalar:${NC}"
echo -e "  ${GREEN}./scripts/cleanup-cloudflare-tunnel.sh${NC}"
echo ""

read -p "¿Iniciar el túnel ahora? (Y/n): " start_now

if [[ ! $start_now =~ ^[Nn]$ ]]; then
    echo ""
    exec "${SCRIPT_DIR}/start-tunnel.sh"
fi
