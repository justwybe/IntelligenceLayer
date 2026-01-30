# RunPod Recovery

## After pod restart/unpause

Files on `/root/` survive. Reinstall system packages:

```bash
cd /root/IntelligenceLayer && bash scripts/startup.sh
```

Verify everything works:

```bash
bash scripts/setup_production.sh 6
```

## After pod termination (full rebuild)

```bash
git clone https://github.com/justwybe/IntelligenceLayer.git /root/IntelligenceLayer
cd /root/IntelligenceLayer
bash scripts/setup_production.sh all
```

## Start inference server

```bash
cd /root/IntelligenceLayer
.venv/bin/python gr00t/eval/run_gr00t_server.py --embodiment-tag GR1 --model-path checkpoints/GR00T-N1.6-3B
```

## Key details

- **GROOT venv**: Python 3.10 at `.venv/` — `transformers==4.51.3`
- **Isaac Sim**: System Python 3.11 — separate environment
- **Model weights**: `checkpoints/GR00T-N1.6-3B` (6.2 GB, re-download with `bash scripts/setup_production.sh 1w`)
- **Inference server**: ZMQ on `tcp://127.0.0.1:5555`
- **TensorRT**: `bash scripts/setup_production.sh 5`
