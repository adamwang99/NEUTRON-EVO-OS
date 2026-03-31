#!/bin/bash
# ─────────────────────────────────────────────────────────────
# NEUTRON CLI — Install Script  (DEPRECATED → use install.sh)
# Installs `neutron` command in PATH.
# ─────────────────────────────────────────────────────────────
# NOTE: This script is kept for backward compatibility.
# For CLI + MCP:  bash install.sh mcp
# For everything: bash install.sh full
# ─────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN="$SCRIPT_DIR/engine/cli/main.py"

echo "─────────────────────────────────────────"
echo "  NEUTRON CLI — Install"
echo "─────────────────────────────────────────"

if [ ! -f "$MAIN" ]; then
    echo "ERROR: engine/cli/main.py not found"
    echo "Run this from the NEUTRON project root."
    exit 1
fi

make_executable() {
    local target="$1"
    # Use Python to discover NEUTRON_ROOT and write the wrapper.
    # This avoids all shell quoting/escaping problems.
    python3 - "$target" "$SCRIPT_DIR" << 'PYEOF'
import os, sys, tempfile
target = sys.argv[1]
script_dir = sys.argv[2]

# Walk upward from ~/.local/bin looking for engine/cli/main.py
root = script_dir
while root != "/" and not os.path.exists(os.path.join(root, "engine", "cli", "main.py")):
    root = os.path.dirname(root)

# Write a shell wrapper that passes the discovered root to Python
wrapper = f"""#!/bin/bash
# NEUTRON CLI — Auto-discovers NEUTRON_ROOT via Python
exec python3 "{root}/engine/cli/main.py" "$@"
"""
with open(target, "w") as f:
    f.write(wrapper)
os.chmod(target, 0o755)
print(f"OK: NEUTRON_ROOT={root}", file=sys.stderr)
PYEOF
}

if [ -w /usr/local/bin ] || [ "$(id -u)" = "0" ]; then
    echo "Installing globally to /usr/local/bin..."
    make_executable "/usr/local/bin/neutron"
    echo "Installed: /usr/local/bin/neutron"
else
    echo "Installing locally to ~/.local/bin..."
    mkdir -p "$HOME/.local/bin"
    make_executable "$HOME/.local/bin/neutron"
    echo "Installed: $HOME/.local/bin/neutron"

    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo ""
        echo "NOTE: Add to PATH in ~/.bashrc:"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
    fi
fi

echo ""
echo "Commands:"
echo "  neutron --help               Show all commands"
echo "  neutron status              System status"
echo "  neutron audit               Full CI audit"
echo "  neutron discover \"idea\"    Discovery interview (12 questions)"
echo "  neutron auto full           Skip all gates"
echo "  neutron auto spec_only      SPEC auto-approved only"
echo "  neutron accept pass        User confirms acceptance"
echo "  neutron ship --rating 4   Ship with rating"
echo "  neutron log               Today's memory log"
echo "  neutron decisions          User decisions log"
echo "─────────────────────────────────────────"
