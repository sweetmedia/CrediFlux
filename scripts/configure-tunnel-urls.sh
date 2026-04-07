#!/bin/bash

# Script para configurar URLs del túnel de Cloudflare
# Actualiza CORS y API URLs automáticamente

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
DOCKER_COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        Configurador de URLs para Cloudflare Tunnel       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${BLUE}Este script configurará tu aplicación para usar las URLs del túnel.${NC}"
echo ""

# Check if files exist
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: No se encontró el archivo .env${NC}"
    exit 1
fi

if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo -e "${RED}Error: No se encontró docker-compose.yml${NC}"
    exit 1
fi

echo -e "${YELLOW}Instrucciones:${NC}"
echo "1. Primero ejecuta el túnel (en otra terminal):"
echo -e "   ${GREEN}./quick-tunnel-free.sh${NC}"
echo ""
echo "2. Copia las URLs que te da el túnel"
echo ""
echo "3. Ingresa esas URLs aquí"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Ask for URLs
read -p "URL del FRONTEND (ej: https://abc-123.trycloudflare.com): " FRONTEND_URL
read -p "URL del BACKEND (ej: https://xyz-456.trycloudflare.com): " BACKEND_URL

# Validate URLs
if [ -z "$FRONTEND_URL" ] || [ -z "$BACKEND_URL" ]; then
    echo -e "${RED}Error: Debes ingresar ambas URLs${NC}"
    exit 1
fi

# Remove trailing slashes
FRONTEND_URL="${FRONTEND_URL%/}"
BACKEND_URL="${BACKEND_URL%/}"

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Configuración a aplicar:${NC}"
echo ""
echo -e "  Frontend: ${GREEN}${FRONTEND_URL}${NC}"
echo -e "  Backend:  ${GREEN}${BACKEND_URL}${NC}"
echo ""
read -p "¿Continuar? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo -e "${BLUE}Configurando...${NC}"
echo ""

# Backup files
cp "$ENV_FILE" "${ENV_FILE}.backup"
cp "$DOCKER_COMPOSE_FILE" "${DOCKER_COMPOSE_FILE}.backup"

echo -e "${GREEN}✓ Backup creado${NC}"

# Update .env - CORS
echo -e "${YELLOW}Actualizando CORS en .env...${NC}"

# Get current CORS, add new URLs
CURRENT_CORS=$(grep "^CORS_ALLOWED_ORIGINS=" "$ENV_FILE" | cut -d= -f2)
NEW_CORS="${CURRENT_CORS},${FRONTEND_URL}"

# Replace CORS line
sed -i.tmp "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=${NEW_CORS}|g" "$ENV_FILE"
rm -f "${ENV_FILE}.tmp"

echo -e "${GREEN}✓ CORS actualizado${NC}"

# Update docker-compose.yml - NEXT_PUBLIC_API_URL
echo -e "${YELLOW}Actualizando API URL en docker-compose.yml...${NC}"

sed -i.tmp "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=${BACKEND_URL}|g" "$DOCKER_COMPOSE_FILE"
rm -f "${DOCKER_COMPOSE_FILE}.tmp"

echo -e "${GREEN}✓ API URL actualizado${NC}"

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Configuración Completada${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Ahora necesitas reiniciar los contenedores:${NC}"
echo ""
echo -e "  ${GREEN}docker-compose restart${NC}"
echo ""

read -p "¿Quieres que reinicie los contenedores automáticamente? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Reiniciando contenedores...${NC}"
    cd "$PROJECT_DIR"
    docker-compose restart
    echo ""
    echo -e "${GREEN}✓ Contenedores reiniciados${NC}"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}¡Todo Listo!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Tu aplicación ahora está configurada para el túnel:${NC}"
echo ""
echo -e "  Accede desde: ${GREEN}${FRONTEND_URL}${NC}"
echo ""
echo -e "${BLUE}Nota: Los túneles deben estar corriendo en otras terminales${NC}"
echo ""
echo -e "${YELLOW}Para volver a configuración local:${NC}"
echo -e "  ${GREEN}./restore-local-config.sh${NC}"
echo ""
