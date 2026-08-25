#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 1 ]; then
  echo "Usage: bash ./install.sh [SKILL_ROOT]" >&2
  exit 2
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="${1:-$HOME/.agents/skills}"
DEST="$SKILL_ROOT/ravenquill"

if [ -e "$DEST" ]; then
  echo "Refusing to overwrite existing destination: $DEST" >&2
  exit 2
fi

mkdir -p "$DEST/methodology" "$DEST/scripts"
cp "$REPO_DIR/SKILL.md" "$DEST/SKILL.md"
cp "$REPO_DIR"/methodology/*.md "$DEST/methodology/"
cp "$REPO_DIR"/scripts/*.py "$DEST/scripts/"

echo "Installed Ravenquill: $DEST"
