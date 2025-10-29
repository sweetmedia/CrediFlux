#!/bin/bash

# Script para mostrar información del túnel

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CF_DIR="${PROJECT_DIR}/.cloudflare"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Información del Túnel${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if command -v cloudflared &> /dev/null; then
    echo -e "${GREEN}Túneles disponibles:${NC}"
    cloudflared tunnel list
    echo ""
fi

if [ -f "${CF_DIR}/config.yml" ]; then
    echo -e "${GREEN}Configuración actual:${NC}"
    cat "${CF_DIR}/config.yml"
    echo ""
fi

echo -e "${BLUE}Para ver túneles activos:${NC}"
echo "  cloudflared tunnel list"
echo ""
echo -e "${BLUE}Para ver conexiones activas:${NC}"
echo "  cloudflared tunnel info crediflux-dev"
