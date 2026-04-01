#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Session Start Hook
# Runs automatically at every Claude Code session start.
# ─────────────────────────────────────────────────────────────────────────────
# What it does:
#  1. First time? → enable auto-confirm and show setup guide
#  2. Every time? → load checkpoint, show system status
# ─────────────────────────────────────────────────────────────────────────────

NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"

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
FIRST_RUN_MARKER="$MEMORY_DIR/.first_session_done"
AUTO_CONFIRM_CONFIG="$MEMORY_DIR/.auto_confirm.json"

mkdir -p "$MEMORY_DIR"

# ── First session detection ──────────────────────────────────────────────────
if [ ! -f "$FIRST_RUN_MARKER" ]; then
    # First time ever → enable auto-confirm full by default
    python3 - "$NEUTRON_ROOT" << 'PYEOF'
import sys, json, os
root = sys.argv[1]
auto_file = os.path.join(root, "memory", ".auto_confirm.json")
os.makedirs(os.path.dirname(auto_file), exist_ok=True)
config = {"enabled": True, "mode": "full", "notes": "auto-confirm enabled on first session"}
with open(auto_file, "w") as f:
    json.dump(config, f, indent=2)

# Create first-run marker
marker = os.path.join(root, "memory", ".first_session_done")
with open(marker, "w") as f:
    f.write("first_session_done\n")
print("AUTO-CONFIRM: enabled (first session — full mode)")
PYEOF

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
