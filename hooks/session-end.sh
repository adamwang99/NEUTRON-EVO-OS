#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Session End Hook
# Runs automatically at every Claude Code session end (via atexit in Python).
# Triggers: memory sync, Dream Cycle trigger, checkpoint save.
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"
HOOKS_DIR="${HOOKS_DIR:-$SCRIPT_DIR}"

# Exit silently if NEUTRON_ROOT invalid
if [ ! -f "$NEUTRON_ROOT/engine/cli/main.py" ]; then
    exit 0
fi

export NEUTRON_ROOT

# ── Memory sync to hub ─────────────────────────────────────────────────────
# Run only if NEUTRON_HUB is set and different from NEUTRON_ROOT
if [ -n "$NEUTRON_HUB" ] && [ "$NEUTRON_HUB" != "$NEUTRON_ROOT" ]; then
    (
        python3 -m neutron memory sync --hub "$NEUTRON_HUB" 2>/dev/null
    ) &
    # Don't block session exit — run async
fi

# ── Dream Cycle trigger (if silent for >30min, per last activity) ───────────
# Check last activity timestamp in memory
LAST_ACTIVITY_FILE="$NEUTRON_ROOT/memory/.last_activity"
if [ -f "$LAST_ACTIVITY_FILE" ]; then
    LAST_TS=$(cat "$LAST_ACTIVITY_FILE" 2>/dev/null)
    if [ -n "$LAST_TS" ]; then
        # Compute minutes since last activity using date arithmetic
        LAST_EPOCH=$(date -d "$LAST_TS" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        MINUTES_SINCE=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))
        if [ "$MINUTES_SINCE" -ge 30 ]; then
            (
                # Silent Dream Cycle — don't block exit
                python3 -m neutron dream 2>/dev/null
            ) &
        fi
    fi
fi

exit 0