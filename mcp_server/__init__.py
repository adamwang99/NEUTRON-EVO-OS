"""
NEUTRON EVO OS — MCP Server
Model Context Protocol server exposing skills as MCP tools, resources, and prompts.

NEUTRON_ROOT is auto-discovered from this file's location (mcp_server/__init__.py).
Parent of mcp_server/ = project root.
"""
import os
import sys
from pathlib import Path

# Self-locate NEUTRON_ROOT from this file's position:
# mcp_server/__init__.py → parent = project root
_NEUTRON_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("NEUTRON_ROOT", str(_NEUTRON_ROOT))
if str(_NEUTRON_ROOT) not in sys.path:
    sys.path.insert(0, str(_NEUTRON_ROOT))

__version__ = "4.1.0"
