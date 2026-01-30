#!/bin/bash
set -e

# Reinstall system packages lost on pod restart
apt-get update && apt-get install -y build-essential yasm cmake libtool git pkg-config libass-dev libfreetype6-dev libvorbis-dev autoconf automake texinfo tmux ffmpeg libegl1 software-properties-common

# Python 3.10 headers
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update && apt-get install -y python3.10-dev

# EGL ICD
mkdir -p /usr/share/glvnd/egl_vendor.d
echo '{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json

# Vulkan ICD
mkdir -p /usr/share/vulkan/icd.d
echo '{"file_format_version":"1.0.0","ICD":{"library_path":"libGLX_nvidia.so.0","api_version":"1.2.140"}}' > /usr/share/vulkan/icd.d/nvidia_icd.json

# Isaac Sim
pip install isaacsim==5.1.0.0

# Load env vars
cd /root/IntelligenceLayer
set -a && source .env && set +a

# Install Gradio frontend dependencies
.venv/bin/python -m pip install gradio plotly 2>/dev/null || true

# Launch Gradio frontend in the background
echo "Starting Gradio frontend on port 7860..."
nohup .venv/bin/python -m frontend.app > /tmp/intelligenceLayer_logs/gradio.log 2>&1 &
echo "Gradio PID: $!"

echo "Startup complete."
