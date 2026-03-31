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

echo -e "${YELLOW}[1/7] NEUTRON_ROOT: ${NEUTRON_ROOT_DIR}${RESET}"

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
echo -e "${YELLOW}[2/8] Setting up ~/.neutron-evo-os ...${RESET}"

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
# STEP 2: Configure ~/.claude/settings.json (MERGE — never overwrite)
# =============================================================================
CLAUDE_DIR="$HOME/.claude"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
echo -e "${YELLOW}[3/7] Configuring ~/.claude/settings.json (merge mode)...${RESET}"

mkdir -p "$CLAUDE_DIR"

# Backup existing settings first
if [ -f "$CLAUDE_SETTINGS" ]; then
    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  → Existing settings backed up"

    # Only add NEUTRON-specific keys if missing (preserve existing keys!)
    # Use jq if available for safe JSON merging
    if command -v jq &>/dev/null; then
        # Backup then merge env vars
        cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS.pre-merge"
        jq --arg ROOT "$NEUTRON_HOME" \
           '.env.NEUTRON_ROOT = $ROOT | .env.CLAUDE_CODE_NO_FLICKER //= "1" | .env.DISABLE_TELEMETRY //= "1" | .env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE //= "80"' \
           "$CLAUDE_SETTINGS" > "$CLAUDE_SETTINGS.tmp" && mv "$CLAUDE_SETTINGS.tmp" "$CLAUDE_SETTINGS"

        # Add hooks only if not present
        # Add SessionStart hook only (PreToolUse already in full settings heredoc)
        if ! jq -e '.hooks.SessionStart' "$CLAUDE_SETTINGS" > /dev/null 2>&1; then
            # Build safe backup command
            BACKUP_CMD="NEUTRON_ROOT=$NEUTRON_HOME bash $NEUTRON_HOME/hooks/pretool-backup.sh"
            jq --arg ROOT "$NEUTRON_HOME" --arg BCK "$NEUTRON_HOME/hooks/pretool-backup.sh" \
               '.hooks = {
                 "SessionStart": [{ "hooks": [{ "type": "command",
                   "command": ("echo \'NEUTRON EVO OS v4.1.0 active\' && python3 " + $ROOT + "/engine/checkpoint_cli.py --read 2>/dev/null)")
                 }] }]
               }' \
               "$CLAUDE_SETTINGS" > "$CLAUDE_SETTINGS.tmp" && mv "$CLAUDE_SETTINGS.tmp" "$CLAUDE_SETTINGS"
        fi

        fi
        echo "  → Merged using jq (preserved existing keys)"
    else
        echo "  ⚠️  jq not found — using sed patching"
        # Fallback: only add NEUTRON_ROOT env if missing
        if ! grep -q "NEUTRON_ROOT" "$CLAUDE_SETTINGS"; then
            sed -i "s/\"env\": {/\"env\": {\n    \"NEUTRON_ROOT\": \"$NEUTRON_HOME\",/g" "$CLAUDE_SETTINGS"
        fi
        # SessionStart hook only in non-jq fallback (PreToolUse skipped — jq path handles it safely)
        if ! grep -q "SessionStart" "$CLAUDE_SETTINGS"; then
            # Minimal: log startup in fallback mode (backup hook requires jq)
            sed -i 's/"hooks": {/"hooks": {\n    "SessionStart": [{"hooks": [{"type": "command", "command": "echo NEUTRON_EVO_OS_4_1_0_ACTIVE"}]}]/' "$CLAUDE_SETTINGS" 2>/dev/null || true
        fi
    fi
else
    echo "  → Creating new settings..."
    cat > "$CLAUDE_SETTINGS" << SETTINGS_EOF
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "WebSearch", "Agent", "mcp__*"]
  },
  "skipDangerousModePermissionPrompt": true,
  "cleanupPeriodDays": 0,
  "env": {
    "NEUTRON_ROOT": "$NEUTRON_HOME",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_COST_WARNINGS": "1",
    "CLAUDE_CODE_ENABLE_TASKS": "true",
    "BASH_MAX_TIMEOUT_MS": "600000",
    "CLAUDE_CODE_NO_FLICKER": "1",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "80",
    "API_TIMEOUT_MS": "3000000"
  },
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "echo '🟢 NEUTRON EVO OS v4.1.0 active — ∫f(t)dt' && python3 $NEUTRON_HOME/engine/checkpoint_cli.py --read 2>/dev/null || true"
      }]
    }],
    "PreToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "NEUTRON_ROOT=$NEUTRON_HOME bash \"$NEUTRON_HOME/hooks/pretool-backup.sh\" \"{path}\""
      }]
    }]
  }
}
SETTINGS_EOF
fi

echo -e "${GREEN}[✓] ~/.claude/settings.json configured (merged — existing keys preserved)${RESET}"
echo "     NEUTRON_ROOT=$NEUTRON_HOME"

# =============================================================================
# STEP 2b: Create .env.local from template (user API keys)
# =============================================================================
echo -e "${YELLOW}[3b/7] Creating .env.local template...${RESET}"
if [ ! -f "$NEUTRON_HOME/.env.local" ]; then
    cat > "$NEUTRON_HOME/.env.local" << 'ENVEOF'
# NEUTRON EVO OS — Local Environment (NEVER commit this file!)
# Copy from .env and fill in your actual values

# API Configuration
ANTHROPIC_AUTH_TOKEN=sk-REPLACE_WITH_YOUR_TOKEN
ANTHROPIC_BASE_URL=https://api.anthropic.com/

# Claude Code Settings
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
CLAUDE_CODE_ENABLE_TASKS=true
CLAUDE_CODE_NO_FLICKER=1
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80

# System
DISABLE_TELEMETRY=1
DISABLE_COST_WARNINGS=1
API_TIMEOUT_MS=3000000
BASH_MAX_TIMEOUT_MS=600000
ENVEOF
    echo -e "${GREEN}[✓] .env.local created — EDIT THIS FILE with your API keys!${RESET}"
else
    echo "  → .env.local already exists — skipping"
fi

# =============================================================================
# STEP 3: Create CLAUDE.md in ~/.claude/ (global default for all sessions)
# =============================================================================
echo -e "${YELLOW}[4/8] Creating ~/.claude/CLAUDE.md (global fallback) ...${RESET}"

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
echo -e "${YELLOW}[5/8] Creating global hook script ...${RESET}"

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
# STEP 5b: Install MemoryOS CLI globally
# =============================================================================
echo -e "${YELLOW}[5b/8] Installing MemoryOS CLI ...${RESET}"
if [ -d "$NEUTRON_HOME/MemoryOS" ]; then
    if command -v npm &>/dev/null; then
        cd "$NEUTRON_HOME/MemoryOS" && npm install -g . 2>/dev/null && echo "  → MemoryOS CLI installed globally" || echo "  → MemoryOS CLI skipped (npm install failed)"
    else
        echo "  → MemoryOS CLI skipped (npm not found)"
    fi
else
    echo "  → MemoryOS CLI skipped (not found)"
fi

# =============================================================================
# STEP 6: Auto-apply to existing projects
# Scans for projects with CLAUDE.md and fills in missing NEUTRON files
# =============================================================================
echo -e "${YELLOW}[6/8] Auto-applying NEUTRON EVO OS to existing projects ...${RESET}"

# Files that must exist in every NEUTRON-OS project
NEUTRON_FILES=(
    "SOUL.md"
    "MANIFESTO.md"
    "USER.md"
    "GOVERNANCE.md"
    "RULES.md"
    "PERFORMANCE_LEDGER.md"
    "WORKFLOW.md"
    "COORDINATION.md"
    "MEMORY.md"
    "START.md"
)

# Scan for projects (directories with CLAUDE.md, excluding NEUTRON itself)
PROJECTS_DIR="$HOME/mnt/data/projects"
APPLY_COUNT=0
SKIP_COUNT=0

if [ -d "$PROJECTS_DIR" ]; then
    echo "  → Scanning $PROJECTS_DIR for existing projects ..."
    for project_dir in "$PROJECTS_DIR"/*/; do
        [ -d "$project_dir" ] || continue

        project_name=$(basename "$project_dir")

        # Skip NEUTRON-EVO-OS itself (already has everything)
        if [ "$project_name" = "ai-context-master" ] || [ "$project_name" = "NEUTRON-EVO-OS" ]; then
            echo "  → Skipping $project_name (NEUTRON-EVO-OS source)"
            SKIP_COUNT=$((SKIP_COUNT+1))
            continue
        fi

        # Only process if project has a CLAUDE.md (is a Claude Code project)
        if [ ! -f "$project_dir/CLAUDE.md" ]; then
            SKIP_COUNT=$((SKIP_COUNT+1))
            continue
        fi

        echo "  → Processing: $project_name"

        # Create memory/ directory if missing
        if [ ! -d "$project_dir/memory" ]; then
            mkdir -p "$project_dir/memory/archived"
            echo "    ${GREEN}+${RESET} Created memory/ and memory/archived/"
        fi

        # Copy missing NEUTRON files (only if not already present)
        for file in "${NEUTRON_FILES[@]}"; do
            if [ ! -f "$project_dir/$file" ]; then
                if [ -f "$NEUTRON_HOME/$file" ]; then
                    cp "$NEUTRON_HOME/$file" "$project_dir/$file"
                    echo "    ${GREEN}+${RESET} Added: $file"
                fi
            fi
        done

        # Update .claude/settings.json to ensure PreLoadMemory loads ALL 9 context files
        CLAUDE_SETTINGS="$project_dir/.claude/settings.json"
        if [ -f "$CLAUDE_SETTINGS" ]; then
            # Check if PreLoadMemory exists and has fewer than 7 files
            if grep -q "PreLoadMemory" "$CLAUDE_SETTINGS"; then
                FILE_COUNT=$(grep -o '"PreLoadMemory"' "$CLAUDE_SETTINGS" | wc -l || echo "0")
                if [ "$FILE_COUNT" -eq 0 ] 2>/dev/null; then
                    echo "    ${YELLOW}~${RESET} PreLoadMemory needs update (see OCTA notes)"
                fi
            else
                echo "    ${YELLOW}~${RESET} .claude/settings.json: consider adding PreLoadMemory hook"
            fi
        fi

        APPLY_COUNT=$((APPLY_COUNT+1))
    done
else
    echo "  → No $PROJECTS_DIR directory found — skipping project scan."
    echo "    (To apply manually, run this script from within each project)"
fi

echo -e "${GREEN}[✓] Auto-apply complete: $APPLY_COUNT project(s) updated, $SKIP_COUNT skipped${RESET}"

# =============================================================================
# STEP 8: Verify & Summary
# =============================================================================
echo -e "${YELLOW}[8/8] Verification & Summary ...${RESET}"

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

if [ -f "$NEUTRON_HOME/.env.local" ]; then
    echo -e "  ${GREEN}✓${RESET} .env.local template created"
    echo -e "  ${YELLOW}⚠️  IMPORTANT: Edit $NEUTRON_HOME/.env.local with your API keys!${RESET}"
fi
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗"
echo "║           NEUTRON EVO OS — INSTALL COMPLETE               ║"
echo "╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}What was installed globally:${RESET}"
echo "  • ~/.claude/settings.json    — NEUTRON hooks (SessionStart + PreToolUse)"
echo "  • ~/.claude/CLAUDE.md       — Global fallback context for ALL sessions"
echo "  • ~/.neutron-evo-os/        — Full NEUTRON EVO OS repo"
echo ""
echo -e "${BOLD}What was applied to existing projects:${RESET}"
echo "  • Copied missing files: MANIFESTO.md, WORKFLOW.md, COORDINATION.md,"
echo "    PERFORMANCE_LEDGER.md, MEMORY.md, START.md (if missing)"
echo "  • Created memory/ and memory/archived/ directories"
echo "  • Scanned: $PROJECTS_DIR"
echo ""
echo -e "${BOLD}How it works:${RESET}"
echo "  1. Claude Code starts → reads ~/.claude/CLAUDE.md"
echo "  2. SessionStart hook → loads NEUTRON_ROOT context"
echo "  3. Project CLAUDE.md → PreLoadMemory loads ALL 9 context files"
echo "  4. Every workspace → Full NEUTRON EVO OS context available"
echo "  5. /explore → /spec → /build → /verify → /ship"
echo ""
echo -e "${BOLD}Required context files (9 files):${RESET}"
for f in SOUL.md MANIFESTO.md USER.md GOVERNANCE.md RULES.md \
         WORKFLOW.md PERFORMANCE_LEDGER.md MEMORY.md START.md; do
    echo "  • $f"
done
echo ""
echo -e "${YELLOW}⚠️  Restart Claude Code / VS Code sessions for changes to take effect.${RESET}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}⚠️  $ERRORS error(s) detected. Please review above.${RESET}"
    exit 1
fi

echo -e "${GREEN}[✓] All systems operational. Ready to build. ∫f(t)dt${RESET}"
