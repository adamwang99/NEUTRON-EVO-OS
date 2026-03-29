#!/bin/bash
# Apply NEUTRON EVO OS to current project
# Usage: ./apply-context.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "========================================"
echo "  Apply NEUTRON EVO OS to this project"
echo "========================================"
echo ""

# Copy CLAUDE.md to current directory
echo "[1/1] Copying CLAUDE.md to project..."
cp "$SCRIPT_DIR/CLAUDE.md" "./CLAUDE.md"

if [ $? -eq 0 ]; then
    echo ""
    echo "   SUCCESS! CLAUDE.md has been copied."
    echo "   Claude Sonnet will now read context automatically."
    echo ""
    echo "   Project: $(pwd)"
    echo ""
else
    echo ""
    echo "   ERROR: Failed to copy CLAUDE.md"
    echo ""
fi
