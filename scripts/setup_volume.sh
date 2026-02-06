#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Network Volume Setup for RunPod
#
# Migrates data (DB, checkpoints, logs) to a persistent network
# volume so it survives pod termination. Uses symlinks so all
# existing paths continue to work. Idempotent — safe to re-run.
#
# Usage: bash scripts/setup_volume.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"
VOLUME_DIR="/runpod-volume"
VOLUME_DATA="$VOLUME_DIR/wybe_data"
STUDIO_DIR="$HOME/.wybe_studio"
CHECKPOINT_DIR="$PROJECT_DIR/checkpoints"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }

# ── Step 1: Check for network volume ──
if [ ! -d "$VOLUME_DIR" ]; then
    warn "No network volume found at $VOLUME_DIR — skipping volume setup."
    warn "Attach a network volume in the RunPod dashboard to enable persistent storage."
    exit 0
fi

log "Network volume detected at $VOLUME_DIR"

# ── Step 2: Create directory structure ──
mkdir -p "$VOLUME_DATA/studio" "$VOLUME_DATA/checkpoints" "$VOLUME_DATA/logs"
log "Volume directories ready at $VOLUME_DATA"

# ── Step 3: Migrate ~/.wybe_studio ──
if [ -d "$STUDIO_DIR" ] && [ ! -L "$STUDIO_DIR" ]; then
    log "Migrating $STUDIO_DIR to volume..."

    # Stop services to prevent SQLite corruption during migration
    if command -v supervisorctl &>/dev/null && pgrep -x supervisord &>/dev/null; then
        log "Stopping services for safe DB migration..."
        supervisorctl stop all 2>/dev/null || true
        sleep 2
    fi

    rsync -a "$STUDIO_DIR/" "$VOLUME_DATA/studio/"
    mv "$STUDIO_DIR" "${STUDIO_DIR}.bak"
    ln -s "$VOLUME_DATA/studio" "$STUDIO_DIR"
    log "Studio data migrated. Backup at ${STUDIO_DIR}.bak"

    # Restart services
    if command -v supervisorctl &>/dev/null && pgrep -x supervisord &>/dev/null; then
        supervisorctl start all 2>/dev/null || true
        log "Services restarted."
    fi
elif [ -L "$STUDIO_DIR" ]; then
    log "Studio data already symlinked — skipping."
else
    # No existing data — just create the symlink
    ln -s "$VOLUME_DATA/studio" "$STUDIO_DIR"
    log "Studio symlink created (no existing data to migrate)."
fi

# ── Step 4: Migrate checkpoints ──
if [ -d "$CHECKPOINT_DIR" ] && [ ! -L "$CHECKPOINT_DIR" ]; then
    log "Migrating checkpoints to volume..."
    rsync -a "$CHECKPOINT_DIR/" "$VOLUME_DATA/checkpoints/"
    mv "$CHECKPOINT_DIR" "${CHECKPOINT_DIR}.bak"
    ln -s "$VOLUME_DATA/checkpoints" "$CHECKPOINT_DIR"
    log "Checkpoints migrated. Backup at ${CHECKPOINT_DIR}.bak"
elif [ -L "$CHECKPOINT_DIR" ]; then
    log "Checkpoints already symlinked — skipping."
else
    ln -s "$VOLUME_DATA/checkpoints" "$CHECKPOINT_DIR"
    log "Checkpoints symlink created (no existing data to migrate)."
fi

# ── Step 5: Set WYBE_DATA_DIR in .env ──
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "^WYBE_DATA_DIR=" "$ENV_FILE"; then
        log "WYBE_DATA_DIR already set in .env — skipping."
    else
        echo "WYBE_DATA_DIR=$VOLUME_DATA/studio" >> "$ENV_FILE"
        log "Added WYBE_DATA_DIR=$VOLUME_DATA/studio to .env"
    fi
else
    warn ".env not found — set WYBE_DATA_DIR=$VOLUME_DATA/studio manually."
fi

# ── Step 6: Symlink log directory ──
ln -sfn "$VOLUME_DATA/logs" /tmp/intelligenceLayer_logs
log "Log directory symlinked: /tmp/intelligenceLayer_logs -> $VOLUME_DATA/logs"

log "Volume setup complete."
