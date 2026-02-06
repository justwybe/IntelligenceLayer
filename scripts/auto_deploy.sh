#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Auto-Deploy Script for RunPod
#
# Polls origin/main every 5 minutes (via cron). If new commits
# exist, pulls them and rebuilds only what changed. Training-safe
# — skips deploy if a training run is active.
#
# Usage: bash scripts/auto_deploy.sh
# Called by cron: */5 * * * * cd /root/IntelligenceLayer && bash scripts/auto_deploy.sh >> $LOG_DIR/deploy.log 2>&1
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"
cd "$PROJECT_DIR"

LOG_DIR="${WYBE_LOG_DIR:-/tmp/intelligenceLayer_logs}"
LOCK_FILE="/tmp/wybe_deploy.lock"
DB_PATH="$HOME/.wybe_studio/studio.db"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEPLOY: $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEPLOY WARN: $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEPLOY ERROR: $*" >&2; }

# ── Acquire exclusive lock (skip if another deploy is running) ──
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    log "Another deploy is already running — skipping."
    exit 0
fi

# ── Check for remote changes ──
git fetch origin main --quiet 2>/dev/null || { err "git fetch failed"; exit 1; }

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0  # Nothing to deploy — silent exit
fi

log "New commits detected: $LOCAL -> $REMOTE"

# ── Training-safe check ──
if [ -f "$DB_PATH" ] && command -v sqlite3 &>/dev/null; then
    RUNNING=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM runs WHERE status='running';" 2>/dev/null || echo "0")
    if [ "$RUNNING" -gt 0 ]; then
        log "Skipping deploy: $RUNNING training run(s) in progress."
        exit 0
    fi
fi

# ── Determine what changed ──
CHANGED=$(git diff --name-only "$LOCAL" "$REMOTE")
log "Changed files:"
echo "$CHANGED" | while read -r f; do echo "  $f"; done

# ── Pull changes (fast-forward only) ──
if ! git pull --ff-only origin main; then
    err "git pull --ff-only failed — local changes conflict with remote."
    err "SSH into the pod and resolve manually."
    exit 1
fi

NEW_SHA=$(git rev-parse --short HEAD)
log "Pulled to $NEW_SHA"

# ── Smart rebuild ──
REBUILT=""
RESTART_SERVICES=""

# Check if web/ changed
if echo "$CHANGED" | grep -q "^web/"; then
    log "Rebuilding Next.js..."
    if (cd "$PROJECT_DIR/web" && npm ci --production=false && npm run build); then
        REBUILT="$REBUILT web"
        RESTART_SERVICES="$RESTART_SERVICES wybe-web"
    else
        err "Next.js build failed — keeping old version running."
        exit 1
    fi
fi

# Check if Python dependencies changed (pyproject.toml)
if echo "$CHANGED" | grep -q "^pyproject\.toml"; then
    log "Reinstalling Python packages (pyproject.toml changed)..."
    if uv pip install --python "$PROJECT_DIR/.venv/bin/python" -e ".[api,frontend]" 2>/dev/null || \
       "$PROJECT_DIR/.venv/bin/python" -m pip install -e ".[api,frontend]" 2>/dev/null; then
        REBUILT="$REBUILT python-deps"
    else
        err "Python install failed — keeping old version running."
        exit 1
    fi
fi

# Check if Python source code changed (just needs service restart, no reinstall)
if echo "$CHANGED" | grep -q "^api/"; then
    RESTART_SERVICES="$RESTART_SERVICES wybe-api"
fi
if echo "$CHANGED" | grep -q "^frontend/"; then
    RESTART_SERVICES="$RESTART_SERVICES wybe-studio"
fi

# Check if supervisor configs changed
if echo "$CHANGED" | grep -q "^scripts/supervisor/"; then
    log "Updating supervisor configs..."
    cp scripts/supervisor/*.conf /etc/supervisor/conf.d/ 2>/dev/null || true
    supervisorctl reread 2>/dev/null || true
    supervisorctl update 2>/dev/null || true
    REBUILT="$REBUILT supervisor-configs"
fi

# ── Restart affected services ──
if [ -n "$RESTART_SERVICES" ]; then
    log "Restarting services:$RESTART_SERVICES"
    for svc in $RESTART_SERVICES; do
        supervisorctl restart "$svc" 2>/dev/null || warn "Failed to restart $svc"
    done
fi

log "Deploy complete: $(git rev-parse --short "$LOCAL") -> $NEW_SHA | rebuilt:${REBUILT:- none}"
