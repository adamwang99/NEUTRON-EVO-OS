#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Session Start Hook
# Runs automatically at every Claude Code session start.
# ─────────────────────────────────────────────────────────────────────────────
# What it does:
#  1. First time? → enable auto-confirm and show setup guide
#  2. Every time? → load checkpoint, show system status
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"
HOOKS_DIR="${HOOKS_DIR:-$SCRIPT_DIR}"

# ── Early exit if NEUTRON_ROOT invalid ──────────────────────────────────────
if [ ! -f "$NEUTRON_ROOT/engine/cli/main.py" ]; then
    # Try to find it
    if [ -f "$(dirname "$0")/../engine/cli/main.py" ]; then
        NEUTRON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
    else
        exit 0  # Silent fail — not a NEUTRON session
    fi
fi

export NEUTRON_ROOT

# ── Paths ────────────────────────────────────────────────────────────────────
MEMORY_DIR="$NEUTRON_ROOT/memory"
ARCHIVED_DIR="$MEMORY_DIR/archived"
FIRST_RUN_MARKER="$MEMORY_DIR/.first_session_done"
AUTO_CONFIRM_CONFIG="$MEMORY_DIR/.auto_confirm.json"
GC_LOCK="$MEMORY_DIR/.gc_running"

mkdir -p "$MEMORY_DIR"

# ── First session detection ──────────────────────────────────────────────────
if [ ! -f "$FIRST_RUN_MARKER" ]; then
    # First time ever → enable auto-confirm full by default
    python3 "$HOOKS_DIR/neutron-first-run.py" "$NEUTRON_ROOT"

    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🟢 NEUTRON EVO OS v4.1.0 — First Time Setup Complete  ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "  ✅ Auto-confirm FULL enabled (all gates skipped)"
    echo "     → To disable:  neutron auto disable"
    echo "     → To change:   neutron auto spec_only"
    echo ""
    echo "  🚀 You're ready. Run: /discover \"your project idea\""
    echo ""
else
    # Normal session → show brief status
    if [ -f "$AUTO_CONFIRM_CONFIG" ]; then
        MODE=$(python3 -c "import json; print(json.load(open('$AUTO_CONFIRM_CONFIG')).get('mode','disabled'))" 2>/dev/null || echo "disabled")
        case "$MODE" in
            full)    ICON="🔓"; LABEL="FULL (all gates skipped)" ;;
            spec_only) ICON="🔒"; LABEL="SPEC ONLY" ;;
            acceptance_only) ICON="🔒"; LABEL="ACCEPTANCE ONLY" ;;
            spec_and_acceptance) ICON="🔒"; LABEL="SPEC + ACCEPTANCE" ;;
            discovery_only) ICON="🔒"; LABEL="DISCOVERY ONLY" ;;
            disabled) ICON="🔴"; LABEL="DISABLED (human control)" ;;
            *) ICON="⚙️"; LABEL="$MODE" ;;
        esac
        echo "  $ICON NEUTRON AUTO: $LABEL"
    fi
fi

# ── Garbage Collection (every session — silent) ─────────────────────────────
# Runs lightweight cleanup silently. Full gc: neutron gc --pycache --tests
# Guard: NEUTRON_ROOT must point to a valid NEUTRON installation.
# Uses flock(1) — atomic, crash-safe, no staleness.
if [ -f "$NEUTRON_ROOT/engine/cli/main.py" ]; then
    # Open lock file on FD 200 (creates if not exists). flock releases automatically
    # when the script exits (normal or crash).
    exec 200>"$GC_LOCK"
    if flock -n 200; then
        (
            # 1. Bash cleanup: __pycache__, *.pyc, .pytest_cache (fast, reliable)
            find "$NEUTRON_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
            find "$NEUTRON_ROOT" -name "*.pyc" -type f -delete 2>/dev/null
            find "$NEUTRON_ROOT" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null

            # 2. Bash cleanup: archived/ old by age (reliable for this)
            if [ -d "$ARCHIVED_DIR" ]; then
                find "$ARCHIVED_DIR" -maxdepth 1 \
                    \( -name "????-??-??_??????????.md" -o -name "????-??-??_*.md" \) \
                    -type f -mtime +7 -delete 2>/dev/null
                # 3. data_*.json dumps in archived/ (test/agent garbage)
                find "$ARCHIVED_DIR" -name "data_*.json" -type f -delete 2>/dev/null
            fi

            # 4. Python cleanup: count-based cap + pending expiry (bash can't do this)
            python3 "$HOOKS_DIR/gc_lightweight.py" 2>/dev/null
        ) 2>/dev/null
        flock -u 200  # release lock
    fi
    # Lock auto-releases on script exit (FD 200 closes)
fi

# ── Load checkpoint if exists ────────────────────────────────────────────────
# Checkpoint CLI writes to memory/YYYY-MM-DD.md as "## [HH:MM] — Task:" entries.
# Find the most recent memory log and show the last checkpoint entry.
LATEST_LOG=$(find "$MEMORY_DIR" -maxdepth 1 -name "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md" -type f | sort -r | head -1)
if [ -n "$LATEST_LOG" ]; then
    LAST_CP=$(grep -A 4 "^## \[" "$LATEST_LOG" | tail -5 2>/dev/null)
    if [ -n "$LAST_CP" ]; then
        echo ""
        echo "📋 Last checkpoint:"
        echo "$LAST_CP" | sed 's/^/   /'
    fi
fi

# ── Load LEARNED.md — RECALL: relevant bugs before coding ────────────────────
# Shows last 2 structured entries (Bug: format) as structured context.
# ~20 lines, ~400 tokens — no terminal spam.
LEARNED="$MEMORY_DIR/LEARNED.md"
if [ -f "$LEARNED" ]; then
    LAST_LEARNED=$(awk '
        /^## \[.*\] Bug: / { section=1; lines=$0; next }
        section && /^## \[/ { section=0 }
        section { lines = lines ORS $0 }
        END { if (section) print lines }
    ' "$LEARNED" 2>/dev/null | tail -2)
    if [ -n "$LAST_LEARNED" ]; then
        echo ""
        echo "## RECENT BUGS (memory/LEARNED.md) — apply before coding:"
        echo "$LAST_LEARNED"
    fi
fi

# ── Load most recent cookbook — RECALL: actionable patterns before coding ───────
# Shows the most recent cookbook pattern (trigger/recognition/resolution/prevention).
# ~15 lines, ~300 tokens — no terminal spam.
COOKBOOK_DIR="$MEMORY_DIR/cookbooks"
if [ -d "$COOKBOOK_DIR" ]; then
    LATEST_COOKBOOK=$(find "$COOKBOOK_DIR" -maxdepth 1 -name "*cookbook*.md" -type f 2>/dev/null | sort -r | head -1)
    if [ -n "$LATEST_COOKBOOK" ] && [ -f "$LATEST_COOKBOOK" ]; then
        # Extract last pattern entry (## Pattern: or ## Bug: sections)
        LAST_PATTERN=$(awk '
            /^## \[.*\] (Pattern:|Bug:)/ { section=1; lines=$0; next }
            section && /^## \[/ { section=0 }
            section { lines = lines ORS $0 }
            END { if (section) print lines }
        ' "$LATEST_COOKBOOK" 2>/dev/null | tail -1)
        if [ -n "$LAST_PATTERN" ]; then
            echo ""
            echo "## RECENT PATTERN (memory/cookbooks/) — apply before coding:"
            echo "$LAST_PATTERN"
        fi
    fi
fi

# ── Context Snapshot (recovery after /compact) ─────────────────────────────
# After context compaction, the next session sees what was in progress.
# neutron snapshot saves state on every skill execution automatically.
# Uses a temp Python script to safely parse JSON without shell injection risk.
SNAPSHOT="$MEMORY_DIR/.context_snapshot.json"
if [ -f "$SNAPSHOT" ]; then
    # Write Python script to temp file (single-quoted heredoc = no variable expansion)
    # This avoids embedding $SNAPSHOT in a -c string which could allow code injection.
    SNAP_TMP=$(mktemp)
    cat > "$SNAP_TMP" <<'PYEOF'
import json, sys, os
from datetime import datetime
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    ts = data.get("snapshot_at", "")
    if ts:
        age = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
        if age < 4:
            print("TASK=" + data.get("task", ""))
            print("STEP=" + data.get("current_step", ""))
            print("STATUS=" + data.get("test_status", ""))
            files = ", ".join(data.get("modified_files", [])[:5])
            print("MODIFIED=" + files)
except Exception:
    pass
PYEOF
    # shellcheck source=SC2090
    eval "$(python3 "$SNAP_TMP" "$SNAPSHOT" 2>/dev/null)"
    rm -f "$SNAP_TMP"
    if [ -n "$TASK" ]; then
        echo ""
        echo "🔄 Context recovered from previous session:"
        echo "   📋 Task: $TASK"
        [ -n "$STEP" ] && echo "   📍 Step: $STEP"
        [ -n "$MODIFIED" ] && echo "   📁 Modified: $MODIFIED"
        echo "   ⚡ To clear:  neutron snapshot clear"
    fi
fi
