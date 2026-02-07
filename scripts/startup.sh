#!/bin/bash
set -e

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"

echo "=== RunPod Pod Restart Recovery ==="

# Set up network volume (if attached) before anything else
if [ -d /runpod-volume ]; then
    echo "Setting up network volume..."
    bash "$PROJECT_DIR/scripts/setup_volume.sh" || echo "WARNING: Volume setup failed — continuing without volume"
fi

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

# Restore from backup if this is a fresh pod (no .env or DB)
cd "$PROJECT_DIR"
if [ ! -f .env ] || [ ! -f "$HOME/.wybe_studio/studio.db" ]; then
    echo "Fresh pod detected — attempting restore from backup..."
    bash "$PROJECT_DIR/scripts/restore_backup.sh" 2>/dev/null || echo "No backup found — continuing with fresh setup."
fi

# Load env vars
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

# Create log directory (may already be a symlink to volume)
LOG_DIR="${WYBE_LOG_DIR:-/tmp/intelligenceLayer_logs}"
mkdir -p "$LOG_DIR"

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

# Install cron jobs for auto-deploy, health monitoring, and backups
echo "Installing cron jobs..."
CRON_DEPLOY="*/5 * * * * cd $PROJECT_DIR && bash scripts/auto_deploy.sh >> $LOG_DIR/deploy.log 2>&1"
CRON_HEALTH="*/2 * * * * cd $PROJECT_DIR && bash scripts/health_monitor.sh >> $LOG_DIR/health.log 2>&1"
CRON_BACKUP="0 * * * * cd $PROJECT_DIR && bash scripts/backup.sh >> $LOG_DIR/backup.log 2>&1"
(
    crontab -l 2>/dev/null | grep -v 'auto_deploy.sh' | grep -v 'health_monitor.sh' | grep -v 'backup.sh'
    echo "$CRON_DEPLOY"
    echo "$CRON_HEALTH"
    echo "$CRON_BACKUP"
) | crontab -
echo "Cron jobs installed (auto-deploy every 5m, health check every 2m, backup hourly)."

echo "=== Startup complete ==="
