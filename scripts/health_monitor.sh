#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Health Monitor for RunPod
#
# Checks HTTP endpoints for all 3 services. If a service is
# running but not responding, restarts it via supervisorctl.
# Writes health_status.json for the /api/health/monitor endpoint.
#
# Usage: bash scripts/health_monitor.sh
# Called by cron: */2 * * * * cd /root/IntelligenceLayer && bash scripts/health_monitor.sh >> $LOG_DIR/health.log 2>&1
# ──────────────────────────────────────────────────────────────
set -uo pipefail  # no -e: we handle errors per-check

LOG_DIR="${WYBE_LOG_DIR:-/tmp/intelligenceLayer_logs}"
STATUS_FILE="$LOG_DIR/health_status.json"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH WARN: $*"; }
crit() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH CRITICAL: $*" >&2; }

mkdir -p "$LOG_DIR"

# ── Service health checks ──
declare -A SERVICES=(
    ["wybe-api"]="http://localhost:8000/api/health"
    ["wybe-web"]="http://localhost:3000"
    ["wybe-studio"]="http://localhost:7860"
)

declare -A STATUS

for svc in "${!SERVICES[@]}"; do
    url="${SERVICES[$svc]}"
    if curl -sf -m 5 "$url" >/dev/null 2>&1; then
        STATUS[$svc]="ok"
    else
        warn "$svc failed health check ($url) — restarting..."
        supervisorctl restart "$svc" 2>/dev/null || true
        sleep 15  # Give service time to start (Next.js needs ~10s)

        if curl -sf -m 5 "$url" >/dev/null 2>&1; then
            log "$svc recovered after restart."
            STATUS[$svc]="recovered"
        else
            crit "$svc still failing after restart — supervisord will keep retrying."
            STATUS[$svc]="failing"
        fi
    fi
done

# ── GPU check ──
GPU_OK="false"
if nvidia-smi >/dev/null 2>&1; then
    GPU_OK="true"
fi

# ── Disk check ──
DISK_PCT=$(df --output=pcent / 2>/dev/null | tail -1 | tr -d ' %' || echo "-1")

# ── Write status JSON ──
cat > "$STATUS_FILE" <<EOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "services": {
    "wybe-api": "${STATUS[wybe-api]:-unknown}",
    "wybe-web": "${STATUS[wybe-web]:-unknown}",
    "wybe-studio": "${STATUS[wybe-studio]:-unknown}"
  },
  "disk_pct": $DISK_PCT,
  "gpu_ok": $GPU_OK
}
EOF

# Only log if something isn't ok
for svc in "${!STATUS[@]}"; do
    if [ "${STATUS[$svc]}" != "ok" ]; then
        log "Status written: $(cat "$STATUS_FILE")"
        break
    fi
done
