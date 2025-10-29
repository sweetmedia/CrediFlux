#!/bin/bash

# Script para iniciar el túnel de Cloudflare

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CF_DIR="${PROJECT_DIR}/.cloudflare"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Iniciando Cloudflare Tunnel${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if [ ! -f "${CF_DIR}/credentials.json" ]; then
    echo -e "${YELLOW}⚠ No se encontró el archivo de credenciales.${NC}"
    echo ""
    echo "Para configurar el túnel, ejecuta estos pasos:"
    echo ""
    echo "1. Autentícate con Cloudflare:"
    echo -e "   ${GREEN}cloudflared tunnel login${NC}"
    echo ""
    echo "2. Crea un túnel:"
    echo -e "   ${GREEN}cloudflared tunnel create crediflux-dev${NC}"
    echo ""
    echo "3. Copia el archivo de credenciales a:"
    echo -e "   ${GREEN}${CF_DIR}/credentials.json${NC}"
    echo ""
    echo "4. Configura los DNS records (el comando te los mostrará)"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Iniciando túnel...${NC}"
echo ""
echo -e "${YELLOW}Presiona Ctrl+C para detener el túnel${NC}"
echo ""

cloudflared tunnel --config "${CF_DIR}/config.yml" run crediflux-dev
