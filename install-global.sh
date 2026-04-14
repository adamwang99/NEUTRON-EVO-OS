#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS v4.3.2 — Global Installer
# Cross-platform: macOS, Linux, WSL
# Purpose: Install NEUTRON to ~/.neutron-evo-os and propagate to all projects
# Usage:   bash install-global.sh [--dir ~/.neutron-evo-os] [--skip-claude]
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
INSTALL_DIR="${NEUTRON_INSTALL_DIR:-$HOME/.neutron-evo-os}"
SKIP_CLAUDE="${NEUTRON_SKIP_CLAUDE:-0}"
FORCE="${NEUTRON_FORCE:-0}"
VERBOSE="${NEUTRON_VERBOSE:-0}"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
section() { echo ""; echo -e "${BOLD}══ $@${RESET}"; }

# ── Parse args ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)         INSTALL_DIR="$2"; shift 2 ;;
        --skip-claude) SKIP_CLAUDE=1; shift ;;
        --force)       FORCE=1; shift ;;
        --verbose)     VERBOSE=1; set -x; shift ;;
        --help|-h)
            cat << 'USAGE'
NEUTRON EVO OS v4.3.2 — Global Installer

Usage: install-global.sh [options]
  --dir DIR             Install to DIR (default: ~/.neutron-evo-os)
  --skip-claude         Skip Claude Code installation check
  --force              Reinstall even if already installed
  --verbose            Verbose output (set -x)
  --help               Show this help

Environment variables:
  NEUTRON_INSTALL_DIR   Override --dir
  NEUTRON_SKIP_CLAUDE    Skip Claude Code check
  NEUTRON_FORCE         Force reinstall
USAGE
            exit 0 ;;
        *) error "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Detect source (local vs clone) ──────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/engine/__init__.py" ]]; then
    SOURCE_DIR="$SCRIPT_DIR"
    SOURCE_TYPE="local"
    info "Detected: local install from $SOURCE_DIR"
elif [[ -f "$SCRIPT_DIR/skills/core/workflow/SKILL.md" ]]; then
    SOURCE_DIR="$SCRIPT_DIR"
    SOURCE_TYPE="source"
    info "Detected: source install from $SOURCE_DIR"
else
    SOURCE_TYPE="clone"
    info "Remote install..."
    if ! command -v git &>/dev/null; then
        error "git required for remote install."
        exit 1
    fi
    if [[ -d "$INSTALL_DIR/.git" ]] && [[ "$FORCE" -eq 0 ]]; then
        success "Already installed at $INSTALL_DIR (use --force to reinstall)"
        exit 0
    fi
    if [[ "$FORCE" -eq 1 && -d "$INSTALL_DIR" ]]; then
        warn "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    fi
    git clone https://github.com/adamwang99/NEUTRON-EVO-OS.git "$INSTALL_DIR" --depth=1 2>/dev/null || \
    git clone git@github.com:adamwang99/NEUTRON-EVO-OS.git "$INSTALL_DIR" --depth=1 || {
        error "Failed to clone. Check git remote."
        exit 1
    }
    SOURCE_DIR="$INSTALL_DIR"
fi

# ── Banner ───────────────────────────────────────────────────────────────────
cat << 'BANNER'

  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
  ██╗      ╔════════════════════════════╗
  ██║      ║  EVO OS — Global Installer v4.3.1 ║
  ╚═══════╝                                ╚══════════════╝
BANNER

# ── 1. Prerequisites ──────────────────────────────────────────────────────────
section "Checking Prerequisites"

if ! command -v python3 &>/dev/null; then
    error "Python 3 not found."
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
    error "Python 3.10+ required, found: $PY_VERSION"
    exit 1
fi
success "Python $PY_VERSION found"

if ! command -v git &>/dev/null; then
    warn "git not found — clone mode will be skipped"
fi

if [[ "$SKIP_CLAUDE" -eq 0 ]] && command -v claude &>/dev/null; then
    CLAUDE_VER=$(claude --version 2>/dev/null | head -1 || echo "unknown")
    success "Claude Code installed: $CLAUDE_VER"
elif [[ "$SKIP_CLAUDE" -eq 0 ]]; then
    warn "Claude Code not found. Install: docs.anthropic.com/en/docs/claude-code"
fi

# ── 2. Install files ───────────────────────────────────────────────────────────
section "Installing to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"

if [[ "$SOURCE_TYPE" != "clone" ]]; then
    info "Copying NEUTRON files..."
    if command -v rsync &>/dev/null; then
        rsync -av --exclude='.git' --exclude='__pycache__' \
            --exclude='*.pyc' --exclude='*.pyo' \
            --exclude='.pytest_cache' \
            "$SOURCE_DIR/" "$INSTALL_DIR/" || true
    else
        cp -r "$SOURCE_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    fi
fi
success "Files installed"

# ── 2b. Make hook scripts executable ─────────────────────────────────────────
for f in "$INSTALL_DIR"/hooks/*.sh; do
    [ -f "$f" ] && chmod +x "$f" 2>/dev/null || true
done

# ── 3. Create directories ─────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR/memory"
mkdir -p "$INSTALL_DIR/memory/archived"
mkdir -p "$INSTALL_DIR/memory/cookbooks"
mkdir -p "$INSTALL_DIR/memory/pending"
mkdir -p "$INSTALL_DIR/memory/.backup"

# ── 4. Configure ~/.claude/settings.json (merge — never overwrite) ──────────────
section "Configuring Claude Code Settings"

CLAUDE_DIR="$HOME/.claude"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
mkdir -p "$CLAUDE_DIR"

# Python block for safe JSON merge — same pattern as install.sh
# Preserves ALL existing settings (mcpServers, permissions, hooks from other tools)
python3 << PYTHON_SCRIPT
import json, os, sys

settings_file = os.environ.get("CLAUDE_SETTINGS", "$CLAUDE_DIR/settings.json")
install_dir = os.environ.get("INSTALL_DIR", "$HOME/.neutron-evo-os")

# Read existing settings (preserve everything)
if os.path.exists(settings_file):
    try:
        settings = json.load(open(settings_file))
    except Exception:
        settings = {}
else:
    settings = {}

# ── Merge env vars ─────────────────────────────────────────────────────────
settings.setdefault("env", {})
env = settings["env"]
# Only set NEUTRON_ROOT if not already present (preserve user's existing value)
if "NEUTRON_ROOT" not in env:
    env["NEUTRON_ROOT"] = install_dir
if "DISABLE_TELEMETRY" not in env:
    env["DISABLE_TELEMETRY"] = "1"
if "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" not in env:
    env["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = "80"

# ── Merge hooks (append if NEUTRON hook not already registered) ─────────────
def _add_hook_if_missing(hook_name, new_entry):
    settings.setdefault("hooks", {}).setdefault(hook_name, [])
    existing_cmds = {
        h.get("command", "")
        for entry in settings["hooks"].get(hook_name, [])
        for h in entry.get("hooks", [])
    }
    if new_entry["hooks"][0]["command"] not in existing_cmds:
        settings["hooks"][hook_name].append(new_entry)

# SessionStart hook
_add_hook_if_missing("SessionStart", {
    "matcher": "",
    "hooks": [{
        "type": "command",
        "command": os.path.join(install_dir, "hooks", "session-start.sh"),
        "args": []
    }]
})

# PreToolUse hook
_add_hook_if_missing("PreToolUse", {
    "matcher": "Edit|Write",
    "hooks": [{
        "type": "command",
        "command": os.path.join(install_dir, "hooks", "pretool-backup.sh"),
        "args": ["{action}", "{file_path}"]
    }]
})

# ── Add MCP server (stdio) if not already present ────────────────────────────
_mcp_config = {
    "type": "stdio",
    "command": "python3",
    "args": ["-m", "mcp_server"],
    "env": {"NEUTRON_ROOT": install_dir}
}
settings.setdefault("mcpServers", {})
if "neutron-evo-os" not in settings["mcpServers"]:
    settings["mcpServers"]["neutron-evo-os"] = _mcp_config

os.makedirs(os.path.dirname(settings_file), exist_ok=True)
with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)

print("settings updated")
PYTHON_SCRIPT

success "Claude Code settings configured (existing keys preserved)"
info "Review: cat $CLAUDE_SETTINGS"

# ── 5. Create .env.local template ───────────────────────────────────────────
section "Environment Setup"
if [[ ! -f "$INSTALL_DIR/.env.local" ]]; then
    cat > "$INSTALL_DIR/.env.local" << 'ENVEOF'
# NEUTRON EVO OS — Local Environment (NEVER commit this file!)
# Copy from .env and fill in your actual values.

# API Configuration
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com/

# Claude Code Settings
DISABLE_TELEMETRY=1
DISABLE_COST_WARNINGS=1
CLAUDE_CODE_ENABLE_TASKS=true
CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80
BASH_MAX_TIMEOUT_MS=600000
ENVEOF
    success ".env.local template created"
    warn "IMPORTANT: Edit $INSTALL_DIR/.env.local with your API keys!"
else
    info ".env.local already exists — skipping"
fi

# ── 6. Propagate to existing Claude Code projects ──────────────────────────────
section "Propagating to Existing Projects"

# Scan for projects in common locations (portable — no hardcoded paths)
SCAN_DIRS=(
    "$HOME/mnt/data/projects"      # Custom mount
    "$HOME/projects"                # Common convention
    "$HOME/code"                    # Common convention
    "$HOME/dev"                    # Common convention
    "$HOME/Projects"               # macOS convention
)

# Files that should exist in every NEUTRON-OS project
NEUTRON_FILES=("SOUL.md" "USER.md" "RULES.md" "PERFORMANCE_LEDGER.md")

PROJECTS_FOUND=0
PROJECTS_UPDATED=0

for scan_dir in "${SCAN_DIRS[@]}"; do
    [[ -d "$scan_dir" ]] || continue
    info "Scanning: $scan_dir"

    # Find directories that are Claude Code projects (have CLAUDE.md)
    # Exclude NEUTRON itself
    for project_dir in "$scan_dir"/*/; do
        [[ -d "$project_dir" ]] || continue

        project_name="$(basename "$project_dir")"

        # Skip NEUTRON itself
        [[ "$project_name" == "ai-context-master" ]] && continue
        [[ "$project_name" == "NEUTRON-EVO-OS" ]] && continue
        [[ "$project_name" == ".neutron-evo-os" ]] && continue

        # Only process if project has a CLAUDE.md (is a Claude Code project)
        [[ -f "$project_dir/CLAUDE.md" ]] || continue

        PROJECTS_FOUND=$((PROJECTS_FOUND + 1))
        info "  Found project: $project_name"

        # Create memory/ directory if missing
        if [[ ! -d "$project_dir/memory" ]]; then
            mkdir -p "$project_dir/memory/archived"
            echo "    + Created memory/ and memory/archived/"
        fi

        # Copy missing NEUTRON files (only if not already present)
        updated=0
        for file in "${NEUTRON_FILES[@]}"; do
            if [[ ! -f "$project_dir/$file" ]]; then
                if [[ -f "$INSTALL_DIR/$file" ]]; then
                    cp "$INSTALL_DIR/$file" "$project_dir/$file"
                    echo "    + Added: $file"
                    updated=1
                fi
            fi
        done

        # Copy .claude/settings.json to project if it has hooks but no MCP server
        if [[ -f "$project_dir/.claude/settings.json" ]]; then
            # Only add MCP server env to project-level settings if missing
            python3 -c "
import json, os
settings_file = os.path.join('$project_dir', '.claude', 'settings.json')
if os.path.exists(settings_file):
    try:
        s = json.load(open(settings_file))
        s.setdefault('env', {})
        if 'NEUTRON_ROOT' not in s['env']:
            s['env']['NEUTRON_ROOT'] = '$INSTALL_DIR'
        with open(settings_file, 'w') as f:
            json.dump(s, f, indent=2)
        print('    + Updated project .claude/settings.json')
    except Exception:
        pass
" 2>/dev/null || true
        fi

        [[ "$updated" -eq 1 ]] && PROJECTS_UPDATED=$((PROJECTS_UPDATED + 1))
    done
done

if [[ "$PROJECTS_FOUND" -eq 0 ]]; then
    info "No existing Claude Code projects found — you'll be prompted on first use"
else
    success "$PROJECTS_FOUND project(s) found, $PROJECTS_UPDATED updated"
fi

# ── 7. Verify & Summary ───────────────────────────────────────────────────────
section "Verifying Installation"

ERRORS=0

if [[ -f "$CLAUDE_SETTINGS" ]] && grep -q "NEUTRON_ROOT" "$CLAUDE_SETTINGS"; then
    success "settings.json has NEUTRON_ROOT"
else
    error "settings.json missing NEUTRON_ROOT"
    ERRORS=$((ERRORS + 1))
fi

if [[ -d "$INSTALL_DIR" ]] && [[ -f "$INSTALL_DIR/engine/__init__.py" ]]; then
    success "NEUTRON_ROOT installed at $INSTALL_DIR"
else
    error "NEUTRON_ROOT install failed"
    ERRORS=$((ERRORS + 1))
fi

if [[ -f "$INSTALL_DIR/hooks/session-start.sh" ]]; then
    success "SessionStart hook installed"
else
    error "SessionStart hook missing"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗"
echo "║         NEUTRON EVO OS v4.3.2 — INSTALL COMPLETE    ║"
echo "╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "  Installed to: $INSTALL_DIR"
echo "  Settings:     $CLAUDE_SETTINGS"
echo ""
echo "  Next steps:"
echo "    • Edit $INSTALL_DIR/.env.local with your API keys"
echo "    • Restart Claude Code sessions"
echo "    • cd to any project and run: claude"
echo ""
if [[ "$ERRORS" -gt 0 ]]; then
    echo -e "${RED}⚠️  $ERRORS error(s). Review above.${RESET}"
    exit 1
fi
echo -e "${GREEN}✓ All systems operational. Ready to build. ∫f(t)dt${RESET}"
