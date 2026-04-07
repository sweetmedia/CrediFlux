#!/bin/bash

# Quick Tunnel GRATIS de Cloudflare (sin cuenta, sin dominio)
# Genera URLs aleatorias temporales

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║      CloudFlare Quick Tunnel - GRATIS y TEMPORAL         ║
║                   CrediFlux                               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${BLUE}Este túnel NO requiere cuenta, dominio ni configuración!${NC}"
echo -e "${BLUE}Genera URLs aleatorias tipo: https://random-name.trycloudflare.com${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Darwin*)    MACHINE=Mac;;
    Linux*)     MACHINE=Linux;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}⚠ cloudflared no está instalado.${NC}"
    echo ""

    if [ "$MACHINE" == "Mac" ]; then
        echo "Instalando con Homebrew..."
        if command -v brew &> /dev/null; then
            brew install cloudflared
        else
            echo -e "${RED}Error: Homebrew no está instalado${NC}"
            echo "Instala Homebrew primero: https://brew.sh"
            exit 1
        fi
    elif [ "$MACHINE" == "Linux" ]; then
        echo "Instalando cloudflared para Linux..."
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    else
        echo -e "${RED}Sistema operativo no soportado${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ cloudflared instalado${NC}"
    echo ""
fi

# Check if Docker services are running
echo -e "${YELLOW}Verificando servicios...${NC}"
echo ""

FRONTEND_RUNNING=false
BACKEND_RUNNING=false

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend corriendo en http://localhost:3000${NC}"
    FRONTEND_RUNNING=true
else
    echo -e "${YELLOW}⚠ Frontend NO está corriendo en http://localhost:3000${NC}"
fi

if curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend corriendo en http://localhost:8000${NC}"
    BACKEND_RUNNING=true
else
    echo -e "${YELLOW}⚠ Backend NO está corriendo en http://localhost:8000${NC}"
fi

echo ""

if [ "$FRONTEND_RUNNING" = false ] && [ "$BACKEND_RUNNING" = false ]; then
    echo -e "${RED}⚠ Ningún servicio está corriendo!${NC}"
    echo ""
    echo "Inicia tus servicios primero:"
    echo -e "  ${GREEN}docker-compose up${NC}"
    echo ""
    read -p "¿Quieres continuar de todas formas? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            ¿Qué servicio quieres exponer?                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  1) Frontend (Next.js) - http://localhost:3000"
echo "  2) Backend (Django API) - http://localhost:8000"
echo "  3) Ambos (en 2 túneles separados)"
echo "  4) Cancelar"
echo ""
read -p "Selecciona una opción (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Iniciando túnel para FRONTEND...${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Espera unos segundos, se generará una URL aleatoria...${NC}"
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}IMPORTANTE - Para acceder desde móvil:${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "1. Copia la URL que aparecerá abajo"
        echo "2. Inicia OTRO túnel para el backend:"
        echo -e "   ${GREEN}./quick-tunnel-free.sh${NC} (en otra terminal, opción 2)"
        echo ""
        echo "3. Ejecuta el configurador:"
        echo -e "   ${GREEN}./configure-tunnel-urls.sh${NC}"
        echo ""
        echo "4. Ingresa ambas URLs (frontend y backend)"
        echo ""
        echo -e "${YELLOW}Presiona Ctrl+C para detener el túnel${NC}"
        echo ""
        sleep 3
        cloudflared tunnel --url http://localhost:3000
        ;;

    2)
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Iniciando túnel para BACKEND API...${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Espera unos segundos, se generará una URL aleatoria...${NC}"
        echo ""
        echo -e "${CYAN}Recuerda copiar esta URL para configurar después${NC}"
        echo -e "${YELLOW}Presiona Ctrl+C para detener el túnel${NC}"
        echo ""
        sleep 2
        cloudflared tunnel --url http://localhost:8000
        ;;

    3)
        echo ""
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}Iniciando 2 túneles (Frontend + Backend)...${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Se abrirán 2 terminales. Guarda ambas URLs!${NC}"
        echo ""

        # Start frontend tunnel in background
        echo -e "${CYAN}Iniciando túnel de Frontend...${NC}"
        osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && echo \"Frontend Tunnel\" && echo \"\" && cloudflared tunnel --url http://localhost:3000"' &

        sleep 2

        # Start backend tunnel in background
        echo -e "${CYAN}Iniciando túnel de Backend...${NC}"
        osascript -e 'tell app "Terminal" to do script "cd \"'$(pwd)'\" && echo \"Backend API Tunnel\" && echo \"\" && cloudflared tunnel --url http://localhost:8000"' &

        echo ""
        echo -e "${GREEN}✓ Túneles iniciados en terminales separadas${NC}"
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}PASO FINAL - Configurar las URLs:${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "1. Copia ambas URLs que aparecen en las terminales"
        echo ""
        echo "2. Ejecuta el configurador:"
        echo -e "   ${GREEN}./configure-tunnel-urls.sh${NC}"
        echo ""
        echo "3. Ingresa las URLs cuando te lo pida"
        echo ""
        echo "4. Espera a que reinicie los contenedores"
        echo ""
        echo -e "${GREEN}¡Listo! Ahora podrás acceder desde tu móvil${NC}"
        echo ""
        ;;

    4)
        echo "Cancelado."
        exit 0
        ;;

    *)
        echo -e "${RED}Opción inválida${NC}"
        exit 1
        ;;
esac
