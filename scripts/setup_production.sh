#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Production Setup Script for NVIDIA GR00T on RunPod
# RTX A6000 (48GB) — runpod/pytorch:2.4.0-py3.11 base image
#
# Phases:
#   1.  Clean venv rebuild with transformers==4.51.3
#   1w. Download model weights (6.2 GB)
#   2.  Install frontend dependencies (Gradio, Anthropic, etc.)
#   3.  System dependencies + EGL/Vulkan rendering
#   4.  Isaac Sim (system Python 3.11)
#   5.  TensorRT optimization
#   6.  Verification
#
# Usage:
#   bash scripts/setup_production.sh [phase]
#   bash scripts/setup_production.sh all
#   bash scripts/setup_production.sh 1
#   bash scripts/setup_production.sh 2
#   bash scripts/setup_production.sh verify
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)] $*${NC}"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN: $*${NC}"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ERROR: $*${NC}" >&2; }
die()  { err "$@"; exit 1; }

# ──────────────────────────────────────────────
# Helper: Install @reboot cron job for auto-start
# ──────────────────────────────────────────────
install_cron_job() {
    log "Installing @reboot cron job for frontend auto-start..."
    CRON_CMD="@reboot cd /root/IntelligenceLayer && bash scripts/startup.sh >> /tmp/intelligenceLayer_logs/startup_cron.log 2>&1"
    (crontab -l 2>/dev/null | grep -v 'scripts/startup.sh'; echo "$CRON_CMD") | crontab -
    log "Cron job installed. Verify with: crontab -l"

    log "Installing supervisord config for wybe-studio..."
    mkdir -p /etc/supervisor/conf.d
    cp scripts/supervisor/wybe-studio.conf /etc/supervisor/conf.d/wybe-studio.conf
    log "Supervisord config installed."
}

# ──────────────────────────────────────────────
# Phase 1: Clean venv rebuild with correct transformers
# ──────────────────────────────────────────────
phase_1() {
    log "Phase 1: Clean venv rebuild with transformers==4.51.3"

    # Verify pyproject.toml has the correct version
    if ! grep -q 'transformers==4.51.3' pyproject.toml; then
        die "pyproject.toml does not pin transformers==4.51.3 — update it first"
    fi

    log "Removing old venv and cached transformer modules..."
    rm -rf .venv
    rm -rf /root/.cache/huggingface/modules/transformers_modules/

    log "Creating fresh venv with Python 3.10..."
    uv sync --python 3.10

    log "Installing project in editable mode..."
    uv pip install --python .venv/bin/python -e .

    log "Verifying Eagle VLM imports..."
    .venv/bin/python -c "
from transformers.image_utils import VideoInput
from transformers.image_processing_utils_fast import (
    BASE_IMAGE_PROCESSOR_FAST_DOCSTRING_PREPROCESS,
    DefaultFastImageProcessorKwargs,
)
from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
print('All Eagle VLM imports: OK')
"

    log "Verifying transformers version..."
    .venv/bin/python -c "
import transformers
assert transformers.__version__ == '4.51.3', f'Got {transformers.__version__}'
print(f'transformers=={transformers.__version__}')
"

    log "Phase 1 complete."
}

# ──────────────────────────────────────────────
# Phase 1.5: Download model weights
# ──────────────────────────────────────────────
phase_1_weights() {
    log "Phase 1.5: Checking/downloading GR00T-N1.6-3B model weights"

    if [ -d "checkpoints/GR00T-N1.6-3B" ] && [ -f "checkpoints/GR00T-N1.6-3B/config.json" ]; then
        log "Model weights already present at checkpoints/GR00T-N1.6-3B"
    else
        log "Downloading GR00T-N1.6-3B from HuggingFace..."
        .venv/bin/python -c "
from huggingface_hub import snapshot_download
snapshot_download('nvidia/GR00T-N1.6-3B', local_dir='checkpoints/GR00T-N1.6-3B')
print('Model weights downloaded successfully')
"
    fi

    log "Phase 1.5 complete."
}

# ──────────────────────────────────────────────
# Phase 2: Frontend dependencies (Gradio, Anthropic, etc.)
# ──────────────────────────────────────────────
phase_2() {
    log "Phase 2: Installing frontend dependencies"

    log "Installing frontend extras..."
    uv pip install --python .venv/bin/python -e ".[frontend]"

    log "Verifying frontend imports..."
    .venv/bin/python -c "
import gradio
import anthropic
import plotly
from dotenv import load_dotenv
print(f'gradio=={gradio.__version__}')
print(f'anthropic=={anthropic.__version__}')
print('All frontend imports: OK')
"

    log "Creating log directory..."
    mkdir -p /tmp/intelligenceLayer_logs

    log "Phase 2 complete."
}

# ──────────────────────────────────────────────
# Phase 3: System dependencies + EGL/Vulkan
# ──────────────────────────────────────────────
phase_3() {
    log "Phase 3: System dependencies and rendering configuration"

    log "Installing system packages (from NVIDIA official Dockerfile)..."
    apt-get update && apt-get install -y \
        build-essential yasm cmake libtool git pkg-config \
        libass-dev libfreetype6-dev libvorbis-dev \
        autoconf automake texinfo tmux ffmpeg libegl1 python3.10-dev supervisor

    log "Configuring NVIDIA EGL ICD (headless GPU rendering)..."
    mkdir -p /usr/share/glvnd/egl_vendor.d
    cat > /usr/share/glvnd/egl_vendor.d/10_nvidia.json << 'EGLEOF'
{
    "file_format_version" : "1.0.0",
    "ICD" : {
        "library_path" : "libEGL_nvidia.so.0"
    }
}
EGLEOF

    log "Configuring Vulkan ICD..."
    mkdir -p /usr/share/vulkan/icd.d
    cat > /usr/share/vulkan/icd.d/nvidia_icd.json << 'VKEOF'
{
    "file_format_version": "1.0.0",
    "ICD": {
        "library_path": "libGLX_nvidia.so.0",
        "api_version": "1.2.140"
    }
}
VKEOF

    log "Loading production environment variables..."
    if [ -f .env ]; then
        set -a
        source .env
        set +a
        log "Environment variables loaded from .env"
    else
        warn ".env not found — copy .env.example to .env and customize"
    fi

    log "Phase 3 complete."
}

# ──────────────────────────────────────────────
# Phase 4: Isaac Sim (separate Python 3.11 environment)
# ──────────────────────────────────────────────
phase_4() {
    log "Phase 4: Isaac Sim setup (system Python 3.11)"

    # Verify system Python is 3.11
    SYS_PY_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [ "$SYS_PY_VER" != "3.11" ]; then
        warn "System Python is $SYS_PY_VER, not 3.11. Isaac Sim 5.1 requires Python 3.11."
        warn "Skipping Isaac Sim installation."
        return 0
    fi

    log "Installing Isaac Sim 5.1.0.0..."
    pip install isaacsim==5.1.0.0

    log "Accepting Isaac Sim EULA..."
    echo "Yes" | python3 -c "import isaacsim" 2>/dev/null || true

    log "Verifying Isaac Sim..."
    python3 -c "
import isaacsim
print('Isaac Sim import: OK')
" || warn "Isaac Sim import check failed — may need GPU context"

    log "Phase 4 complete."
}

# ──────────────────────────────────────────────
# Phase 5: TensorRT optimization
# ──────────────────────────────────────────────
phase_5() {
    log "Phase 5: TensorRT optimization for DiT action head"

    log "Installing TensorRT dependencies..."
    uv pip install --python .venv/bin/python -e ".[tensorrt]"

    log "Verifying TensorRT installation..."
    .venv/bin/python -c "
import onnx
import tensorrt
print(f'ONNX: {onnx.__version__}')
print(f'TensorRT: {tensorrt.__version__}')
"

    if [ -d "checkpoints/GR00T-N1.6-3B" ]; then
        log "Building TensorRT engine for RTX A6000..."
        .venv/bin/python scripts/deployment/build_tensorrt_engine.py \
            --model-path checkpoints/GR00T-N1.6-3B \
            --embodiment-tag GR1
        log "TensorRT engine built."
    else
        warn "Model weights not found. Run phase 1 with weights download first."
        warn "Skipping TensorRT engine build."
    fi

    log "Phase 5 complete."
}

# ──────────────────────────────────────────────
# Phase 6: Production verification
# ──────────────────────────────────────────────
phase_6() {
    log "Phase 6: Production verification"
    PASS=0
    FAIL=0

    run_test() {
        local name="$1"
        shift
        if "$@" 2>&1; then
            log "PASS: $name"
            PASS=$((PASS + 1))
        else
            err "FAIL: $name"
            FAIL=$((FAIL + 1))
        fi
    }

    # Test 1: GPU and CUDA
    run_test "GPU/CUDA" bash -c '
        nvidia-smi > /dev/null 2>&1 && \
        '"$PROJECT_DIR"'/.venv/bin/python -c "
import torch
assert torch.cuda.is_available(), \"CUDA not available\"
print(f\"GPU: {torch.cuda.get_device_name(0)}\")
print(f\"CUDA: {torch.version.cuda}\")
print(f\"PyTorch: {torch.__version__}\")
"'

    # Test 2: Transformers version and Eagle imports
    run_test "Transformers/Eagle" "$PROJECT_DIR/.venv/bin/python" -c "
import transformers
assert transformers.__version__ == '4.51.3', f'Expected 4.51.3, got {transformers.__version__}'
from transformers.image_utils import VideoInput
from transformers.image_processing_utils_fast import (
    BASE_IMAGE_PROCESSOR_FAST_DOCSTRING_PREPROCESS,
    DefaultFastImageProcessorKwargs,
)
from transformers.modeling_utils import ALL_ATTENTION_FUNCTIONS
print(f'transformers=={transformers.__version__}: All imports OK')
"

    # Test 3: Flash Attention
    run_test "FlashAttention" "$PROJECT_DIR/.venv/bin/python" -c "
from flash_attn import flash_attn_func
import torch
q = torch.randn(2, 8, 128, 64, device='cuda', dtype=torch.float16)
k = torch.randn(2, 8, 128, 64, device='cuda', dtype=torch.float16)
v = torch.randn(2, 8, 128, 64, device='cuda', dtype=torch.float16)
out = flash_attn_func(q, k, v)
print(f'FlashAttention: OK (shape {out.shape})')
"

    # Test 4: GROOT model load
    if [ -d "checkpoints/GR00T-N1.6-3B" ]; then
        run_test "GROOT model load" "$PROJECT_DIR/.venv/bin/python" -c "
from gr00t.policy.gr00t_policy import Gr00tPolicy
from gr00t.data.embodiment_tags import EmbodimentTag
import torch
policy = Gr00tPolicy(
    model_path='checkpoints/GR00T-N1.6-3B',
    embodiment_tag=EmbodimentTag.GR1,
    device='cuda',
)
print(f'GROOT model loaded. GPU mem: {torch.cuda.memory_allocated(0)/1e9:.1f} GB')
"
    else
        warn "SKIP: GROOT model load (weights not downloaded)"
    fi

    # Test 5: EGL rendering
    run_test "EGL rendering" bash -c '
        [ -f /usr/share/glvnd/egl_vendor.d/10_nvidia.json ] && \
        echo "EGL ICD configured: OK"
    '

    # Test 6: Vulkan ICD
    run_test "Vulkan ICD" bash -c '
        [ -f /usr/share/vulkan/icd.d/nvidia_icd.json ] && \
        echo "Vulkan ICD configured: OK"
    '

    # Test 7: Isaac Sim (system Python)
    SYS_PY_VER=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
    if [ "$SYS_PY_VER" = "3.11" ]; then
        run_test "Isaac Sim" python3 -c "
import isaacsim
print('Isaac Sim import: OK')
"
    else
        warn "SKIP: Isaac Sim (system Python is $SYS_PY_VER, not 3.11)"
    fi

    # Test 8: Frontend (Gradio + assistant)
    run_test "Frontend imports" "$PROJECT_DIR/.venv/bin/python" -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from frontend.app import create_app
app = create_app()
print('Wybe Studio frontend: OK')
"

    # Test 9: Environment variables
    run_test "Environment variables" bash -c '
        [ -f '"$PROJECT_DIR"'/.env ] && \
        grep -q "MUJOCO_GL=egl" '"$PROJECT_DIR"'/.env && \
        grep -q "PYTORCH_CUDA_ALLOC_CONF" '"$PROJECT_DIR"'/.env && \
        echo "Production .env configured: OK"
    '

    echo ""
    log "═══════════════════════════════════════"
    log "Verification Summary: $PASS passed, $FAIL failed"
    log "═══════════════════════════════════════"

    if [ "$FAIL" -gt 0 ]; then
        err "Some tests failed. Review output above."
        return 1
    fi

    install_cron_job
}

# ──────────────────────────────────────────────
# Main dispatch
# ──────────────────────────────────────────────
case "${1:-all}" in
    1)       phase_1 ;;
    1w|weights) phase_1_weights ;;
    2)       phase_2 ;;
    3)       phase_3 ;;
    4)       phase_4 ;;
    5)       phase_5 ;;
    6|verify) phase_6 ;;
    all)
        phase_1
        phase_1_weights
        phase_2
        phase_3
        phase_4
        phase_5
        phase_6
        ;;
    *)
        echo "Usage: $0 {1|1w|2|3|4|5|6|verify|all}"
        echo ""
        echo "Phases:"
        echo "  1       Clean venv rebuild with transformers==4.51.3"
        echo "  1w      Download model weights (6.2 GB)"
        echo "  2       Frontend dependencies (Gradio, Anthropic)"
        echo "  3       System deps + EGL/Vulkan"
        echo "  4       Isaac Sim (Python 3.11)"
        echo "  5       TensorRT optimization"
        echo "  6       Production verification"
        echo "  all     Run all phases sequentially"
        exit 1
        ;;
esac
