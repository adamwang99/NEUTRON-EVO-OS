#!/usr/bin/env bash
# NEUTRON EVO OS — PreToolUse Hook (Path Boundary Guard)
# Blocks Read/Glob/Grep operations that escape the project directory.
#
# Invoked by Claude Code PreToolUse hook before every tool call.
# Usage: pretool-guard.sh "action" "filepath" "extra..."
#
# Policy: Claude Code must NOT read/write files outside the active project.
# For cross-project context, use NEUTRON MCP tools instead.

set -euo pipefail

ACTION="${1:-}"
FILEPATH="${2:-}"

# ── Only guard Read/Glob/Grep ─────────────────────────────────────────────────
case "$ACTION" in
    Read|Glob|Grep) ;;
    *) exit 0 ;;
esac

# ── Skip: no file path provided ──────────────────────────────────────────────
if [ -z "$FILEPATH" ]; then
    exit 0
fi

# ── Skip: commands, patterns, URLs ───────────────────────────────────────────
# Glob/Grep can have a path or a pattern (e.g. "**/*.py").
# If it looks like a glob pattern (contains *, ?, [), skip path check.
if [[ "$FILEPATH" =~ [\?\*\[!] ]]; then
    exit 0
fi

# ── Resolve absolute path ─────────────────────────────────────────────────────
FILEPATH_RESOLVED="$(realpath -- "$FILEPATH" 2>/dev/null || echo "$FILEPATH")"

# ── Skip: relative paths are project-scoped by default ────────────────────────
if [[ "$FILEPATH_RESOLVED" != /* ]]; then
    exit 0
fi

# ── Determine project root ────────────────────────────────────────────────────
# Prefer CWD if it looks like a valid project directory, else NEUTRON_ROOT.
CWD="$(pwd 2>/dev/null || echo "")"
NEUTRON_ROOT="${NEUTRON_ROOT:-${HOME}/.neutron-evo-os}"

# Normalize: resolve symlinks and remove trailing slashes
CWD_RESOLVED="$(realpath -- "$CWD" 2>/dev/null || echo "$CWD")"
CWD_RESOLVED="${CWD_RESOLVED%/}"
FILE_DIR="$(dirname -- "$FILEPATH_RESOLVED")"
FILE_DIR="${FILE_DIR%/}"
NEUTRON_ROOT_RESOLVED="$(realpath -- "$NEUTRON_ROOT" 2>/dev/null || echo "$NEUTRON_ROOT")"
NEUTRON_ROOT_RESOLVED="${NEUTRON_ROOT_RESOLVED%/}"

# ── Check: is FILE_DIR inside CWD? ───────────────────────────────────────────
IS_UNDER_CWD=false
if [[ "$FILE_DIR" == "$CWD_RESOLVED" ]] || [[ "$FILE_DIR" == "$CWD_RESOLVED"/* ]]; then
    IS_UNDER_CWD=true
fi

# ── Check: is FILE_DIR inside NEUTRON_ROOT? ──────────────────────────────────
IS_UNDER_NEUTRON=false
if [[ "$FILE_DIR" == "$NEUTRON_ROOT_RESOLVED" ]] || [[ "$FILE_DIR" == "$NEUTRON_ROOT_RESOLVED"/* ]]; then
    IS_UNDER_NEUTRON=true
fi

# ── Allow: inside CWD ─────────────────────────────────────────────────────────
if $IS_UNDER_CWD; then
    exit 0
fi

# ── Allow: inside NEUTRON_ROOT ────────────────────────────────────────────────
if $IS_UNDER_NEUTRON; then
    exit 0
fi

# ── BLOCK: cross-project read ─────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  NEUTRON — ACCESS DENIED: Cross-Project Boundary Violation       ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Operation: $ACTION"
echo "║  Tried to read:"
echo "║    $FILEPATH_RESOLVED"
echo "║  Project root:"
echo "║    $CWD_RESOLVED"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  SOLUTION: Use NEUTRON MCP tools for cross-project context:"
echo "║    - neutron memory --action search --query <keyword>"
echo "║    - neutron checkpoint --action read"
echo "║    - neutron context --task audit"
echo "╚══════════════════════════════════════════════════════════════════╝"
exit 1
