#!/bin/bash

# Script para limpiar/desinstalar Cloudflare Tunnel de CrediFlux
# Este script elimina toda la configuración y opcionalmente desinstala cloudflared

set -e  # Exit on error

echo "================================"
echo "CrediFlux - Cloudflare Tunnel Cleanup"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CF_DIR="${PROJECT_DIR}/.cloudflare"

# Ask for confirmation
echo -e "${YELLOW}⚠ Este script eliminará:${NC}"
echo "  - Configuración del túnel (${CF_DIR})"
echo "  - Scripts relacionados"
echo "  - Opcionalmente: cloudflared del sistema"
echo ""
read -p "¿Estás seguro de continuar? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operación cancelada."
    exit 0
fi

echo ""
echo -e "${BLUE}Limpiando configuración del túnel...${NC}"

# Check if tunnel exists in Cloudflare
if command -v cloudflared &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Túneles encontrados en Cloudflare:${NC}"
    cloudflared tunnel list 2>/dev/null || true
    echo ""

    read -p "¿Quieres eliminar el túnel 'crediflux-dev' de Cloudflare? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Eliminando túnel de Cloudflare...${NC}"
        cloudflared tunnel delete crediflux-dev 2>/dev/null || echo -e "${YELLOW}⚠ No se pudo eliminar el túnel (puede que no exista)${NC}"
    fi
fi

# Remove configuration directory
if [ -d "${CF_DIR}" ]; then
    echo -e "${YELLOW}Eliminando directorio de configuración: ${CF_DIR}${NC}"
    rm -rf "${CF_DIR}"
    echo -e "${GREEN}✓ Directorio eliminado${NC}"
fi

# Remove generated scripts
if [ -f "${SCRIPT_DIR}/start-tunnel.sh" ]; then
    echo -e "${YELLOW}Eliminando start-tunnel.sh${NC}"
    rm -f "${SCRIPT_DIR}/start-tunnel.sh"
    echo -e "${GREEN}✓ Script eliminado${NC}"
fi

if [ -f "${SCRIPT_DIR}/tunnel-info.sh" ]; then
    echo -e "${YELLOW}Eliminando tunnel-info.sh${NC}"
    rm -f "${SCRIPT_DIR}/tunnel-info.sh"
    echo -e "${GREEN}✓ Script eliminado${NC}"
fi

echo ""
echo -e "${YELLOW}¿Quieres desinstalar cloudflared del sistema?${NC}"
echo "  (Esto eliminará cloudflared completamente)"
read -p "Desinstalar cloudflared? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Detect OS
    OS="$(uname -s)"
    case "${OS}" in
        Darwin*)    MACHINE=Mac;;
        Linux*)     MACHINE=Linux;;
        *)          MACHINE="UNKNOWN:${OS}"
    esac

    if [ "$MACHINE" == "Mac" ]; then
        if command -v brew &> /dev/null; then
            echo -e "${YELLOW}Desinstalando cloudflared con Homebrew...${NC}"
            brew uninstall cloudflared
            echo -e "${GREEN}✓ cloudflared desinstalado${NC}"
        else
            echo -e "${YELLOW}⚠ Homebrew no encontrado, elimina cloudflared manualmente${NC}"
        fi
    elif [ "$MACHINE" == "Linux" ]; then
        echo -e "${YELLOW}Desinstalando cloudflared...${NC}"
        sudo apt-get remove -y cloudflared 2>/dev/null || sudo dpkg -r cloudflared 2>/dev/null || true
        echo -e "${GREEN}✓ cloudflared desinstalado${NC}"
    fi
else
    echo -e "${BLUE}ℹ cloudflared no fue desinstalado (puedes usarlo para otros proyectos)${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ Limpieza Completada${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}Archivos y configuraciones del túnel eliminados.${NC}"
echo ""
echo "Si quieres volver a configurar el túnel, ejecuta:"
echo -e "  ${GREEN}./scripts/setup-cloudflare-tunnel.sh${NC}"
echo ""
