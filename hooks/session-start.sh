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

# ── Load LEARNED.md (bug fixes & patterns — never repeat the same mistake) ───
LEARNED="$MEMORY_DIR/LEARNED.md"
if [ -f "$LEARNED" ]; then
    # Show last 3 entries only (most recent first)
    TOTAL=$(grep -c "^## \[" "$LEARNED" 2>/dev/null || echo 0)
    if [ "$TOTAL" -gt 0 ]; then
        echo ""
        echo "📚 LEARNED.md — $TOTAL bug fix(es) recorded"
        # Print the last section block (from last "## " to end)
        LAST_LEARNED=$(awk '/^## \[.*\] Bug: /{section=$0} section{body=section ORS $0} END{print body}' "$LEARNED" 2>/dev/null | tail -20)
        if [ -n "$LAST_LEARNED" ]; then
            echo "$LAST_LEARNED" | sed 's/^/   /'
        fi
    fi
fi

# ── Load hub LEARNED.md (accumulated from all projects) ──────────────────────
# NEUTRON_HUB points to ~/.neutron-evo-os — cross-project knowledge base.
# Skip if hub is same as local (hub project itself has no separate hub).
if [ -n "$NEUTRON_HUB" ] && [ -d "$NEUTRON_HUB/memory" ] && [ "$NEUTRON_HUB" != "$NEUTRON_ROOT" ]; then
    HUB_LEARNED="$NEUTRON_HUB/memory/LEARNED.md"
    if [ -f "$HUB_LEARNED" ]; then
        HUB_TOTAL=$(grep -c "^## \[" "$HUB_LEARNED" 2>/dev/null || echo 0)
        if [ "$HUB_TOTAL" -gt 0 ]; then
            echo ""
            echo "📡 HUB LEARNED.md — $HUB_TOTAL bug fix(es) from all projects"
            # Show last 3 hub entries (most recent bugs from any project)
            HUB_LAST=$(awk '/^## \[.*\] Bug: /{section=$0} section{body=section ORS $0} END{print body}' "$HUB_LEARNED" 2>/dev/null | tail -25)
            if [ -n "$HUB_LAST" ]; then
                echo "$HUB_LAST" | sed 's/^/   /'
            fi
        fi
    fi
fi

# ── Load LEARNED pending entries (AI suggestions awaiting human approval) ─────
PENDING="$MEMORY_DIR/pending/LEARNED_pending.md"
if [ -f "$PENDING" ]; then
    PENDING_COUNT=$(grep -c "^\[PENDING\]" "$PENDING" 2>/dev/null || echo 0)
    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo ""
        echo "📋 $PENDING_COUNT pending LEARNED entry/entries — awaiting your approval"
        echo "   neutron memory approve <draft_id>   OR   neutron memory reject <draft_id>"
        echo "   neutron memory pending              ← list all"
        head -12 "$PENDING" | sed 's/^/   /'
    fi
fi

# ── Load most recent cookbook (distilled knowledge from Dream Cycle) ───────
COOKBOOK=$(find "$MEMORY_DIR/cookbooks" -name "*.md" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
if [ -n "$COOKBOOK" ] && [ -f "$COOKBOOK" ]; then
    echo ""
    echo "📖 Recent cookbook: $(basename "$COOKBOOK")"
    head -15 "$COOKBOOK" 2>/dev/null | sed 's/^/   /'
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
