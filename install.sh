#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS v4.1.0 — Unified Installer
# ─────────────────────────────────────────────────────────────────────────────
# One script for everything:
#   • CLI only     → bash install.sh cli
#   • CLI + MCP    → bash install.sh mcp    (recommended)
#   • System-wide  → bash install.sh full   (MCP + hooks + all projects)
#   • Interactive  → bash install.sh        (asks what to install)
# ─────────────────────────────────────────────────────────────────────────────
set -e

# ANSI
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
OK="${GREEN}✓${RESET}"; ERR="${RED}✗${RESET}"; WARN="${YELLOW}⚠${RESET}"

info()  { echo -e "${CYAN}[info]${RESET} $1"; }
ok()    { echo -e "${OK} $1"; }
warn()  { echo -e "${WARN} $1"; }
error() { echo -e "${ERR} $1"; exit 1; }

# ── Resolve NEUTRON_ROOT ─────────────────────────────────────────────────────
if [ -n "$NEUTRON_ROOT" ] && [ -d "$NEUTRON_ROOT" ]; then
    NEUTRON_ROOT_DIR="$(realpath "$NEUTRON_ROOT")"
else
    # Detect from this script's location
    SOURCE="${BASH_SOURCE[0]}"
    while [ -L "$SOURCE" ]; do SOURCE="$(readlink -f "$SOURCE")"; done
    NEUTRON_ROOT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
fi

# ── Verify repo ───────────────────────────────────────────────────────────────
check_repo() {
    for f in SOUL.md engine/cli/main.py mcp_server/__init__.py; do
        if [ ! -f "$NEUTRON_ROOT_DIR/$f" ]; then
            error "Not a NEUTRON-EVO-OS repository: $NEUTRON_ROOT_DIR/$f not found"
        fi
    done
}
check_repo

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       NEUTRON EVO OS v4.1.0 — Unified Installer         ║"
echo "║       ∫f(t)dt — Functional Credibility Over Inertia      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  Root: ${BOLD}$NEUTRON_ROOT_DIR${RESET}"
echo ""

# ── Parse mode ────────────────────────────────────────────────────────────────
MODE="${1:-interactive}"
if [ "$MODE" = "cli" ]; then
    MODE_CLI=true; MODE_MCP=false; MODE_FULL=false
elif [ "$MODE" = "mcp" ]; then
    MODE_CLI=true; MODE_MCP=true; MODE_FULL=false
elif [ "$MODE" = "full" ]; then
    MODE_CLI=true; MODE_MCP=true; MODE_FULL=true
elif [ "$MODE" = "interactive" ] || [ "$1" = "" ]; then
    echo "What do you want to install?"
    echo "  [1] CLI only          — neutron command (${BOLD}bash install.sh cli${RESET})"
    echo "  [2] CLI + MCP         — neutron + Claude Code tools (${BOLD}bash install.sh mcp${RESET}) ← recommended"
    echo "  [3] Full system-wide  — MCP + hooks + apply to all projects (${BOLD}bash install.sh full${RESET})"
    echo ""
    echo -n "Select [1/2/3] (default: 2): "
    read -r choice
    case "${choice:-2}" in
        1) MODE_CLI=true; MODE_MCP=false; MODE_FULL=false ;;
        2) MODE_CLI=true; MODE_MCP=true; MODE_FULL=false ;;
        3) MODE_CLI=true; MODE_MCP=true; MODE_FULL=true ;;
        *) MODE_CLI=true; MODE_MCP=true; MODE_FULL=false ;;
    esac
else
    error "Unknown mode: $1. Use: cli | mcp | full | interactive"
fi

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — CLI (always)
# ══════════════════════════════════════════════════════════════════════════════
if $MODE_CLI; then
    echo -e "\n${BOLD}─── Installing NEUTRON CLI ───${RESET}"

    # Detect writable location
    if [ -w /usr/local/bin ] || [ "$(id -u)" = "0" ]; then
        TARGET="/usr/local/bin/neutron"
        TARGET_DIR="/usr/local/bin"
    else
        TARGET="$HOME/.local/bin/neutron"
        TARGET_DIR="$HOME/.local/bin"
        mkdir -p "$TARGET_DIR"
    fi

    # Write wrapper using Python (avoids shell quoting hell)
    python3 - "$TARGET" "$NEUTRON_ROOT_DIR" << 'PYEOF'
import os, sys
target, root = sys.argv[1], sys.argv[2]
# Walk upward to find engine/cli/main.py (robust against symlinks)
import pathlib
p = pathlib.Path(root)
for _ in range(20):  # max 20 levels up
    if (p / "engine" / "cli" / "main.py").exists():
        break
    p = p.parent
wrapper = f"""#!/bin/bash
# NEUTRON CLI — Auto-discovers NEUTRON_ROOT
# Resolved root: {p}
exec python3 "{p}/engine/cli/main.py" "$@"
"""
with open(target, "w") as f:
    f.write(wrapper)
os.chmod(target, 0o755)
print(f"OK: {target}  (NEUTRON_ROOT={p})")
PYEOF

    ok "neutron installed → $TARGET"

    # Warn if PATH issue
    case ":$PATH:" in
        *":$TARGET_DIR:"*) ;;
        *) warn "Add to ~/.bashrc:  export PATH=\"$TARGET_DIR:\$PATH\"" ;;
    esac

    # Quick verify
    if command -v neutron &>/dev/null; then
        echo -n "  Running verify: "
        neutron status 2>/dev/null | head -1 | sed 's/^/→ /' || true
    fi
fi

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — MCP Server
# ══════════════════════════════════════════════════════════════════════════════
if $MODE_MCP; then
    echo -e "\n${BOLD}─── Installing MCP Server ───${RESET}"

    # Check Node.js
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version 2>/dev/null || echo "unknown")
        ok "Node.js found: $NODE_VERSION"
    else
        warn "Node.js not found — Claude Code may not work"
        warn "Install via: curl -fsSL https://fnm.vercel.app/install | bash"
    fi

    # Check Claude Code
    if command -v claude &>/dev/null; then
        ok "Claude Code found"
    else
        warn "Claude Code not in PATH"
    fi

    # Add MCP server
    if command -v claude &>/dev/null; then
        info "Adding MCP server to Claude Code..."
        claude mcp add neutron-evo-os -- python3 -m mcp_server 2>/dev/null && ok "MCP server registered" || {
            # Try user scope if local already exists
            claude mcp add -s user neutron-evo-os -- python3 -m mcp_server 2>/dev/null && ok "MCP server registered (user scope)" || {
                warn "MCP add failed — you may need to add manually:"
                warn '  claude mcp add neutron-evo-os -- python3 -m mcp_server'
            }
        }
    else
        info "Claude Code not found — add MCP manually:"
        info "  claude mcp add neutron-evo-os -- python3 -m mcp_server"
        info "Or copy .mcp.json into project root"
    fi

    # Copy .mcp.json if not already there
    if [ ! -f "$NEUTRON_ROOT_DIR/.mcp.json" ]; then
        cat > "$NEUTRON_ROOT_DIR/.mcp.json" << 'MCPJSON'
{
  "mcpServers": {
    "NEUTRON-EVO-OS": {
      "command": "python3",
      "args": ["-m", "mcp_server"],
      "env": {}
    }
  }
}
MCPJSON
        ok ".mcp.json created"
    else
        ok ".mcp.json already exists"
    fi
fi

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — System-wide (hooks + all projects)
# ══════════════════════════════════════════════════════════════════════════════
if $MODE_FULL; then
    echo -e "\n${BOLD}─── System-wide Setup ───${RESET}"

    CLAUDE_DIR="$HOME/.claude"
    CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
    mkdir -p "$CLAUDE_DIR"

    # 1. Link ~/.neutron-evo-os to this repo
    NEUTRON_HOME="$HOME/.neutron-evo-os"
    if [ -L "$NEUTRON_HOME" ]; then
        EXISTING=$(readlink "$NEUTRON_HOME")
        if [ "$EXISTING" = "$NEUTRON_ROOT_DIR" ]; then
            ok "~/.neutron-evo-os → $NEUTRON_ROOT_DIR"
        else
            warn "~/.neutron-evo-os already points elsewhere: $EXISTING"
        fi
    elif [ -d "$NEUTRON_HOME" ]; then
        warn "$NEUTRON_HOME is a directory (not a symlink) — skipping"
    else
        ln -s "$NEUTRON_ROOT_DIR" "$NEUTRON_HOME"
        ok "~/.neutron-evo-os → $NEUTRON_ROOT_DIR"
    fi

    # 2. Create ~/.claude/CLAUDE.md (global fallback)
    cat > "$CLAUDE_DIR/CLAUDE.md" << EOF
# NEUTRON EVO OS — Global Context
> ∫f(t)dt — Functional Credibility Over Institutional Inertia

## System
- **Version**: 4.1.0
- **NEUTRON_ROOT**: $NEUTRON_ROOT_DIR
- **Owner**: Adam Wang

## Workflow
/explore → /discover → /spec (USER REVIEW) → /build → /accept (USER CONFIRMS) → /ship

## Skills (7 core)
context | memory | workflow | engine | checkpoint | discovery | acceptance_test

## Quick Commands
- neutron status   — System health
- neutron audit    — CI audit (7 skills)
- neutron discover — 12-question interview
- neutron log      — Today's memory

## Full Context
Full files at: $NEUTRON_ROOT_DIR/
*Loaded at every Claude Code session start.*
EOF
    ok "~/.claude/CLAUDE.md created"

    # 3. Setup SessionStart hook
    if [ -f "$CLAUDE_SETTINGS" ]; then
        # Only add hook if not present (preserve all existing settings!)
        if ! grep -q "NEUTRON_ROOT\|NEUTRON-EVO" "$CLAUDE_SETTINGS" 2>/dev/null; then
            # Add NEUTRON_ROOT env if missing
            if ! grep -q "NEUTRON_ROOT" "$CLAUDE_SETTINGS" 2>/dev/null; then
                if command -v jq &>/dev/null; then
                    cp "$CLAUDE_SETTINGS" "$CLAUDE_SETTINGS.backup"
                    jq --arg ROOT "$NEUTRON_ROOT_DIR" \
                       '.env.NEUTRON_ROOT = $ROOT | .env.CLAUDE_CODE_NO_FLICKER //= "1"' \
                       "$CLAUDE_SETTINGS" > "$CLAUDE_SETTINGS.tmp" && mv "$CLAUDE_SETTINGS.tmp" "$CLAUDE_SETTINGS"
                    ok "Added NEUTRON_ROOT to settings.json (jq merge)"
                else
                    warn "jq not found — add NEUTRON_ROOT to ~/.claude/settings.json manually:"
                    warn "  \"NEUTRON_ROOT\": \"$NEUTRON_ROOT_DIR\""
                fi
            fi
        else
            ok "settings.json already has NEUTRON context"
        fi
    else
        # Create minimal settings
        cat > "$CLAUDE_SETTINGS" << EOF
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": ["Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebFetch", "mcp__*"]
  },
  "skipDangerousModePermissionPrompt": true,
  "env": {
    "NEUTRON_ROOT": "$NEUTRON_ROOT_DIR",
    "CLAUDE_CODE_NO_FLICKER": "1"
  }
}
EOF
        ok "Created ~/.claude/settings.json"
    fi

    # 4. Auto-apply to existing projects
    echo -e "\n${BOLD}─── Auto-apply to existing projects ───${RESET}"
    PROJECTS_DIR="$HOME/mnt/data/projects"
    if [ -d "$PROJECTS_DIR" ]; then
        APPLY=0
        for project_dir in "$PROJECTS_DIR"/*/; do
            [ -d "$project_dir" ] || continue
            name=$(basename "$project_dir")
            # Skip NEUTRON-EVO-OS itself
            [ "$name" = "ai-context-master" ] || [ "$name" = "NEUTRON-EVO-OS" ] && continue

            # Only apply if it has CLAUDE.md (is a Claude Code project)
            [ -f "$project_dir/CLAUDE.md" ] || continue

            echo -n "  → $name: "
            mkdir -p "$project_dir/memory/archived" 2>/dev/null || true
            # Copy missing NEUTRON files
            for f in SOUL.md MANIFESTO.md RULES.md PERFORMANCE_LEDGER.md START.md; do
                [ -f "$NEUTRON_ROOT_DIR/$f" ] && [ ! -f "$project_dir/$f" ] && cp "$NEUTRON_ROOT_DIR/$f" "$project_dir/$f"
            done
            echo -e "${OK}applied"
            APPLY=$((APPLY+1))
        done
        [ "$APPLY" -eq 0 ] && echo "  (no other Claude Code projects found)"
    fi
fi

# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗"
echo "║           INSTALL COMPLETE — ∫f(t)dt                              ║"
echo "╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${BOLD}NEUTRON_ROOT:${RESET} $NEUTRON_ROOT_DIR"
echo ""
echo -e "  ${BOLD}Commands:${RESET}"
echo "    neutron status          System health"
echo "    neutron audit           CI audit (7 skills)"
echo "    neutron discover \"...\" Start discovery"
echo "    neutron --help          All 18 commands"
echo ""
echo -e "  ${BOLD}MCP tools (in Claude Code):${RESET}"
echo "    neutron_checkpoint | neutron_context | neutron_discovery"
echo "    neutron_memory | neutron_workflow | neutron_acceptance"
echo "    neutron_engine | neutron_audit | neutron_auto_confirm"
echo ""

if $MODE_FULL; then
    echo -e "  ${YELLOW}⚠  Restart Claude Code sessions for hooks to take effect.${RESET}"
fi

echo -e "${GREEN}[✓] Ready to build. ∫f(t)dt${RESET}"
