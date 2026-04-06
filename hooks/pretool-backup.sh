#!/usr/bin/env bash
# NEUTRON EVO OS — PreToolUse Hook (Backup + Regression Guard)
# Invoked by Claude Code PreToolUse hook before every file write.
#
# Usage: pretool-backup.sh "action" "filepath"
#   action: Read|Write|Edit|bash|etc.
#   filepath: path of the file being modified
#
# Two-phase protection:
#   1. BACKUP   — copy file to .backup/ before write (existing)
#   2. REGRESSION — run smoke test after write to catch breakage early

set -euo pipefail

# Resolve NEUTRON_ROOT: project-local override, else default install
if [ -f "$(dirname "$0")/../.neutron_root" ]; then
    NEUTRON_ROOT="$(cat "$(dirname "$0")/../.neutron_root")"
elif [ -n "${NEUTRON_ROOT:-}" ]; then
    :  # keep env value
else
    NEUTRON_ROOT="$HOME/.neutron-evo-os"
fi

BACKUP_DIR="$NEUTRON_ROOT/.backup"
GUARD_DIR="$NEUTRON_ROOT/memory/.regression"

ACTION="${1:-}"
FILEPATH="${2:-}"

# ── Only protect file writes (not read-only commands) ─────────────────────────
case "$ACTION" in
    Write|Edit)
        FILEPATH="$FILEPATH"
        ;;
    *)
        exit 0
        ;;
esac

if [ -z "$FILEPATH" ]; then
    exit 0
fi

# Resolve absolute path
FILEPATH="$(realpath "$FILEPATH" 2>/dev/null || echo "$FILEPATH")"

# ── Phase 1: Backup before write ───────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
if [ -f "$FILEPATH" ]; then
    cp -- "$FILEPATH" "$BACKUP_DIR/$(basename "$FILEPATH").$(date +%Y%m%d_%H%M%S).bak" 2>/dev/null || true
fi

# ── Phase 2: Run regression smoke test after backup ───────────────────────────
# Only run on engine/, skills/, or mcp_server/ changes (skip test/docs/configs)
REL_PATH="${FILEPATH#$NEUTRON_ROOT/}"
case "$REL_PATH" in
    engine/*|skills/*|mcp_server/*)
        if [ -f "$NEUTRON_ROOT/engine/regression_guard.py" ]; then
            python3 "$NEUTRON_ROOT/engine/regression_guard.py" \
                --check --files "$FILEPATH" 2>/dev/null || true
        fi
        ;;
    *)
        # Skip regression on non-critical files (tests, docs, configs)
        ;;
esac
