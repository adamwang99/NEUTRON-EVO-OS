#!/bin/bash
# compact-keep-full.sh — Proactive context compaction with "keep-full" semantics
# Usage: ./compact-keep-full.sh
# Calls Claude Code to rewind + summarize from checkpoint, preserving early context

set -e

CLAUDE_BIN="${CLAUDE_BIN:-claude}"

# Create checkpoint marker
CHECKPOINT_FILE="${NEUTRON_ROOT:-.}"/.claude/.compact_checkpoint
date +"%Y-%m-%d %H:%M" > "$CHECKPOINT_FILE"

echo "📋 Compact checkpoint marked at $(cat "$CHECKPOINT_FILE")"
echo "💡 In next Claude Code session, use: /rewind → 'Summarize from here' at the checkpoint"
echo "   This preserves all context before the checkpoint while compressing after it."