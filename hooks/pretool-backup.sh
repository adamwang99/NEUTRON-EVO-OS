#!/usr/bin/env bash
# NEUTRON EVO OS — PreToolUse Hook (Smart Backup + Regression Guard)
# Invoked by Claude Code PreToolUse hook before every file write.
#
# Usage: pretool-backup.sh "action" "filepath"
#   action: Write|Edit
#   filepath: path of the file being modified
#
# Smart backup strategy:
#   - SKIP: binary files (images, PDFs, videos, archives), files > MAX_SIZE,
#     generated directories (node_modules, __pycache__, .git, target/, dist/),
#     lock files (package-lock.json, Cargo.lock)
#   - BACKUP: source code files (< MAX_SIZE), config files, documentation
#   - PHASE 2: regression smoke test ONLY for engine/, skills/, mcp_server/

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────────
# Resolve NEUTRON_ROOT: project-local override, else default install
if [ -f "$(dirname "$0")/../.neutron_root" ]; then
    NEUTRON_ROOT="$(cat "$(dirname "$0")/../.neutron_root")"
elif [ -n "${NEUTRON_ROOT:-}" ]; then
    :  # keep env value
else
    NEUTRON_ROOT="$HOME/.neutron-evo-os"
fi

BACKUP_DIR="$NEUTRON_ROOT/.backup"

# ── Size cap (bytes) — skip files larger than this ─────────────────────────────
MAX_SIZE=2097152   # 2 MB

# ── Patterns to ALWAYS skip ───────────────────────────────────────────────────
# Binary / media / archive extensions
SKIP_EXT_REGEX='\.(png|jpg|jpeg|gif|ico|webp|svg|mp4|mp3|wav|ogg|flac|pdf|zip|tar|gz|bz2|7z|rar|tgz|exe|dll|so|dylib|wasm|bin|dat|db|sqlite|mdb|accdb)$'

# Directories to always skip — pattern matches "/dirname/" or "/dirname$" anywhere in path
SKIP_PATHS_REGEX='/(node_modules|\.git|__pycache__|\.pytest_cache|\.mypy_cache|target|dist|build|\.next|\.nuxt|\.svelte-kit|vendor|\.venv|venv|env|\.tox|eggs|\.egg-info|_site|\.sass-cache|bower_components|\.cache)/'

# Lock files — NEVER backup (merge conflict, generated, large)
SKIP_FILES_REGEX='(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|go\.sum|Pipfile\.lock|poetry\.lock|\.lock|package\.json\.bak)$'

# File types worth backing up (source + config, not binary)
BACKABLE_EXT_REGEX='\.(py|rs|go|ts|tsx|js|jsx|java|c|cpp|cxx|h|hxx|hpp|cs|rb|php|swift|kt|scala|r|lua|sh|bash|zsh|fish|ps1|bat|cmd|sql|graphql|vue|svelte|md|mdx|yaml|yml|toml|json|toml|ini|conf|cfg|env|properties|xml|html|css|scss|sass|less|har|proto|tf|terraform|dockerfile|makefile|gemfile|rakefile)$'

ACTION="${1:-}"
FILEPATH="${2:-}"

# ── Only protect file writes ──────────────────────────────────────────────────
case "$ACTION" in
    Write|Edit) ;;
    *) exit 0 ;;
esac

if [ -z "$FILEPATH" ]; then
    exit 0
fi

# Resolve absolute path safely — -- stops option injection
FILEPATH="$(realpath -- "$FILEPATH" 2>/dev/null || echo "$FILEPATH")"

# ── Skip: no absolute path ───────────────────────────────────────────────────
if [[ "$FILEPATH" != /* ]]; then
    exit 0
fi

# ── Skip: binary / media / archive extensions ───────────────────────────────
if [[ "$FILEPATH" =~ $SKIP_EXT_REGEX ]]; then
    exit 0
fi

# ── Skip: in generated / large directories ─────────────────────────────────
if [[ "$FILEPATH" =~ $SKIP_PATHS_REGEX ]]; then
    exit 0
fi

# ── Skip: lock files ─────────────────────────────────────────────────────────
if [[ "$FILEPATH" =~ $SKIP_FILES_REGEX ]]; then
    exit 0
fi

# ── Skip: file size > MAX_SIZE ──────────────────────────────────────────────
if [ -f "$FILEPATH" ]; then
    SIZE=$(stat -c%s -- "$FILEPATH" 2>/dev/null || stat -f%z -- "$FILEPATH" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt "$MAX_SIZE" ]; then
        exit 0
    fi
fi

# ── Phase 1: Backup only if file exists and is backupable source/config ─────
# Backup: known source/config extensions (explicit allowlist) OR .env.example
# The allowlist is conservative: only real source code and config files.
# This prevents backing up generated data files, CSV dumps, log files, etc.
mkdir -p "$BACKUP_DIR"
if [ -f "$FILEPATH" ]; then
    if [[ "$FILEPATH" =~ $BACKABLE_EXT_REGEX ]] || [[ "$FILEPATH" == *.env.example ]]; then
        BASENAME="$(basename -- "$FILEPATH")"
        TS="$(date +%Y%m%d_%H%M%S)"
        # Limit: keep max 200 backup files per project dir to prevent disk bloat
        BACKUP_COUNT=$(ls "$BACKUP_DIR"/"$BASENAME".*.bak 2>/dev/null | wc -l)
        if [ "$BACKUP_COUNT" -ge 200 ]; then
            # Remove oldest backup for this file
            ls -t "$BACKUP_DIR"/"$BASENAME".*.bak 2>/dev/null | tail -1 | xargs rm -f 2>/dev/null || true
        fi
        cp -- "$FILEPATH" "$BACKUP_DIR/${BASENAME}.${TS}.bak" 2>/dev/null || true
    fi
fi

# ── Phase 2: Regression smoke test ONLY for NEUTRON engine code ─────────────
REL_PATH="${FILEPATH#$NEUTRON_ROOT/}"
case "$REL_PATH" in
    engine/*|skills/*|mcp_server/*)
        if [ -f "$NEUTRON_ROOT/engine/regression_guard.py" ]; then
            python3 "$NEUTRON_ROOT/engine/regression_guard.py" \
                --check --files "$FILEPATH" 2>/dev/null || true
        fi
        ;;
esac
