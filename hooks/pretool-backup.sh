#!/usr/bin/env bash
# NEUTRON EVO OS — PreToolUse Backup Hook
# Safe backup script invoked by Claude Code PreToolUse hook.
# Usage: pretool-backup.sh "file1,file2,..."
# Invoked from settings.json PreToolUse hook.
# NOTE: {path} is expanded by Claude Code before passing here.
# We treat the input as filenames only — no shell evaluation.

set -euo pipefail

NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"
BACKUP_DIR="$NEUTRON_ROOT/.backup"

PATHS="${1:-}"

if [ -z "$PATHS" ]; then
    exit 0
fi

mkdir -p "$BACKUP_DIR"

# Iterate over comma-separated paths — each path is trusted from Claude Code
IFS=',' read -ra FILELIST <<< "$PATHS"
for filepath in "${FILELIST[@]}"; do
    # Trim whitespace
    filepath="$(echo "$filepath" | xargs)"
    if [ -f "$filepath" ]; then
        cp -- "$filepath" "$BACKUP_DIR/$(basename "$filepath").$(date +%Y%m%d_%H%M%S).bak" 2>/dev/null || true
    fi
done
