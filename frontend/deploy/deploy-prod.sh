#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${PROD_HOST:-}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PATH="${REMOTE_PATH:-/data/www/FinEngine/frontend/dist}"
SSH_PORT="${SSH_PORT:-22}"
SSH_KEY="${SSH_KEY:-}"
DRY_RUN="${DRY_RUN:-0}"
SKIP_BUILD="${SKIP_BUILD:-0}"

if [[ -z "$REMOTE_HOST" ]]; then
  echo "Missing PROD_HOST. Example:"
  echo "  PROD_HOST=finengine.example.com bash frontend/deploy/deploy-prod.sh"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$FRONTEND_DIR/dist"

SSH_OPTS=(-p "$SSH_PORT")
if [[ -n "$SSH_KEY" ]]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi
RSYNC_SSH="ssh -p $(printf '%q' "$SSH_PORT")"
if [[ -n "$SSH_KEY" ]]; then
  RSYNC_SSH+=" -i $(printf '%q' "$SSH_KEY")"
fi

RSYNC_OPTS=(-az --delete --info=progress2)
if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_OPTS+=(-n)
fi

cd "$FRONTEND_DIR"

if [[ "$SKIP_BUILD" != "1" ]]; then
  npm run build
fi

ssh "${SSH_OPTS[@]}" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p '$REMOTE_PATH'"
rsync "${RSYNC_OPTS[@]}" -e "$RSYNC_SSH" "$DIST_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"

echo "Prod frontend deployed to $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
