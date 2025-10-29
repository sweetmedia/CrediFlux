#!/bin/bash

# Script para configurar Cloudflare Tunnel para CrediFlux
# Este script instala cloudflared y configura el túnel

set -e  # Exit on error

echo "================================"
echo "CrediFlux - Cloudflare Tunnel Setup"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Darwin*)    MACHINE=Mac;;
    Linux*)     MACHINE=Linux;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BLUE}Sistema detectado: ${MACHINE}${NC}"
echo ""

# Check if cloudflared is installed
if command -v cloudflared &> /dev/null; then
    echo -e "${GREEN}✓ cloudflared ya está instalado${NC}"
    cloudflared --version
else
    echo -e "${YELLOW}⚠ cloudflared no está instalado. Instalando...${NC}"

    if [ "$MACHINE" == "Mac" ]; then
        # Install with Homebrew on macOS
        if command -v brew &> /dev/null; then
            brew install cloudflared
        else
            echo -e "${RED}✗ Homebrew no está instalado. Por favor instala Homebrew primero:${NC}"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [ "$MACHINE" == "Linux" ]; then
        # Install on Linux
        wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
        sudo dpkg -i cloudflared-linux-amd64.deb
        rm cloudflared-linux-amd64.deb
    else
        echo -e "${RED}✗ Sistema operativo no soportado${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ cloudflared instalado correctamente${NC}"
fi

echo ""
echo "================================"
echo "Configuración del Túnel"
echo "================================"
echo ""

# Create cloudflare config directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CF_DIR="${PROJECT_DIR}/.cloudflare"

mkdir -p "${CF_DIR}"

# Create tunnel config
cat > "${CF_DIR}/config.yml" << EOF
# Cloudflare Tunnel Configuration for CrediFlux
tunnel: crediflux-dev
credentials-file: ${CF_DIR}/credentials.json

ingress:
  # Frontend (Next.js)
  - hostname: crediflux.example.com
    service: http://localhost:3000

  # Backend API (Django)
  - hostname: api-crediflux.example.com
    service: http://localhost:8000

  # Catch-all rule (required)
  - service: http_status:404
EOF

echo -e "${GREEN}✓ Archivo de configuración creado en: ${CF_DIR}/config.yml${NC}"
echo ""

# Create tunnel startup script
cat > "${SCRIPT_DIR}/start-tunnel.sh" << 'EOF'
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
EOF

chmod +x "${SCRIPT_DIR}/start-tunnel.sh"

echo -e "${GREEN}✓ Script de inicio creado: ${SCRIPT_DIR}/start-tunnel.sh${NC}"
echo ""

# Create tunnel info script
cat > "${SCRIPT_DIR}/tunnel-info.sh" << 'EOF'
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
EOF

chmod +x "${SCRIPT_DIR}/tunnel-info.sh"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ Instalación Completada${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Próximos pasos:${NC}"
echo ""
echo "1. Autentica con Cloudflare:"
echo -e "   ${GREEN}cloudflared tunnel login${NC}"
echo ""
echo "2. Crea el túnel:"
echo -e "   ${GREEN}cloudflared tunnel create crediflux-dev${NC}"
echo ""
echo "3. Esto generará un archivo de credenciales. Cópialo a:"
echo -e "   ${GREEN}${CF_DIR}/credentials.json${NC}"
echo ""
echo "4. Configura los DNS records que te muestre el comando anterior"
echo ""
echo "5. Edita ${CF_DIR}/config.yml y reemplaza 'example.com' con tu dominio"
echo ""
echo "6. Inicia el túnel:"
echo -e "   ${GREEN}./scripts/start-tunnel.sh${NC}"
echo ""
echo "Para más información: ./scripts/tunnel-info.sh"
echo ""
