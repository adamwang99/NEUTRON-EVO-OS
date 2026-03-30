#!/usr/bin/env bash
# =============================================================================
# NEUTRON EVO OS v4.1.0 — Global Installer
# =============================================================================
# Purpose: Apply NEUTRON EVO OS context to ALL projects (current & future)
# Usage:   bash install-global.sh
# Requirements: git, bash
# =============================================================================

set -e

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       NEUTRON EVO OS v4.1.0 — Global Installer           ║"
echo "║       ∫f(t)dt — Functional Credibility Over Inertia       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"

# =============================================================================
# STEP 0: Determine NEUTRON_ROOT
# =============================================================================
if [ -n "$NEUTRON_ROOT" ] && [ -d "$NEUTRON_ROOT" ]; then
    NEUTRON_ROOT_DIR="$NEUTRON_ROOT"
else
    # Default: this script's parent directory (repo root)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    NEUTRON_ROOT_DIR="$SCRIPT_DIR"
fi

echo -e "${YELLOW}[1/6] NEUTRON_ROOT: ${NEUTRON_ROOT_DIR}${RESET}"

# Verify core files exist
for f in SOUL.md MANIFESTO.md USER.md GOVERNANCE.md RULES.md; do
    if [ ! -f "$NEUTRON_ROOT_DIR/$f" ]; then
        echo -e "${RED}✗ ERROR: $f not found in $NEUTRON_ROOT_DIR${RESET}"
        echo "  → Please run this script from the NEUTRON-EVO-OS repository root."
        exit 1
    fi
done
echo -e "${GREEN}[✓] Core files verified${RESET}"

# =============================================================================
# STEP 1: Clone / update ~/.neutron-evo-os
# =============================================================================
NEUTRON_HOME="$HOME/.neutron-evo-os"
echo -e "${YELLOW}[2/6] Setting up ~/.neutron-evo-os ...${RESET}"

if [ -d "$NEUTRON_HOME/.git" ]; then
    echo "  → Updating existing installation..."
    cd "$NEUTRON_HOME" && git pull 2>/dev/null || true
elif [ -d "$NEUTRON_ROOT_DIR/.git" ]; then
    echo "  → Creating symlink (this repo is already NEUTRON-EVO-OS)..."
    if [ ! -e "$NEUTRON_HOME" ]; then
        ln -s "$NEUTRON_ROOT_DIR" "$NEUTRON_HOME"
    fi
else
    echo "  → Cloning fresh copy..."
    git clone https://github.com/adamwang99/NEUTRON-EVO-OS.git "$NEUTRON_HOME" 2>/dev/null || \
    git clone git@github.com:adamwang99/NEUTRON-EVO-OS.git "$NEUTRON_HOME"
fi
echo -e "${GREEN}[✓] ~/.neutron-evo-os ready${RESET}"

# =============================================================================
# STEP 2: Configure ~/.claude/settings.json
# =============================================================================
CLAUDE_DIR="$HOME/.claude"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
echo -e "${YELLOW}[3/6] Configuring ~/.claude/settings.json ...${RESET}"

mkdir -p "$CLAUDE_DIR"

# Create settings from scratch (or merge with existing)
if [ -f "$CLAUDE_SETTINGS" ]; then
    echo "  → Merging with existing settings..."
    # Backup first
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
else
    echo "  → Creating new settings..."
fi

# Write complete settings.json
cat > "$CLAUDE_SETTINGS" << 'SETTINGS_EOF'
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "Agent",
      "mcp__*"
    ]
  },
  "model": "opus[1m]",
  "skipDangerousModePermissionPrompt": true,
  "cleanupPeriodDays": 0,
  "env": {
    "NEUTRON_ROOT": "___NEUTRON_ROOT___",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_COST_WARNINGS": "1",
    "CLAUDE_CODE_ENABLE_TASKS": "true",
    "BASH_MAX_TIMEOUT_MS": "600000"
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '🟢 NEUTRON EVO OS v4.1.0 active — ∫f(t)dt' && [ -d \"$HOME/.neutron-evo-os\" ] && cat \"$HOME/.neutron-evo-os/SOUL.md\" 2>/dev/null | head -5"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "NEUTRON_ROOT=___NEUTRON_ROOT___ bash -c 'mkdir -p \"$NEUTRON_ROOT/.backup\" && for f in $(echo \"{path}\" | tr \",\" \"\\n\"); do if [ -f \"$f\" ]; then cp \"$f\" \"$NEUTRON_ROOT/.backup/$(basename \"$f\").$(date +%Y%m%d_%H%M%S).bak\" 2>/dev/null; fi; done' 2>/dev/null"
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF

# Replace placeholder with actual path
sed -i "s|___NEUTRON_ROOT___|${NEUTRON_HOME}|g" "$CLAUDE_SETTINGS"

echo -e "${GREEN}[✓] ~/.claude/settings.json configured${RESET}"
echo "     NEUTRON_ROOT=$NEUTRON_HOME"

# =============================================================================
# STEP 3: Create CLAUDE.md in ~/.claude/ (global default for all sessions)
# =============================================================================
echo -e "${YELLOW}[4/6] Creating ~/.claude/CLAUDE.md (global fallback) ...${RESET}"

cat > "$CLAUDE_DIR/CLAUDE.md" << EOF
# NEUTRON EVO OS — Global Context
> ∫f(t)dt — Functional Credibility Over Institutional Inertia

## System Info
- **Version**: 4.1.0
- **NEUTRON_ROOT**: $NEUTRON_HOME
- **Owner**: Adam Wang

## Quick Start
Run any Claude Code session — NEUTRON EVO OS loads automatically.

## Full Context Loading Order
1. SOUL.md       → Identity & ∫f(t)dt philosophy
2. MANIFESTO.md  → Core principles
3. USER.md       → User preferences
4. GOVERNANCE.md → Policy rules
5. RULES.md      → Operating procedures (5-step workflow)
6. WORKFLOW.md   → Task distribution & parallel processing
7. PERFORMANCE_LEDGER.md → Skill CI tracking

## 5-Step Workflow
/explore → /spec → /build → /verify → /ship

## Key Files
- Full context at: $NEUTRON_HOME/
- Global settings: ~/.claude/settings.json
- Daily logs: $NEUTRON_HOME/memory/

*Loaded automatically at session start.*
EOF

echo -e "${GREEN}[✓] ~/.claude/CLAUDE.md created${RESET}"

# =============================================================================
# STEP 4: Create global hook script
# =============================================================================
echo -e "${YELLOW}[5/6] Creating global hook script ...${RESET}"

HOOK_SCRIPT="$NEUTRON_HOME/hooks/session-start.sh"
mkdir -p "$(dirname "$HOOK_SCRIPT")"

cat > "$HOOK_SCRIPT" << 'HOOK_EOF'
#!/usr/bin/env bash
# NEUTRON EVO OS — Session Start Hook
# This script is executed at the start of every Claude Code session

NEUTRON_ROOT="${NEUTRON_ROOT:-$HOME/.neutron-evo-os}"

if [ -d "$NEUTRON_ROOT" ]; then
    echo ""
    echo "🟢 NEUTRON EVO OS v4.1.0 — ∫f(t)dt"
    echo "   Root: $NEUTRON_ROOT"
    echo ""

    # Load key context snippets
    if [ -f "$NEUTRON_ROOT/SOUL.md" ]; then
        head -10 "$NEUTRON_ROOT/SOUL.md"
    fi
else
    echo "⚠️  NEUTRON_ROOT not found: $NEUTRON_ROOT"
    echo "   Run: bash ~/.neutron-evo-os/install-global.sh"
fi
HOOK_EOF

chmod +x "$HOOK_SCRIPT"
echo -e "${GREEN}[✓] Hook script created at $HOOK_SCRIPT${RESET}"

# =============================================================================
# STEP 5: Verify
# =============================================================================
echo -e "${YELLOW}[6/6] Verification ...${RESET}"

ERRORS=0

if [ -f "$CLAUDE_SETTINGS" ]; then
    if grep -q "NEUTRON_ROOT" "$CLAUDE_SETTINGS"; then
        echo -e "  ${GREEN}✓${RESET} settings.json has NEUTRON_ROOT"
    else
        echo -e "  ${RED}✗${RESET} settings.json missing NEUTRON_ROOT"
        ERRORS=$((ERRORS+1))
    fi
fi

if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
    echo -e "  ${GREEN}✓${RESET} ~/.claude/CLAUDE.md exists"
else
    echo -e "  ${RED}✗${RESET} ~/.claude/CLAUDE.md missing"
    ERRORS=$((ERRORS+1))
fi

if [ -d "$NEUTRON_HOME" ]; then
    COUNT=$(ls -1 "$NEUTRON_HOME"/SOUL.md "$NEUTRON_HOME"/MANIFESTO.md "$NEUTRON_HOME"/RULES.md 2>/dev/null | wc -l)
    if [ "$COUNT" -ge 3 ]; then
        echo -e "  ${GREEN}✓${RESET} NEUTRON_ROOT has core files ($COUNT/3+)"
    else
        echo -e "  ${RED}✗${RESET} NEUTRON_ROOT missing core files ($COUNT/3+ found)"
        ERRORS=$((ERRORS+1))
    fi
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗"
echo "║           NEUTRON EVO OS — INSTALL COMPLETE               ║"
echo "╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}What was installed:${RESET}"
echo "  • ~/.claude/settings.json    — Claude Code globally reads NEUTRON context"
echo "  • ~/.claude/CLAUDE.md       — Global fallback context for all sessions"
echo "  • ~/.neutron-evo-os/        — Full NEUTRON EVO OS repo"
echo ""
echo -e "${BOLD}How it works:${RESET}"
echo "  1. ${BOLD}Claude Code starts${RESET} → reads ~/.claude/CLAUDE.md"
echo "  2. ${BOLD}SessionStart hook${RESET} → loads NEUTRON_ROOT context"
echo "  3. ${BOLD}5-step workflow${RESET}   → /explore /spec /build /verify /ship"
echo ""
echo -e "${YELLOW}⚠️  Restart any open Claude Code sessions for changes to take effect.${RESET}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}⚠️  $ERRORS error(s) detected. Please review above.${RESET}"
    exit 1
fi

echo -e "${GREEN}[✓] All systems operational. Ready to build. ∫f(t)dt${RESET}"
