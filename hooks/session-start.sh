#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Session Start Hook
# Runs automatically at every Claude Code session start.
# ─────────────────────────────────────────────────────────────────────────────
# What it does:
#  1. First time? → enable auto-confirm and show setup guide
#  2. Every time?
#     a. GC cleanup (silent, floc)
#     b. Dream Cycle (12h debounce, background)
#     c. Write structured .claude/CLAUDE.md with RECALL context
#        → Claude Code auto-loads this file → structured LEARNED/cookbook injection
#     d. Context snapshot echo (for /compact recovery)
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

# ── Dream Cycle Auto-Trigger ────────────────────────────────────────────────
# Runs Dream Cycle once every 12 hours (debounce via .last_dream timestamp).
# Runs silently in background — no output unless debugging.
DREAM_LOCK="$MEMORY_DIR/.dream.lock"
DREAM_LAST="$MEMORY_DIR/.last_dream"
if [ ! -f "$DREAM_LOCK" ]; then
    SHOULD_RUN=0
    if [ -f "$DREAM_LAST" ]; then
        LAST_EPOCH=$(cat "$DREAM_LAST" 2>/dev/null)
        if [ -n "$LAST_EPOCH" ] && [ -n "${LAST_EPOCH//[0-9]/}" ]; then
            NOW_EPOCH=$(date +%s)
            HOURS_SINCE=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
            [ "$HOURS_SINCE" -ge 12 ] && SHOULD_RUN=1
        else
            SHOULD_RUN=1
        fi
    else
        SHOULD_RUN=1
        date +%s > "$DREAM_LAST"
    fi

    if [ "$SHOULD_RUN" -eq 1 ] && [ -d "$COOKBOOK_DIR" ]; then
        # Fire Dream Cycle in background — never blocks session start
        python3 -c "
import sys, os, threading
NR = os.environ.get('NEUTRON_ROOT', '$NEUTRON_ROOT')
sys.path.insert(0, NR)
try:
    from engine.dream_engine import dream_cycle
    def run():
        r = dream_cycle(json_output=True)
        print(f'🌙 Dream Cycle: {r[\"status\"]}', flush=True)
    threading.Thread(target=run, daemon=True).start()
except Exception as e:
    pass  # silent: never interrupt session start
" > /dev/null 2>&1 &
    fi
fi

# ── Structured Context File ──────────────────────────────────────────────────
# Write .claude/CLAUDE.md with RECALL context (LEARNED bugs + cookbook patterns).
# Claude Code auto-loads .claude/CLAUDE.md at session start.
# Python avoids all bash heredoc/quoting issues for multi-line content.
CONTEXT_TMP=$(mktemp)
cat > "$CONTEXT_TMP" <<'PYEOF'
import os, re
from datetime import datetime

nr = os.environ.get("NEUTRON_ROOT", os.getcwd())
mem = os.path.join(nr, "memory")
ctx = os.path.join(nr, ".claude", "CLAUDE.md")
today = datetime.now()
version = "v4.2.0-upgrade"
lines = []

lines.append(f"# Session Context — NEUTRON {version} — {today.strftime('%Y-%m-%d')}")
lines.append("")
lines.append("## System State")
lines.append(f"- Session: {today.strftime('%Y-%m-%d')}")

# 1. Checkpoint: last task from daily log
import glob
logs = sorted(glob.glob(os.path.join(mem, "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")), reverse=True)
if logs:
    content = open(logs[0]).read()
    m = re.search(r"^## \[.*?\] — (.+?):", content, re.MULTILINE)
    if m:
        lines.append(f"- Last task: {m.group(1).strip()}")
    m2 = re.search(r"^Step: (.+)$", content, re.MULTILINE)
    if m2:
        lines.append(f"- Step: {m2.group(1).strip()}")

lines.append("")
lines.append("## RECALL — Apply Before Coding")
lines.append("")

# 2. LEARNED.md: last 2 bug entries
learned = os.path.join(mem, "LEARNED.md")
if os.path.exists(learned):
    content = open(learned).read()
    sections = []
    for block in re.split(r"\n(?=## \[)", content):
        if " Bug: " in block:
            sections.append(block.strip())
    if sections:
        lines.append("### Recent Bug Fixes (memory/LEARNED.md)")
        for s in sections[-2:]:
            lines.append(s)
        lines.append("")

# 3. Cookbooks: most recent pattern
cookbook_dir = os.path.join(mem, "cookbooks")
if os.path.isdir(cookbook_dir):
    books = sorted(glob.glob(os.path.join(cookbook_dir, "*cookbook*.md")), reverse=True)
    if books:
        content = open(books[0]).read()
        sections = []
        for block in re.split(r"\n(?=## \[)", content):
            if "Pattern:" in block or "Bug:" in block:
                sections.append(block.strip())
        if sections:
            lines.append("### Recent Pattern (memory/cookbooks/)")
            lines.append(sections[-1])
            lines.append("")

lines.append(f"*Generated: {today.strftime('%Y-%m-%d %H:%M')}*")

os.makedirs(os.path.dirname(ctx), exist_ok=True)
with open(ctx, "w") as f:
    f.write("\n".join(lines) + "\n")
PYEOF
python3 "$CONTEXT_TMP" && rm -f "$CONTEXT_TMP"

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
