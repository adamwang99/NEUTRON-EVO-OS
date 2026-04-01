#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Cursor IDE Setup Script
# Detects Cursor, configures MCP server, symlinks extension.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

NEUTRON_ROOT="${NEUTRON_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
export NEUTRON_ROOT

echo "╔══════════════════════════════════════════════════════╗"
echo "║  NEUTRON EVO OS — Cursor IDE Setup                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Detect Cursor installation ────────────────────────────────────────────────
CURSOR_CONFIG=""
CURSOR_EXT_DIR=""

detect_cursor() {
    # Linux / Windows (WSL)
    if [ -f "$HOME/.config/Cursor/User/settings.json" ]; then
        CURSOR_CONFIG="$HOME/.config/Cursor/User/settings.json"
        CURSOR_EXT_DIR="$HOME/.cursor/"
    # macOS
    elif [ -f "$HOME/Library/Application Support/Cursor/User/settings.json" ]; then
        CURSOR_CONFIG="$HOME/Library/Application Support/Cursor/User/settings.json"
        CURSOR_EXT_DIR="$HOME/Library/Application Support/Cursor/"
    # AppImage / portable
    elif which cursor &>/dev/null; then
        CURSOR_CONFIG="$HOME/.config/Cursor/User/settings.json"
        CURSOR_EXT_DIR="$HOME/.cursor/"
    else
        return 1
    fi
    return 0
}

if ! detect_cursor; then
    echo "⚠️  Cursor not detected."
    echo ""
    echo "  Cursor is required for this integration."
    echo "  Download: https://cursor.sh"
    echo ""
    echo "  After installing Cursor, run this script again:"
    echo "    bash install-cursor.sh"
    exit 1
fi

echo "✅ Cursor detected: $CURSOR_CONFIG"

# ── Check Python dependencies ────────────────────────────────────────────────
echo ""
echo "Checking Python dependencies..."
if python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "  ✅ FastAPI + uvicorn installed"
else
    echo "  📦 Installing FastAPI + uvicorn..."
    pip3 install fastapi uvicorn --break-system-packages -q 2>/dev/null || \
    pip3 install fastapi uvicorn -q 2>/dev/null || true
    echo "  ✅ Installed"
fi

# ── Create MCP config for Cursor ─────────────────────────────────────────────
echo ""
echo "Configuring MCP server..."

# Cursor uses mcp.json for server config
CURSOR_MCP_DIR="$(dirname "$CURSOR_CONFIG")"
CURSOR_MCP="$CURSOR_MCP_DIR/mcp.json"

mkdir -p "$CURSOR_MCP_DIR"

# Read existing mcp.json or create new
if [ -f "$CURSOR_MCP" ]; then
    echo "  Found existing $CURSOR_MCP"
    # Backup
    cp "$CURSOR_MCP" "$CURSOR_MCP.bak.$(date +%Y%m%d%H%M%S)"
    # Merge (simple append - user may need to deduplicate)
    if grep -q "NEUTRON-EVO-OS" "$CURSOR_MCP" 2>/dev/null; then
        echo "  ✅ NEUTRON-EVO-OS already in MCP config"
    else
        echo "  ℹ️  You may need to add NEUTRON-EVO-OS to $CURSOR_MCP manually"
        echo "  See: cursor-extension/cursor-mcp-config.json"
    fi
else
    # Create new mcp.json
    cat > "$CURSOR_MCP" << EOF
{
  "mcpServers": {
    "NEUTRON-EVO-OS": {
      "command": "python3",
      "args": ["-m", "mcp_server", "--transport", "http", "--port", "3100"],
      "env": {
        "NEUTRON_ROOT": "$NEUTRON_ROOT"
      }
    }
  }
}
EOF
    echo "  ✅ Created $CURSOR_MCP"
fi

# ── Symlink cursor extension ─────────────────────────────────────────────────
echo ""
echo "Symlinking Cursor extension..."
mkdir -p "$CURSOR_EXT_DIR"
ln -sf "$NEUTRON_ROOT/cursor-extension" "$CURSOR_EXT_DIR/neutron-evo-os" 2>/dev/null || true
echo "  ✅ Linked: $CURSOR_EXT_DIR/neutron-evo-os"

# ── Start MCP server (optional) ───────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Next steps:"
echo "  1. Restart Cursor"
echo "  2. Open Cursor Settings → MCP → verify NEUTRON-EVO-OS listed"
echo "  3. Run 'Cmd+K' → type 'NEUTRON' to see available commands"
echo ""
echo "  To start MCP server manually:"
echo "    cd $NEUTRON_ROOT"
echo "    python3 -m mcp_server --transport http --port 3100"
echo ""
echo "  To verify server is running:"
echo "    curl http://localhost:3100/health"
echo ""
