# RunPod Deployment & Recovery

## After pod restart/unpause

Files on `/root/` survive. Reinstall system packages and relaunch frontend:

```bash
cd /root/IntelligenceLayer && bash scripts/startup.sh
```

Verify everything works:

```bash
bash scripts/setup_production.sh verify
```

## After pod termination (full rebuild)

```bash
git clone https://github.com/justwybe/IntelligenceLayer.git /root/IntelligenceLayer
cd /root/IntelligenceLayer
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY
bash scripts/setup_production.sh all
```

## Setup phases (run individually if needed)

| Phase | Command | Description |
|-------|---------|-------------|
| 1 | `bash scripts/setup_production.sh 1` | Clean venv rebuild (Python 3.10, transformers==4.51.3) |
| 1w | `bash scripts/setup_production.sh 1w` | Download model weights (6.2 GB from HuggingFace) |
| 2 | `bash scripts/setup_production.sh 2` | Frontend dependencies (Gradio, Anthropic, plotly) |
| 3 | `bash scripts/setup_production.sh 3` | System deps + EGL/Vulkan rendering config |
| 4 | `bash scripts/setup_production.sh 4` | Isaac Sim 5.1 (requires system Python 3.11) |
| 5 | `bash scripts/setup_production.sh 5` | TensorRT optimization (ONNX export + engine build) |
| 6 | `bash scripts/setup_production.sh verify` | Production verification (GPU, model, frontend) |

## Start inference server

```bash
cd /root/IntelligenceLayer
.venv/bin/python gr00t/eval/run_gr00t_server.py --embodiment-tag GR1 --model-path checkpoints/GR00T-N1.6-3B
```

## Start Wybe Studio (frontend only)

```bash
cd /root/IntelligenceLayer
.venv/bin/python -m frontend.app
```

The frontend launches on port 7860 with HTTPS.

## Key details

- **GR00T venv**: Python 3.10 at `.venv/` — `transformers==4.51.3`
- **Isaac Sim**: System Python 3.11 — separate environment
- **Model weights**: `checkpoints/GR00T-N1.6-3B` (6.2 GB, re-download with `bash scripts/setup_production.sh 1w`)
- **Inference server**: ZMQ on `tcp://127.0.0.1:5555`
- **Frontend**: Gradio on port 7860 (auto-launched by `startup.sh`)
- **AI Assistant**: Requires `ANTHROPIC_API_KEY` in `.env`
- **TensorRT**: `bash scripts/setup_production.sh 5`
