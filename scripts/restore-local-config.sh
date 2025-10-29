#!/bin/bash

# Script para restaurar configuración local (sin túnel)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
DOCKER_COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"

clear

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       Restaurar Configuración Local                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if backups exist
if [ -f "${ENV_FILE}.backup" ] || [ -f "${DOCKER_COMPOSE_FILE}.backup" ]; then
    echo -e "${YELLOW}Se encontraron backups. ¿Quieres restaurarlos?${NC}"
    echo ""
    read -p "Restaurar desde backup? (y/N): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "${ENV_FILE}.backup" ]; then
            mv "${ENV_FILE}.backup" "$ENV_FILE"
            echo -e "${GREEN}✓ .env restaurado${NC}"
        fi

        if [ -f "${DOCKER_COMPOSE_FILE}.backup" ]; then
            mv "${DOCKER_COMPOSE_FILE}.backup" "$DOCKER_COMPOSE_FILE"
            echo -e "${GREEN}✓ docker-compose.yml restaurado${NC}"
        fi

        echo ""
        echo -e "${YELLOW}Reiniciando contenedores...${NC}"
        cd "$PROJECT_DIR"
        docker-compose restart

        echo ""
        echo -e "${GREEN}✓ Configuración local restaurada${NC}"
        echo ""
        exit 0
    fi
fi

# Manual restore
echo -e "${YELLOW}Restaurando configuración local manualmente...${NC}"
echo ""

# Restore .env CORS
sed -i.tmp "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://10.0.0.150:3000|g" "$ENV_FILE"
rm -f "${ENV_FILE}.tmp"
echo -e "${GREEN}✓ CORS restaurado${NC}"

# Restore docker-compose.yml API URL
sed -i.tmp "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://10.0.0.150:8000|g" "$DOCKER_COMPOSE_FILE"
rm -f "${DOCKER_COMPOSE_FILE}.tmp"
echo -e "${GREEN}✓ API URL restaurado${NC}"

echo ""
echo -e "${YELLOW}Reiniciando contenedores...${NC}"
cd "$PROJECT_DIR"
docker-compose restart

echo ""
echo -e "${GREEN}✓ Configuración local restaurada${NC}"
echo ""
echo "Ahora puedes acceder a:"
echo -e "  ${GREEN}http://localhost:3000${NC}"
echo ""
