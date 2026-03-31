"""
NEUTRON EVO OS — MCP Resources
NEUTRON memory and system data as MCP resources.
URIs: memory://today | ledger://ci
"""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

_REPO_ROOT = Path(os.environ.get("NEUTRON_ROOT", str(Path(__file__).parent.parent)))
MEMORY_DIR = _REPO_ROOT / "memory"
LEDGER_PATH = _REPO_ROOT / "PERFORMANCE_LEDGER.md"


def list_resources():
    return [
        {
            "uri": "memory://today",
            "name": "Today's Memory Log",
            "description": "The session memory log for today (YYYY-MM-DD.md)",
            "mimeType": "text/markdown",
        },
        {
            "uri": "ledger://ci",
            "name": "CI Performance Ledger",
            "description": "Skill Credibility Index scores and recent activity",
            "mimeType": "text/markdown",
        },
    ]


def read_resource(uri: str) -> dict:
    """Read the resource at the given URI."""
    if uri == "memory://today":
        log_path = MEMORY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            content = log_path.read_text(errors="replace")
        else:
            content = "# No memory log for today\nStart a session to create one."
    elif uri == "ledger://ci":
        if LEDGER_PATH.exists():
            content = LEDGER_PATH.read_text(errors="replace")
        else:
            content = "# Ledger not found\n"
    else:
        content = f"# Unknown resource: {uri}\nSupported: memory://today, ledger://ci"

    # Truncate to avoid huge MCP payloads (MCP has response size limits).
    # Truncate from END so recent entries are preserved (they're at the bottom).
    MAX_LEN = 5000
    if len(content) > MAX_LEN:
        content = content[:MAX_LEN] + "\n\n... (truncated — see memory/YYYY-MM-DD.md for full log)"

    return {
        "contents": [{"uri": uri, "mimeType": "text/markdown", "text": content}]
    }
