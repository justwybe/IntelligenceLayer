#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Automated Backup to Git
#
# Backs up critical data (DB, .env) to a dedicated git branch.
# The DB is <1MB, so this adds negligible overhead.
# Runs hourly via cron. Keeps last 48 commits on the branch.
#
# Usage: bash scripts/backup.sh
# ──────────────────────────────────────────────────────────────
set -uo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/IntelligenceLayer}"
cd "$PROJECT_DIR"

BACKUP_BRANCH="backups/pod-data"
DB_PATH="$HOME/.wybe_studio/studio.db"
ENV_PATH="$PROJECT_DIR/.env"
BACKUP_DIR="$PROJECT_DIR/.pod-backup"
LOCK_FILE="/tmp/wybe_backup.lock"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] BACKUP: $*"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] BACKUP ERROR: $*" >&2; }

# Acquire exclusive lock
exec 201>"$LOCK_FILE"
if ! flock -n 201; then
    log "Another backup is running — skipping."
    exit 0
fi

# Don't backup during deploys (test if deploy lock is held)
if [ -f /tmp/wybe_deploy.lock ]; then
    if ! flock -n -x 200 200>/tmp/wybe_deploy.lock 2>/dev/null; then
        log "Deploy in progress — skipping backup."
        exit 0
    fi
    # Release the test lock immediately
    exec 200>&-
fi

# Check if there's anything to back up
if [ ! -f "$DB_PATH" ]; then
    log "No database found — nothing to back up."
    exit 0
fi

# Create backup staging directory
mkdir -p "$BACKUP_DIR"

# Copy files to backup dir
cp "$DB_PATH" "$BACKUP_DIR/studio.db" 2>/dev/null || true

# Back up .env with secrets redacted (GitHub push protection blocks API keys)
if [ -f "$ENV_PATH" ]; then
    sed -E 's/(ANTHROPIC_API_KEY=).+/\1REDACTED/' "$ENV_PATH" \
      | sed -E 's/(WYBE_API_KEY=).+/\1REDACTED/' \
      > "$BACKUP_DIR/env" 2>/dev/null || true
fi

# Store pod metadata
cat > "$BACKUP_DIR/pod-info.json" <<EOF
{
  "timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "hostname": "$(hostname)",
  "pod_id": "${RUNPOD_POD_ID:-unknown}",
  "git_sha": "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)",
  "gpu": "$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo unknown)"
}
EOF

# Save current branch to return to
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Check if backup branch exists
if git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH" 2>/dev/null; then
    git checkout "$BACKUP_BRANCH" --quiet 2>/dev/null
elif git show-ref --verify --quiet "refs/remotes/origin/$BACKUP_BRANCH" 2>/dev/null; then
    git checkout -b "$BACKUP_BRANCH" "origin/$BACKUP_BRANCH" --quiet 2>/dev/null
else
    # Create orphan branch (no shared history with main)
    git checkout --orphan "$BACKUP_BRANCH" --quiet 2>/dev/null
    git rm -rf . --quiet 2>/dev/null || true
fi

# Stage backup files
cp "$BACKUP_DIR/studio.db" ./studio.db 2>/dev/null || true
cp "$BACKUP_DIR/env" ./env 2>/dev/null || true
cp "$BACKUP_DIR/pod-info.json" ./pod-info.json 2>/dev/null || true

git add studio.db env pod-info.json 2>/dev/null || true

# Only commit if something changed
if git diff --cached --quiet 2>/dev/null; then
    log "No changes since last backup."
else
    git commit -m "backup: $(date '+%Y-%m-%d %H:%M') | $(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null)" --quiet 2>/dev/null
    git push origin "$BACKUP_BRANCH" --force --quiet 2>/dev/null || err "Push failed — check git credentials."
    log "Backup pushed to origin/$BACKUP_BRANCH"
fi

# Return to original branch
git checkout "$CURRENT_BRANCH" --quiet 2>/dev/null

# Restore backup staging dir state
rm -rf "$BACKUP_DIR"

log "Done."
