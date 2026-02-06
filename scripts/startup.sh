#!/bin/bash
set -e

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"

echo "=== RunPod Pod Restart Recovery ==="

# Reinstall system packages lost on pod restart
echo "Installing system packages..."
apt-get update && apt-get install -y \
    build-essential yasm cmake libtool git pkg-config \
    libass-dev libfreetype6-dev libvorbis-dev \
    autoconf automake texinfo tmux ffmpeg libegl1 software-properties-common

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

# Create log directory
mkdir -p /tmp/intelligenceLayer_logs

# Launch Gradio frontend in the background
echo "Starting Gradio frontend on port 7860..."
nohup .venv/bin/python -m frontend.app > /tmp/intelligenceLayer_logs/gradio.log 2>&1 &
echo "Gradio PID: $!"

echo "=== Startup complete ==="
