# RunPod Deployment & Recovery

## After pod restart/unpause

Files on `/root/` survive. The frontend **auto-starts** on pod restart via:

1. `@reboot` cron job runs `startup.sh`
2. `startup.sh` reinstalls system packages and starts **supervisord**
3. Supervisord manages the Gradio process — auto-restarts on crash

No manual intervention is needed.

If the cron job isn't installed yet, or you need to manually restart:

```bash
cd /root/IntelligenceLayer && bash scripts/startup.sh
```

### Managing the frontend with supervisord

```bash
supervisorctl status wybe-studio     # check if running
supervisorctl restart wybe-studio    # restart the frontend
supervisorctl stop wybe-studio       # stop the frontend
supervisorctl start wybe-studio      # start the frontend
supervisorctl tail -f wybe-studio    # follow live logs
```

Logs: `/tmp/intelligenceLayer_logs/gradio.log` (50MB max, 3 rotated backups).

### Verify everything works

```bash
bash scripts/setup_production.sh verify   # also installs cron job + supervisor config
crontab -l                                 # confirm @reboot entry exists
supervisorctl status wybe-studio          # should show RUNNING
```

## After pod termination (full rebuild)

```bash
git clone https://github.com/justwybe/IntelligenceLayer.git /root/IntelligenceLayer
cd /root/IntelligenceLayer
cp .env.example .env
bash scripts/set_api_key.sh   # paste your Anthropic API key when prompted
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

The frontend is managed by supervisord and auto-starts. To manually run it (e.g. for debugging):

```bash
supervisorctl stop wybe-studio                    # stop supervised instance first
cd /root/IntelligenceLayer
.venv/bin/python -m frontend.app                   # run in foreground
```

The frontend launches on port 7860 with HTTPS.

## Key details

- **GR00T venv**: Python 3.10 at `.venv/` — `transformers==4.51.3`
- **Isaac Sim**: System Python 3.11 — separate environment
- **Model weights**: `checkpoints/GR00T-N1.6-3B` (6.2 GB, re-download with `bash scripts/setup_production.sh 1w`)
- **Inference server**: ZMQ on `tcp://127.0.0.1:5555`
- **Frontend**: Gradio on port 7860 (managed by supervisord, auto-restarts on crash)
- **AI Assistant**: Requires `ANTHROPIC_API_KEY` in `.env`
- **TensorRT**: `bash scripts/setup_production.sh 5`
