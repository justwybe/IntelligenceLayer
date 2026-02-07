#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Restore from Git Backup
#
# Pulls the latest backup from the backups/pod-data branch and
# restores the DB and .env. Run this on a fresh pod after
# cloning the repo.
#
# Usage: bash scripts/restore_backup.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"
cd "$PROJECT_DIR"

BACKUP_BRANCH="backups/pod-data"
DB_DIR="$HOME/.wybe_studio"
ENV_PATH="$PROJECT_DIR/.env"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] RESTORE: $*"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] RESTORE WARN: $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] RESTORE ERROR: $*" >&2; }

# Fetch the backup branch
log "Fetching backup branch..."
git fetch origin "$BACKUP_BRANCH" --quiet 2>/dev/null || {
    err "No backup branch found (origin/$BACKUP_BRANCH). Nothing to restore."
    exit 1
}

# Show what we're restoring
log "Latest backup:"
git log "origin/$BACKUP_BRANCH" -1 --oneline 2>/dev/null || true
echo ""

# Extract files from the backup branch without switching branches
RESTORE_DIR=$(mktemp -d)

git show "origin/$BACKUP_BRANCH:pod-info.json" > "$RESTORE_DIR/pod-info.json" 2>/dev/null && {
    log "Backup metadata:"
    cat "$RESTORE_DIR/pod-info.json"
    echo ""
} || true

# Restore database
git show "origin/$BACKUP_BRANCH:studio.db" > "$RESTORE_DIR/studio.db" 2>/dev/null
if [ -s "$RESTORE_DIR/studio.db" ]; then
    mkdir -p "$DB_DIR"
    if [ -f "$DB_DIR/studio.db" ]; then
        cp "$DB_DIR/studio.db" "$DB_DIR/studio.db.pre-restore"
        warn "Existing DB backed up to $DB_DIR/studio.db.pre-restore"
    fi
    cp "$RESTORE_DIR/studio.db" "$DB_DIR/studio.db"
    log "Database restored to $DB_DIR/studio.db ($(du -h "$DB_DIR/studio.db" | cut -f1))"
else
    warn "No database in backup."
fi

# Restore .env
git show "origin/$BACKUP_BRANCH:env" > "$RESTORE_DIR/env" 2>/dev/null
if [ -s "$RESTORE_DIR/env" ]; then
    if [ -f "$ENV_PATH" ]; then
        cp "$ENV_PATH" "${ENV_PATH}.pre-restore"
        warn "Existing .env backed up to ${ENV_PATH}.pre-restore"
    fi
    cp "$RESTORE_DIR/env" "$ENV_PATH"
    log ".env restored ($(wc -l < "$ENV_PATH") lines)"
else
    warn "No .env in backup."
fi

rm -rf "$RESTORE_DIR"

log "Restore complete. Run 'bash scripts/startup.sh' to start services."
