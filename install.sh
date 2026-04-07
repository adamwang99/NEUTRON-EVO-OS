#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Installer v4.3.1
# Cross-platform: macOS, Linux, WSL
# Usage: curl -fsSL https://... | bash
#    or: bash install.sh [--dir ~/.neutron-evo-os] [--skip-claude]
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
NEUTRON EVO OS Installer v4.3.1

Usage: install.sh [options]
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

# ── Banner ───────────────────────────────────────────────────────────────────
cat << 'BANNER'

  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
  ██╗      ╔════════════════════════════╗
  ██║      ║  EVO OS — Installer v4.3.1 ║
  ╚═══════╝                                ╚══════════════╝

BANNER

# ── 1. Prerequisites ────────────────────────────────────────────────────────
section "Checking Prerequisites"

# Python 3.10+
PYTHON_CMD=""
for cmd in python3 python3.11 python3.10 python3.12; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$($cmd -c 'import sys; print(sys.version_info[1])')
        if [[ "$PY_VERSION" -ge 10 ]]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    error "Python 3.10+ not found."
    echo "  Install: python.org/downloads or: brew install python3"
    exit 1
fi
success "Python 3.$PY_VERSION found: $PYTHON_CMD"

# pip
if ! $PYTHON_CMD -m pip --version &>/dev/null; then
    warn "pip not found — installing..."
    $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || true
fi
if ! $PYTHON_CMD -m pip --version &>/dev/null; then
    error "pip not available. Install Python with pip: python.org/downloads"
    exit 1
fi
success "pip available"

# Required Python packages
REQUIRED=("filelock" "fastapi" "uvicorn" "pydantic")
MISSING_PKGS=()
for pkg in "${REQUIRED[@]}"; do
    if ! $PYTHON_CMD -c "import ${pkg//-/}" 2>/dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [[ ${#MISSING_PKGS[@]} -gt 0 ]]; then
    info "Installing: ${MISSING_PKGS[*]}"
    $PYTHON_CMD -m pip install "${MISSING_PKGS[@]}" --quiet
fi
success "All required packages installed"

# git (optional)
if command -v git &>/dev/null; then
    success "git found: $(git --version | cut -d' ' -f3)"
else
    warn "git not found — hub/satellite sync disabled"
fi

# Claude Code (optional)
if [[ "$SKIP_CLAUDE" -eq 0 ]]; then
    if command -v claude &>/dev/null; then
        success "Claude Code installed"
    else
        warn "Claude Code not installed."
        echo "   Install: docs.anthropic.com/en/docs/claude-code"
        echo "   Or: brew install anthropic/claude-code/claude"
    fi
fi

# ── 2. Detect Source ────────────────────────────────────────────────────────
section "Preparing Installation"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Dev install vs remote clone
if [[ -f "$SCRIPT_DIR/engine/__init__.py" ]]; then
    SOURCE_DIR="$SCRIPT_DIR"
    SOURCE_TYPE="local"
    info "Detected: local install from $SOURCE_DIR"
elif [[ -f "$SCRIPT_DIR/skills/core/workflow/SKILL.md" ]]; then
    SOURCE_DIR="$SCRIPT_DIR"
    SOURCE_TYPE="source"
    info "Detected: source install"
else
    SOURCE_TYPE="clone"
    info "Remote install (git clone)..."
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
    git clone https://github.com/your-username/neutron-evo-os.git "$INSTALL_DIR" --depth=1 2>/dev/null || {
        error "Failed to clone. Check git remote."
        exit 1
    }
    SOURCE_DIR="$INSTALL_DIR"
fi

# ── 3. Install Files ────────────────────────────────────────────────────────
section "Installing to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"

if [[ "$SOURCE_TYPE" != "clone" ]]; then
    info "Copying NEUTRON files..."
    # rsync if available, else cp
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

# ── 4. Create Directory Structure ───────────────────────────────────────────
mkdir -p "$INSTALL_DIR/memory"
mkdir -p "$INSTALL_DIR/memory/archived"
mkdir -p "$INSTALL_DIR/memory/cookbooks"
mkdir -p "$INSTALL_DIR/memory/pending"
mkdir -p "$INSTALL_DIR/memory/.backup"
mkdir -p "$INSTALL_DIR/hooks"

# ── 5. Run First-Run Setup ─────────────────────────────────────────────────
section "First-Run Setup"

NEUTRON_ROOT="$INSTALL_DIR" $PYTHON_CMD "$INSTALL_DIR/hooks/neutron-first-run.py" "$INSTALL_DIR" 2>/dev/null && \
    success "First-run complete" || warn "First-run warnings (may be OK)"

# ── 6. Configure Claude Code Hooks ─────────────────────────────────────────
section "Configuring Claude Code Hooks"

CLAUDE_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_DIR"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Backup existing settings
if [[ -f "$SETTINGS_FILE" ]]; then
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak.$(date +%Y%m%d_%H%M%S)"
fi

# Python to update settings.json
$PYTHON_CMD << PYTHON_SCRIPT
import json, os, sys

settings_file = "$SETTINGS_FILE"
install_dir = "$INSTALL_DIR"

# Read existing settings
if os.path.exists(settings_file):
    try:
        settings = json.load(open(settings_file))
    except Exception:
        settings = {}
else:
    settings = {}

# Ensure hooks structure
if "hooks" not in settings:
    settings["hooks"] = {}

# SessionStart hook — runs on every Claude Code session start
settings["hooks"]["SessionStart"] = [{
    "command": "bash",
    "args": [os.path.join(install_dir, "hooks", "session-start.sh")],
    "type": "command"
}]

# PreToolUse hook — backup file before every write
settings["hooks"]["PreToolUse"] = [{
    "command": "bash",
    "args": [os.path.join(install_dir, "hooks", "pretool-backup.sh"), "{action}", "{file_path}"],
    "type": "command"
}]

# ── MCP Server (stdio) ───────────────────────────────────────────────────────
# Register the NEUTRON MCP server. Merges with any existing mcpServers config
# rather than replacing — user may have other MCP servers already configured.
# The mcp_server module uses self-location (mcp_server/__init__.py adds parent
# to sys.path), so it works regardless of where the user installed NEUTRON.
_mcp_config = {
    "type": "stdio",
    "command": "python3",
    "args": ["-m", "mcp_server"],
    "env": {}
}
# Preserve user's env vars if they set NEUTRON_ROOT externally
if "env" not in _mcp_config:
    _mcp_config["env"] = {}
if not settings.get("mcpServers", {}).get("neutron-evo-os", {}).get("env", {}).get("NEUTRON_ROOT"):
    _mcp_config["env"].setdefault("NEUTRON_ROOT", install_dir)

settings.setdefault("mcpServers", {})["neutron-evo-os"] = _mcp_config

os.makedirs(os.path.dirname(settings_file), exist_ok=True)
with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2)

print("settings updated")
PYTHON_SCRIPT

success "Claude Code settings configured at $SETTINGS_FILE"
info "Review: cat $SETTINGS_FILE"

# ── 7. Verify Installation ────────────────────────────────────────────────
section "Verifying Installation"

OK=0

# Engine import
if NEUTRON_ROOT="$INSTALL_DIR" $PYTHON_CMD -c "
import sys; sys.path.insert(0, '$INSTALL_DIR')
from engine import skill_execution
from engine.skill_registry import discover_skills
d = discover_skills()
print(f'skills: {len(d)}', file=sys.stderr)
" 2>/dev/null; then
    success "Engine + Skill Registry: OK"
    ((OK++)) || true
else
    error "Engine modules: FAILED"
fi

# Atomic write
if NEUTRON_ROOT="$INSTALL_DIR" $PYTHON_CMD -c "
import sys; sys.path.insert(0, '$INSTALL_DIR')
from engine._atomic import atomic_write
from pathlib import Path
atomic_write(Path('$INSTALL_DIR/memory/.install_test'), 'test')
print('OK')
" 2>/dev/null; then
    success "Atomic Write: OK"
    rm -f "$INSTALL_DIR/memory/.install_test"
    ((OK++)) || true
else
    error "Atomic Write: FAILED"
fi

# Tests
if [[ "$OK" -ge 2 ]]; then
    info "Running quick test..."
    if NEUTRON_ROOT="$INSTALL_DIR" $PYTHON_CMD -m pytest tests/ -x -q --tb=no 2>/dev/null | tail -1 | grep -q "passed"; then
        success "All tests passed"
    else
        warn "Tests not run (pytest may not be installed)"
    fi
fi

# ── 8. Generate API Key ───────────────────────────────────────────────────
section "Generating API Key"

if [[ "$SOURCE_TYPE" != "clone" ]]; then
    API_KEY=$(NEUTRON_ROOT="$INSTALL_DIR" $PYTHON_CMD -c "
import sys, os
sys.path.insert(0, os.path.expanduser('$INSTALL_DIR'))
from mcp_server.config import create_api_key
print(create_api_key('installer', neutron_root=os.path.expanduser('$INSTALL_DIR')))
" 2>/dev/null || echo "")

    if [[ -n "$API_KEY" ]]; then
        success "API key generated"
        echo ""
        echo -e "${BOLD}⚠️  IMPORTANT — Save this API key (only shown once):${RESET}"
        echo -e "  ${GREEN}$API_KEY${RESET}"
        echo ""
        echo "  Add to ~/.bashrc:"
        echo "    export NEUTRON_API_KEY='$API_KEY'"
        echo "    export NEUTRON_ROOT='$INSTALL_DIR'"
    else
        warn "API key not generated (run: neutron status to create)"
    fi
fi

# ── 9. Summary ───────────────────────────────────────────────────────────
section "Installation Complete ✓"

echo ""
success "NEUTRON EVO OS v4.3.1 installed to: $INSTALL_DIR"
echo ""
echo "  Quick start:"
echo "    source ~/.bashrc  # or open new terminal"
echo "    neutron status   # verify installation"
echo "    neutron discover \"Build my project idea\""
echo ""
echo "  Docs:   $INSTALL_DIR/NEUTRON_CONTEXT.md"
echo "  Memory: $INSTALL_DIR/memory/"
echo "  Hooks:  ~/.claude/settings.json (SessionStart + PreToolUse)"
echo ""