#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NEUTRON EVO OS — Cline Setup Script
# Detects VS Code + Cline, configures MCP server.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

NEUTRON_ROOT="${NEUTRON_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
export NEUTRON_ROOT

echo "╔══════════════════════════════════════════════════════╗"
echo "║  NEUTRON EVO OS — Cline Setup                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Detect Cline (VS Code extension) ─────────────────────────────────────────
# Cline runs as a VS Code extension. MCP config goes in VS Code settings.

CLINE_CONFIG=""
detect_cline() {
    # VS Code settings location (all platforms)
    local cfg_dir=""
    case "$(uname)" in
        Linux|Darwin)
            cfg_dir="$HOME/.config/Code/User"
            ;;
        MINGW*|CYGWIN*|MSYS*)
            cfg_dir="$APPDATA/Code/User"
            ;;
    esac

    if [ -d "$cfg_dir" ]; then
        CLINE_CONFIG="$cfg_dir"
        return 0
    fi
    return 1
}

if ! detect_cline; then
    echo "⚠️  VS Code (required by Cline) not detected."
    echo ""
    echo "  Install VS Code: https://code.visualstudio.com"
    echo "  Then install Cline extension from VS Code marketplace."
    echo ""
    echo "  After VS Code + Cline are installed, run:"
    echo "    bash install-cline.sh"
    exit 1
fi

echo "✅ VS Code detected: $CLINE_CONFIG"

# ── Check Python dependencies ─────────────────────────────────────────────────
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

# ── Detect Cline MCP config location ─────────────────────────────────────────
# Cline v3+ supports MCP via ~/.cline/mcp.json or VS Code settings
CLINE_MCP="$HOME/.cline/mcp.json"

# ── Create MCP config ────────────────────────────────────────────────────────
echo ""
echo "Configuring MCP server for Cline..."

mkdir -p "$(dirname "$CLINE_MCP")"

if [ -f "$CLINE_MCP" ]; then
    echo "  Found existing $CLINE_MCP"
    if grep -q "NEUTRON-EVO-OS" "$CLINE_MCP" 2>/dev/null; then
        echo "  ✅ NEUTRON-EVO-OS already in Cline MCP config"
    else
        echo "  ℹ️  Adding NEUTRON to $CLINE_MCP..."
        # Merge JSON manually (basic approach)
        python3 - "$NEUTRON_ROOT" "$CLINE_MCP" << 'PYEOF'
import json, sys, os, shutil

cfg_path = sys.argv[2]
neutron_root = sys.argv[1]

shutil.copy(cfg_path, cfg_path + ".bak")

with open(cfg_path) as f:
    try:
        cfg = json.load(f)
    except:
        cfg = {"mcpServers": {}}

if "mcpServers" not in cfg:
    cfg["mcpServers"] = {}

cfg["mcpServers"]["NEUTRON-EVO-OS"] = {
    "command": "python3",
    "args": ["-m", "mcp_server", "--transport", "http", "--port", "3100"],
    "env": {"NEUTRON_ROOT": neutron_root}
}

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("  ✅ NEUTRON added to Cline MCP config")
PYEOF
    fi
else
    cat > "$CLINE_MCP" << EOF
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
    echo "  ✅ Created $CLINE_MCP"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Setup complete!                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Next steps:"
echo "  1. Reload VS Code window (Cmd+Shift+P → Reload Window)"
echo "  2. Open Cline → verify NEUTRON-EVO-OS MCP server"
echo "  3. Start MCP server:"
echo "       cd $NEUTRON_ROOT"
echo "       python3 -m mcp_server --transport http --port 3100"
echo ""
echo "  MCP tools available in Cline:"
echo "    neutron_checkpoint, neutron_context, neutron_memory,"
echo "    neutron_workflow, neutron_engine, neutron_audit"
echo ""
