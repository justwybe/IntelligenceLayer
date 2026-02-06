#!/bin/bash
set -e

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"

echo "=== RunPod Pod Restart Recovery ==="

# Reinstall system packages lost on pod restart
echo "Installing system packages..."
apt-get update && apt-get install -y \
    build-essential yasm cmake libtool git pkg-config \
    libass-dev libfreetype6-dev libvorbis-dev \
    autoconf automake texinfo tmux ffmpeg libegl1 software-properties-common supervisor

# Python 3.10 headers (PPA usually already present from setup_production.sh)
apt-get install -y python3.10-dev 2>/dev/null || true

# EGL ICD (may fail on read-only filesystems — already present from setup_production.sh)
mkdir -p /usr/share/glvnd/egl_vendor.d 2>/dev/null || true
echo '{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json 2>/dev/null || true

# Vulkan ICD
mkdir -p /usr/share/vulkan/icd.d 2>/dev/null || true
echo '{"file_format_version":"1.0.0","ICD":{"library_path":"libGLX_nvidia.so.0","api_version":"1.2.140"}}' > /usr/share/vulkan/icd.d/nvidia_icd.json 2>/dev/null || true

# Isaac Sim (optional — may fail if system Python 3.11 is not available)
pip install isaacsim==5.1.0.0 2>/dev/null || true

# Load env vars
cd "$PROJECT_DIR"
if [ -f .env ]; then
    set -a && source .env && set +a
    echo "Environment variables loaded."
else
    echo "WARNING: .env not found — copy .env.example to .env and add your ANTHROPIC_API_KEY"
fi

# Install frontend dependencies using the proper extras
echo "Installing frontend dependencies..."
uv pip install --python .venv/bin/python -e ".[frontend]" 2>/dev/null || \
    .venv/bin/python -m pip install gradio plotly anthropic python-dotenv 2>/dev/null || true

# Install API dependencies
echo "Installing API dependencies..."
uv pip install --python .venv/bin/python -e ".[api]" 2>/dev/null || \
    .venv/bin/python -m pip install fastapi uvicorn pydantic-settings websockets 2>/dev/null || true

# Install Node.js 22 LTS if not present
if ! command -v node &> /dev/null; then
    echo "Installing Node.js 22 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi
echo "Node.js: $(node --version 2>/dev/null || echo 'not installed')"

# Build Next.js frontend
echo "Building Next.js frontend..."
if [ -d "$PROJECT_DIR/web" ]; then
    cd "$PROJECT_DIR/web"
    npm ci --production=false 2>/dev/null || npm install
    npm run build
    cd "$PROJECT_DIR"
    echo "Next.js build complete."
else
    echo "WARNING: web/ directory not found — skipping Next.js build"
fi

# Create log directory
mkdir -p /tmp/intelligenceLayer_logs

# Install and start supervisord for process management
echo "Configuring supervisord..."
cp scripts/supervisor/wybe-studio.conf /etc/supervisor/conf.d/wybe-studio.conf
cp scripts/supervisor/wybe-api.conf /etc/supervisor/conf.d/wybe-api.conf
cp scripts/supervisor/wybe-web.conf /etc/supervisor/conf.d/wybe-web.conf

# Start or reload supervisord
if pgrep -x supervisord > /dev/null; then
    supervisorctl reread
    supervisorctl update
    echo "Supervisord reloaded."
else
    supervisord -c /etc/supervisor/supervisord.conf
    echo "Supervisord started."
fi

echo "Service status:"
supervisorctl status

echo "=== Startup complete ==="
