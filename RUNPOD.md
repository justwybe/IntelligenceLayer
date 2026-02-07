# RunPod Deployment & Recovery

## Automated systems

Four cron jobs keep the pod healthy and up-to-date:

| Schedule | Script | Purpose |
|----------|--------|---------|
| `@reboot` | `startup.sh` | Full rebuild on pod restart |
| `*/2 min` | `health_monitor.sh` | HTTP checks + auto-restart failing services |
| `*/5 min` | `auto_deploy.sh` | Git-poll deploy (training-safe, smart rebuild) |
| `hourly` | `backup.sh` | DB + .env to `backups/pod-data` branch |

Supervisord manages 3 services with `autorestart=true`:
- **wybe-api** — FastAPI on port 8000
- **wybe-web** — Next.js on port 3000
- **wybe-studio** — Gradio on port 7860

## After pod restart/unpause

No manual intervention needed. The `@reboot` cron runs `startup.sh` which:
1. Sets up network volume (if attached)
2. Restores from backup (if fresh pod)
3. Reinstalls system packages
4. Rebuilds Next.js
5. Starts supervisord + all 3 services
6. Installs cron jobs

If the cron job isn't installed yet:
```bash
cd /root/IntelligenceLayer && bash scripts/startup.sh
```

## After pod termination (full rebuild)

Recovery from the `backups/pod-data` git branch:

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=$HOME/.local/bin:$PATH

# 2. Clone repo
cd /root
git clone https://github.com/justwybe/IntelligenceLayer.git
cd IntelligenceLayer

# 3. Restore DB + .env from backup
bash scripts/restore_backup.sh

# 4. Re-add your API key (redacted in backup)
nano .env   # set ANTHROPIC_API_KEY=sk-ant-...

# 5. Run production setup (phase 3 first for system deps)
bash scripts/setup_production.sh 3
bash scripts/setup_production.sh 1
bash scripts/setup_production.sh 1w   # model weights (6.2 GB)
bash scripts/setup_production.sh 2

# 6. Build Next.js
cd web && npm ci --production=false && npm run build && cd ..

# 7. Start services
apt-get install -y supervisor cron && service cron start
mkdir -p /tmp/intelligenceLayer_logs
cp scripts/supervisor/*.conf /etc/supervisor/conf.d/
supervisord -c /etc/supervisor/supervisord.conf

# 8. Install cron jobs
bash scripts/startup.sh   # or manually via crontab
```

Or let `startup.sh` handle everything (auto-detects fresh pod and restores backup).

## Managing services

```bash
supervisorctl status                  # check all services
supervisorctl restart wybe-api        # restart API
supervisorctl restart wybe-web        # restart Next.js
supervisorctl restart wybe-studio     # restart Gradio
supervisorctl tail -f wybe-api        # follow live logs
```

## Health monitoring

```bash
curl localhost:8000/api/health/monitor   # JSON status of all services
cat /tmp/intelligenceLayer_logs/health_status.json  # same, from file
```

The health monitor checks HTTP endpoints every 2 minutes. If a service is running but not responding, it restarts it via supervisorctl.

## Auto-deploy

Push to `main` and the pod updates within 5 minutes:
- Only rebuilds what changed (web/ = Next.js, api/ = restart API, pyproject.toml = pip install)
- Training-safe: skips deploy if training runs are active
- `--ff-only`: won't mess up if files were edited on the pod

## Backups

Hourly backup of `~/.wybe_studio/studio.db` and `.env` (redacted) to the `backups/pod-data` branch.

Restore on a new pod:
```bash
bash scripts/restore_backup.sh
```

## Network volume (optional)

If a network volume is attached at `/runpod-volume`, run:
```bash
bash scripts/setup_volume.sh
```
This migrates DB + checkpoints to the volume with symlinks. Data then survives pod termination.

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

## Key details

- **GR00T venv**: Python 3.10 at `.venv/` — `transformers==4.51.3`
- **Isaac Sim**: System Python 3.11 — separate environment
- **Model weights**: `checkpoints/GR00T-N1.6-3B` (6.2 GB, re-download with `bash scripts/setup_production.sh 1w`)
- **Inference server**: ZMQ on `tcp://127.0.0.1:5555`
- **Services**: API (8000), Next.js (3000), Gradio (7860) — all managed by supervisord
- **AI Assistant**: Requires `ANTHROPIC_API_KEY` in `.env`
- **Logs**: `/tmp/intelligenceLayer_logs/` (50MB max per service, 3 rotated backups)
- **TensorRT**: `bash scripts/setup_production.sh 5`
